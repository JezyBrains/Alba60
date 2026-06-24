"use client";

import PlayingCard from "./PlayingCard";
import { useLanguage } from "@/lib/LanguageContext";
import { SUIT_SYMBOLS, SUIT_COLORS } from "@/lib/types";
import type { CardData } from "@/lib/types";

interface TrickPlay {
  player: number;
  card: CardData;
}

interface TableAreaProps {
  trumpSuit: string | null;
  currentTrick: TrickPlay[];
  drawPileSize: number;
}

/** The green felt center of the table — shows the current trick and trump indicator */
export default function TableArea({ trumpSuit, currentTrick, drawPileSize }: TableAreaProps) {
  const { t } = useLanguage();

  return (
    <div className="glass-panel mx-3 px-4 py-8 flex flex-col items-center relative min-h-[180px] justify-center mt-2 mb-4">
      {/* Trump badge — top left */}
      {trumpSuit && (
        <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-game-bg/60 border border-game-border rounded-full px-3 py-1 shadow-inner">
          <span className="text-oracle-glow text-[0.55rem] font-bold tracking-[0.25em] uppercase drop-shadow-sm">
            {t("setup.turufu")}
          </span>
          <span
            className={`text-sm font-bold ${
              SUIT_COLORS[trumpSuit] === "red" ? "text-suit-red drop-shadow-md" : "text-white drop-shadow-md"
            }`}
          >
            {SUIT_SYMBOLS[trumpSuit]}
          </span>
        </div>
      )}

      {/* Draw pile badge — top right */}
      {drawPileSize > 0 && (
        <div className="absolute top-3 right-3 flex items-center gap-1.5 bg-game-bg/60 border border-game-border rounded-full px-3 py-1 shadow-inner">
          <span className="text-ink-dim text-[0.65rem] tracking-wider">🂠</span>
          <span className="text-ink-muted text-[0.65rem] font-bold tabular-nums">{drawPileSize}</span>
        </div>
      )}

      {/* Played cards */}
      {currentTrick.length === 0 ? (
        <div className="flex flex-col items-center opacity-30 mt-4">
          <p className="text-white text-[0.65rem] font-bold tracking-[0.4em] uppercase">— {t("game.playArea") || "TABLE"} —</p>
        </div>
      ) : (
        <div className="flex gap-8 items-end justify-center mt-4 w-full px-6">
          {currentTrick.map((tp, i) => {
            const isYou = tp.player === 0;
            return (
              <div key={i} className={`flex flex-col items-center gap-3 w-1/2 ${isYou ? 'animate-slide-up' : 'animate-slide-down'}`}>
                <span className={`text-[0.6rem] font-bold tracking-[0.25em] uppercase ${isYou ? 'text-oracle-glow' : 'text-ink-dim'}`}>
                  {isYou ? t("game.you") : t("game.opp")}
                </span>
                <div className={isYou ? "" : "opacity-80 scale-95"}>
                  <PlayingCard card={tp.card} size="lg" className="shadow-2xl" />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
