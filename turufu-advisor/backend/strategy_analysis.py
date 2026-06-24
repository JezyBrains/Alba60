#!/usr/bin/env python3
"""
Albastini Strategy Analyzer
============================
Runs 10,000 games with smart strategies, records winning move sequences,
and mines patterns/traps for a strategy guide.
"""

from __future__ import annotations
import sys, json, random, collections
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field

sys.path.insert(0, str(Path(__file__).parent))

from src.engine.game_logic import GameState, Card, create_deck, Trick
from src.engine.constants import (
    HAND_SIZE, VALID_SUITS, VALID_RANKS, POINT_VALUES,
    TOTAL_DECK_POINTS, POWER_RANKING,
)

# ── Smart Strategy (plays like a strong human) ──────────────────────────

def smart_play(hand: Set[Card], trick: Trick, trump: str, 
               played_cards: Set[Card], leader: bool) -> Card:
    """Advanced strategy that considers trick context, trump management, and point capture."""
    cards = list(hand)
    
    if leader:
        return _smart_lead(cards, trump, played_cards)
    else:
        lead_card = trick.plays[0].card
        return _smart_follow(cards, lead_card, trump, played_cards)


def _smart_lead(cards: List[Card], trump: str, played: Set[Card]) -> Card:
    """Choose best card to lead with."""
    trumps = [c for c in cards if c.suit == trump]
    non_trumps = [c for c in cards if c.suit != trump]
    
    # Count remaining trumps in the game
    trumps_played = sum(1 for c in played if c.suit == trump)
    trumps_out = 9 - trumps_played - len(trumps)  # opponent's trumps
    
    # If we have strong non-trump aces/7s and opponent might be out of that suit
    for suit in VALID_SUITS:
        if suit == trump:
            continue
        suit_cards = [c for c in non_trumps if c.suit == suit]
        if not suit_cards:
            continue
        suit_played = sum(1 for c in played if c.suit == suit)
        # If 6+ cards of this suit played, opponent likely can't follow
        best = max(suit_cards, key=lambda c: c.power)
        if suit_played >= 6 and best.points > 0:
            # Risky — opponent will trump. Lead low instead
            continue
        if best.rank in ("A", "7") and suit_played < 5:
            return best  # Lead with strong card in fresh suit
    
    # Lead with trump Ace/7 if we dominate trumps
    if len(trumps) >= 3 and trumps_out <= 2:
        best_trump = max(trumps, key=lambda c: c.power)
        if best_trump.points > 0:
            return best_trump  # Draw out their trumps
    
    # Default: lead lowest-value card to minimize risk
    return min(cards, key=lambda c: (c.points, c.power))


def _smart_follow(cards: List[Card], lead: Card, trump: str, played: Set[Card]) -> Card:
    """Choose best card to follow with."""
    same_suit = [c for c in cards if c.suit == lead.suit]
    trumps = [c for c in cards if c.suit == trump]
    
    if same_suit:
        # Can follow suit
        winners = [c for c in same_suit if c.power > lead.power]
        losers = [c for c in same_suit if c.power <= lead.power]
        
        if winners:
            # Win with minimum winning card if trick has points
            trick_pts = lead.points
            if trick_pts >= 10:
                return min(winners, key=lambda c: c.power)  # Win cheaply
            elif trick_pts > 0:
                return min(winners, key=lambda c: c.power)
            else:
                # Trick has 0 points — dump a high-point card to win, or play low
                return max(winners, key=lambda c: c.points) if any(w.points > 0 for w in winners) else min(winners, key=lambda c: c.power)
        else:
            # Can't win — dump lowest value
            return min(losers, key=lambda c: (c.points, c.power))
    
    elif lead.suit != trump and trumps:
        # Can trump
        trick_pts = lead.points
        if trick_pts >= 10:
            return min(trumps, key=lambda c: c.power)  # Trump cheaply for big points
        elif trick_pts >= 3:
            return min(trumps, key=lambda c: c.power)
        else:
            # Not worth trumping for 0-2 points — dump junk
            junk = [c for c in cards if c.suit != trump and c.points == 0]
            if junk:
                return min(junk, key=lambda c: c.power)
            return min(trumps, key=lambda c: c.power)
    
    else:
        # Can't follow, can't trump — dump lowest value
        return min(cards, key=lambda c: (c.points, c.power))


# ── Random & Greedy baselines ───────────────────────────────────────────

def random_play(hand: Set[Card], trick: Trick, trump: str, 
                played: Set[Card], leader: bool) -> Card:
    return random.choice(list(hand))

def greedy_play(hand: Set[Card], trick: Trick, trump: str,
                played: Set[Card], leader: bool) -> Card:
    return max(hand, key=lambda c: c.points)


# ── Game record ─────────────────────────────────────────────────────────

@dataclass 
class MoveRecord:
    trick_num: int
    position: str        # "lead" or "follow"
    player: int
    card: str            # "A_SPADES"
    trick_points: int    # total points in this trick
    won_trick: bool
    trump: str
    is_trump: bool
    cards_in_hand: int
    draw_pile_left: int
    score_before: Tuple[int, int]

@dataclass
class GameRecord:
    game_id: int
    seed: int
    winner: Optional[int]
    final_scores: Tuple[int, int]
    mrithi: bool
    moves: List[MoveRecord]
    trump: str
    margin: int  # winner's score - loser's score


# ── Simulator ───────────────────────────────────────────────────────────

def simulate_game(game_id: int, seed: int, 
                  strat_user, strat_opp) -> GameRecord:
    rng = random.Random(seed)
    deck = create_deck()
    rng.shuffle(deck)
    trump = rng.choice(list(VALID_SUITS))
    
    hands = [set(deck[:HAND_SIZE]), set(deck[HAND_SIZE:HAND_SIZE*2])]
    pile = deck[HAND_SIZE*2:]
    
    gs = GameState()
    gs.initialize(trump_suit=trump, user_hand=list(hands[0]), num_players=2)
    
    strats = [strat_user, strat_opp]
    moves = []
    trick_num = 0
    all_played: Set[Card] = set()
    
    while not gs.game_over and trick_num < 36:
        for _ in range(2):
            pid = gs.turn_index
            hand = hands[pid]
            if not hand:
                break
            
            is_leader = len(gs.current_trick.plays) == 0
            score_before = (gs.players[0].points_captured, gs.players[1].points_captured)
            
            card = strats[pid](hand, gs.current_trick, trump, all_played, is_leader)
            hand.discard(card)
            
            move = MoveRecord(
                trick_num=trick_num,
                position="lead" if is_leader else "follow",
                player=pid,
                card=f"{card.rank}_{card.suit}",
                trick_points=0,  # filled after trick
                won_trick=False,
                trump=trump,
                is_trump=card.suit == trump,
                cards_in_hand=len(hand),
                draw_pile_left=len(pile),
                score_before=score_before,
            )
            
            result = gs.play_card(pid, card)
            all_played.add(card)
            
            if result:
                trick_num += 1
                trick_pts = result["points_won"]
                winner_id = result["trick_winner"]
                
                # Update last 2 moves with trick result
                moves.append(move)
                for m in moves[-2:]:
                    m.trick_points = trick_pts
                    m.won_trick = (m.player == winner_id)
                
                # Draw phase
                for dpid in [winner_id, 1 - winner_id]:
                    if pile:
                        drawn = pile.pop(0)
                        hands[dpid].add(drawn)
                        if dpid == 0:
                            gs.register_user_draw([drawn])
                
                if result.get("game_over"):
                    break
            else:
                moves.append(move)
        
        if gs.game_over:
            break
    
    scores = (gs.players[0].points_captured, gs.players[1].points_captured)
    winner = 0 if scores[0] >= 61 else (1 if scores[1] >= 61 else None)
    mrithi = winner is not None and scores[1 - winner] < 10
    margin = abs(scores[0] - scores[1])
    
    return GameRecord(game_id, seed, winner, scores, mrithi, moves, trump, margin)


# ── Analysis Engine ─────────────────────────────────────────────────────

def analyze_games(records: List[GameRecord]) -> Dict:
    """Extract strategic patterns from winning games."""
    
    user_wins = [g for g in records if g.winner == 0]
    user_losses = [g for g in records if g.winner == 1]
    mrithis = [g for g in records if g.mrithi and g.winner == 0]
    
    # 1. Lead card analysis — what cards win tricks when leading?
    lead_wins = collections.Counter()
    lead_total = collections.Counter()
    lead_pts_captured = collections.defaultdict(list)
    
    for g in user_wins:
        for m in g.moves:
            if m.player == 0 and m.position == "lead":
                rank = m.card.split("_")[0]
                lead_total[rank] += 1
                if m.won_trick:
                    lead_wins[rank] += 1
                    lead_pts_captured[rank].append(m.trick_points)
    
    # 2. Trump timing — when do winners play trump?
    trump_early = 0  # tricks 0-5
    trump_mid = 0    # tricks 6-11
    trump_late = 0   # tricks 12+
    trump_lead_wins = 0
    trump_follow_wins = 0
    
    for g in user_wins:
        for m in g.moves:
            if m.player == 0 and m.is_trump:
                if m.trick_num < 6: trump_early += 1
                elif m.trick_num < 12: trump_mid += 1
                else: trump_late += 1
                if m.won_trick:
                    if m.position == "lead": trump_lead_wins += 1
                    else: trump_follow_wins += 1
    
    # 3. Dump patterns — what do losers dump when they can't win?
    dump_cards = collections.Counter()
    for g in user_wins:
        for m in g.moves:
            if m.player == 0 and not m.won_trick and m.position == "follow":
                rank = m.card.split("_")[0]
                dump_cards[rank] += 1
    
    # 4. Endgame patterns (last 6 tricks, no draw pile)
    endgame_win_rate = {"won": 0, "total": 0}
    endgame_trump_plays = 0
    
    for g in user_wins:
        endgame_moves = [m for m in g.moves if m.draw_pile_left == 0 and m.player == 0]
        for m in endgame_moves:
            endgame_win_rate["total"] += 1
            if m.won_trick:
                endgame_win_rate["won"] += 1
            if m.is_trump:
                endgame_trump_plays += 1
    
    # 5. Score momentum — at what point do winners pull ahead?
    lead_at_trick = collections.defaultdict(lambda: {"ahead": 0, "behind": 0, "tied": 0})
    for g in user_wins:
        for m in g.moves:
            if m.player == 0:
                diff = m.score_before[0] - m.score_before[1]
                t = min(m.trick_num, 17)
                if diff > 0: lead_at_trick[t]["ahead"] += 1
                elif diff < 0: lead_at_trick[t]["behind"] += 1
                else: lead_at_trick[t]["tied"] += 1
    
    # 6. Trap patterns — high-point tricks won by following
    traps = []
    for g in user_wins:
        for m in g.moves:
            if m.player == 0 and m.position == "follow" and m.won_trick and m.trick_points >= 13:
                traps.append({
                    "game": g.game_id,
                    "trick": m.trick_num,
                    "card_played": m.card,
                    "points_captured": m.trick_points,
                    "was_trump": m.is_trump,
                    "score_before": m.score_before,
                })
    
    # 7. Mrithi (skunk) patterns
    mrithi_patterns = []
    for g in mrithis:
        trump_count = sum(1 for m in g.moves if m.player == 0 and m.is_trump)
        tricks_won = sum(1 for m in g.moves if m.player == 0 and m.won_trick) // 1  
        mrithi_patterns.append({
            "game": g.game_id, "score": g.final_scores,
            "margin": g.margin, "trumps_played": trump_count,
        })
    
    # 8. Best opening moves (first 3 tricks)
    opening_sequences = collections.Counter()
    for g in user_wins:
        openers = [m.card.split("_")[0] for m in g.moves 
                   if m.player == 0 and m.trick_num < 3]
        if openers:
            opening_sequences[tuple(openers[:3])] += 1
    
    return {
        "summary": {
            "total_games": len(records),
            "user_wins": len(user_wins),
            "user_losses": len(user_losses),
            "win_rate": round(len(user_wins) / max(len(records), 1) * 100, 1),
            "mrithi_count": len(mrithis),
            "avg_winning_margin": round(sum(g.margin for g in user_wins) / max(len(user_wins), 1), 1),
            "avg_losing_margin": round(sum(g.margin for g in user_losses) / max(len(user_losses), 1), 1),
        },
        "lead_card_analysis": {
            rank: {
                "times_led": lead_total[rank],
                "tricks_won": lead_wins[rank],
                "win_rate": round(lead_wins[rank] / max(lead_total[rank], 1) * 100, 1),
                "avg_pts_captured": round(sum(lead_pts_captured[rank]) / max(len(lead_pts_captured[rank]), 1), 1),
            }
            for rank in ["A", "7", "K", "J", "Q", "6", "5", "4", "3"]
        },
        "trump_timing": {
            "early_0_5": trump_early,
            "mid_6_11": trump_mid, 
            "late_12_plus": trump_late,
            "trump_lead_wins": trump_lead_wins,
            "trump_follow_wins": trump_follow_wins,
        },
        "dump_when_losing": {rank: dump_cards[rank] for rank in ["3", "4", "5", "6", "Q", "J", "K", "7", "A"]},
        "endgame": {
            "tricks_played": endgame_win_rate["total"],
            "tricks_won": endgame_win_rate["won"],
            "win_rate": round(endgame_win_rate["won"] / max(endgame_win_rate["total"], 1) * 100, 1),
            "trump_plays": endgame_trump_plays,
        },
        "top_traps": sorted(traps, key=lambda t: -t["points_captured"])[:20],
        "mrithi_games": mrithi_patterns[:10],
        "best_openings": [{"sequence": list(k), "count": v} for k, v in opening_sequences.most_common(15)],
    }


# ── Main ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Albastini Strategy Analyzer")
    parser.add_argument("--games", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    
    N = args.games
    print(f"\n{'='*60}")
    print(f" Albastini Strategy Analyzer — {N} games")
    print(f" Smart (user) vs Random (opponent)")
    print(f"{'='*60}\n")
    
    records = []
    for i in range(N):
        if i % 500 == 0:
            print(f"  Simulating game {i+1}/{N}...", end="\r", flush=True)
        records.append(simulate_game(i+1, args.seed + i, smart_play, random_play))
    
    print(f"  Completed {N} games.                    ")
    
    analysis = analyze_games(records)
    
    out_dir = Path(__file__).parent / "logs" / "strategy"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Save full analysis
    out_path = out_dir / "analysis.json"
    out_path.write_text(json.dumps(analysis, indent=2, default=str))
    
    # Save winning game move logs  
    wins = [g for g in records if g.winner == 0]
    win_log_path = out_dir / "winning_games.jsonl"
    with win_log_path.open("w") as f:
        for g in wins[:500]:  # Top 500 wins
            f.write(json.dumps({
                "game_id": g.game_id, "seed": g.seed, "trump": g.trump,
                "scores": g.final_scores, "margin": g.margin, "mrithi": g.mrithi,
                "moves": [{"t": m.trick_num, "pos": m.position, "p": m.player,
                           "card": m.card, "pts": m.trick_points, "won": m.won_trick,
                           "trump_card": m.is_trump, "pile": m.draw_pile_left,
                           "score": m.score_before}
                          for m in g.moves]
            }, default=str) + "\n")
    
    # Print report
    s = analysis["summary"]
    print(f"\n{'='*60}")
    print(f" RESULTS")
    print(f"{'='*60}")
    print(f"  Win Rate: {s['win_rate']}% ({s['user_wins']}/{s['total_games']})")
    print(f"  Mrithi (skunk) wins: {s['mrithi_count']}")
    print(f"  Avg winning margin: {s['avg_winning_margin']} pts")
    print(f"  Avg losing margin: {s['avg_losing_margin']} pts")
    
    print(f"\n{'─'*60}")
    print(f" LEAD CARD EFFECTIVENESS (when user leads)")
    print(f"{'─'*60}")
    print(f"  {'Rank':<6} {'Led':>6} {'Won':>6} {'Win%':>7} {'Avg Pts':>8}")
    for rank, data in analysis["lead_card_analysis"].items():
        print(f"  {rank:<6} {data['times_led']:>6} {data['tricks_won']:>6} {data['win_rate']:>6.1f}% {data['avg_pts_captured']:>7.1f}")
    
    print(f"\n{'─'*60}")
    print(f" TRUMP TIMING")
    print(f"{'─'*60}")
    tt = analysis["trump_timing"]
    print(f"  Early (tricks 0-5):  {tt['early_0_5']}")
    print(f"  Mid (tricks 6-11):   {tt['mid_6_11']}")
    print(f"  Late (tricks 12+):   {tt['late_12_plus']}")
    print(f"  Trump lead wins:     {tt['trump_lead_wins']}")
    print(f"  Trump follow wins:   {tt['trump_follow_wins']}")
    
    print(f"\n{'─'*60}")
    print(f" BEST TRAPS (follow & capture 13+ pts)")
    print(f"{'─'*60}")
    for t in analysis["top_traps"][:10]:
        print(f"  Game {t['game']:>5} trick {t['trick']:>2}: played {t['card_played']:<12} "
              f"captured {t['points_captured']:>2} pts {'(TRUMP)' if t['was_trump'] else ''}")
    
    print(f"\n{'─'*60}")
    print(f" ENDGAME (draw pile empty)")
    print(f"{'─'*60}")
    eg = analysis["endgame"]
    print(f"  Tricks played: {eg['tricks_played']}")
    print(f"  Win rate: {eg['win_rate']}%")
    print(f"  Trump plays: {eg['trump_plays']}")
    
    print(f"\n{'─'*60}")
    print(f" TOP OPENING SEQUENCES (first 3 moves)")
    print(f"{'─'*60}")
    for o in analysis["best_openings"][:10]:
        print(f"  {' → '.join(o['sequence']):<20} ({o['count']} wins)")
    
    print(f"\n  Full analysis: {out_path}")
    print(f"  Winning games: {win_log_path}\n")
