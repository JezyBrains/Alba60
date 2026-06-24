"use client";

import { useLanguage } from "@/lib/LanguageContext";
import PlayingCard from "./PlayingCard";
import type { CardData } from "@/lib/types";
import { cardKey } from "@/lib/types";

interface HandDisplayProps {
  hand: CardData[];
  recommendedKey: string | null;
  onCardPlay: (card: CardData) => void;
  disabled?: boolean;
}

/**
 * The player's hand — displayed as real cards in a scrollable row.
 * Recommended card glows and lifts. Tapping plays it instantly.
 */
export default function HandDisplay({
  hand,
  recommendedKey,
  onCardPlay,
  disabled = false,
}: HandDisplayProps) {
  const { t } = useLanguage();

  if (hand.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="text-ink-dim text-sm tracking-wider uppercase">
          {t("game.drawCards")}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <p className="text-ink-dim text-[0.6rem] tracking-[0.25em] uppercase">
        {disabled ? t("game.opponent") + " " + t("narrator.opponentTurn") : t("game.selectCard")}
      </p>

      {/* Scrollable card row — large tap targets */}
      <div className="flex gap-2.5 justify-center px-4 overflow-x-auto pb-2">
        {hand.map((card) => {
          const key = cardKey(card);
          const isRecommended = key === recommendedKey;

          return (
            <PlayingCard
              key={key}
              card={card}
              size="lg"
              recommended={isRecommended && !disabled}
              onClick={disabled ? undefined : onCardPlay}
            />
          );
        })}
      </div>
    </div>
  );
}
