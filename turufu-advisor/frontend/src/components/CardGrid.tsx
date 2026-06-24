"use client";

import { useState, useCallback } from "react";
import {
  CardData,
  SUITS,
  RANKS,
  SUIT_SYMBOLS,
  SUIT_COLORS,
  POINT_VALUES,
  cardKey,
} from "@/lib/types";

interface CardGridProps {
  /** Cards already played in the game — shown as disabled */
  playedCards: Set<string>;
  /** Cards currently in user's hand — highlighted */
  userHand: Set<string>;
  /** The AI recommended card key */
  recommendedCard: string | null;
  /** Callback when a card is tapped */
  onCardTap: (card: CardData) => void;
  /** Label shown above the grid */
  label: string;
  /** Whether to allow multi-select mode (for hand setup / drawing) */
  multiSelect?: boolean;
  /** Callback for multi-select confirmation */
  onConfirm?: (cards: CardData[]) => void;
  /** How many cards to select in multi-select mode */
  selectCount?: number;
}

export default function CardGrid({
  playedCards,
  userHand,
  recommendedCard,
  onCardTap,
  label,
  multiSelect = false,
  onConfirm,
  selectCount,
}: CardGridProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const handleTap = useCallback(
    (card: CardData) => {
      const key = cardKey(card);
      if (playedCards.has(key)) return;

      if (multiSelect) {
        setSelected((prev) => {
          const next = new Set(prev);
          if (next.has(key)) {
            next.delete(key);
          } else {
            if (selectCount && next.size >= selectCount) return prev;
            next.add(key);
          }
          return next;
        });
      } else {
        onCardTap(card);
      }
    },
    [playedCards, multiSelect, selectCount, onCardTap]
  );

  const handleConfirm = useCallback(() => {
    if (!onConfirm) return;
    const cards: CardData[] = [];
    selected.forEach((key) => {
      const [rank, suit] = key.split("_");
      cards.push({ suit, rank });
    });
    onConfirm(cards);
    setSelected(new Set());
  }, [selected, onConfirm]);

  return (
    <div className="w-full animate-slide-up">
      {/* Label */}
      <div className="flex items-center justify-between px-5 mb-3">
        <span className="text-ink-tertiary text-[0.6rem] tracking-[0.3em] uppercase">
          {label}
        </span>
        {multiSelect && selectCount && (
          <span className="text-ink-tertiary text-[0.6rem] tabular-nums">
            {selected.size} / {selectCount}
          </span>
        )}
      </div>

      {/* The Grid — 9 columns (one per rank), 4 rows (one per suit) */}
      <div className="px-3">
        {SUITS.map((suit) => {
          const color = SUIT_COLORS[suit];
          const symbol = SUIT_SYMBOLS[suit];

          return (
            <div key={suit} className="flex gap-1.5 mb-1.5">
              {/* Suit indicator */}
              <div
                className={`flex items-center justify-center w-8 text-lg ${
                  color === "red" ? "suit-red" : "suit-black"
                }`}
              >
                {symbol}
              </div>

              {/* Rank cells */}
              {RANKS.map((rank) => {
                const card: CardData = { suit, rank };
                const key = cardKey(card);
                const isPlayed = playedCards.has(key);
                const isInHand = userHand.has(key);
                const isRecommended = recommendedCard === key;
                const isSelected = selected.has(key);

                let cellClass = "card-cell ";
                if (isPlayed) {
                  cellClass += "card-cell-played";
                } else if (isSelected || isInHand) {
                  cellClass += "card-cell-selected";
                } else {
                  cellClass += "card-cell-idle";
                }

                if (isRecommended && !isPlayed) {
                  cellClass += " oracle-recommended";
                }

                return (
                  <button
                    key={key}
                    className={`${cellClass} flex-1`}
                    onClick={() => handleTap(card)}
                    disabled={isPlayed}
                    aria-label={`${rank} of ${suit}`}
                  >
                    <span
                      className={
                        isPlayed
                          ? ""
                          : isSelected || isInHand
                          ? "text-ink-inverse"
                          : color === "red"
                          ? "suit-red"
                          : "suit-black"
                      }
                    >
                      {rank}
                    </span>
                  </button>
                );
              })}
            </div>
          );
        })}
      </div>

      {/* Multi-select confirm button */}
      {multiSelect && onConfirm && (
        <div className="px-5 mt-4">
          <button
            onClick={handleConfirm}
            disabled={selectCount ? selected.size !== selectCount : selected.size === 0}
            className="w-full py-3.5 bg-ink text-ink-inverse text-sm font-medium tracking-wider uppercase rounded-lg
                       disabled:opacity-20 transition-opacity duration-200 active:scale-[0.98]"
          >
            Confirm
          </button>
        </div>
      )}
    </div>
  );
}
