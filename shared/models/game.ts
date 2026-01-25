import { sql } from "drizzle-orm";
import { index, integer, jsonb, pgTable, text, timestamp, varchar } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const gameSaves = pgTable(
  "game_saves",
  {
    id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
    userId: varchar("user_id").notNull(),
    gameId: varchar("game_id").notNull(),
    playerName: varchar("player_name"),
    currentEra: varchar("current_era"),
    phase: varchar("phase"),
    state: jsonb("state").notNull(),
    savedAt: timestamp("saved_at").defaultNow(),
    startedAt: timestamp("started_at"),
  },
  (table) => [
    index("idx_game_saves_user").on(table.userId),
    index("idx_game_saves_user_game").on(table.userId, table.gameId),
  ]
);

export const insertGameSaveSchema = createInsertSchema(gameSaves).omit({ id: true, savedAt: true });
export type InsertGameSave = z.infer<typeof insertGameSaveSchema>;
export type GameSave = typeof gameSaves.$inferSelect;

export const leaderboardEntries = pgTable(
  "leaderboard_entries",
  {
    id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
    userId: varchar("user_id").notNull(),
    gameId: varchar("game_id"),
    playerName: varchar("player_name").notNull(),
    turnsSurvived: integer("turns_survived").default(0),
    erasVisited: integer("eras_visited").default(0),
    belongingScore: integer("belonging_score").default(0),
    legacyScore: integer("legacy_score").default(0),
    freedomScore: integer("freedom_score").default(0),
    totalScore: integer("total_score").default(0),
    endingType: varchar("ending_type"),
    finalEra: varchar("final_era"),
    blurb: text("blurb"),
    endingNarrative: text("ending_narrative"),
    createdAt: timestamp("created_at").defaultNow(),
  },
  (table) => [
    index("idx_leaderboard_user").on(table.userId),
    index("idx_leaderboard_total").on(table.totalScore),
  ]
);

export const insertLeaderboardEntrySchema = createInsertSchema(leaderboardEntries).omit({ id: true, createdAt: true });
export type InsertLeaderboardEntry = z.infer<typeof insertLeaderboardEntrySchema>;
export type LeaderboardEntry = typeof leaderboardEntries.$inferSelect;

export const gameHistories = pgTable(
  "game_histories",
  {
    id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
    gameId: varchar("game_id").notNull(),
    userId: varchar("user_id").notNull(),
    playerName: varchar("player_name"),
    startedAt: timestamp("started_at"),
    endedAt: timestamp("ended_at"),
    eras: jsonb("eras").default([]),
    finalScore: jsonb("final_score"),
    endingType: varchar("ending_type"),
    blurb: text("blurb"),
  },
  (table) => [
    index("idx_game_histories_user").on(table.userId),
    index("idx_game_histories_game").on(table.gameId),
  ]
);

export const insertGameHistorySchema = createInsertSchema(gameHistories).omit({ id: true });
export type InsertGameHistory = z.infer<typeof insertGameHistorySchema>;
export type GameHistory = typeof gameHistories.$inferSelect;

export const aoaEntries = pgTable(
  "aoa_entries",
  {
    id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
    entryId: varchar("entry_id").notNull().unique(),
    userId: varchar("user_id").notNull(),
    gameId: varchar("game_id"),
    playerName: varchar("player_name"),
    characterName: varchar("character_name"),
    finalEra: varchar("final_era"),
    finalEraYear: integer("final_era_year"),
    erasVisited: integer("eras_visited").default(0),
    turnsSurvived: integer("turns_survived").default(0),
    endingType: varchar("ending_type"),
    belongingScore: integer("belonging_score").default(0),
    legacyScore: integer("legacy_score").default(0),
    freedomScore: integer("freedom_score").default(0),
    totalScore: integer("total_score").default(0),
    keyNpcs: jsonb("key_npcs").default([]),
    definingMoments: jsonb("defining_moments").default([]),
    wisdomMoments: jsonb("wisdom_moments").default([]),
    itemsUsed: jsonb("items_used").default([]),
    playerNarrative: text("player_narrative"),
    historianNarrative: text("historian_narrative"),
    createdAt: timestamp("created_at").defaultNow(),
  },
  (table) => [
    index("idx_aoa_user").on(table.userId),
    index("idx_aoa_created").on(table.createdAt),
    index("idx_aoa_entry_id").on(table.entryId),
  ]
);

export const insertAoaEntrySchema = createInsertSchema(aoaEntries).omit({ id: true, createdAt: true });
export type InsertAoaEntry = z.infer<typeof insertAoaEntrySchema>;
export type AoaEntry = typeof aoaEntries.$inferSelect;
