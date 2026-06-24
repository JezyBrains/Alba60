"use client";

import { useState, useCallback } from "react";
import { useLanguage } from "@/lib/LanguageContext";
import { SUITS, RANKS, SUIT_SYMBOLS, SUIT_COLORS, cardKey } from "@/lib/types";
import type { CardData } from "@/lib/types";
import PlayingCard from "./PlayingCard";

const HAND_SIZE = 6;

interface GameSetupProps {
  onInitialize: (trumpSuit: string, hand: CardData[], bottomTrump?: CardData) => void;
}

export default function GameSetup({ onInitialize }: GameSetupProps) {
  const { t, lang, toggleLang } = useLanguage();
  const [step, setStep] = useState<"bottom_trump" | "hand">("bottom_trump");
  const [trumpSuit, setTrumpSuit] = useState<string | null>(null);
  const [bottomTrump, setBottomTrump] = useState<CardData | null>(null);
  const [manualTrumpOverride, setManualTrumpOverride] = useState(false);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());

  // Bottom trump card key for excluding from hand selection
  const bottomTrumpKey = bottomTrump ? cardKey(bottomTrump) : null;

  const handleSelectBottomTrump = useCallback((suit: string, rank: string) => {
    const card: CardData = { suit, rank };
    setBottomTrump(card);
    // AUTO-DERIVE trump suit from the bottom trump card
    if (!manualTrumpOverride) {
      setTrumpSuit(suit);
    }
    setStep("hand");
  }, [manualTrumpOverride]);

  const handleSkipBottomTrump = useCallback(() => {
    // Allow playing without bottom trump (legacy mode)
    setStep("hand");
  }, []);

  const toggleCard = useCallback((card: CardData) => {
    const key = cardKey(card);
    // Don't allow selecting the bottom trump card
    if (key === bottomTrumpKey) return;

    setSelectedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) { next.delete(key); }
      else if (next.size < HAND_SIZE) { next.add(key); }
      return next;
    });
  }, [bottomTrumpKey]);

  const handleStart = useCallback(() => {
    if (!trumpSuit || selectedKeys.size !== HAND_SIZE) return;
    const cards: CardData[] = [...selectedKeys].map((key) => {
      const [rank, suit] = key.split("_");
      return { suit, rank };
    });
    onInitialize(trumpSuit, cards, bottomTrump ?? undefined);
  }, [trumpSuit, selectedKeys, bottomTrump, onInitialize]);

  return (
    <div className="min-h-dvh bg-game flex flex-col relative animate-fade-in pb-10">
      {/* Language toggle */}
      <button
        onClick={toggleLang}
        className="absolute top-6 right-6 text-ink-dim text-[0.65rem] tracking-[0.25em] uppercase hover:text-white transition-colors z-10 font-semibold"
      >
        {lang === "en" ? "EN / SW" : "SW / EN"}
      </button>

      {/* ---- Bottom Trump Selection (Step 1) ---- */}
      {step === "bottom_trump" && (
        <div className="flex flex-col items-center justify-center flex-1 px-6 mt-12">
          {/* Glowing Title */}
          <div className="relative mb-2">
            <div className="absolute -inset-4 bg-oracle-glow opacity-10 blur-2xl rounded-full"></div>
            <h1 className="relative text-5xl font-extrabold tracking-tighter bg-clip-text text-transparent bg-gradient-to-br from-white via-ink-muted to-ink-dim drop-shadow-md">
              Albastini
            </h1>
          </div>
          <p className="text-ink-dim text-[0.65rem] font-medium tracking-[0.3em] uppercase mb-4 text-center">
            {t("setup.selectBottomTrump") || "Select the Bottom Trump Card"}
          </p>
          <p className="text-ink-dim text-[0.5rem] tracking-wider mb-8 text-center max-w-xs opacity-70">
            {t("setup.bottomTrumpHint") || "The face-up card at the bottom of the draw pile. This sets the trump suit automatically."}
          </p>

          {/* Card picker grid for bottom trump */}
          <div className="space-y-3 w-full max-w-sm mb-8">
            {SUITS.map((suit) => {
              const isRed = SUIT_COLORS[suit] === "red";
              return (
                <div key={suit} className="flex items-center gap-2">
                  <div className={`w-8 h-8 flex items-center justify-center rounded-full glass-panel shrink-0 ${isRed ? "text-suit-red bg-suit-redDim" : "text-white bg-suit-blackDim"}`}>
                    <span className="text-lg leading-none drop-shadow-md">{SUIT_SYMBOLS[suit]}</span>
                  </div>
                  <div className="flex-1 grid grid-cols-6 gap-1.5">
                    {RANKS.map((rank) => (
                      <button
                        key={`${rank}_${suit}`}
                        onClick={() => handleSelectBottomTrump(suit, rank)}
                        className="h-11 rounded-xl text-sm font-bold transition-all duration-200 active:scale-90 border bg-game-glass border-game-border text-ink-muted hover:bg-game-glassHover hover:text-white"
                      >
                        {rank}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Skip button */}
          <button
            onClick={handleSkipBottomTrump}
            className="text-ink-dim text-[0.6rem] tracking-[0.2em] uppercase hover:text-ink-muted transition-colors"
          >
            {t("setup.skipBottomTrump") || "Skip (manual trump selection)"}
          </button>
        </div>
      )}

      {/* ---- Hand Selection (Step 2) ---- */}
      {step === "hand" && (
        <div className="flex flex-col flex-1 px-5 pt-8 pb-6 max-w-lg mx-auto w-full">
          {/* Header */}
          <div className="flex items-center gap-4 mb-2">
            <button
              onClick={() => {
                setStep("bottom_trump");
                setBottomTrump(null);
                if (!manualTrumpOverride) setTrumpSuit(null);
                setSelectedKeys(new Set());
              }}
              className="text-ink-dim hover:text-white transition-colors p-2 -ml-2 rounded-full hover:bg-white/5"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M19 12H5M12 19l-7-7 7-7"/>
              </svg>
            </button>
            <h2 className="text-3xl font-bold tracking-tight text-white drop-shadow-sm">{t("setup.yourHand")}</h2>
          </div>

          <div className="flex justify-between items-end mb-4 px-1">
            <div>
              {/* Trump suit display with manual override toggle */}
              {trumpSuit ? (
                <p className="text-ink-muted text-[0.7rem] uppercase tracking-wider font-medium">
                  {t("setup.turufu")}:{" "}
                  <span className={`font-bold ${SUIT_COLORS[trumpSuit] === "red" ? "text-suit-red" : "text-white drop-shadow-md"}`}>
                    {SUIT_SYMBOLS[trumpSuit]} {trumpSuit.toLowerCase()}
                  </span>
                  {bottomTrump && !manualTrumpOverride && (
                    <button
                      onClick={() => setManualTrumpOverride(true)}
                      className="ml-2 text-ink-dim text-[0.5rem] tracking-wider hover:text-ink-muted transition-colors"
                    >
                      ✏️ override
                    </button>
                  )}
                </p>
              ) : (
                <p className="text-ink-dim text-[0.7rem] uppercase tracking-wider font-medium">
                  {t("setup.selectTrump")}
                </p>
              )}

              {/* Manual trump override selector */}
              {manualTrumpOverride && (
                <div className="flex gap-2 mt-2">
                  {SUITS.map((suit) => {
                    const isRed = SUIT_COLORS[suit] === "red";
                    return (
                      <button
                        key={suit}
                        onClick={() => { setTrumpSuit(suit); setManualTrumpOverride(false); }}
                        className={`w-8 h-8 flex items-center justify-center rounded-lg border transition-all
                          ${trumpSuit === suit
                            ? isRed ? "bg-suit-red border-suit-red text-white" : "bg-white border-white text-game-bg"
                            : "bg-game-glass border-game-border text-ink-muted hover:text-white"
                          }`}
                      >
                        {SUIT_SYMBOLS[suit]}
                      </button>
                    );
                  })}
                </div>
              )}

              {/* Bottom trump card display */}
              {bottomTrump && (
                <p className="text-ink-dim text-[0.55rem] tracking-wider mt-1.5 flex items-center gap-1.5">
                  <span className="text-oracle-glow">▼</span>
                  Bottom:{" "}
                  <span className={`font-bold ${SUIT_COLORS[bottomTrump.suit] === "red" ? "text-suit-red" : "text-white"}`}>
                    {bottomTrump.rank}{SUIT_SYMBOLS[bottomTrump.suit]}
                  </span>
                </p>
              )}
            </div>

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

          {/* Card picker grid — with bottom trump grayed out */}
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
                      const isBottomTrump = key === bottomTrumpKey;
                      return (
                        <button
                          key={key}
                          onClick={() => toggleCard(card)}
                          disabled={isBottomTrump}
                          className={`
                            h-11 rounded-xl text-sm font-bold
                            transition-all duration-200 active:scale-90
                            border
                            ${isBottomTrump
                              ? "bg-game-glass/30 border-oracle-glow/30 text-oracle-glow/40 cursor-not-allowed line-through"
                              : isSel
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
            disabled={selectedKeys.size !== HAND_SIZE || !trumpSuit}
            className={`
              mt-8 w-full py-4 rounded-2xl text-sm font-extrabold tracking-[0.25em] uppercase
              transition-all duration-300 active:scale-[0.98] relative overflow-hidden
              ${selectedKeys.size === HAND_SIZE && trumpSuit
                ? "bg-oracle-glow text-game-bg shadow-neon hover:shadow-[0_0_25px_rgba(0,255,157,0.7)]" 
                : "bg-game-glass border border-game-border text-ink-dim pointer-events-none"}
            `}
          >
            {selectedKeys.size === HAND_SIZE && trumpSuit && (
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent -translate-x-full animate-[shimmer_2s_infinite]"></div>
            )}
            {t("setup.startGame")}
          </button>
        </div>
      )}
    </div>
  );
}
