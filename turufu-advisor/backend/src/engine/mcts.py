"""
Information Set Monte Carlo Tree Search (IS-MCTS) for Albastini
===============================================================

Why IS-MCTS and not standard MCTS?
In Albastini, you cannot see your opponent's hand. Standard MCTS assumes
perfect information. IS-MCTS handles this by:

1. DETERMINIZE: Sample a "possible world" — randomly deal unknown cards
   to opponents (respecting void-suit constraints from observed play).
2. SIMULATE: Run a standard MCTS playout on that determinized state.
3. AGGREGATE: Repeat across many determinizations. The move that performs
   best *across all possible worlds* is the mathematically optimal play.

Phase 3 Upgrades:
- CACHED BAYESIAN DETERMINIZATION: Weights computed once per turn, not per sim.
- DYNAMIC ΔP TRICK 12 HEURISTIC: Only lose trick 12 if bottom trump value > trick value.
- ENDGAME MINIMAX HARD FORK: When draw_pile == 0, switch to alpha-beta for perfect play.

Performance notes for M3 Max:
- 36-card deck with 6-card hands = very tractable game tree.
- No follow-suit = higher branching factor but shallower depth.
- M3 Max (36GB): 200 determinizations × 200 sims = 40,000 playouts target.
- Time budget: 300ms hard cap for zero-lag mobile UX.
"""

from __future__ import annotations

import math
import random
import time
from copy import deepcopy
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

from .game_logic import GameState, Card, Trick, TrickPlay
from .minimax import EndgameSolver
from .constants import (
    WIN_THRESHOLD,
    MRITHI_THRESHOLD,
    TOTAL_DECK_POINTS,
    HAND_SIZE,
    BOTTOM_TRUMP_TRIGGER,
)

# ---------------------------------------------------------------------------
# M3 Max Hardware Profile
# ---------------------------------------------------------------------------
M3_MAX_DETERMINIZATIONS = 200
M3_MAX_SIMS_PER_DET = 200
M3_MAX_TIME_LIMIT_MS = 300.0


# ---------------------------------------------------------------------------
# MCTS Node
# ---------------------------------------------------------------------------
@dataclass
class MCTSNode:
    """A node in the search tree."""
    card: Optional[Card] = None       # The move that led to this node
    parent: Optional[MCTSNode] = None
    children: List[MCTSNode] = field(default_factory=list)
    visits: int = 0
    total_reward: float = 0.0
    untried_moves: List[Card] = field(default_factory=list)
    player_id: int = 0

    @property
    def ucb1(self) -> float:
        """Upper Confidence Bound for Trees — balances exploration vs exploitation."""
        if self.visits == 0:
            return float("inf")
        exploitation = self.total_reward / self.visits
        exploration = math.sqrt(2.0 * math.log(self.parent.visits) / self.visits)
        return exploitation + exploration

    def best_child(self) -> MCTSNode:
        """Select child with highest UCB1 score."""
        return max(self.children, key=lambda c: c.ucb1)

    def most_visited_child(self) -> MCTSNode:
        """After search completes, the most robust move is the most visited."""
        return max(self.children, key=lambda c: c.visits)

    def expand(self, card: Card, player_id: int) -> MCTSNode:
        """Create a child node for an untried move."""
        child = MCTSNode(card=card, parent=self, player_id=player_id)
        self.untried_moves.remove(card)
        self.children.append(child)
        return child


# ---------------------------------------------------------------------------
# Heuristic Evaluation
# ---------------------------------------------------------------------------
def evaluate_terminal(state: GameState, maximizing_player: int = 0) -> float:
    """
    Evaluate a completed game state.

    Scoring:
    - Win (61+ points): +1.0
    - Win with Mrithi (opponent < 10 points): +2.0
    - Loss: -1.0
    - Loss with Mrithi (user < 10 points): -2.0
    - Draw-ish (neither at 61): proportional score based on point lead
    """
    user = state.players[maximizing_player]
    best_opponent_pts = max(
        p.points_captured for p in state.players if p.player_id != maximizing_player
    )

    if user.points_captured >= WIN_THRESHOLD:
        # Check for Mrithi — can we skunk them?
        if state.num_players == 2 and best_opponent_pts < MRITHI_THRESHOLD:
            return 2.0  # Double victory points
        return 1.0

    if best_opponent_pts >= WIN_THRESHOLD:
        if state.num_players == 2 and user.points_captured < MRITHI_THRESHOLD:
            return -2.0  # We got skunked
        return -1.0

    # Mid-game heuristic: normalized point advantage
    point_diff = user.points_captured - best_opponent_pts
    return point_diff / TOTAL_DECK_POINTS


def evaluate_state(state: GameState, maximizing_player: int = 0) -> float:
    """
    Non-terminal state evaluation for early cutoff in deep simulations.
    Combines current score advantage with Mrithi opportunity and
    the DYNAMIC ΔP Trick 12 Bottom Trump heuristic.
    """
    user = state.players[maximizing_player]
    opponents = [p for p in state.players if p.player_id != maximizing_player]
    best_opp = max(opponents, key=lambda p: p.points_captured)

    points_remaining = TOTAL_DECK_POINTS - sum(p.points_captured for p in state.players)

    # Base score: normalized point lead
    score = (user.points_captured - best_opp.points_captured) / TOTAL_DECK_POINTS

    # Bonus: if we're on track for 61+ points
    if user.points_captured >= WIN_THRESHOLD:
        score += 0.5

    # Mrithi bonus: if opponent is below 10 and few points remain
    if (
        state.num_players == 2
        and best_opp.points_captured < MRITHI_THRESHOLD
        and points_remaining < 30
    ):
        skunk_feasibility = 1.0 - (best_opp.points_captured / MRITHI_THRESHOLD)
        score += 0.3 * skunk_feasibility

    # --- DYNAMIC ΔP TRICK 12 BOTTOM TRUMP HEURISTIC ---
    # When draw_pile == 2, the loser of this trick gets the bottom trump.
    # Only recommend losing if: ΔP = P_bottom_trump - P_trick_loss > 0
    if (
        state.draw_pile_size == BOTTOM_TRUMP_TRIGGER
        and state.bottom_trump_card is not None
    ):
        bottom_value = state.bottom_trump_card.points  # 0-11
        # Estimate trick value from cards already on the table
        trick_value = state.current_trick.points if state.current_trick.plays else 0
        delta_p = bottom_value - trick_value

        if delta_p > 0:
            # Worth losing this trick to get the bottom trump
            # Scale bonus by how much better the bottom trump is
            score += 0.15 * (delta_p / 11.0)

    return score


def _heuristic_pick(moves: list, state: GameState, player_id: int) -> Card:
    """
    Smart rollout card selection — not random, not exhaustive.
    
    Albastini strategy principles:
    - LEADING: Play LOW cards to bait opponent into wasting value
    - FOLLOWING (can win): Play CHEAPEST winner to save big guns
    - FOLLOWING (can't win): Dump lowest-value card (don't waste points)
    - TRUMP CONSERVATION: Only trump when pot value justifies it
    - ACE HOLDING: Save Aces/7s to capture opponent's big tricks
    """
    trump = state.trump_suit
    trick = state.current_trick
    is_leading = len(trick.plays) == 0
    
    if is_leading:
        # --- LEADING STRATEGY ---
        # Play LOW value non-trump cards to bait opponent
        # Save trumps and high cards for capturing
        non_trump = [c for c in moves if c.suit != trump]
        pool = non_trump if non_trump else moves
        
        # Prefer low-point, low-power cards when leading
        return min(pool, key=lambda c: (c.points * 10 + c.power))
    
    else:
        # --- FOLLOWING STRATEGY ---
        lead_card = trick.plays[0].card
        lead_suit = lead_card.suit
        pot_value = trick.points  # Points currently on the table
        
        # Cards that can WIN this trick
        winners = []
        losers = []
        for c in moves:
            # Check if this card would beat the current best
            test_trick = Trick()
            for tp in trick.plays:
                test_trick.plays.append(tp)
            test_trick.plays.append(TrickPlay(player_id, c))
            if test_trick.winner(trump) == player_id:
                winners.append(c)
            else:
                losers.append(c)
        
        if winners:
            # Can win — but should we?
            if pot_value >= 4:
                # Pot is worth winning — use CHEAPEST winner
                return min(winners, key=lambda c: (c.points * 10 + c.power))
            else:
                # Low-value pot — only win if we can use a zero-point card
                cheap_winners = [c for c in winners if c.points == 0]
                if cheap_winners:
                    return min(cheap_winners, key=lambda c: c.power)
                # Otherwise dump a loser to save our good cards
                if losers:
                    return min(losers, key=lambda c: (c.points * 10 + c.power))
                return min(winners, key=lambda c: (c.points * 10 + c.power))
        else:
            # Can't win — dump lowest value card
            return min(losers, key=lambda c: (c.points * 10 + c.power))


def smart_playout(state: GameState, maximizing_player: int = 0) -> float:
    """
    Play the game to completion with heuristic moves (not random).
    Returns the heuristic evaluation of the terminal state.
    """
    sim = deepcopy(state)
    max_moves = 100  # Safety valve

    for _ in range(max_moves):
        if sim.game_over:
            break

        player_id = sim.turn_index
        moves = sim.get_valid_moves(player_id)

        if not moves:
            # If a player has no cards and draw pile is empty, skip
            if sim.draw_pile_size == 0:
                # Check if ALL players are out of cards
                if all(len(p.hand) == 0 for p in sim.players):
                    sim.game_over = True
                    break
                sim.turn_index = (sim.turn_index + 1) % sim.num_players
                continue
            break

        card = _heuristic_pick(moves, sim, player_id)
        sim.play_card(player_id, card)

    return evaluate_terminal(sim, maximizing_player)


# ---------------------------------------------------------------------------
# IS-MCTS Engine with Endgame Minimax Hard Fork
# ---------------------------------------------------------------------------
class ISMCTSEngine:
    """
    Information Set Monte Carlo Tree Search engine for Albastini.

    Phase 3 architecture:
    - draw_pile > 0: IS-MCTS with cached Bayesian determinization
    - draw_pile == 0: Alpha-Beta Minimax (perfect information solver)
    """

    def __init__(
        self,
        num_determinizations: int = M3_MAX_DETERMINIZATIONS,
        simulations_per_det: int = M3_MAX_SIMS_PER_DET,
        time_limit_ms: float = M3_MAX_TIME_LIMIT_MS,
    ):
        self.num_determinizations = num_determinizations
        self.simulations_per_det = simulations_per_det
        self.time_limit_ms = time_limit_ms
        self.endgame_solver = EndgameSolver()

    def find_best_move(self, game_state: GameState) -> Dict:
        """
        Run the appropriate solver and return the best card to play.

        HARD FORK:
        - draw_pile > 0 → IS-MCTS with Bayesian determinization
        - draw_pile == 0 → Alpha-Beta Minimax (exact solve)
        """
        if game_state.turn_index != 0:
            return {"best_card": None, "win_probability": 0.0, "simulations_run": 0}

        user_hand = game_state.get_valid_moves(0)
        if not user_hand:
            return {"best_card": None, "win_probability": 0.0, "simulations_run": 0}

        if len(user_hand) == 1:
            return {
                "best_card": user_hand[0],
                "win_probability": 1.0,
                "simulations_run": 0,
                "all_moves": [{"card": user_hand[0].to_dict(), "visits": 1, "avg_reward": 0}],
                "mrithi_viable": False,
                "solver": "forced",
            }

        # ── HARD FORK: Perfect Information → Minimax ──
        if game_state.draw_pile_size == 0:
            return self.endgame_solver.solve(game_state)

        # ── Imperfect Information → IS-MCTS ──
        return self._run_ismcts(game_state, user_hand)

    def _run_ismcts(self, game_state: GameState, user_hand: List[Card]) -> Dict:
        """
        IS-MCTS with cached Bayesian determinization.
        Weights are computed ONCE here, then passed to every determinization.
        """
        # ── PRE-COMPUTE Bayesian weights (cached for all determinizations) ──
        cached_weights = game_state.compute_bayesian_weights()

        # Aggregate results across all determinizations
        move_scores: Dict[Card, List[float]] = {card: [] for card in user_hand}
        move_visits: Dict[Card, int] = {card: 0 for card in user_hand}
        total_sims = 0
        det_count = 0
        start_time = time.time()

        for det_idx in range(self.num_determinizations):
            # Check time budget
            elapsed_ms = (time.time() - start_time) * 1000
            if elapsed_ms > self.time_limit_ms:
                break

            # Create determinized state with CACHED weights
            det_state = game_state.create_determinization(cached_weights)
            det_count += 1

            # Run MCTS on this determinized state
            root = MCTSNode(
                untried_moves=list(user_hand),
                player_id=0,
            )

            sims_remaining = self.simulations_per_det
            while sims_remaining > 0:
                elapsed_ms = (time.time() - start_time) * 1000
                if elapsed_ms > self.time_limit_ms:
                    break

                sim_state = deepcopy(det_state)
                node = root

                # SELECT — walk down tree using UCB1
                while not node.untried_moves and node.children:
                    node = node.best_child()
                    sim_state.play_card(node.player_id, node.card)

                # EXPAND — add one new child node
                if node.untried_moves:
                    card = random.choice(node.untried_moves)
                    child = node.expand(card, player_id=0)
                    sim_state.play_card(0, card)
                    node = child

                # ROLLOUT — random playout to terminal state
                reward = smart_playout(sim_state, maximizing_player=0)

                # BACKPROPAGATE — update all ancestors
                while node is not None:
                    node.visits += 1
                    node.total_reward += reward
                    node = node.parent

                sims_remaining -= 1
                total_sims += 1

            # Aggregate results from this determinization
            for child in root.children:
                if child.card in move_scores:
                    avg = child.total_reward / max(child.visits, 1)
                    move_scores[child.card].append(avg)
                    move_visits[child.card] += child.visits

        # Find the move with the best average reward across determinizations
        best_card = max(
            move_scores.keys(),
            key=lambda c: (
                sum(move_scores[c]) / max(len(move_scores[c]), 1)
            ),
        )

        best_avg = sum(move_scores[best_card]) / max(len(move_scores[best_card]), 1)

        # Build ranked move list for the frontend
        all_moves = []
        for card in user_hand:
            scores = move_scores[card]
            avg = sum(scores) / max(len(scores), 1) if scores else 0
            all_moves.append({
                "card": card.to_dict(),
                "visits": move_visits[card],
                "avg_reward": round(avg, 4),
            })
        all_moves.sort(key=lambda m: m["avg_reward"], reverse=True)

        # Evaluate Mrithi viability
        mrithi_viable = (
            game_state.num_players == 2
            and game_state.players[1].points_captured < MRITHI_THRESHOLD
        )

        # Convert reward to a pseudo-probability (normalized to 0–1)
        win_prob = max(0.0, min(1.0, (best_avg + 2.0) / 4.0))

        return {
            "best_card": best_card,
            "win_probability": round(win_prob, 4),
            "simulations_run": total_sims,
            "determinizations_completed": det_count,
            "all_moves": all_moves,
            "mrithi_viable": mrithi_viable,
            "solver": "ismcts",
        }
