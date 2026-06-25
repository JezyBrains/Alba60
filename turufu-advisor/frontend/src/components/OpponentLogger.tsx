"use client";

import { useState } from "react";
import { useLanguage } from "@/lib/LanguageContext";
import { SUITS, RANKS, SUIT_SYMBOLS, SUIT_COLORS, cardKey } from "@/lib/types";
import type { CardData } from "@/lib/types";

interface OpponentLoggerProps {
  onCardSelected: (card: CardData) => void;
  onClose?: () => void;
  unavailableCards?: Set<string>;
}

/**
 * Compact bottom-sheet for logging the opponent's played card.
 * Shows a 4×9 grid (suit rows × rank cols) as large tap targets.
 * Selecting a card immediately fires the callback — no confirm needed.
 * Cards already played/in-hand are greyed out and not selectable.
 */
export default function OpponentLogger({ onCardSelected, onClose, unavailableCards }: OpponentLoggerProps) {
  const { t } = useLanguage();

  const handleTap = (card: CardData) => {
    onCardSelected(card);
  };

  return (
    <div className="animate-slide-up bg-game-glass backdrop-blur-xl border-t border-game-border pt-4 pb-2 px-3 rounded-t-3xl shadow-glass mt-2">
      {/* Header */}
      <div className="flex items-center justify-between px-2 mb-4">
        <span className="text-oracle-danger text-[0.65rem] md:text-sm font-bold tracking-[0.25em] uppercase drop-shadow-sm">
          {t("game.logOpponent")}
        </span>
        {onClose && (
          <button
            onClick={onClose}
            className="text-ink-dim hover:text-white transition-colors"
          >
            ✕
          </button>
        )}
      </div>

      {/* 4-suit × 9-rank grid */}
      <div className="space-y-3 pb-2">
        {SUITS.map((suit) => {
          const isRed = SUIT_COLORS[suit] === "red";

          return (
            <div key={suit} className="flex items-center gap-2">
              {/* Suit label */}
              <div className={`w-8 h-8 md:w-12 md:h-12 flex items-center justify-center rounded-full glass-panel shrink-0 ${isRed ? "text-suit-red bg-suit-redDim" : "text-white bg-suit-blackDim"}`}>
                <span className="text-lg md:text-2xl leading-none drop-shadow-md">{SUIT_SYMBOLS[suit]}</span>
              </div>

              {/* Rank buttons */}
              <div className="flex-1 grid grid-cols-9 gap-1 md:gap-2">
                {RANKS.map((rank) => {
                  const card: CardData = { suit, rank };
                  const key = cardKey(card);
                  const isUsed = unavailableCards?.has(key) ?? false;

                  return (
                    <button
                      key={key}
                      disabled={isUsed}
                      onPointerDown={() => { if (!isUsed) handleTap(card); }}
                      className={`
                        flex-1 h-10 md:h-14 rounded-lg md:rounded-xl text-sm md:text-lg font-bold
                        transition-all duration-200 border flex items-center justify-center
                        ${isUsed
                          ? "bg-game-surface/40 border-white/5 text-white/15 line-through cursor-not-allowed"
                          : "bg-game-surface border-white/20 text-white hover:bg-white/20 hover:border-white/40 active:scale-90 active:shadow-neon"
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
    </div>
  );
}
