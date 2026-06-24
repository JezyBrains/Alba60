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

const SIZE_MAP = {
  sm: { width: "w-10", height: "h-14", rank: "text-base", suit: "text-lg", pad: "p-1" },
  md: { width: "w-14", height: "h-20", rank: "text-xl", suit: "text-2xl", pad: "p-1.5" },
  lg: { width: "w-16", height: "h-24", rank: "text-2xl", suit: "text-3xl", pad: "p-2" },
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
        <span className={`text-sm ${isRed ? "suit-red" : "suit-black"} leading-none`}>
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
        <span className={`text-sm ${isRed ? "suit-red" : "suit-black"} leading-none`}>
          {symbol}
        </span>
      </div>
    </div>
  );
}
