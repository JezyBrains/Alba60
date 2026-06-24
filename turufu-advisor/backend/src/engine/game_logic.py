"""
Albastini Game Logic
====================
Core data structures and game state management for the 36-card
Tanzanian trick-taking card game.

Key design decisions:
- Cards are frozen dataclasses for hashability (used in sets for O(1) lookup).
- GameState is fully mutable and tracks everything the IS-MCTS engine needs:
  known hands, played cards, remaining deck, running scores, void-suit inference.
- No follow-suit rule: every card in hand is always a legal move.
  This dramatically increases the branching factor but simplifies get_valid_moves().
- The draw-back-to-6 mechanic means the game has variable-length phases:
  a "draw phase" (deck has cards) and an "endgame phase" (hands drain to 0).
- The dealer (opponent, player 1) ALWAYS leads the first trick.
- After a trick, the winner draws first, then the loser. Winner leads next.
"""

from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict, Tuple

from .constants import (
    VALID_RANKS,
    VALID_SUITS,
    POINT_VALUES,
    POWER_RANKING,
    HAND_SIZE,
    WIN_THRESHOLD,
    MRITHI_THRESHOLD,
    TOTAL_DECK_POINTS,
    DEFAULT_PLAYERS,
    DEALER_PLAYER_ID,
)


# ---------------------------------------------------------------------------
# Card
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Card:
    """
    Immutable card representation. Frozen for use as dict keys and set members.
    """
    suit: str
    rank: str

    @property
    def points(self) -> int:
        return POINT_VALUES[self.rank]

    @property
    def power(self) -> int:
        return POWER_RANKING[self.rank]

    def __repr__(self) -> str:
        symbols = {"SPADES": "♠", "HEARTS": "♥", "DIAMONDS": "♦", "CLUBS": "♣"}
        return f"{self.rank}{symbols.get(self.suit, self.suit)}"

    def to_dict(self) -> dict:
        return {"suit": self.suit, "rank": self.rank, "points": self.points}


# ---------------------------------------------------------------------------
# Deck Factory
# ---------------------------------------------------------------------------
def create_deck() -> List[Card]:
    """Generate the full 36-card Albastini deck."""
    return [Card(suit=s, rank=r) for s in VALID_SUITS for r in VALID_RANKS]


# ---------------------------------------------------------------------------
# Trick (a single round of plays)
# ---------------------------------------------------------------------------
@dataclass
class TrickPlay:
    """One card played in a trick, tagged with who played it."""
    player_id: int
    card: Card


@dataclass
class Trick:
    """
    A single trick — one card per player.
    The first card played sets the led suit.
    """
    plays: List[TrickPlay] = field(default_factory=list)

    @property
    def led_suit(self) -> Optional[str]:
        return self.plays[0].card.suit if self.plays else None

    @property
    def points(self) -> int:
        return sum(p.card.points for p in self.plays)

    def is_complete(self, num_players: int) -> bool:
        return len(self.plays) >= num_players

    def winner(self, trump_suit: str) -> int:
        """
        Resolve trick winner using Albastini rules:
        1. Highest trump card wins.
        2. If no trumps, highest power card of the led suit wins.
        """
        if not self.plays:
            raise ValueError("Cannot resolve an empty trick")

        best_play = self.plays[0]
        led = self.led_suit

        for play in self.plays[1:]:
            card = play.card
            best = best_play.card

            # Case 1: Current card is trump
            if card.suit == trump_suit:
                if best.suit != trump_suit:
                    # Trump beats non-trump always
                    best_play = play
                elif card.power > best.power:
                    # Higher trump beats lower trump
                    best_play = play

            # Case 2: Current card follows led suit, best is NOT trump
            elif card.suit == led and best.suit != trump_suit:
                if best.suit != led:
                    # Led suit beats off-suit (when no trump in play)
                    best_play = play
                elif card.power > best.power:
                    # Higher led-suit card wins
                    best_play = play

            # Case 3: Off-suit, non-trump — never wins

        return best_play.player_id


# ---------------------------------------------------------------------------
# Player State
# ---------------------------------------------------------------------------
@dataclass
class Player:
    """
    Tracks a single player's known state.
    For the human user (player 0), hand is fully known.
    For opponents, hand is unknown but void_suits narrows IS-MCTS sampling.
    """
    player_id: int
    hand: Set[Card] = field(default_factory=set)
    actual_hand_size: int = 0
    tricks_won: int = 0
    points_captured: int = 0
    void_suits: Set[str] = field(default_factory=set)

    def add_points(self, pts: int) -> None:
        self.points_captured += pts

    def has_won(self) -> bool:
        return self.points_captured >= WIN_THRESHOLD

    def is_skunked(self) -> bool:
        """True if this player is below the Mrithi threshold."""
        return self.points_captured < MRITHI_THRESHOLD


# ---------------------------------------------------------------------------
# Game State
# ---------------------------------------------------------------------------
class GameState:
    """
    Complete Albastini game state — the single source of truth.

    Architecture notes:
    - `draw_pile`: Cards remaining to be drawn (face-down, unknown order).
    - `remaining_unknown`: Cards that haven't been seen by the user.
      This is the sample space for IS-MCTS determinizations.
    - `played_cards`: All cards that have been played (perfect memory).
    - `current_trick`: The in-progress trick being built.
    """

    def __init__(self, num_players: int = DEFAULT_PLAYERS):
        self.num_players = num_players
        self.players: List[Player] = [Player(i) for i in range(num_players)]
        self.trump_suit: Optional[str] = None

        # Card tracking
        self.draw_pile: List[Card] = []       # Ordered draw pile (shuffled)
        self.played_cards: Set[Card] = set()  # All cards played across all tricks
        self.remaining_unknown: Set[Card] = set()  # Cards user hasn't seen

        # Trick state
        self.current_trick: Trick = Trick()
        self.tricks_history: List[Trick] = []
        self.current_leader: int = 0  # Who leads the current trick
        self.turn_index: int = 0      # Whose turn it is right now

        # Game phase
        self.game_over: bool = False
        self.round_number: int = 0
        self.user_draw_pending: bool = False  # True when user must register a drawn card

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------
    def initialize(
        self,
        trump_suit: str,
        user_hand: List[Card],
        num_players: int = DEFAULT_PLAYERS,
    ) -> None:
        """
        Set up a new game round.
        - trump_suit: The Turufu suit for this round.
        - user_hand: The 6 cards the human user was dealt.
        - The dealer (opponent, player 1) ALWAYS leads the first trick.
        """
        self.num_players = num_players
        self.players = [Player(i) for i in range(num_players)]
        self.trump_suit = trump_suit
        self.game_over = False
        self.round_number = 0

        # Build full deck and remove user's known hand
        full_deck = set(create_deck())
        user_cards = set(user_hand)
        self.players[0].hand = user_cards

        for p in self.players:
            p.actual_hand_size = HAND_SIZE

        # Everything else is unknown to the user
        self.remaining_unknown = full_deck - user_cards
        self.played_cards = set()
        self.current_trick = Trick()
        self.tricks_history = []

        # Dealer (opponent) leads the first trick
        self.current_leader = DEALER_PLAYER_ID
        self.turn_index = DEALER_PLAYER_ID

        # The draw pile is the remaining cards after all initial hands dealt
        # We don't know opponent hands, but we know deck_size - (hand_size * num_players) remain
        cards_in_hands = HAND_SIZE * num_players
        self.draw_pile_size = len(full_deck) - cards_in_hands

    def register_bidding_swap(
        self, cards_given: List[Card], cards_received: List[Card]
    ) -> None:
        """
        After the bidding phase (Ngarasha swap), update the user's hand
        and the engine's knowledge of which cards are still in play.
        """
        user = self.players[0]

        # Remove given cards from user's hand
        for card in cards_given:
            user.hand.discard(card)
            # These cards go to the opponent — they are now "known to exist in opponent hands"
            # but we don't know WHICH opponent, so they stay in remaining_unknown

        # Add received cards to user's hand
        for card in cards_received:
            user.hand.add(card)
            self.remaining_unknown.discard(card)  # No longer unknown

    # ------------------------------------------------------------------
    # Card Play
    # ------------------------------------------------------------------
    def play_card(self, player_id: int, card: Card) -> Optional[Dict]:
        """
        Register a card being played.
        Returns a dict with trick result if the trick is now complete, else None.
        """
        # Update card tracking
        self.played_cards.add(card)
        self.remaining_unknown.discard(card)

        if card in self.players[player_id].hand:
            self.players[player_id].hand.discard(card)
            
        self.players[player_id].actual_hand_size -= 1

        # Add to current trick
        self.current_trick.plays.append(TrickPlay(player_id, card))

        # Check if trick is complete
        if self.current_trick.is_complete(self.num_players):
            return self._resolve_trick()

        # Advance turn
        self.turn_index = (self.turn_index + 1) % self.num_players
        return None

    def _resolve_trick(self) -> Dict:
        """
        Determine trick winner, award points, handle draw phase, advance state.
        """
        trick = self.current_trick
        winner_id = trick.winner(self.trump_suit)
        points_won = trick.points

        # Award points
        winner = self.players[winner_id]
        winner.add_points(points_won)
        winner.tricks_won += 1

        # Archive trick
        self.tricks_history.append(trick)

        # Handle draw-back-to-6: WINNER draws first, then LOSER
        loser_id = 1 - winner_id  # 2-player: other player is the loser
        draw_order = [winner_id, loser_id]

        cards_drawn = 0
        user_drew = 0
        if self.draw_pile_size > 0:
            for pid in draw_order:
                player = self.players[pid]
                cards_to_draw = HAND_SIZE - player.actual_hand_size
                actual_draw = min(cards_to_draw, self.draw_pile_size)
                self.draw_pile_size -= actual_draw
                player.actual_hand_size += actual_draw
                cards_drawn += actual_draw
                if pid == 0:
                    user_drew = actual_draw
                # For user (player 0), drawn cards will be registered via API
                # For opponents, cards remain in remaining_unknown
            # Only require draw registration if the user actually drew cards
            if user_drew > 0:
                self.user_draw_pending = True

        # Prepare next trick
        self.current_trick = Trick()
        self.current_leader = winner_id
        self.turn_index = winner_id
        self.round_number += 1

        # Check game end: all cards played and all hands empty
        if self.draw_pile_size == 0 and all(p.actual_hand_size == 0 for p in self.players):
            self.game_over = True

        return self._build_trick_result(winner_id, points_won)

    def _build_trick_result(self, winner_id: int, points_won: int) -> Dict:
        """Build a rich result object for the frontend."""
        scores = {p.player_id: p.points_captured for p in self.players}
        return {
            "trick_winner": winner_id,
            "points_won": points_won,
            "scores": scores,
            "game_over": self.game_over,
            "mrithi_status": self._evaluate_mrithi(),
            "win_status": self._evaluate_win(),
        }

    # ------------------------------------------------------------------
    # User draws new cards (after a trick, during draw phase)
    # ------------------------------------------------------------------
    def register_user_draw(self, cards: List[Card]) -> None:
        """When the user draws new cards, update their known hand.
        
        Raises ValueError if a card has already been played (impossible draw)
        or if the card is already in the user's hand (duplicate entry).
        """
        for card in cards:
            if card in self.played_cards:
                raise ValueError(
                    f"Invalid draw: {card} was already played this game. "
                    f"Please check the card you entered."
                )
            if card in self.players[0].hand:
                raise ValueError(
                    f"Invalid draw: {card} is already in your hand."
                )
            self.players[0].hand.add(card)
            self.remaining_unknown.discard(card)
        # Draw phase complete — advice can now run again
        self.user_draw_pending = False

    # ------------------------------------------------------------------
    # Win / Mrithi Evaluation
    # ------------------------------------------------------------------
    def _evaluate_win(self) -> Dict:
        """Check if any player has crossed the 61-point threshold.

        Edge case: 60:60 split — no one wins this round (standard Albastini
        rule: the round is a tie, neither player scores VP for it).
        """
        for p in self.players:
            if p.has_won():
                return {"winner": p.player_id, "points": p.points_captured, "tie": False}

        # Tie check: all cards played and scores split exactly (60:60 in 2-player)
        if self.game_over:
            scores = [p.points_captured for p in self.players]
            if len(set(scores)) == 1:
                return {"winner": None, "tie": True,
                        "scores": {p.player_id: p.points_captured for p in self.players}}

        return {"winner": None, "tie": False}

    def _evaluate_mrithi(self) -> Dict:
        """
        Evaluate Mrithi (skunk) status for the 2-player case.
        Returns info about whether a 2-VP victory is achievable or threatened.
        """
        if self.num_players != 2:
            return {"applicable": False}

        user = self.players[0]
        opponent = self.players[1]

        points_remaining = TOTAL_DECK_POINTS - user.points_captured - opponent.points_captured
        opponent_max_possible = opponent.points_captured + points_remaining

        return {
            "applicable": True,
            "user_points": user.points_captured,
            "opponent_points": opponent.points_captured,
            "points_remaining_in_game": points_remaining,
            "opponent_skunked": opponent.is_skunked() and self.game_over,
            "skunk_possible": opponent_max_possible < MRITHI_THRESHOLD
                              if not self.game_over else False,
            "skunk_threatened": user.points_captured < MRITHI_THRESHOLD,
        }

    # ------------------------------------------------------------------
    # IS-MCTS Support Methods
    # ------------------------------------------------------------------
    def get_valid_moves(self, player_id: int) -> List[Card]:
        """
        In Albastini, there is NO follow-suit requirement.
        Every card in the player's hand is always a legal move.
        """
        return list(self.players[player_id].hand)

    def get_information_set(self) -> Dict:
        """
        Returns the information visible to the user (player 0) for IS-MCTS.
        This is the "information set" — everything the user knows for certain.
        """
        return {
            "user_hand": list(self.players[0].hand),
            "trump_suit": self.trump_suit,
            "played_cards": list(self.played_cards),
            "remaining_unknown": list(self.remaining_unknown),
            "scores": {p.player_id: p.points_captured for p in self.players},
            "current_trick": [
                {"player": tp.player_id, "card": tp.card.to_dict()}
                for tp in self.current_trick.plays
            ],
            "opponent_void_suits": {
                p.player_id: list(p.void_suits)
                for p in self.players if p.player_id != 0
            },
            "draw_pile_size": self.draw_pile_size,
            "tricks_won": {p.player_id: p.tricks_won for p in self.players},
        }

    def create_determinization(self) -> GameState:
        """
        Create a "possible world" for IS-MCTS by randomly dealing
        the unknown cards to opponents, respecting void-suit constraints.
        This is the key operation in Information Set MCTS.
        """
        det = deepcopy(self)

        # Collect all unknown cards
        unknown = list(det.remaining_unknown)
        random.shuffle(unknown)

        # Deal cards to opponents respecting void suits and hand size
        for player in det.players:
            if player.player_id == 0:
                continue  # User's hand is known

            # Cards this opponent could hold (not void in any suit they've shown void in)
            eligible = [c for c in unknown if c.suit not in player.void_suits]
            cards_needed = player.actual_hand_size - len(player.hand)
            cards_needed = max(0, min(cards_needed, len(eligible)))

            dealt = eligible[:cards_needed]
            player.hand = player.hand.union(dealt)

            for c in dealt:
                unknown.remove(c)

        return det

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------
    def to_snapshot(self) -> Dict:
        """Full state snapshot for frontend sync."""
        return {
            "trump_suit": self.trump_suit,
            "turn_index": self.turn_index,
            "round_number": self.round_number,
            "game_over": self.game_over,
            "draw_pile_size": self.draw_pile_size,
            "user_hand": [c.to_dict() for c in sorted(
                self.players[0].hand, key=lambda c: (c.suit, -c.power)
            )],
            "scores": {p.player_id: p.points_captured for p in self.players},
            "tricks_won": {p.player_id: p.tricks_won for p in self.players},
            "current_trick": [
                {"player": tp.player_id, "card": tp.card.to_dict()}
                for tp in self.current_trick.plays
            ],
            "cards_played_total": len(self.played_cards),
            "played_cards": [c.to_dict() for c in self.played_cards],
            "cards_remaining_unknown": len(self.remaining_unknown),
            "user_hand_size": self.players[0].actual_hand_size,
            "opponent_hand_size": self.players[1].actual_hand_size,
            # When draw pile is empty, remaining_unknown = exactly the opponent's hand.
            # Only reveal if the count matches to avoid showing stale/corrupt data.
            "opponent_known_hand": (
                [c.to_dict() for c in sorted(
                    self.remaining_unknown, key=lambda c: (c.suit, -c.power)
                )]
                if self.draw_pile_size == 0
                   and not self.user_draw_pending
                   and len(self.remaining_unknown) == self.players[1].actual_hand_size
                else []
            ),
            "mrithi": self._evaluate_mrithi(),
            "win_status": self._evaluate_win(),
            "user_draw_pending": self.user_draw_pending,
        }
