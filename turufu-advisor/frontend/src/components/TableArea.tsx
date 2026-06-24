"use client";

import PlayingCard from "./PlayingCard";
import { useLanguage } from "@/lib/LanguageContext";
import { SUIT_SYMBOLS, SUIT_COLORS, POINT_VALUES, formatCard } from "@/lib/types";
import type { CardData } from "@/lib/types";

interface TrickPlay {
  player: number;
  card: CardData;
}

interface TableAreaProps {
  trumpSuit: string | null;
  currentTrick: TrickPlay[];
  drawPileSize: number;
  bottomTrumpCard?: CardData | null;
  bottomTrumpDrawnBy?: number | null;
}

/** The green felt center of the table — shows the current trick, trump indicator, and bottom trump */
export default function TableArea({
  trumpSuit,
  currentTrick,
  drawPileSize,
  bottomTrumpCard,
  bottomTrumpDrawnBy,
}: TableAreaProps) {
  const { t } = useLanguage();
  const isLastDraw = drawPileSize === 2;
  const bottomTrumpVisible = bottomTrumpCard && drawPileSize > 0 && bottomTrumpDrawnBy == null;

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

      {/* Draw pile badge + Bottom Trump — top right */}
      <div className="absolute top-3 right-3 flex items-center gap-2">
        {/* Bottom Trump card (face-up next to draw pile) */}
        {bottomTrumpVisible && (
          <div
            className={`
              relative flex items-center gap-1 bg-game-bg/60 border rounded-full px-2.5 py-1 shadow-inner
              transition-all duration-500
              ${isLastDraw
                ? "border-oracle-glow/50 animate-[pulse_2s_ease-in-out_infinite]"
                : "border-game-border"
              }
            `}
          >
            {/* Pulse ring for last draw */}
            {isLastDraw && (
              <div className="absolute -inset-1 rounded-full border border-oracle-glow/20 animate-[ping_2s_ease-in-out_infinite] pointer-events-none"></div>
            )}
            <span className="text-[0.5rem] text-ink-dim font-semibold tracking-wider uppercase">▼</span>
            <span
              className={`text-xs font-bold ${
                SUIT_COLORS[bottomTrumpCard.suit] === "red" ? "text-suit-red" : "text-white"
              }`}
            >
              {formatCard(bottomTrumpCard)}
            </span>
            {/* Point value badge */}
            {POINT_VALUES[bottomTrumpCard.rank] > 0 && (
              <span className="text-[0.5rem] text-oracle-glow font-bold tabular-nums">
                +{POINT_VALUES[bottomTrumpCard.rank]}
              </span>
            )}
          </div>
        )}

        {/* Draw pile count */}
        {drawPileSize > 0 && (
          <div className="flex items-center gap-1.5 bg-game-bg/60 border border-game-border rounded-full px-3 py-1 shadow-inner">
            <span className="text-ink-dim text-[0.65rem] tracking-wider">🂠</span>
            <span className="text-ink-muted text-[0.65rem] font-bold tabular-nums">{drawPileSize}</span>
          </div>
        )}
      </div>

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

      {/* Bottom Trump drawn notification */}
      {bottomTrumpCard && bottomTrumpDrawnBy != null && (
        <div className="absolute bottom-3 left-1/2 -translate-x-1/2 bg-game-bg/80 border border-game-border rounded-full px-4 py-1.5 shadow-inner">
          <p className="text-[0.55rem] text-ink-muted font-semibold tracking-wider uppercase">
            <span className={`font-bold ${bottomTrumpDrawnBy === 0 ? "text-oracle-glow" : "text-oracle-danger"}`}>
              {bottomTrumpDrawnBy === 0 ? t("game.you") : t("game.opp")}
            </span>
            {" drew "}
            <span className={`font-bold ${SUIT_COLORS[bottomTrumpCard.suit] === "red" ? "text-suit-red" : "text-white"}`}>
              {formatCard(bottomTrumpCard)}
            </span>
          </p>
        </div>
      )}
    </div>
  );
}
