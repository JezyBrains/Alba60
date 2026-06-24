"""
Game Logger
===========
Writes every move, trick-result and advice to a JSON-lines file
at  backend/logs/<game_id>.jsonl

Each line is a self-contained JSON event so the file can be streamed
and partially analysed even while a game is in progress.

Event schema (all events share these top-level fields)::

    {
        "game_id":   "<uuid>",
        "seq":       <int>,          # monotonically increasing within a game
        "ts":        "<iso-8601>",   # wall-clock timestamp
        "event":     "<event-type>", # see EVENT_* constants below
        <event-specific fields>
    }
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Event type labels
# ---------------------------------------------------------------------------
EVENT_GAME_INIT    = "game_init"
EVENT_CARD_PLAYED  = "card_played"
EVENT_CARD_DRAWN   = "card_drawn"
EVENT_TRICK_RESULT = "trick_result"
EVENT_ADVICE       = "advice"
EVENT_GAME_OVER    = "game_over"

# Directory relative to this file's package root → backend/logs/
_LOG_DIR = Path(__file__).parent.parent.parent / "logs"


class GameLogger:
    """
    One instance per game session.

    Usage::

        logger = GameLogger(game_id="abc-123")
        logger.log_init(trump_suit="SPADES", user_hand=[...], draw_pile_size=24)
        logger.log_play(player_id=0, card=card.to_dict(), turn_index=0)
        logger.log_advice(advice_payload)
        logger.log_trick(trick_result_dict)
        logger.log_game_over(scores, tricks_won, winner)
    """

    def __init__(self, game_id: str) -> None:
        self.game_id = game_id
        self._seq = 0
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._path = _LOG_DIR / f"{game_id}.jsonl"
        self._fh = self._path.open("a", encoding="utf-8")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def log_init(self, trump_suit: str, user_hand: list, draw_pile_size: int) -> None:
        self._write(EVENT_GAME_INIT, {
            "trump_suit":     trump_suit,
            "user_hand":      user_hand,
            "draw_pile_size": draw_pile_size,
        })

    def log_play(self, player_id: int, card: Dict, turn_index: int) -> None:
        self._write(EVENT_CARD_PLAYED, {
            "player_id":  player_id,
            "card":       card,
            "turn_index": turn_index,
        })

    def log_draw(self, player_id: int, cards: list) -> None:
        self._write(EVENT_CARD_DRAWN, {
            "player_id": player_id,
            "cards":     cards,
        })

    def log_trick(self, trick_result: Dict) -> None:
        self._write(EVENT_TRICK_RESULT, trick_result)

    def log_advice(self, advice: Optional[Dict]) -> None:
        if advice and advice.get("best_card"):
            self._write(EVENT_ADVICE, {
                "best_card":     advice["best_card"],
                "win_prob":      advice.get("win_probability", 0),
                "simulations":   advice.get("simulations_run", 0),
                "mrithi_viable": advice.get("mrithi_viable", False),
            })

    def log_game_over(self, scores: Dict, tricks_won: Dict, winner) -> None:
        self._write(EVENT_GAME_OVER, {
            "scores":     scores,
            "tricks_won": tricks_won,
            "winner":     winner,
        })
        self._fh.flush()

    def close(self) -> None:
        try:
            self._fh.flush()
            self._fh.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _write(self, event: str, payload: Dict[str, Any]) -> None:
        self._seq += 1
        record: Dict[str, Any] = {
            "game_id": self.game_id,
            "seq":     self._seq,
            "ts":      datetime.now(timezone.utc).isoformat(),
            "event":   event,
        }
        record.update(payload)
        line = json.dumps(record, ensure_ascii=False, default=str)
        self._fh.write(line + "\n")
        self._fh.flush()  # keep file readable mid-game
