"""
Albastini Game Constants
========================
Hardcoded parameters for the 36-card Tanzanian trick-taking game.
These values define the entire game universe and MUST NOT be modified at runtime.
"""

# ---------------------------------------------------------------------------
# Deck composition — Standard 52 minus 2s, 8s, 9s, 10s, Jokers = 36 cards
# ---------------------------------------------------------------------------
VALID_RANKS = ("A", "7", "K", "J", "Q", "6", "5", "4", "3")
VALID_SUITS = ("SPADES", "HEARTS", "DIAMONDS", "CLUBS")

DECK_SIZE = 36  # len(VALID_RANKS) * len(VALID_SUITS)

# ---------------------------------------------------------------------------
# Point values — This IS the game. 120 total points in the deck.
# ---------------------------------------------------------------------------
POINT_VALUES = {
    "A": 11,
    "7": 10,
    "K": 4,
    "J": 3,
    "Q": 2,
    "6": 0,
    "5": 0,
    "4": 0,
    "3": 0,
}

# ---------------------------------------------------------------------------
# Power hierarchy — Determines who wins a trick (index 0 = strongest)
# This is SEPARATE from point values. A "7" beats a "K" even though
# a King is worth 4 points and a 7 is worth 10.
# ---------------------------------------------------------------------------
POWER_RANKING = {
    "A": 8,  # Highest power
    "7": 7,
    "K": 6,
    "J": 5,
    "Q": 4,
    "6": 3,
    "5": 2,
    "4": 1,
    "3": 0,  # Lowest power
}

# ---------------------------------------------------------------------------
# Win conditions — The heuristic function targets
# ---------------------------------------------------------------------------
TOTAL_DECK_POINTS = 120
WIN_THRESHOLD = 61          # Points needed to win the round
MRITHI_THRESHOLD = 10       # Opponent below this = 2 VP (skunked)

# ---------------------------------------------------------------------------
# Game mechanics
# ---------------------------------------------------------------------------
HAND_SIZE = 6               # Players always hold exactly 6 cards
MAX_PLAYERS = 6
DEFAULT_PLAYERS = 2
DEALER_PLAYER_ID = 1        # Opponent is the dealer and leads the first trick

# ---------------------------------------------------------------------------
# Draw pile & Bottom Trump
# ---------------------------------------------------------------------------
DRAW_PILE_INITIAL = 24      # 36 - (6*2) = 24 cards: 23 face-down + 1 face-up
BOTTOM_TRUMP_TRIGGER = 2    # When pile reaches 2, last draw triggers bottom trump
ENDGAME_TRICKS = 6          # After pile empties: 6 tricks of perfect information
