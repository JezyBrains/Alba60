"""
Albastini Game Advisor — FastAPI Backend
========================================
Hybrid REST + WebSocket API. REST for initialization and config.
WebSocket for real-time gameplay — every state change auto-pushes
the IS-MCTS best move to the client with zero polling.

All game state is held in-memory (single-session design).
"""

from __future__ import annotations

import json
import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict

from .engine.game_logic import GameState, Card, create_deck
from .engine.mcts import ISMCTSEngine
from .engine.constants import VALID_SUITS, VALID_RANKS, POINT_VALUES, POWER_RANKING
from .engine.game_logger import GameLogger

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Albastini Game Advisor",
    description="IS-MCTS engine for the 36-card Tanzanian trick-taking game.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory state
# ---------------------------------------------------------------------------
game = GameState()
engine = ISMCTSEngine()  # M3 Max defaults from constants
_logger: Optional[GameLogger] = None   # set on every /game/init
_current_game_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Pydantic Models (for REST endpoints)
# ---------------------------------------------------------------------------
class CardModel(BaseModel):
    suit: str
    rank: str


class InitGameRequest(BaseModel):
    trump_suit: str
    user_hand: List[CardModel]
    num_players: int = 2
    bottom_trump_card: Optional[CardModel] = None


class EngineConfigRequest(BaseModel):
    num_determinizations: int = 200
    simulations_per_det: int = 200
    time_limit_ms: float = 300.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def validate_card(suit: str, rank: str) -> Card:
    """Validate and create a Card from raw strings."""
    if suit not in VALID_SUITS:
        raise ValueError(f"Invalid suit: {suit}")
    if rank not in VALID_RANKS:
        raise ValueError(f"Invalid rank: {rank}")
    return Card(suit=suit, rank=rank)


def to_card(model: CardModel) -> Card:
    """Convert Pydantic model to engine Card."""
    if model.suit not in VALID_SUITS:
        raise HTTPException(400, f"Invalid suit: {model.suit}")
    if model.rank not in VALID_RANKS:
        raise HTTPException(400, f"Invalid rank: {model.rank}")
    return Card(suit=model.suit, rank=model.rank)


def run_advice() -> Dict:
    """Execute IS-MCTS (or Minimax in endgame) and format for the client."""
    result = engine.find_best_move(game)
    best = result.get("best_card")
    return {
        "best_card": best.to_dict() if best else None,
        "win_probability": result["win_probability"],
        "simulations_run": result["simulations_run"],
        "determinizations_completed": result.get("determinizations_completed", 0),
        "all_moves": result.get("all_moves", []),
        "mrithi_viable": result.get("mrithi_viable", False),
        "solver": result.get("solver", "ismcts"),
    }


# ---------------------------------------------------------------------------
# REST Endpoints (Init, Rules, Config — things that happen once)
# ---------------------------------------------------------------------------
@app.get("/")
def health():
    return {"status": "ok", "service": "Albastini Advisor", "version": "0.2.0"}


@app.get("/rules")
def get_rules():
    """Return the hardcoded game parameters for frontend reference."""
    return {
        "deck_size": 36,
        "valid_suits": list(VALID_SUITS),
        "valid_ranks": list(VALID_RANKS),
        "point_values": POINT_VALUES,
        "power_ranking": POWER_RANKING,
        "win_threshold": 61,
        "mrithi_threshold": 10,
        "total_deck_points": 120,
        "hand_size": 5,
    }


@app.post("/game/init")
def init_game(req: InitGameRequest):
    """Initialize a new game round. Called once per game."""
    import uuid
    global game, _logger, _current_game_id

    if req.trump_suit not in VALID_SUITS:
        raise HTTPException(400, f"Invalid trump suit: {req.trump_suit}")
    if len(req.user_hand) != 6:
        raise HTTPException(400, "User hand must contain exactly 6 cards")

    # Close previous logger cleanly
    if _logger:
        _logger.close()

    # Fresh game ID — this is the anti-hallucination key
    game_id = str(uuid.uuid4())
    _current_game_id = game_id

    user_hand = [to_card(c) for c in req.user_hand]

    # Bottom Trump card (optional — the face-up card at the bottom of the draw pile)
    bottom_trump: Card | None = None
    if req.bottom_trump_card:
        bottom_trump = to_card(req.bottom_trump_card)

    game = GameState(num_players=req.num_players)
    game.initialize(
        trump_suit=req.trump_suit,
        user_hand=user_hand,
        num_players=req.num_players,
        bottom_trump_card=bottom_trump,
    )

    # Start logging this game
    _logger = GameLogger(game_id)
    _logger.log_init(
        trump_suit=req.trump_suit,
        user_hand=[c.to_dict() for c in user_hand],
        draw_pile_size=game.draw_pile_size,
    )

    # Auto-run first advice (opponent leads, so advice is suppressed automatically)
    advice = run_advice()
    if _logger:
        _logger.log_advice(advice)

    return {
        "message": "Game initialized",
        "game_id": game_id,
        "state": game.to_snapshot(),
        "advice": advice,
    }


@app.post("/engine/config")
def configure_engine(req: EngineConfigRequest):
    """Tune IS-MCTS parameters at runtime."""
    global engine
    engine = ISMCTSEngine(
        num_determinizations=req.num_determinizations,
        simulations_per_det=req.simulations_per_det,
        time_limit_ms=req.time_limit_ms,
    )
    return {"message": "Engine reconfigured"}


@app.get("/games")
def list_games():
    """List all recorded game log files."""
    from pathlib import Path
    log_dir = Path(__file__).parent.parent.parent / "logs"
    if not log_dir.exists():
        return {"games": []}
    files = sorted(log_dir.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    return {"games": [f.stem for f in files], "count": len(files)}


@app.get("/games/{game_id}")
def get_game_log(game_id: str):
    """Return the full event log for a specific game ID."""
    from pathlib import Path
    log_path = Path(__file__).parent.parent.parent / "logs" / f"{game_id}.jsonl"
    if not log_path.exists():
        raise HTTPException(404, f"Game {game_id} not found")
    events = []
    with log_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                events.append(json.loads(line))
    return {"game_id": game_id, "events": events, "total": len(events)}


# ---------------------------------------------------------------------------
# WebSocket — The real-time game pipeline
# ---------------------------------------------------------------------------
@app.websocket("/ws/game")
async def game_socket(websocket: WebSocket):
    """
    Single WebSocket connection for all gameplay.

    Client sends JSON messages:
      { "type": "play",  "game_id": "<uuid>", "player_id": 0, "card": {"suit": "SPADES", "rank": "A"} }
      { "type": "draw",  "game_id": "<uuid>", "cards": [{"suit": "HEARTS", "rank": "7"}, ...] }
      { "type": "swap",  "game_id": "<uuid>", "cards_given": [...], "cards_received": [...] }
      { "type": "state"  }  — request current state (no game_id check needed)
      { "type": "advice" }  — request MCTS advice on demand

    Server pushes after every state change:
      { "type": "update", "game_id": "<uuid>", "state": {...}, "advice": {...}, "trick_result": {...} | null }
    """
    global game, _logger, _current_game_id

    await websocket.accept()

    # Send initial state on connect — include current game_id so frontend can sync
    try:
        advice = run_advice() if game.trump_suit else None
        await websocket.send_json({
            "type": "connected",
            "game_id": _current_game_id,
            "state": game.to_snapshot(),
            "advice": advice,
        })
    except Exception:
        pass

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = msg.get("type", "")
            trick_result = None

            # ------------------------------------------------------------------
            # Game-ID guard: reject moves from a stale / mismatched session
            # (state + advice requests are always allowed without an ID)
            # ------------------------------------------------------------------
            if msg_type not in ("state", "advice"):
                client_gid = msg.get("game_id")
                if client_gid and client_gid != _current_game_id:
                    await websocket.send_json({
                        "type": "error",
                        "message": "game_id mismatch — please start a new game",
                        "current_game_id": _current_game_id,
                    })
                    continue

            try:
                if msg_type == "play":
                    card = validate_card(msg["card"]["suit"], msg["card"]["rank"])
                    trick_result = game.play_card(msg["player_id"], card)
                    # Debug: trace trick resolution
                    print(f"[PLAY] P{msg['player_id']} → {card.rank}{card.suit[0]} | "
                          f"trump={game.trump_suit} | trick_plays={len(game.current_trick.plays)}")
                    if trick_result:
                        plays_str = " vs ".join(
                            f"P{tp.player_id}:{tp.card.rank}{tp.card.suit[0]}"
                            for tp in game.tricks_history[-1].plays
                        )
                        print(f"[TRICK] {plays_str} → Winner: P{trick_result['trick_winner']} "
                              f"+{trick_result['points_won']}pts")
                    if _logger:
                        _logger.log_play(
                            player_id=msg["player_id"],
                            card=card.to_dict(),
                            turn_index=game.turn_index,
                        )
                        if trick_result:
                            _logger.log_trick(trick_result)
                            if trick_result.get("game_over") and _logger:
                                ws = trick_result.get("win_status", {})
                                _logger.log_game_over(
                                    scores=game.to_snapshot()["scores"],
                                    tricks_won=game.to_snapshot()["tricks_won"],
                                    winner=ws.get("winner"),
                                )

                elif msg_type == "draw":
                    cards = [validate_card(c["suit"], c["rank"]) for c in msg["cards"]]
                    game.register_user_draw(cards)
                    if _logger:
                        _logger.log_draw(
                            player_id=0,
                            cards=[c.to_dict() for c in cards],
                        )

                elif msg_type == "swap":
                    given = [validate_card(c["suit"], c["rank"]) for c in msg["cards_given"]]
                    received = [validate_card(c["suit"], c["rank"]) for c in msg["cards_received"]]
                    game.register_bidding_swap(given, received)

                elif msg_type == "state":
                    await websocket.send_json({
                        "type": "update",
                        "game_id": _current_game_id,
                        "state": game.to_snapshot(),
                        "advice": None,
                        "trick_result": None,
                    })
                    continue

                elif msg_type == "advice":
                    advice = run_advice()
                    if _logger:
                        _logger.log_advice(advice)
                    await websocket.send_json({
                        "type": "update",
                        "game_id": _current_game_id,
                        "state": game.to_snapshot(),
                        "advice": advice,
                        "trick_result": None,
                    })
                    continue

                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    })
                    continue

            except (ValueError, KeyError) as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })
                continue

            # After any state mutation, auto-push state + fresh advice
            # Only run advice if the user doesn't have a pending draw
            if game.game_over or game.user_draw_pending:
                advice = None
            else:
                advice = run_advice()

            if _logger and advice:
                _logger.log_advice(advice)

            await websocket.send_json({
                "type": "update",
                "game_id": _current_game_id,
                "state": game.to_snapshot(),
                "advice": advice,
                "trick_result": trick_result,
            })

    except (WebSocketDisconnect, RuntimeError):
        pass
