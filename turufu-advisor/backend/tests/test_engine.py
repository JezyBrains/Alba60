"""
Albastini Engine Smoke Test
============================
Validates core game logic and IS-MCTS engine integrity.
Run with: python -m pytest tests/ -v
"""

import sys
import os

# Add parent to path so we can import src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.engine.constants import VALID_RANKS, VALID_SUITS, POINT_VALUES, DECK_SIZE
from src.engine.game_logic import Card, GameState, create_deck, Trick, TrickPlay
from src.engine.mcts import ISMCTSEngine, evaluate_terminal


def test_deck_composition():
    """The Albastini deck must have exactly 36 cards with 120 total points."""
    deck = create_deck()
    assert len(deck) == DECK_SIZE == 36

    total_points = sum(c.points for c in deck)
    assert total_points == 120, f"Expected 120 total points, got {total_points}"

    # Verify no banned ranks
    banned = {"2", "8", "9", "10"}
    for card in deck:
        assert card.rank not in banned, f"Banned rank found: {card}"

    print("✓ Deck: 36 cards, 120 points, no banned ranks")


def test_card_point_values():
    """Point values must match the Albastini specification."""
    assert Card("SPADES", "A").points == 11
    assert Card("HEARTS", "7").points == 10
    assert Card("DIAMONDS", "K").points == 4
    assert Card("CLUBS", "J").points == 3
    assert Card("SPADES", "Q").points == 2
    assert Card("HEARTS", "6").points == 0
    assert Card("DIAMONDS", "3").points == 0
    print("✓ Point values match specification")


def test_card_power_hierarchy():
    """Power ranking: A > 7 > K > J > Q > 6 > 5 > 4 > 3."""
    powers = [Card("SPADES", r).power for r in VALID_RANKS]
    assert powers == sorted(powers, reverse=True), f"Power hierarchy violation: {powers}"
    print("✓ Power hierarchy correct")


def test_trick_resolution_no_trump():
    """Without trump, highest power card of the led suit wins."""
    trump = "HEARTS"
    trick = Trick()
    trick.plays = [
        TrickPlay(0, Card("SPADES", "Q")),   # Led suit, power 4
        TrickPlay(1, Card("SPADES", "A")),   # Led suit, power 8 — WINNER
    ]
    winner = trick.winner(trump)
    assert winner == 1, f"Expected player 1, got {winner}"
    print("✓ Trick resolution (no trump): highest led-suit card wins")


def test_trick_resolution_trump_beats_lead():
    """A trump card beats any non-trump card regardless of power."""
    trump = "HEARTS"
    trick = Trick()
    trick.plays = [
        TrickPlay(0, Card("SPADES", "A")),   # Ace of Spades (highest non-trump)
        TrickPlay(1, Card("HEARTS", "3")),   # Lowest trump — but it's TRUMP
    ]
    winner = trick.winner(trump)
    assert winner == 1, f"Expected player 1 (trump wins), got {winner}"
    print("✓ Trick resolution (trump): lowest trump beats highest non-trump")


def test_trick_resolution_higher_trump_wins():
    """When both play trump, higher power trump wins."""
    trump = "HEARTS"
    trick = Trick()
    trick.plays = [
        TrickPlay(0, Card("HEARTS", "3")),   # Low trump
        TrickPlay(1, Card("HEARTS", "7")),   # High trump — WINNER
    ]
    winner = trick.winner(trump)
    assert winner == 1, f"Expected player 1, got {winner}"
    print("✓ Trick resolution: higher trump beats lower trump")


def test_trick_offsuit_loses():
    """Off-suit non-trump cards never win the trick."""
    trump = "HEARTS"
    trick = Trick()
    trick.plays = [
        TrickPlay(0, Card("SPADES", "3")),     # Led suit, low
        TrickPlay(1, Card("DIAMONDS", "A")),   # Off-suit Ace — LOSES
    ]
    winner = trick.winner(trump)
    assert winner == 0, f"Expected player 0 (off-suit loses), got {winner}"
    print("✓ Trick resolution: off-suit non-trump always loses")


def test_game_initialization():
    """Game state initializes correctly with known hand and unknown remainder."""
    gs = GameState(num_players=2)
    hand = [
        Card("SPADES", "A"), Card("HEARTS", "7"), Card("DIAMONDS", "K"),
        Card("CLUBS", "J"), Card("SPADES", "Q"),
    ]
    gs.initialize(trump_suit="HEARTS", user_hand=hand, num_players=2)

    assert len(gs.players[0].hand) == 5
    assert gs.trump_suit == "HEARTS"
    assert len(gs.remaining_unknown) == 36 - 5  # 31 unknown cards
    assert gs.draw_pile_size == 36 - (5 * 2)    # 26 cards in draw pile
    print("✓ Game initialization: 5-card hand, 31 unknown, 26 in draw pile")


def test_no_follow_suit_rule():
    """Every card in hand is a legal move, regardless of led suit."""
    gs = GameState(num_players=2)
    hand = [
        Card("SPADES", "A"), Card("HEARTS", "7"), Card("DIAMONDS", "K"),
        Card("CLUBS", "J"), Card("SPADES", "Q"),
    ]
    gs.initialize(trump_suit="HEARTS", user_hand=hand, num_players=2)

    # Simulate opponent leading with Diamonds
    gs.play_card(1, Card("DIAMONDS", "A"))

    # User should be able to play ANY card
    moves = gs.get_valid_moves(0)
    assert len(moves) == 5, f"Expected 5 legal moves, got {len(moves)}"
    print("✓ No follow-suit: all 5 cards are legal regardless of led suit")


def test_mrithi_evaluation():
    """Mrithi (skunk) detection when opponent is below 10 points."""
    gs = GameState(num_players=2)
    gs.players[0].points_captured = 115
    gs.players[1].points_captured = 5
    gs.game_over = True

    mrithi = gs._evaluate_mrithi()
    assert mrithi["applicable"] is True
    assert mrithi["opponent_skunked"] is True
    print("✓ Mrithi detection: opponent at 5 points is correctly skunked")


def test_mcts_returns_valid_move():
    """IS-MCTS engine must return a card that exists in the user's hand."""
    gs = GameState(num_players=2)
    hand = [
        Card("SPADES", "A"), Card("HEARTS", "7"), Card("DIAMONDS", "K"),
        Card("CLUBS", "J"), Card("SPADES", "Q"),
    ]
    gs.initialize(trump_suit="HEARTS", user_hand=hand, num_players=2)

    mcts = ISMCTSEngine(
        num_determinizations=5,
        simulations_per_det=10,
        time_limit_ms=2000,
    )
    result = mcts.find_best_move(gs)

    best = result["best_card"]
    assert best in hand, f"MCTS returned {best} which is not in hand"
    assert 0 <= result["win_probability"] <= 1.0
    print(f"✓ IS-MCTS: recommended {best} with {result['win_probability']:.1%} win probability")
    print(f"  Simulations: {result['simulations_run']}, Mrithi viable: {result['mrithi_viable']}")


if __name__ == "__main__":
    tests = [
        test_deck_composition,
        test_card_point_values,
        test_card_power_hierarchy,
        test_trick_resolution_no_trump,
        test_trick_resolution_trump_beats_lead,
        test_trick_resolution_higher_trump_wins,
        test_trick_offsuit_loses,
        test_game_initialization,
        test_no_follow_suit_rule,
        test_mrithi_evaluation,
        test_mcts_returns_valid_move,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if failed == 0:
        print("All tests passed. Engine is ready.")
