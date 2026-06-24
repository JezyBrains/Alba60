#!/usr/bin/env python3
"""
Albastini Game Simulator
========================
Plays N complete games automatically using the live engine, logs every event,
checks invariants after every state transition, and prints a full bug report.

Usage:
    python simulate_games.py              # 200 games, default seed
    python simulate_games.py --games 500 --seed 42 --verbose

The script imports the engine directly (no HTTP/WS needed) so it runs fast.
After all games, it analyses the logs and prints a summary of any violations.
"""

from __future__ import annotations

import sys
import os
import json
import random
import argparse
import traceback
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Set, Tuple

# Make sure we can import the backend engine
sys.path.insert(0, str(Path(__file__).parent))

from src.engine.game_logic import GameState, Card, create_deck, Trick, TrickPlay
from src.engine.constants import (
    HAND_SIZE, VALID_SUITS, VALID_RANKS, POINT_VALUES,
    TOTAL_DECK_POINTS, WIN_THRESHOLD, MRITHI_THRESHOLD,
)

# ---------------------------------------------------------------------------
# Simulation config
# ---------------------------------------------------------------------------
STRATEGIES = ("random", "greedy_points", "greedy_power")


# ---------------------------------------------------------------------------
# Invariant checker — runs after every state mutation
# ---------------------------------------------------------------------------
class InvariantViolation(Exception):
    pass


def check_invariants(gs: GameState, real_hands: List[Set[Card]], draw_pile: List[Card],
                     label: str) -> None:
    """Raise InvariantViolation with a clear message if anything is wrong."""
    errors = []

    # 1. Total points must be consistent (sum of scores + points still unplayed)
    scored = sum(p.points_captured for p in gs.players)
    if scored > TOTAL_DECK_POINTS:
        errors.append(f"Scored points overflow: {scored} > {TOTAL_DECK_POINTS}")

    # 2. Hand sizes never exceed HAND_SIZE
    for i, hand in enumerate(real_hands):
        if len(hand) > HAND_SIZE:
            errors.append(f"Player {i} hand too large: {len(hand)} > {HAND_SIZE}")

    # 3. actual_hand_size must match real hand length
    for i, hand in enumerate(real_hands):
        ahs = gs.players[i].actual_hand_size
        if ahs != len(hand):
            errors.append(
                f"Player {i} actual_hand_size={ahs} but real hand len={len(hand)}"
            )

    # 4. Draw pile never negative
    if gs.draw_pile_size < 0:
        errors.append(f"Draw pile negative: {gs.draw_pile_size}")

    # 5. No card appears in more than one location (hand[0], hand[1], played, pile)
    all_locations: Dict[Card, str] = {}
    for i, hand in enumerate(real_hands):
        for c in hand:
            if c in all_locations:
                errors.append(f"Card {c} in both {all_locations[c]} and player{i}_hand")
            all_locations[c] = f"player{i}_hand"
    for c in draw_pile:
        if c in all_locations:
            errors.append(f"Card {c} in both {all_locations[c]} and draw_pile")
        all_locations[c] = "draw_pile"
    for c in gs.played_cards:
        if c in all_locations:
            errors.append(f"Card {c} in both {all_locations[c]} and played_cards")
        all_locations[c] = "played"
    # Also check current trick
    for tp in gs.current_trick.plays:
        if tp.card in all_locations and all_locations[tp.card] != "played":
            errors.append(f"Card {tp.card} in both {all_locations[tp.card]} and current_trick")

    # 6. Total card count = DECK_SIZE
    in_trick = {tp.card for tp in gs.current_trick.plays}
    total = len(all_locations) + len(in_trick & set(all_locations)) - len(in_trick & set(all_locations))
    # Simpler: count unique across all sets
    all_cards_seen = (
        set().union(*real_hands)
        | set(draw_pile)
        | gs.played_cards
        | {tp.card for tp in gs.current_trick.plays}
    )
    full_deck = set(create_deck())
    missing = full_deck - all_cards_seen
    extra = all_cards_seen - full_deck
    if missing:
        errors.append(f"Cards missing from tracking: {missing}")
    if extra:
        errors.append(f"Unknown cards appeared: {extra}")

    if errors:
        raise InvariantViolation(f"[{label}] " + " | ".join(errors))


# ---------------------------------------------------------------------------
# Strategy functions — decide which card a player plays
# ---------------------------------------------------------------------------

def _pick_random(hand: Set[Card], _trick: Trick, _trump: str) -> Card:
    return random.choice(list(hand))


def _pick_greedy_points(hand: Set[Card], trick: Trick, trump: str) -> Card:
    """Play the highest-value card if likely to win; dump lowest otherwise."""
    hand_list = sorted(hand, key=lambda c: c.points, reverse=True)
    # Play highest point card (greedy — not necessarily smart but deterministic)
    return hand_list[0]


def _pick_greedy_power(hand: Set[Card], trick: Trick, trump: str) -> Card:
    """Play highest-power card first."""
    return max(hand, key=lambda c: c.power)


STRATEGY_FN = {
    "random": _pick_random,
    "greedy_points": _pick_greedy_points,
    "greedy_power": _pick_greedy_power,
}


# ---------------------------------------------------------------------------
# Core simulator
# ---------------------------------------------------------------------------

@dataclass
class GameResult:
    game_id: int
    winner: Optional[int]       # None = draw / no winner (shouldn't happen)
    scores: Dict[int, int]
    tricks_won: Dict[int, int]
    total_tricks: int
    mrithi: bool                # True if opponent was skunked
    errors: List[str]
    events: List[dict]
    seed: int


def simulate_one_game(
    game_id: int,
    seed: int,
    strategy_user: str = "random",
    strategy_opp: str = "random",
    verbose: bool = False,
) -> GameResult:
    """
    Play one complete Albastini game from init to game_over.
    Maintains the REAL state of both hands separately so we can check invariants.
    """
    rng = random.Random(seed)
    errors: List[str] = []
    events: List[dict] = []
    seq = 0

    def log(event: str, **payload):
        nonlocal seq
        seq += 1
        rec = {"game_id": game_id, "seq": seq,
                "ts": datetime.now(timezone.utc).isoformat(),
                "event": event, **payload}
        events.append(rec)
        if verbose:
            print(f"  [{seq:3d}] {event}: {payload}")

    # --- Deal cards ---
    deck = create_deck()
    rng.shuffle(deck)
    trump_suit = rng.choice(list(VALID_SUITS))

    user_hand: Set[Card] = set(deck[:HAND_SIZE])
    opp_hand:  Set[Card] = set(deck[HAND_SIZE:HAND_SIZE*2])
    draw_pile: List[Card] = deck[HAND_SIZE*2:]   # 24 cards face-down

    log("game_init",
        trump_suit=trump_suit,
        user_hand=[c.to_dict() for c in user_hand],
        opp_hand=[c.to_dict() for c in opp_hand],
        draw_pile_size=len(draw_pile))

    # --- Init engine ---
    gs = GameState()
    gs.initialize(
        trump_suit=trump_suit,
        user_hand=list(user_hand),
        num_players=2,
    )

    # Override engine's draw_pile_size with the real count
    assert gs.draw_pile_size == len(draw_pile), \
        f"Draw pile mismatch: engine={gs.draw_pile_size} real={len(draw_pile)}"

    strategy_fns = [STRATEGY_FN[strategy_user], STRATEGY_FN[strategy_opp]]
    real_hands = [user_hand, opp_hand]

    try:
        check_invariants(gs, real_hands, draw_pile, "init")
    except InvariantViolation as e:
        errors.append(str(e))

    # --- Main game loop ---
    trick_count = 0
    max_tricks = 36   # safety valve (can't have more tricks than cards)

    while not gs.game_over and trick_count < max_tricks:
        # One full trick: each player plays a card
        for _ in range(gs.num_players):
            pid = gs.turn_index
            hand = real_hands[pid]

            if not hand:
                errors.append(f"Player {pid} has no cards to play at trick {trick_count+1}")
                break

            card = strategy_fns[pid](hand, gs.current_trick, trump_suit)
            hand.discard(card)

            log("card_played",
                player_id=pid,
                card=card.to_dict(),
                turn_index=gs.turn_index,
                hand_sizes=[len(h) for h in real_hands])

            try:
                trick_result = gs.play_card(pid, card)
            except Exception as e:
                errors.append(f"play_card error at trick={trick_count+1} pid={pid} card={card}: {e}")
                trick_result = None

            if trick_result:
                # Trick is complete
                trick_count += 1
                winner_id = trick_result["trick_winner"]
                pts = trick_result["points_won"]
                log("trick_result",
                    trick_winner=winner_id,
                    points_won=pts,
                    scores=trick_result["scores"],
                    draw_pile_size=gs.draw_pile_size,
                    game_over=trick_result["game_over"])

                # --- Draw phase ---
                # Winner draws first, then loser (matches engine logic)
                draw_order = [winner_id, 1 - winner_id]
                for dpid in draw_order:
                    if draw_pile:
                        drawn = draw_pile.pop(0)
                        real_hands[dpid].add(drawn)

                        if dpid == 0:  # user: must register with engine
                            try:
                                gs.register_user_draw([drawn])
                                log("card_drawn",
                                    player_id=0,
                                    card=drawn.to_dict(),
                                    draw_pile_remaining=len(draw_pile))
                            except ValueError as e:
                                errors.append(f"register_user_draw failed: {e}")
                        else:
                            log("opp_draw",
                                player_id=1,
                                draw_pile_remaining=len(draw_pile))

                # Verify engine draw pile size matches real pile
                if gs.draw_pile_size != len(draw_pile):
                    errors.append(
                        f"Draw pile size mismatch after trick {trick_count}: "
                        f"engine={gs.draw_pile_size} real={len(draw_pile)}"
                    )

                # Check invariants
                try:
                    check_invariants(gs, real_hands, draw_pile,
                                     f"after_trick_{trick_count}")
                except InvariantViolation as e:
                    errors.append(str(e))

                if trick_result.get("game_over"):
                    break

            else:
                # Mid-trick — check invariants
                try:
                    check_invariants(gs, real_hands, draw_pile,
                                     f"mid_trick_{trick_count+1}_p{pid}")
                except InvariantViolation as e:
                    errors.append(str(e))

        if trick_result and trick_result.get("game_over"):
            break

    # --- Post-game checks ---
    final_scores = {p.player_id: p.points_captured for p in gs.players}
    final_tricks = {p.player_id: p.tricks_won for p in gs.players}
    total_scored = sum(final_scores.values())

    if total_scored != TOTAL_DECK_POINTS:
        errors.append(
            f"Point total wrong at game end: {total_scored} != {TOTAL_DECK_POINTS}"
        )

    if draw_pile:
        errors.append(f"Game ended but draw pile not empty: {len(draw_pile)} cards left")

    for i, hand in enumerate(real_hands):
        if hand:
            errors.append(f"Game ended but player {i} still has cards: {hand}")

    winner = None
    for p in gs.players:
        if p.has_won():
            winner = p.player_id

    mrithi = any(p.is_skunked() and p.player_id != winner for p in gs.players)

    log("game_over",
        scores=final_scores,
        tricks_won=final_tricks,
        winner=winner,
        mrithi=mrithi,
        errors=errors)

    return GameResult(
        game_id=game_id,
        winner=winner,
        scores=final_scores,
        tricks_won=final_tricks,
        total_tricks=trick_count,
        mrithi=mrithi,
        errors=errors,
        events=events,
        seed=seed,
    )


# ---------------------------------------------------------------------------
# Runner + reporting
# ---------------------------------------------------------------------------

def run_simulations(
    n_games: int = 200,
    base_seed: int = 0,
    strategy_user: str = "random",
    strategy_opp: str = "random",
    verbose: bool = False,
    save_logs: bool = True,
) -> None:
    log_dir = Path(__file__).parent / "logs" / "simulations"
    log_dir.mkdir(parents=True, exist_ok=True)
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_log_path = log_dir / f"run_{run_ts}.jsonl"

    print(f"\n{'='*60}")
    print(f" Albastini Simulator — {n_games} games")
    print(f" Strategies: user={strategy_user}  opp={strategy_opp}")
    print(f" Seed base: {base_seed}")
    print(f"{'='*60}\n")

    results: List[GameResult] = []
    error_games: List[GameResult] = []
    point_totals = []
    winners = {0: 0, 1: 0, None: 0}

    with run_log_path.open("w") as fh:
        for i in range(n_games):
            seed = base_seed + i
            if not verbose and i % 20 == 0:
                print(f"  Playing game {i+1}/{n_games}...", end="\r", flush=True)

            try:
                result = simulate_one_game(
                    game_id=i + 1,
                    seed=seed,
                    strategy_user=strategy_user,
                    strategy_opp=strategy_opp,
                    verbose=verbose,
                )
            except Exception as e:
                tb = traceback.format_exc()
                result = GameResult(
                    game_id=i + 1, winner=None,
                    scores={}, tricks_won={}, total_tricks=0,
                    mrithi=False,
                    errors=[f"CRASH: {e}\n{tb}"],
                    events=[], seed=seed,
                )

            results.append(result)
            if result.errors:
                error_games.append(result)

            winners[result.winner] = winners.get(result.winner, 0) + 1
            point_totals.append(sum(result.scores.values()))

            if save_logs:
                for ev in result.events:
                    fh.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")

    # --- Report ---
    print(f"\n{'='*60}")
    print(f" RESULTS  ({n_games} games)")
    print(f"{'='*60}")
    print(f"  User (P0) wins : {winners.get(0,0):4d}  ({winners.get(0,0)/n_games*100:.1f}%)")
    print(f"  Opp  (P1) wins : {winners.get(1,0):4d}  ({winners.get(1,0)/n_games*100:.1f}%)")
    print(f"  No winner      : {winners.get(None,0):4d}  ({winners.get(None,0)/n_games*100:.1f}%)")
    print(f"  Avg total pts  : {sum(point_totals)/n_games:.1f}  (expected {TOTAL_DECK_POINTS})")
    print(f"  Games with errors: {len(error_games)} / {n_games}")
    if point_totals:
        wrong = [p for p in point_totals if p != TOTAL_DECK_POINTS]
        if wrong:
            print(f"  ⚠  Point-total wrong in {len(wrong)} games: values={set(wrong)}")

    if error_games:
        print(f"\n{'─'*60}")
        print(" BUGS FOUND")
        print(f"{'─'*60}")
        # Deduplicate by error message
        seen_errors: Dict[str, List[int]] = {}
        for gr in error_games:
            for err in gr.errors:
                key = err[:120]
                seen_errors.setdefault(key, []).append(gr.game_id)

        for err_msg, game_ids in sorted(seen_errors.items(), key=lambda x: -len(x[1])):
            print(f"\n  [{len(game_ids)}x] {err_msg}")
            print(f"       Game IDs: {game_ids[:10]}{'...' if len(game_ids) > 10 else ''}")
            # Show the relevant event sequence for the first failing game
            gid = game_ids[0]
            gr = next(r for r in error_games if r.game_id == gid)
            # Print last 5 events before game_over
            relevant = [e for e in gr.events if e["event"] != "game_over"][-5:]
            print(f"       Last events in game {gid} (seed={gr.seed}):")
            for ev in relevant:
                print(f"         seq={ev['seq']} {ev['event']}: "
                      f"{json.dumps({k:v for k,v in ev.items() if k not in ('game_id','ts','event')}, default=str)}")
    else:
        print("\n  ✅  No invariant violations found across all games!")

    print(f"\n  Full logs: {run_log_path}\n")

    # Save summary JSON for analysis
    summary = {
        "run_ts": run_ts,
        "n_games": n_games,
        "strategy_user": strategy_user,
        "strategy_opp": strategy_opp,
        "base_seed": base_seed,
        "wins_user": winners.get(0, 0),
        "wins_opp": winners.get(1, 0),
        "no_winner": winners.get(None, 0),
        "avg_total_pts": sum(point_totals) / max(len(point_totals), 1),
        "error_count": len(error_games),
        "unique_errors": list(seen_errors.keys()) if error_games else [],
    }
    summary_path = log_dir / f"summary_{run_ts}.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"  Summary  : {summary_path}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Albastini game simulator")
    parser.add_argument("--games",    type=int, default=200,      help="Number of games to simulate")
    parser.add_argument("--seed",     type=int, default=0,        help="Base random seed")
    parser.add_argument("--strategy-user", default="random",      choices=STRATEGIES)
    parser.add_argument("--strategy-opp",  default="random",      choices=STRATEGIES)
    parser.add_argument("--verbose",  action="store_true",        help="Print every event")
    parser.add_argument("--no-save",  action="store_true",        help="Don't save log files")
    args = parser.parse_args()

    run_simulations(
        n_games=args.games,
        base_seed=args.seed,
        strategy_user=args.strategy_user,
        strategy_opp=args.strategy_opp,
        verbose=args.verbose,
        save_logs=not args.no_save,
    )
