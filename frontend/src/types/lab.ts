// Narrative Lab TypeScript types

export interface LabSnapshot {
  id: string;
  user_id: string;
  label: string;
  tags: string[];
  game_state: Record<string, any>;
  conversation_history: Array<{ role: string; content: string }>;
  system_prompt: string | null;
  era_id: string | null;
  era_name: string | null;
  era_year: number | null;
  era_location: string | null;
  total_turns: number;
  phase: string | null;
  player_name: string | null;
  belonging_value: number;
  legacy_value: number;
  freedom_value: number;
  available_choices: LabChoice[];
  source: string;
  source_game_id: string | null;
  created_at: string;
}

export interface LabChoice {
  id: string;
  text: string;
}

export interface LabGeneration {
  id: string;
  user_id: string;
  snapshot_id: string;
  choice_id: string;
  choice_text: string | null;
  model: string;
  system_prompt: string;
  turn_prompt: string;
  dice_roll: number | null;
  temperature: number;
  max_tokens: number;
  raw_response: string;
  narrative_text: string | null;
  anchor_deltas: Record<string, number> | null;
  parsed_npcs: string[];
  parsed_wisdom: string | null;
  parsed_character_name: string | null;
  parsed_choices: LabChoice[];
  rating: number | null;
  notes: string | null;
  comparison_group: string | null;
  comparison_label: string | null;
  generation_time_ms: number | null;
  created_at: string;
}

export interface LabPromptVariant {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  prompt_type: string;
  template: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface LabEra {
  id: string;
  name: string;
  year: number | null;
  location: string | null;
}

export interface LabModel {
  id: string;
  label: string;
  description: string;
}

export interface LabConfig {
  default_model: string;
  premium_model: string;
  default_temperature: number;
  default_max_tokens: number;
  dice_range: { min: number; max: number };
}

export interface GenerateRequest {
  snapshot_id: string;
  choice_id: string;
  model?: string;
  system_prompt?: string;
  turn_prompt?: string;
  dice_roll?: number;
  temperature?: number;
  max_tokens?: number;
  comparison_group?: string;
  comparison_label?: string;
}

export interface BatchGenerateRequest {
  snapshot_id: string;
  choice_id: string;
  variants: Array<{
    label?: string;
    model?: string;
    system_prompt?: string;
    turn_prompt?: string;
    dice_roll?: number;
    temperature?: number;
    max_tokens?: number;
  }>;
}

export interface SaveEntry {
  user_id: string;
  game_id: string;
  player_name: string | null;
  current_era: string | null;
  phase: string | null;
  saved_at: string;
  email: string | null;
  first_name: string | null;
  last_name: string | null;
}

export interface PaginatedResponse<T> {
  total: number;
  [key: string]: T[] | number;
}
