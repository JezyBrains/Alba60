"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import { useGameSocket } from "@/hooks/useGameSocket";
import { useLanguage } from "@/lib/LanguageContext";
import { cardKey, SUIT_SYMBOLS, SUIT_COLORS } from "@/lib/types";
import type { CardData, GamePhase } from "@/lib/types";

import GameSetup from "./GameSetup";
import Narrator from "./Narrator";
import OpponentArea from "./OpponentArea";
import TableArea from "./TableArea";
import HandDisplay from "./HandDisplay";
import OpponentLogger from "./OpponentLogger";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const HAND_SIZE = 6;

export default function GameBoard() {
  const { connected, state, advice, lastTrickResult, error, playCard, drawCards, clearTrickResult, setGameId } =
    useGameSocket();
  const { t, lang, toggleLang } = useLanguage();

  const [phase, setPhase] = useState<GamePhase>("setup");
  const [inputMode, setInputMode] = useState<"user" | "opponent">("opponent");
  const [showTrickOverlay, setShowTrickOverlay] = useState(false);
  const [showDrawSheet, setShowDrawSheet] = useState(false);
  const [drawSelected, setDrawSelected] = useState<Set<string>>(new Set());

  // Recommended card key
  const recommendedKey = useMemo(() => {
    if (!advice?.best_card) return null;
    return cardKey(advice.best_card);
  }, [advice]);

  // Cards that are unavailable for drawing (already played, in hand, or known opponent)
  const unavailableCards = useMemo(() => {
    const keys = new Set<string>();
    // Cards already played in the game
    for (const c of state?.played_cards || []) keys.add(cardKey(c));
    // Cards currently in user's hand
    for (const c of state?.user_hand || []) keys.add(cardKey(c));
    // Cards in the current trick (being played right now)
    for (const tp of state?.current_trick || []) keys.add(cardKey(tp.card));
    // Known opponent hand cards
    for (const c of state?.opponent_known_hand || []) keys.add(cardKey(c));
    return keys;
  }, [state?.played_cards, state?.user_hand, state?.current_trick, state?.opponent_known_hand]);

  // Sync inputMode to backend turn_index
  useEffect(() => {
    if (state && phase === "playing") {
      setInputMode(state.turn_index === 0 ? "user" : "opponent");
    }
  }, [state?.turn_index, phase]);

  // Trick resolution overlay
  useEffect(() => {
    if (!lastTrickResult) return;
    setShowTrickOverlay(true);
    const t = setTimeout(() => {
      setShowTrickOverlay(false);
      clearTrickResult();
      // Draw sheet is now triggered by state.user_draw_pending from server
      // (avoids stale closure over draw_pile_size)
    }, 1800);
    return () => clearTimeout(t);
  }, [lastTrickResult]);

  // When server says user must draw, show the draw sheet
  // But skip if there's nothing to draw (pile empty or hand full)
  useEffect(() => {
    if (state?.user_draw_pending && phase === "playing" && !showTrickOverlay) {
      const needed = Math.min(
        HAND_SIZE - (state?.user_hand?.length || 0),
        state?.draw_pile_size || 0
      );
      if (needed <= 0) {
        // Nothing to draw — send empty draw to clear the pending flag
        drawCards([]);
        return;
      }
      setShowDrawSheet(true);
      setPhase("drawing");
    }
  }, [state?.user_draw_pending, showTrickOverlay]);

  useEffect(() => {
    if (state?.game_over) setPhase("game_over");
  }, [state?.game_over]);

  // Init game
  const handleInitialize = useCallback(async (trumpSuit: string, hand: CardData[]) => {
    try {
      const res = await fetch(`${API_URL}/game/init`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ trump_suit: trumpSuit, user_hand: hand, num_players: 2 }),
      });
      if (res.ok) {
        const data = await res.json();
        // Seed the WebSocket hook with the new game ID immediately
        if (data.game_id) setGameId(data.game_id);
        setPhase("playing");
        setInputMode("opponent");
      }
    } catch (e) { console.error(e); }
  }, [setGameId]);

  // User plays a card from their hand
  const handleUserPlay = useCallback((card: CardData) => {
    if (inputMode !== "user") return;
    playCard(0, card);
  }, [inputMode, playCard]);

  // Log opponent's card from the bottom sheet
  const handleOpponentCard = useCallback((card: CardData) => {
    playCard(1, card);
  }, [playCard]);

  // Confirm drawn cards — server validates the card; sheet closes only on success
  const handleDrawConfirm = useCallback(() => {
    const cards: CardData[] = [...drawSelected].map((key) => {
      const [rank, suit] = key.split("_");
      return { suit, rank };
    });
    drawCards(cards);
    setDrawSelected(new Set());
    // Don't close the sheet here — the useEffect on state.user_draw_pending
    // will close it once the server validates and clears the flag.
    // If the server rejects (already-played card), the error toast fires
    // and the sheet stays open so the user can correct their entry.
  }, [drawSelected, drawCards]);

  // Close draw sheet as soon as server confirms draw is valid
  useEffect(() => {
    if (!state?.user_draw_pending && phase === "drawing") {
      setShowDrawSheet(false);
      setPhase("playing");
    }
  }, [state?.user_draw_pending, phase]);

  // ---- SETUP ----
  if (phase === "setup") return <GameSetup onInitialize={handleInitialize} />;

  // ---- GAME OVER ----
  if (phase === "game_over" && state) {
    const userPts = state.scores[0] || 0;
    const oppPts = state.scores[1] || 0;
    const won = userPts >= 61;
    const skunked = won && oppPts < 10;

    return (
      <div className="min-h-dvh bg-game flex flex-col items-center justify-center px-6 animate-fade-in relative pb-10">
        <button onClick={toggleLang} className="absolute top-6 right-6 text-ink-dim text-[0.65rem] tracking-[0.25em] uppercase hover:text-white transition-colors z-10 font-semibold">
          {lang === "en" ? "EN / SW" : "SW / EN"}
        </button>

        <div className="glass-panel p-10 flex flex-col items-center gap-5 w-full max-w-sm relative overflow-hidden">
          {/* Subtle glow behind the panel text */}
          <div className={`absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-1/2 blur-[50px] rounded-full opacity-20 pointer-events-none ${won ? 'bg-oracle-glow' : 'bg-oracle-danger'}`}></div>
          
          <p className="text-white/50 text-[0.65rem] font-medium tracking-[0.3em] uppercase relative z-10">{t("game.gameOver")}</p>
          <h1 className={`text-5xl font-extrabold relative z-10 drop-shadow-lg ${won ? "text-oracle-glow" : "text-oracle-danger"}`}>
            {won ? (skunked ? "MRITHI" : t("game.victory").toUpperCase()) : t("game.defeat").toUpperCase()}
          </h1>

          <div className="flex gap-10 mt-4 relative z-10">
            <div className="flex flex-col items-center">
              <span className="text-4xl font-bold text-white tabular-nums drop-shadow-md">{userPts}</span>
              <span className="text-ink-dim text-[0.6rem] tracking-[0.25em] font-semibold uppercase mt-1">{t("game.you")}</span>
            </div>
            <div className="text-white/10 text-4xl font-light self-center">|</div>
            <div className="flex flex-col items-center">
              <span className="text-4xl font-bold text-ink-muted tabular-nums drop-shadow-md">{oppPts}</span>
              <span className="text-ink-dim text-[0.6rem] tracking-[0.25em] font-semibold uppercase mt-1">{t("game.opp")}</span>
            </div>
          </div>

          {skunked && (
            <p className="text-oracle-mrithi text-xs font-bold tracking-[0.2em] uppercase animate-pulse mt-2 relative z-10">
              {t("mrithi.2xvp")}
            </p>
          )}
        </div>

        <button
          onClick={() => { setPhase("setup"); setInputMode("opponent"); }}
          className="mt-10 w-full max-w-sm py-4 bg-oracle-glow text-game-bg shadow-neon font-extrabold tracking-[0.25em] uppercase rounded-2xl active:scale-95 transition-all hover:shadow-[0_0_25px_rgba(0,255,157,0.7)]"
        >
          {t("game.newGame")}
        </button>
      </div>
    );
  }

  // ---- PLAYING / DRAWING ----
  const userPts  = state?.scores?.[0] || 0;
  const oppPts   = state?.scores?.[1] || 0;
  const winLine  = (61 / 120) * 100;

  return (
    <div className="min-h-dvh bg-game flex flex-col relative overflow-hidden">

      {/* Language toggle */}
      <button onClick={toggleLang} className="absolute top-6 right-6 z-50 text-ink-dim text-[0.65rem] tracking-[0.25em] uppercase hover:text-white transition-colors font-semibold">
        {lang === "en" ? "EN / SW" : "SW / EN"}
      </button>

      {/* Reconnecting banner */}
      {!connected && (
        <div className="flex items-center justify-center py-2 bg-oracle-danger/90 z-50 backdrop-blur-md shadow-md">
          <span className="text-white text-[0.65rem] font-bold tracking-[0.25em] uppercase drop-shadow-sm">{t("game.reconnecting")}</span>
        </div>
      )}

      {/* ---- OPPONENT AREA ---- */}
      <OpponentArea
        cardCount={HAND_SIZE - (state?.current_trick.filter(t => t.player === 1).length || 0)}
        points={oppPts}
        tricks={state?.tricks_won?.[1] || 0}
        isTheirTurn={inputMode === "opponent"}
        opponentKnownHand={state?.opponent_known_hand}
      />

      {/* ---- NARRATOR ---- */}
      <Narrator
        state={state ?? null}
        lastTrickResult={lastTrickResult}
        inputMode={inputMode}
        phase={phase}
      />

      {/* ---- TABLE (FELT) ---- */}
      <TableArea
        trumpSuit={state?.trump_suit ?? null}
        currentTrick={(state?.current_trick || []).map(tp => ({
          player: tp.player,
          card: tp.card,
        }))}
        drawPileSize={state?.draw_pile_size || 0}
      />

      {/* ---- ORACLE PANEL ---- */}
      {inputMode === "user" && advice?.best_card && (
        <div className="oracle-panel rounded-2xl mx-3 mt-3 px-4 py-3 flex items-center gap-4 animate-fade-in">
          <div className="flex flex-col">
            <span className="text-oracle-glow text-[0.55rem] tracking-[0.3em] uppercase mb-0.5">
              {t("oracle.playThis")}
            </span>
            <div className="flex items-baseline gap-1.5">
              <span className={`text-3xl font-bold ${SUIT_COLORS[advice.best_card.suit] === "red" ? "text-red-400" : "text-white"}`}>
                {advice.best_card.rank}
              </span>
              <span className={`text-2xl ${SUIT_COLORS[advice.best_card.suit] === "red" ? "text-red-400" : "text-white"}`}>
                {SUIT_SYMBOLS[advice.best_card.suit]}
              </span>
            </div>
          </div>

          <div className="flex-1" />

          <div className="flex flex-col items-end">
            <span className="text-oracle-glow text-2xl font-bold tabular-nums">
              {Math.round(advice.win_probability * 100)}%
            </span>
            <span className="text-ink-dim text-[0.55rem] tracking-wider uppercase">
              {t("oracle.winProb")}
            </span>
          </div>

          {advice.mrithi_viable && (
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-oracle-mrithi animate-pulse" />
              <span className="text-oracle-mrithi text-[0.55rem] tracking-wider uppercase">Mrithi</span>
            </div>
          )}
        </div>
      )}

      {/* ---- SCORE BARS ---- */}
      {state && (
        <div className="mx-3 mt-3 flex flex-col gap-1.5">
          {/* User bar */}
          <div className="flex items-center gap-2">
            <span className="text-ink-dim text-[0.6rem] w-6 text-right tabular-nums">{userPts}</span>
            <div className="score-bar-track flex-1 relative">
              <div className="score-bar-fill bg-oracle-glow" style={{ width: `${(userPts / 120) * 100}%` }} />
              <div className="absolute top-0 h-full w-px bg-white/20" style={{ left: `${winLine}%` }} />
            </div>
            <span className="text-ink-dim text-[0.6rem] w-4">{t("game.you")}</span>
          </div>
          {/* Opp bar */}
          <div className="flex items-center gap-2">
            <span className="text-ink-dim text-[0.6rem] w-6 text-right tabular-nums">{oppPts}</span>
            <div className="score-bar-track flex-1 relative">
              <div className="score-bar-fill bg-oracle-danger/70" style={{ width: `${(oppPts / 120) * 100}%` }} />
              <div className="absolute top-0 h-full w-px bg-white/20" style={{ left: `${winLine}%` }} />
            </div>
            <span className="text-ink-dim text-[0.6rem] w-4">{t("game.opp")}</span>
          </div>
        </div>
      )}

      {/* ---- USER HAND ---- */}
      <div className="mt-auto pt-3 pb-4 safe-area-bottom">
        {phase === "playing" && (
          <>
            {inputMode === "user" ? (
              /* User's actual cards */
              <HandDisplay
                hand={state?.user_hand || []}
                recommendedKey={recommendedKey}
                onCardPlay={handleUserPlay}
              />
            ) : (
              /* Log opponent's card */
              <OpponentLogger onCardSelected={handleOpponentCard} unavailableCards={unavailableCards} />
            )}
          </>
        )}

        {/* Drawing phase */}
        {phase === "drawing" && showDrawSheet && (
          <div className="animate-slide-up px-4">
            <p className="text-oracle-glow text-[0.65rem] font-bold tracking-[0.25em] uppercase mb-4 text-center drop-shadow-sm">
              {t("game.drawCards")}
            </p>
            {/* Quick draw grid */}
            <div className="space-y-3">
              {["SPADES","HEARTS","DIAMONDS","CLUBS"].map((suit) => {
                const isRed = SUIT_COLORS[suit] === "red";
                return (
                  <div key={suit} className="flex items-center gap-2">
                    <div className={`w-8 h-8 flex items-center justify-center rounded-full glass-panel shrink-0 ${isRed ? "text-suit-red bg-suit-redDim" : "text-white bg-suit-blackDim"}`}>
                      <span className="text-lg leading-none drop-shadow-md">{SUIT_SYMBOLS[suit]}</span>
                    </div>
                    <div className="flex-1 grid grid-cols-9 gap-1">
                      {["A","7","K","J","Q","6","5","4","3"].map((rank) => {
                        const key = `${rank}_${suit}`;
                        const isSel = drawSelected.has(key);
                        const isUsed = unavailableCards.has(key);
                        const needed = Math.min(HAND_SIZE - (state?.user_hand.length || 0), state?.draw_pile_size || 0);
                        return (
                          <button
                            key={key}
                            disabled={isUsed}
                            onClick={() => {
                              if (isUsed) return;
                              setDrawSelected(prev => {
                                const next = new Set(prev);
                                if (next.has(key)) { next.delete(key); }
                                else if (next.size < needed) { next.add(key); }
                                return next;
                              });
                            }}
                            className={`
                              flex-1 h-10 rounded-lg text-xs font-bold transition-all duration-200 border
                              ${isUsed
                                ? "bg-game-bg/30 border-game-border/30 text-ink-dim/30 line-through cursor-not-allowed opacity-40"
                                : isSel
                                  ? isRed
                                    ? "bg-suit-red border-suit-red text-white shadow-neonDanger active:scale-90"
                                    : "bg-white border-white text-game-bg shadow-glass active:scale-90"
                                  : "bg-game-glass border-game-border text-ink-muted hover:bg-game-glassHover hover:text-white active:scale-90"
                              }
                            `}
                          >
                            {rank}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
            <button
              onClick={handleDrawConfirm}
              disabled={drawSelected.size === 0}
              className={`
                mt-6 w-full py-4 rounded-2xl text-sm font-extrabold tracking-[0.25em] uppercase
                transition-all duration-300 active:scale-[0.98] relative overflow-hidden
                ${drawSelected.size > 0 
                  ? "bg-oracle-glow text-game-bg shadow-neon hover:shadow-[0_0_25px_rgba(0,255,157,0.7)]" 
                  : "bg-game-glass border border-game-border text-ink-dim pointer-events-none"}
              `}
            >
              {t("game.confirm")}
            </button>
          </div>
        )}
      </div>

      {/* ---- TRICK RESULT OVERLAY ---- */}
      {showTrickOverlay && lastTrickResult && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-game-bg/80 backdrop-blur-md animate-fade-in">
          <div className="glass-panel px-12 py-10 flex flex-col items-center gap-4 relative overflow-hidden">
            <div className={`absolute top-0 left-1/2 -translate-x-1/2 w-full h-1/2 blur-[40px] rounded-full opacity-20 pointer-events-none ${lastTrickResult.trick_winner === 0 ? 'bg-oracle-glow' : 'bg-oracle-danger'}`}></div>
            <p className="text-white/50 text-[0.65rem] font-medium tracking-[0.3em] uppercase relative z-10">
              {lastTrickResult.trick_winner === 0 ? t("narrator.youWon") : t("narrator.oppWon")}
            </p>
            <span className={`text-6xl font-extrabold drop-shadow-lg relative z-10 ${lastTrickResult.trick_winner === 0 ? "text-oracle-glow" : "text-oracle-danger"}`}>
              +{lastTrickResult.points_won}
            </span>
            <span className="text-white/40 text-[0.65rem] font-bold tracking-[0.25em] uppercase relative z-10">{t("narrator.pts")}</span>
          </div>
        </div>
      )}

      {/* ---- ERROR TOAST ---- */}
      {error && (
        <div className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 px-5 py-2.5 bg-oracle-danger text-white text-xs tracking-wider rounded-full animate-fade-in">
          {error}
        </div>
      )}
    </div>
  );
}
