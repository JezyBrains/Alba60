"use client";

import { useState, useCallback } from "react";
import { useLanguage } from "@/lib/LanguageContext";
import { SUITS, RANKS, SUIT_SYMBOLS, SUIT_COLORS, cardKey } from "@/lib/types";
import type { CardData } from "@/lib/types";
import PlayingCard from "./PlayingCard";

const HAND_SIZE = 6;

interface GameSetupProps {
  onInitialize: (trumpSuit: string, hand: CardData[]) => void;
}

export default function GameSetup({ onInitialize }: GameSetupProps) {
  const { t, lang, toggleLang } = useLanguage();
  const [step, setStep] = useState<"trump" | "hand">("trump");
  const [trumpSuit, setTrumpSuit] = useState<string | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());

  const toggleCard = useCallback((card: CardData) => {
    const key = cardKey(card);
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) { next.delete(key); }
      else if (next.size < HAND_SIZE) { next.add(key); }
      return next;
    });
  }, []);

  const handleStart = useCallback(() => {
    if (!trumpSuit || selectedKeys.size !== HAND_SIZE) return;
    const cards: CardData[] = [...selectedKeys].map((key) => {
      const [rank, suit] = key.split("_");
      return { suit, rank };
    });
    onInitialize(trumpSuit, cards);
  }, [trumpSuit, selectedKeys, onInitialize]);

  return (
    <div className="min-h-dvh bg-game flex flex-col relative animate-fade-in pb-10">
      {/* Language toggle */}
      <button
        onClick={toggleLang}
        className="absolute top-6 right-6 text-ink-dim text-[0.65rem] tracking-[0.25em] uppercase hover:text-white transition-colors z-10 font-semibold"
      >
        {lang === "en" ? "EN / SW" : "SW / EN"}
      </button>

      {/* ---- Trump Selection ---- */}
      {step === "trump" && (
        <div className="flex flex-col items-center justify-center flex-1 px-6 mt-12">
          {/* Glowing Title */}
          <div className="relative mb-2">
            <div className="absolute -inset-4 bg-oracle-glow opacity-10 blur-2xl rounded-full"></div>
            <h1 className="relative text-5xl font-extrabold tracking-tighter bg-clip-text text-transparent bg-gradient-to-br from-white via-ink-muted to-ink-dim drop-shadow-md">
              Albastini
            </h1>
          </div>
          <p className="text-ink-dim text-[0.65rem] font-medium tracking-[0.3em] uppercase mb-16 text-center">
            {t("setup.selectTrump")}
          </p>

          <div className="grid grid-cols-2 gap-5 w-full max-w-sm">
            {SUITS.map((suit) => {
              const isRed = SUIT_COLORS[suit] === "red";
              return (
                <button
                  key={suit}
                  onClick={() => { setTrumpSuit(suit); setStep("hand"); }}
                  className={`
                    relative overflow-hidden group
                    flex flex-col items-center justify-center py-10 rounded-2xl
                    transition-all duration-300 ease-out active:scale-95
                    glass-panel
                    ${isRed
                      ? "hover:border-suit-red/40 hover:shadow-neonDanger bg-gradient-to-br from-suit-redDim to-transparent"
                      : "hover:border-white/20 hover:shadow-glass bg-gradient-to-br from-suit-blackDim to-transparent"
                    }
                  `}
                >
                  {/* Subtle inner top highlight */}
                  <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
                  
                  <span className={`text-6xl mb-3 drop-shadow-lg transition-transform duration-300 group-hover:scale-110 group-hover:-translate-y-1 ${isRed ? "text-suit-red" : "text-white"}`}>
                    {SUIT_SYMBOLS[suit]}
                  </span>
                  <span className="text-ink-muted text-[0.65rem] font-semibold tracking-[0.25em] uppercase">
                    {suit.toLowerCase()}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* ---- Hand Selection ---- */}
      {step === "hand" && (
        <div className="flex flex-col flex-1 px-5 pt-8 pb-6 max-w-lg mx-auto w-full">
          {/* Header */}
          <div className="flex items-center gap-4 mb-2">
            <button
              onClick={() => { setStep("trump"); setTrumpSuit(null); setSelectedKeys(new Set()); }}
              className="text-ink-dim hover:text-white transition-colors p-2 -ml-2 rounded-full hover:bg-white/5"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M19 12H5M12 19l-7-7 7-7"/>
              </svg>
            </button>
            <h2 className="text-3xl font-bold tracking-tight text-white drop-shadow-sm">{t("setup.yourHand")}</h2>
          </div>

          <div className="flex justify-between items-end mb-6 px-1">
            <p className="text-ink-muted text-[0.7rem] uppercase tracking-wider font-medium">
              {t("setup.turufu")}:{" "}
              <span className={`font-bold ${SUIT_COLORS[trumpSuit!] === "red" ? "text-suit-red" : "text-white drop-shadow-md"}`}>
                {SUIT_SYMBOLS[trumpSuit!]} {trumpSuit!.toLowerCase()}
              </span>
            </p>
            <div className="flex items-center gap-1.5">
              <span className="text-oracle-glow text-lg font-bold leading-none">{selectedKeys.size}</span>
              <span className="text-ink-dim text-xs font-medium uppercase tracking-widest leading-none mt-1">/ {HAND_SIZE}</span>
            </div>
          </div>

          {/* Preview of selected cards */}
          <div className="glass-panel p-4 mb-6 min-h-[120px]">
            {selectedKeys.size === 0 ? (
              <div className="h-full flex items-center justify-center text-ink-dim text-xs tracking-widest uppercase font-medium">
                Tap cards below to build your hand
              </div>
            ) : (
              <div className="flex gap-2 flex-wrap">
                {[...selectedKeys].map((key) => {
                  const [rank, suit] = key.split("_");
                  return (
                    <div key={key} className="animate-slide-up">
                      <PlayingCard
                        card={{ suit, rank }}
                        size="md"
                        onClick={() => toggleCard({ suit, rank })}
                      />
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Card picker grid */}
          <div className="space-y-3 flex-1">
            {SUITS.map((suit) => {
              const isRed = SUIT_COLORS[suit] === "red";
              return (
                <div key={suit} className="flex items-center gap-2">
                  <div className={`w-8 h-8 flex items-center justify-center rounded-full glass-panel shrink-0 ${isRed ? "text-suit-red bg-suit-redDim" : "text-white bg-suit-blackDim"}`}>
                    <span className="text-lg leading-none drop-shadow-md">{SUIT_SYMBOLS[suit]}</span>
                  </div>
                  <div className="flex-1 grid grid-cols-6 gap-1.5">
                    {RANKS.map((rank) => {
                      const card: CardData = { suit, rank };
                      const key = cardKey(card);
                      const isSel = selectedKeys.has(key);
                      return (
                        <button
                          key={key}
                          onClick={() => toggleCard(card)}
                          className={`
                            h-11 rounded-xl text-sm font-bold
                            transition-all duration-200 active:scale-90
                            border
                            ${isSel
                              ? isRed
                                ? "bg-suit-red border-suit-red text-white shadow-neonDanger"
                                : "bg-white border-white text-game-bg shadow-glass"
                              : "bg-game-glass border-game-border text-ink-muted hover:bg-game-glassHover hover:text-white"
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

          {/* Start button */}
          <button
            onClick={handleStart}
            disabled={selectedKeys.size !== HAND_SIZE}
            className={`
              mt-8 w-full py-4 rounded-2xl text-sm font-extrabold tracking-[0.25em] uppercase
              transition-all duration-300 active:scale-[0.98] relative overflow-hidden
              ${selectedKeys.size === HAND_SIZE 
                ? "bg-oracle-glow text-game-bg shadow-neon hover:shadow-[0_0_25px_rgba(0,255,157,0.7)]" 
                : "bg-game-glass border border-game-border text-ink-dim pointer-events-none"}
            `}
          >
            {selectedKeys.size === HAND_SIZE && (
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent -translate-x-full animate-[shimmer_2s_infinite]"></div>
            )}
            {t("setup.startGame")}
          </button>
        </div>
      )}
    </div>
  );
}
