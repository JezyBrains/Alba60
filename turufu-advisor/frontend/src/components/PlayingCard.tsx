"use client";

import { CardData, SUIT_SYMBOLS, SUIT_COLORS } from "@/lib/types";

interface PlayingCardProps {
  card: CardData;
  size?: "sm" | "md" | "lg";
  recommended?: boolean;
  selected?: boolean;
  faceDown?: boolean;
  onClick?: (card: CardData) => void;
  className?: string;
}

/**
 * Responsive SIZE_MAP — mobile defaults + desktop overrides via CSS classes.
 * Desktop (md:) breakpoint = 768px+
 */
const SIZE_MAP = {
  sm: {
    width: "w-10 md:w-14",
    height: "h-14 md:h-20",
    rank: "text-base md:text-xl",
    suit: "text-lg md:text-2xl",
    suitLabel: "text-sm md:text-base",
    pad: "p-1 md:p-1.5",
  },
  md: {
    width: "w-14 md:w-20",
    height: "h-20 md:h-28",
    rank: "text-xl md:text-2xl",
    suit: "text-2xl md:text-4xl",
    suitLabel: "text-sm md:text-lg",
    pad: "p-1.5 md:p-2",
  },
  lg: {
    width: "w-16 md:w-24",
    height: "h-24 md:h-36",
    rank: "text-2xl md:text-3xl",
    suit: "text-3xl md:text-5xl",
    suitLabel: "text-sm md:text-lg",
    pad: "p-2 md:p-3",
  },
};

export default function PlayingCard({
  card,
  size = "md",
  recommended = false,
  selected = false,
  faceDown = false,
  onClick,
  className = "",
}: PlayingCardProps) {
  const sz = SIZE_MAP[size];
  const symbol = SUIT_SYMBOLS[card.suit] || "?";
  const isRed = SUIT_COLORS[card.suit] === "red";

  if (faceDown) {
    return (
      <div
        className={`card-back ${sz.width} ${sz.height} ${className}`}
        style={{ aspectRatio: "2/3" }}
      />
    );
  }

  return (
    <div
      className={`
        card-face ${sz.width} ${sz.height} ${sz.pad}
        ${recommended ? "recommended animate-glow" : ""}
        ${selected ? "selected" : ""}
        ${onClick ? "cursor-pointer" : "cursor-default"}
        ${className}
      `}
      onClick={() => onClick?.(card)}
      style={{ aspectRatio: "2/3" }}
    >
      {/* Top-left rank + suit */}
      <div className="flex flex-col items-start leading-none">
        <span className={`${sz.rank} font-bold ${isRed ? "suit-red" : "suit-black"} leading-none`}>
          {card.rank}
        </span>
        <span className={`${sz.suitLabel} ${isRed ? "suit-red" : "suit-black"} leading-none`}>
          {symbol}
        </span>
      </div>

      {/* Center suit */}
      <div className="absolute inset-0 flex items-center justify-center">
        <span className={`${sz.suit} opacity-20 ${isRed ? "suit-red" : "suit-black"}`}>
          {symbol}
        </span>
      </div>

      {/* Bottom-right rank + suit (rotated 180°) */}
      <div className="flex flex-col items-end leading-none rotate-180">
        <span className={`${sz.rank} font-bold ${isRed ? "suit-red" : "suit-black"} leading-none`}>
          {card.rank}
        </span>
        <span className={`${sz.suitLabel} ${isRed ? "suit-red" : "suit-black"} leading-none`}>
          {symbol}
        </span>
      </div>
    </div>
  );
}
