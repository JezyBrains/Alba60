"use client";

import { useLanguage } from "@/lib/LanguageContext";
import PlayingCard from "./PlayingCard";

interface OpponentAreaProps {
  cardCount: number;
  points: number;
  tricks: number;
  isTheirTurn: boolean;
  opponentKnownHand?: CardData[];
}

/** Opponent's area — face-down cards (or face-up in endgame) + score at the top of the screen */
export default function OpponentArea({ cardCount, points, tricks, isTheirTurn, opponentKnownHand = [] }: OpponentAreaProps) {
  const { t } = useLanguage();
  
  const showKnownCards = opponentKnownHand.length > 0;

  return (
    <div className="flex flex-col items-center pt-4 pb-2 px-4">
      {/* Label + score */}
      <div className="flex items-center gap-3 mb-3">
        <div
          className={`w-2 h-2 rounded-full transition-colors duration-300 ${
            isTheirTurn ? "bg-oracle-danger animate-pulse" : "bg-ink-dim"
          }`}
        />
        <span className="text-ink-muted text-xs tracking-widest uppercase">
          {t("game.opponent")}
        </span>
        <span className="text-ink text-sm font-semibold tabular-nums">{points}</span>
        <span className="text-ink-dim text-xs">{t("narrator.pts")}</span>
        <span className="text-ink-dim text-xs">· {tricks} {t("game.tricks").toLowerCase()}</span>
      </div>

      {/* Cards: Face-up in endgame, face-down otherwise */}
      <div className="flex gap-1.5 justify-center relative">
        {showKnownCards && (
          <div className="absolute -top-3 right-0 left-0 text-center">
             <span className="text-[0.55rem] text-oracle-glow tracking-widest uppercase bg-black/50 px-2 py-0.5 rounded-full">Known Hand</span>
          </div>
        )}
        {showKnownCards ? (
          opponentKnownHand.map((card, i) => (
            <PlayingCard
              key={`${card.suit}_${card.rank}_${i}`}
              card={card}
              size="sm"
            />
          ))
        ) : (
          Array.from({ length: Math.max(cardCount, 0) }).map((_, i) => (
            <PlayingCard
              key={i}
              card={{ suit: "SPADES", rank: "A" }}
              faceDown
              size="sm"
            />
          ))
        )}
        {cardCount === 0 && !showKnownCards && (
          <span className="text-ink-dim text-xs tracking-wider uppercase py-4">
            No cards
          </span>
        )}
      </div>
    </div>
  );
}
