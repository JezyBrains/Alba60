"use client";

import { useLanguage } from "@/lib/LanguageContext";

interface ScoreBoardProps {
  userPoints: number;
  opponentPoints: number;
  userTricks: number;
  opponentTricks: number;
  drawPileSize: number;
  roundNumber: number;
  mrithiThreatened: boolean;
}

export default function ScoreBoard({
  userPoints,
  opponentPoints,
  userTricks,
  opponentTricks,
  drawPileSize,
  roundNumber,
  mrithiThreatened,
}: ScoreBoardProps) {
  const { t } = useLanguage();

  const userWidth = Math.min((userPoints / 120) * 100, 100);
  const oppWidth = Math.min((opponentPoints / 120) * 100, 100);
  const winLine = (61 / 120) * 100;

  return (
    <div className="w-full px-5 py-4 animate-fade-in">
      {/* Points header */}
      <div className="flex justify-between items-baseline mb-3">
        <div className="flex flex-col">
          <span className="text-stat tabular-nums">{userPoints}</span>
          <span className="text-ink-tertiary text-[0.55rem] tracking-[0.2em] uppercase">
            {t("game.you")}
          </span>
        </div>

        <div className="flex flex-col items-center">
          <span className="text-ink-tertiary text-[0.55rem] tracking-[0.3em] uppercase">
            {t("game.of120")}
          </span>
        </div>

        <div className="flex flex-col items-end">
          <span className="text-stat tabular-nums">{opponentPoints}</span>
          <span className="text-ink-tertiary text-[0.55rem] tracking-[0.2em] uppercase">
            {t("game.opp")}
          </span>
        </div>
      </div>

      {/* Score bars */}
      <div className="relative w-full h-1.5 bg-surface-muted rounded-full mb-1">
        <div
          className="score-fill absolute top-0 left-0 h-full bg-ink rounded-full"
          style={{ width: `${userWidth}%` }}
        />
        <div
          className="absolute top-[-3px] h-[calc(100%+6px)] w-px bg-ink-tertiary/30"
          style={{ left: `${winLine}%` }}
        />
      </div>
      <div className="relative w-full h-1.5 bg-surface-muted rounded-full mb-4">
        <div
          className="score-fill absolute top-0 left-0 h-full bg-ink-tertiary rounded-full"
          style={{ width: `${oppWidth}%` }}
        />
        <div
          className="absolute top-[-3px] h-[calc(100%+6px)] w-px bg-ink-tertiary/30"
          style={{ left: `${winLine}%` }}
        />
      </div>

      {/* Meta stats row */}
      <div className="flex justify-between text-ink-tertiary text-[0.6rem] tracking-wider">
        <span>{t("game.tricks")} {userTricks}–{opponentTricks}</span>
        <span>{t("game.round")} {roundNumber}</span>
        <span>{drawPileSize} {t("game.inDeck")}</span>
      </div>

      {/* Mrithi warning */}
      {mrithiThreatened && (
        <div className="flex items-center justify-center gap-2 mt-3 animate-pulse-slow">
          <div className="w-1.5 h-1.5 rounded-full bg-oracle-danger" />
          <span className="text-oracle-danger text-[0.6rem] tracking-[0.2em] uppercase font-medium">
            {t("mrithi.threat")}
          </span>
        </div>
      )}
    </div>
  );
}
