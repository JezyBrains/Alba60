/* ----------------------------------------------------------------
   TypeScript Types for the Albastini Game Advisor
   Mirrors the backend's data structures for type-safe WebSocket comms.
   ---------------------------------------------------------------- */

export interface CardData {
  suit: string;
  rank: string;
  points?: number;
}

export interface TrickPlay {
  player: number;
  card: CardData;
}

export interface MrithiStatus {
  applicable: boolean;
  user_points?: number;
  opponent_points?: number;
  points_remaining_in_game?: number;
  opponent_skunked?: boolean;
  skunk_possible?: boolean;
  skunk_threatened?: boolean;
}

export interface WinStatus {
  winner: number | null;
  points?: number;
}

export interface GameSnapshot {
  trump_suit: string | null;
  turn_index: number;
  round_number: number;
  game_over: boolean;
  draw_pile_size: number;
  user_hand: CardData[];
  scores: Record<number, number>;
  tricks_won: Record<number, number>;
  current_trick: TrickPlay[];
  cards_played_total: number;
  cards_remaining_unknown: number;
  opponent_known_hand: CardData[];
  mrithi: MrithiStatus;
  win_status: WinStatus;
  user_draw_pending: boolean;
}

export interface MoveEvaluation {
  card: CardData;
  visits: number;
  avg_reward: number;
}

export interface AdvicePayload {
  best_card: CardData | null;
  win_probability: number;
  simulations_run: number;
  determinizations_completed?: number;
  all_moves: MoveEvaluation[];
  mrithi_viable: boolean;
}

export interface TrickResult {
  trick_winner: number;
  points_won: number;
  scores: Record<number, number>;
  game_over: boolean;
  mrithi_status: MrithiStatus;
  win_status: WinStatus;
}

export interface WSMessage {
  type: "connected" | "update" | "error";
  state?: GameSnapshot;
  advice?: AdvicePayload | null;
  trick_result?: TrickResult | null;
  message?: string;
}

export type GamePhase = "setup" | "playing" | "drawing" | "game_over";

export const SUITS = ["SPADES", "HEARTS", "DIAMONDS", "CLUBS"] as const;
export const RANKS = ["A", "7", "K", "J", "Q", "6", "5", "4", "3"] as const;

export const SUIT_SYMBOLS: Record<string, string> = {
  SPADES: "♠",
  HEARTS: "♥",
  DIAMONDS: "♦",
  CLUBS: "♣",
};

export const SUIT_COLORS: Record<string, "red" | "black"> = {
  SPADES: "black",
  HEARTS: "red",
  DIAMONDS: "red",
  CLUBS: "black",
};

export const POINT_VALUES: Record<string, number> = {
  A: 11, "7": 10, K: 4, J: 3, Q: 2, "6": 0, "5": 0, "4": 0, "3": 0,
};

export function cardKey(card: CardData): string {
  return `${card.rank}_${card.suit}`;
}

export function formatCard(card: CardData): string {
  return `${card.rank}${SUIT_SYMBOLS[card.suit] || card.suit}`;
}
