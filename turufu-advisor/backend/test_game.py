from src.engine.game_logic import GameState, Card, create_deck
from src.engine.constants import HAND_SIZE

g = GameState(num_players=2)
deck = create_deck()
user_hand = deck[:6]
g.initialize(trump_suit="SPADES", user_hand=user_hand)

print("Initial draw pile size:", g.draw_pile_size)
print("Opponent actual_hand_size:", g.players[1].actual_hand_size)

# Opponent leads
opp_card = list(g.remaining_unknown)[0]
res = g.play_card(1, opp_card)
print("After opp plays:", opp_card, "Opp hand size:", g.players[1].actual_hand_size, "Trick complete:", res is not None)

# User plays
user_card = user_hand[0]
res = g.play_card(0, user_card)
print("After user plays:", user_card, "User hand size:", g.players[0].actual_hand_size, "Trick complete:", res is not None)

print("Post trick draw pile:", g.draw_pile_size)
print("Post trick User hand size:", g.players[0].actual_hand_size)
print("Post trick Opp hand size:", g.players[1].actual_hand_size)
