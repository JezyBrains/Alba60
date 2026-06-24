"use client";

import { useLanguage } from "@/lib/LanguageContext";
import type { GameSnapshot, TrickResult, CardData } from "@/lib/types";
import { formatCard, SUIT_SYMBOLS, SUIT_COLORS } from "@/lib/types";

interface NarratorProps {
  state: GameSnapshot | null;
  lastTrickResult: TrickResult | null;
  inputMode: "user" | "opponent";
  phase: "setup" | "playing" | "drawing" | "game_over";
}

/**
 * Game State Narrator — the bold, instructional text at the top of the screen.
 * Tells the player exactly what just happened and what to do next.
 * Fully connected to the LanguageProvider for EN/SW bilingual output.
 */
export default function Narrator({ state, lastTrickResult, inputMode, phase }: NarratorProps) {
  const { t } = useLanguage();

  // Derive the narrative from current game state
  let primaryText = "";
  let secondaryText = "";

  if (!state || phase === "setup") {
    return null;
  }

  if (phase === "game_over") {
    primaryText = t("game.gameOver");
    return (
      <div className="w-full px-5 pt-8 pb-4 animate-fade-in">
        <p className="text-center text-2xl font-extrabold tracking-[0.25em] text-white uppercase drop-shadow-md">{primaryText}</p>
      </div>
    );
  }

  // Drawing phase
  if (phase === "drawing") {
    primaryText = lastTrickResult
      ? lastTrickResult.trick_winner === 0
        ? `${t("narrator.youWon")} +${lastTrickResult.points_won} ${t("narrator.pts")}`
        : `${t("narrator.oppWon")} +${lastTrickResult.points_won} ${t("narrator.pts")}`
      : "";
    secondaryText = t("narrator.drawCard");

    return (
      <div className="w-full px-5 pt-8 pb-4 animate-fade-in flex flex-col items-center gap-1.5">
        {primaryText && (
          <p className="text-center text-lg font-bold text-white tracking-wide drop-shadow-sm">{primaryText}</p>
        )}
        <div className="bg-oracle-glow/10 border border-oracle-glow/30 px-4 py-1.5 rounded-full shadow-[0_0_15px_rgba(0,255,157,0.15)]">
          <p className="text-center text-[0.65rem] font-bold tracking-[0.25em] uppercase text-oracle-glow">{secondaryText}</p>
        </div>
      </div>
    );
  }

  // Playing phase — determine what's happening
  const trickCards = state.current_trick;

  if (trickCards.length === 0) {
    // No cards played in current trick
    if (lastTrickResult) {
      // Just finished a trick
      const winner = lastTrickResult.trick_winner;
      primaryText = winner === 0
        ? `${t("narrator.youWon")} +${lastTrickResult.points_won} ${t("narrator.pts")}`
        : `${t("narrator.oppWon")} +${lastTrickResult.points_won} ${t("narrator.pts")}`;
    }

    // Who leads?
    if (state.turn_index === 0) {
      secondaryText = t("narrator.yourTurn");
    } else {
      secondaryText = state.round_number === 0
        ? t("narrator.gameStart")
        : t("narrator.opponentTurn");
    }
  } else if (trickCards.length === 1) {
    // One card played — show it and prompt the next player
    const played = trickCards[0];
    const cardStr = formatCard(played.card);

    if (played.player === 1) {
      // Opponent played, it's our turn
      primaryText = `${t("narrator.opponentPlayed")} ${cardStr}.`;
      secondaryText = t("narrator.yourTurn");
    } else {
      // We played, waiting for opponent
      primaryText = `${t("narrator.youPlayed")} ${cardStr}.`;
      secondaryText = t("narrator.waiting");
    }
  }

  const isYourTurn = secondaryText === t("narrator.yourTurn");

  return (
    <div className="w-full px-5 pt-8 pb-4 animate-fade-in flex flex-col items-center gap-1.5">
      {primaryText && (
        <p className="text-center text-base font-medium text-ink-muted tracking-wide">{primaryText}</p>
      )}
      <div className={`px-4 py-1.5 rounded-full transition-all duration-500 ${isYourTurn ? "bg-oracle-glow/10 border border-oracle-glow/30 shadow-[0_0_15px_rgba(0,255,157,0.15)]" : "bg-game-glass border border-game-border"}`}>
        <p className={`text-center text-[0.65rem] font-bold tracking-[0.25em] uppercase ${isYourTurn ? "text-oracle-glow" : "text-ink-dim"}`}>{secondaryText}</p>
      </div>
    </div>
  );
}
