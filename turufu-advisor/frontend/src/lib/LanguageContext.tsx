"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

// ---------------------------------------------------------------------------
// Dictionary — EN / SW
// ---------------------------------------------------------------------------
type Lang = "en" | "sw";

const DICT: Record<string, Record<Lang, string>> = {
  // Setup
  "setup.title": { en: "Albastini", sw: "Albastini" },
  "setup.selectTrump": { en: "Select the Turufu", sw: "Chagua Turufu" },
  "setup.yourHand": { en: "Your Hand", sw: "Kadi Zako" },
  "setup.cardsSelected": { en: "cards selected", sw: "kadi zimechaguliwa" },
  "setup.startGame": { en: "Start Game", sw: "Anza Mchezo" },
  "setup.turufu": { en: "Turufu", sw: "Turufu" },

  // Game
  "game.yourPlay": { en: "Your play", sw: "Zamu yako" },
  "game.opponent": { en: "Opponent", sw: "Mpinzani" },
  "game.selectCard": { en: "Select your card", sw: "Chagua kadi yako" },
  "game.logOpponent": { en: "Log opponent's card", sw: "Ingiza kadi ya mpinzani" },
  "game.drawCards": { en: "Select drawn cards", sw: "Chagua kadi ulizoziota" },
  "game.confirm": { en: "Confirm", sw: "Thibitisha" },
  "game.you": { en: "You", sw: "Wewe" },
  "game.opp": { en: "Opp", sw: "Mpin" },
  "game.of120": { en: "of 120", sw: "ya 120" },
  "game.tricks": { en: "Tricks", sw: "Raundi" },
  "game.round": { en: "Round", sw: "Raundi" },
  "game.inDeck": { en: "in deck", sw: "kwenye deki" },
  "game.newGame": { en: "New Game", sw: "Mchezo Mpya" },
  "game.gameOver": { en: "Game Over", sw: "Mchezo Umekwisha" },
  "game.victory": { en: "Victory", sw: "Ushindi" },
  "game.defeat": { en: "Defeat", sw: "Kushindwa" },
  "game.reconnecting": { en: "Reconnecting…", sw: "Inaunganisha…" },
  "game.endgame": { en: "Endgame", sw: "Mwisho" },
  "game.cardsLeft": { en: "cards left", sw: "kadi zimebaki" },

  // Oracle
  "oracle.playThis": { en: "Play this card", sw: "Cheza kadi hii" },
  "oracle.calculating": { en: "Calculating…", sw: "Inahesabu…" },
  "oracle.opponentTurn": { en: "Opponent's turn", sw: "Zamu ya mpinzani" },
  "oracle.winProb": { en: "Win probability", sw: "Uwezekano wa kushinda" },
  "oracle.mrithi": { en: "Mrithi possible — 2× VP", sw: "Mrithi inawezekana — 2× VP" },
  "oracle.sims": { en: "sims", sw: "hesabu" },
  "oracle.worlds": { en: "worlds", sw: "ulimwengu" },

  // Narrator
  "narrator.opponentPlayed": { en: "Opponent played", sw: "Mpinzani amecheza" },
  "narrator.yourTurn": { en: "Your turn.", sw: "Zamu yako." },
  "narrator.opponentTurn": { en: "Opponent's turn.", sw: "Zamu ya mpinzani." },
  "narrator.youPlayed": { en: "You played", sw: "Umecheza" },
  "narrator.youWon": { en: "You won the trick!", sw: "Umeshinda raundi!" },
  "narrator.oppWon": { en: "Opponent won the trick.", sw: "Mpinzani ameshinda raundi." },
  "narrator.drawCard": { en: "Draw your cards.", sw: "Vuta kadi zako." },
  "narrator.gameStart": { en: "Game started. Opponent leads.", sw: "Mchezo umeanza. Mpinzani anaongoza." },
  "narrator.waiting": { en: "Waiting for opponent's card.", sw: "Inasubiri kadi ya mpinzani." },
  "narrator.trickWon": { en: "won!", sw: "ameshinda!" },
  "narrator.drawPrompt": { en: "Draw a card.", sw: "Vuta kadi." },
  "narrator.pts": { en: "pts", sw: "alama" },

  // Mrithi warnings
  "mrithi.threat": { en: "Mrithi threat — you're under 10", sw: "Hatari ya Mrithi — uko chini ya 10" },
  "mrithi.2xvp": { en: "2× Victory Points", sw: "2× Alama za Ushindi" },
};

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------
interface LanguageContextValue {
  lang: Lang;
  toggleLang: () => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextValue>({
  lang: "en",
  toggleLang: () => {},
  t: (k) => k,
});

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>("en");

  const toggleLang = useCallback(() => {
    setLang((prev) => (prev === "en" ? "sw" : "en"));
  }, []);

  const t = useCallback(
    (key: string): string => {
      const entry = DICT[key];
      if (!entry) return key;
      return entry[lang] || entry["en"] || key;
    },
    [lang]
  );

  return (
    <LanguageContext.Provider value={{ lang, toggleLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}

export type { Lang };
