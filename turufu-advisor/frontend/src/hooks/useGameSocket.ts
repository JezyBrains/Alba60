"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type {
  GameSnapshot,
  AdvicePayload,
  TrickResult,
  WSMessage,
  CardData,
} from "@/lib/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws/game";

interface GameSocketState {
  connected: boolean;
  gameId: string | null;
  state: GameSnapshot | null;
  advice: AdvicePayload | null;
  lastTrickResult: TrickResult | null;
  error: string | null;
}

export function useGameSocket() {
  const wsRef     = useRef<WebSocket | null>(null);
  const gameIdRef = useRef<string | null>(null);

  const [socketState, setSocketState] = useState<GameSocketState>({
    connected: false,
    gameId: null,
    state: null,
    advice: null,
    lastTrickResult: null,
    error: null,
  });

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setSocketState((s) => ({ ...s, connected: true, error: null }));
    };

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage & { game_id?: string } = JSON.parse(event.data);

        if (msg.type === "connected" || msg.type === "update") {
          if (msg.game_id) {
            gameIdRef.current = msg.game_id;
          }
          setSocketState((s) => ({
            ...s,
            gameId: msg.game_id ?? s.gameId,
            state: msg.state ?? s.state,
            advice: msg.advice !== undefined ? msg.advice : s.advice,
            lastTrickResult: msg.trick_result ?? null,
            error: null,
          }));
        } else if (msg.type === "error") {
          const isMismatch = (msg.message ?? "").includes("game_id mismatch");
          setSocketState((s) => ({
            ...s,
            advice: isMismatch ? null : s.advice,
            error: msg.message ?? "Unknown error",
          }));
        }
      } catch {
        // Silently ignore malformed messages
      }
    };

    ws.onclose = () => {
      setSocketState((s) => ({ ...s, connected: false }));
      setTimeout(connect, 2000);
    };

    ws.onerror = () => {
      setSocketState((s) => ({ ...s, error: "Connection lost" }));
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const payload = gameIdRef.current
        ? { game_id: gameIdRef.current, ...data }
        : data;
      wsRef.current.send(JSON.stringify(payload));
    }
  }, []);

  /** Called by GameBoard after /game/init so the hook tracks the new ID immediately */
  const setGameId = useCallback((id: string) => {
    gameIdRef.current = id;
    setSocketState((s) => ({ ...s, gameId: id }));
  }, []);

  const playCard = useCallback(
    (playerId: number, card: CardData) => {
      send({ type: "play", player_id: playerId, card });
    },
    [send]
  );

  const drawCards = useCallback(
    (cards: CardData[]) => {
      send({ type: "draw", cards });
    },
    [send]
  );

  const registerSwap = useCallback(
    (given: CardData[], received: CardData[]) => {
      send({ type: "swap", cards_given: given, cards_received: received });
    },
    [send]
  );

  const requestAdvice = useCallback(() => {
    send({ type: "advice" });
  }, [send]);

  const requestState = useCallback(() => {
    send({ type: "state" });
  }, [send]);

  const clearTrickResult = useCallback(() => {
    setSocketState((s) => ({ ...s, lastTrickResult: null }));
  }, []);

  return {
    ...socketState,
    setGameId,
    playCard,
    drawCards,
    registerSwap,
    requestAdvice,
    requestState,
    clearTrickResult,
  };
}
