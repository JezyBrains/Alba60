"use client";

import { useLanguage } from "@/lib/LanguageContext";
import { AdvicePayload, SUIT_SYMBOLS, SUIT_COLORS } from "@/lib/types";

interface OracleDisplayProps {
  advice: AdvicePayload | null;
  isUserTurn: boolean;
}

export default function OracleDisplay({ advice, isUserTurn }: OracleDisplayProps) {
  const { t } = useLanguage();

  if (!advice || !advice.best_card) {
    return (
      <div className="flex flex-col items-center justify-center py-12 animate-fade-in">
        <p className="text-ink-tertiary text-sm tracking-widest uppercase">
          {isUserTurn ? t("oracle.calculating") : t("oracle.opponentTurn")}
        </p>
      </div>
    );
  }

  const card = advice.best_card;
  const symbol = SUIT_SYMBOLS[card.suit] || "";
  const color = SUIT_COLORS[card.suit] || "black";
  const prob = Math.round(advice.win_probability * 100);

  return (
    <div className="flex flex-col items-center justify-center py-8 px-4 animate-fade-in">
      {/* The Oracle — focal point */}
      <p className="text-ink-tertiary text-[0.65rem] tracking-[0.3em] uppercase mb-4">
        {t("oracle.playThis")}
      </p>

      <div className="flex items-baseline gap-3 mb-6">
        <span
          className={`text-oracle-xl ${
            color === "red" ? "suit-red" : "suit-black"
          }`}
        >
          {card.rank}
        </span>
        <span
          className={`text-[3rem] leading-none ${
            color === "red" ? "suit-red" : "suit-black"
          }`}
        >
          {symbol}
        </span>
      </div>

      {/* Win probability */}
      <div className="flex flex-col items-center gap-1 mb-4">
        <div className="flex items-baseline gap-1.5">
          <span className="text-stat tabular-nums">{prob}</span>
          <span className="text-ink-tertiary text-xs">%</span>
        </div>
        <p className="text-ink-tertiary text-[0.6rem] tracking-[0.2em] uppercase">
          {t("oracle.winProb")}
        </p>
      </div>

      {/* Mrithi indicator */}
      {advice.mrithi_viable && (
        <div className="flex items-center gap-2 mt-2 animate-pulse-slow">
          <div className="w-1.5 h-1.5 rounded-full bg-oracle-mrithi" />
          <span className="text-oracle-mrithi text-[0.6rem] tracking-[0.25em] uppercase font-medium">
            {t("oracle.mrithi")}
          </span>
        </div>
      )}

      {/* Simulation stats */}
      <p className="text-ink-tertiary/40 text-[0.55rem] tracking-wider mt-6 tabular-nums">
        {advice.simulations_run.toLocaleString()} {t("oracle.sims")} · {advice.determinizations_completed ?? 0} {t("oracle.worlds")}
      </p>
    </div>
  );
}
