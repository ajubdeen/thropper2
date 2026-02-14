import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import type {
  LabSnapshot,
  LabGeneration,
  LabPromptVariant,
  LabEra,
  LabModel,
  LabConfig,
  SaveEntry,
  GenerateRequest,
  BatchGenerateRequest,
  LiveStatus,
  VersionHistoryEntry,
} from "@/types/lab";

// ==================== Snapshots ====================

export function useSnapshots(params?: {
  era_id?: string;
  search?: string;
  limit?: number;
  offset?: number;
}) {
  const searchParams = new URLSearchParams();
  if (params?.era_id) searchParams.set("era_id", params.era_id);
  if (params?.search) searchParams.set("search", params.search);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();

  return useQuery<{ snapshots: LabSnapshot[]; total: number }>({
    queryKey: ["/api/lab/snapshots", qs],
    queryFn: async () => {
      const res = await fetch(`/api/lab/snapshots${qs ? `?${qs}` : ""}`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
      return res.json();
    },
  });
}

export function useSnapshot(id: string | null) {
  return useQuery<LabSnapshot>({
    queryKey: ["/api/lab/snapshots", id],
    queryFn: async () => {
      const res = await fetch(`/api/lab/snapshots/${id}`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
      return res.json();
    },
    enabled: !!id,
  });
}

export function useCreateSnapshot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: Record<string, any>) => {
      const res = await apiRequest("POST", "/api/lab/snapshots", data);
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["/api/lab/snapshots"] }),
  });
}

export function useImportSnapshot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      user_id: string;
      game_id: string;
      label?: string;
      tags?: string[];
    }) => {
      const res = await apiRequest("POST", "/api/lab/snapshots/from-save", data);
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["/api/lab/snapshots"] }),
  });
}

export function useCreateSyntheticSnapshot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      label: string;
      era_id: string;
      total_turns?: number;
      belonging?: number;
      legacy?: number;
      freedom?: number;
      player_name?: string;
      mode?: string;
      region?: string;
      tags?: string[];
    }) => {
      const res = await apiRequest("POST", "/api/lab/snapshots/synthetic", data);
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["/api/lab/snapshots"] }),
  });
}

export function useUpdateSnapshot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...data
    }: { id: string } & Record<string, any>) => {
      const res = await apiRequest("PATCH", `/api/lab/snapshots/${id}`, data);
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["/api/lab/snapshots"] }),
  });
}

export function useDeleteSnapshot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiRequest("DELETE", `/api/lab/snapshots/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["/api/lab/snapshots"] }),
  });
}

export function useAllSaves() {
  return useQuery<SaveEntry[]>({
    queryKey: ["/api/lab/saves"],
    queryFn: async () => {
      const res = await fetch("/api/lab/saves", { credentials: "include" });
      if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
      return res.json();
    },
  });
}

// ==================== Generation ====================

export function useGenerateNarrative() {
  const qc = useQueryClient();
  return useMutation<LabGeneration, Error, GenerateRequest>({
    mutationFn: async (data) => {
      const res = await apiRequest("POST", "/api/lab/generate", data);
      return res.json();
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["/api/lab/generations"] }),
  });
}

export function useGenerateBatch() {
  const qc = useQueryClient();
  return useMutation<
    { comparison_group: string; generations: LabGeneration[] },
    Error,
    BatchGenerateRequest
  >({
    mutationFn: async (data) => {
      const res = await apiRequest("POST", "/api/lab/generate/batch", data);
      return res.json();
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["/api/lab/generations"] }),
  });
}

export function useGenerations(params?: {
  snapshot_id?: string;
  model?: string;
  rating?: number;
  comparison_group?: string;
  limit?: number;
  offset?: number;
}) {
  const searchParams = new URLSearchParams();
  if (params?.snapshot_id)
    searchParams.set("snapshot_id", params.snapshot_id);
  if (params?.model) searchParams.set("model", params.model);
  if (params?.rating !== undefined)
    searchParams.set("rating", String(params.rating));
  if (params?.comparison_group)
    searchParams.set("comparison_group", params.comparison_group);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();

  return useQuery<{ generations: LabGeneration[]; total: number }>({
    queryKey: ["/api/lab/generations", qs],
    queryFn: async () => {
      const res = await fetch(
        `/api/lab/generations${qs ? `?${qs}` : ""}`,
        { credentials: "include" }
      );
      if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
      return res.json();
    },
  });
}

export function useGeneration(id: string | null) {
  return useQuery<LabGeneration>({
    queryKey: ["/api/lab/generations", id],
    queryFn: async () => {
      const res = await fetch(`/api/lab/generations/${id}`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
      return res.json();
    },
    enabled: !!id,
  });
}

export function useUpdateGeneration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...data
    }: { id: string; rating?: number; notes?: string }) => {
      const res = await apiRequest(
        "PATCH",
        `/api/lab/generations/${id}`,
        data
      );
      return res.json();
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["/api/lab/generations"] }),
  });
}

export function useDeleteGeneration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiRequest("DELETE", `/api/lab/generations/${id}`);
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["/api/lab/generations"] }),
  });
}

// ==================== Prompt Variants ====================

export function usePromptVariants(promptType?: string) {
  const qs = promptType ? `?prompt_type=${promptType}` : "";
  return useQuery<LabPromptVariant[]>({
    queryKey: ["/api/lab/prompts", promptType],
    queryFn: async () => {
      const res = await fetch(`/api/lab/prompts${qs}`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
      return res.json();
    },
  });
}

export function useCreatePromptVariant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      name: string;
      description?: string;
      prompt_type: string;
      template: string;
      is_default?: boolean;
    }) => {
      const res = await apiRequest("POST", "/api/lab/prompts", data);
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["/api/lab/prompts"] }),
  });
}

export function useUpdatePromptVariant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      ...data
    }: { id: string } & Record<string, any>) => {
      const res = await apiRequest("PUT", `/api/lab/prompts/${id}`, data);
      return res.json();
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["/api/lab/prompts"] }),
  });
}

export function useDeletePromptVariant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiRequest("DELETE", `/api/lab/prompts/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["/api/lab/prompts"] }),
  });
}

// ==================== Prompt Version Control ====================

export function usePushLive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (variantId: string) => {
      const res = await apiRequest("POST", `/api/lab/prompts/${variantId}/push`);
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/lab/prompts"] });
      qc.invalidateQueries({ queryKey: ["/api/lab/prompts/live"] });
      qc.invalidateQueries({ queryKey: ["/api/lab/prompts/versions"] });
    },
  });
}

export function useRevertPrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (promptType: string) => {
      const res = await apiRequest("POST", `/api/lab/prompts/revert/${promptType}`);
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/lab/prompts"] });
      qc.invalidateQueries({ queryKey: ["/api/lab/prompts/live"] });
      qc.invalidateQueries({ queryKey: ["/api/lab/prompts/versions"] });
    },
  });
}

export function useLiveStatus() {
  return useQuery<LiveStatus>({
    queryKey: ["/api/lab/prompts/live"],
    queryFn: async () => {
      const res = await fetch("/api/lab/prompts/live", { credentials: "include" });
      if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
      return res.json();
    },
  });
}

export function useVersionHistory(promptType: string | null) {
  return useQuery<VersionHistoryEntry[]>({
    queryKey: ["/api/lab/prompts/versions", promptType],
    queryFn: async () => {
      const res = await fetch(`/api/lab/prompts/versions/${promptType}`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
      return res.json();
    },
    enabled: !!promptType,
  });
}

export function useBaselinePrompt(promptType: string | null) {
  return useQuery<{ prompt_type: string; template: string }>({
    queryKey: ["/api/lab/prompts/baseline", promptType],
    queryFn: async () => {
      const res = await fetch(`/api/lab/prompts/baseline/${promptType}`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
      return res.json();
    },
    enabled: !!promptType,
    staleTime: Infinity,
  });
}

export function useSeedBaselines() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", "/api/lab/prompts/seed-baselines");
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["/api/lab/prompts"] });
      qc.invalidateQueries({ queryKey: ["/api/lab/prompts/versions"] });
    },
  });
}

// ==================== Utility ====================

export function useEras() {
  return useQuery<LabEra[]>({
    queryKey: ["/api/lab/eras"],
    queryFn: async () => {
      const res = await fetch("/api/lab/eras", { credentials: "include" });
      if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
      return res.json();
    },
    staleTime: Infinity,
  });
}

export function useModels() {
  return useQuery<LabModel[]>({
    queryKey: ["/api/lab/models"],
    queryFn: async () => {
      const res = await fetch("/api/lab/models", { credentials: "include" });
      if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
      return res.json();
    },
    staleTime: Infinity,
  });
}

export function useLabConfig() {
  return useQuery<LabConfig>({
    queryKey: ["/api/lab/config"],
    queryFn: async () => {
      const res = await fetch("/api/lab/config", { credentials: "include" });
      if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
      return res.json();
    },
    staleTime: Infinity,
  });
}

export function usePreviewPrompts(
  snapshotId: string | null,
  choiceId: string,
  diceRoll: number
) {
  const qs = new URLSearchParams({
    choice_id: choiceId,
    dice_roll: String(diceRoll),
  }).toString();

  return useQuery<{
    system_template: string;
    system_variables: Record<string, string>;
    turn_template: string;
    turn_variables: Record<string, string>;
  }>({
    queryKey: ["/api/lab/snapshots", snapshotId, "prompts", choiceId, diceRoll],
    queryFn: async () => {
      const res = await fetch(
        `/api/lab/snapshots/${snapshotId}/prompts?${qs}`,
        { credentials: "include" }
      );
      if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
      return res.json();
    },
    enabled: !!snapshotId,
  });
}

// ==================== Quick Play ====================

export interface QuickPlayStartParams {
  player_name?: string;
  region?: string;
  system_prompt_variant_id?: string;
  turn_prompt_variant_id?: string;
  arrival_prompt_variant_id?: string;
  window_prompt_variant_id?: string;
  model?: string;
  temperature?: number;
  dice_roll?: number;
}

export interface QuickPlayTurnParams {
  model?: string;
  temperature?: number;
  dice_roll?: number;
}

export function useQuickPlayStart() {
  return useMutation({
    mutationFn: async (data?: QuickPlayStartParams) => {
      const res = await apiRequest("POST", "/api/lab/quickplay/start", data || {});
      return res.json();
    },
  });
}

export function useQuickPlayEnterEra() {
  return useMutation({
    mutationFn: async ({
      sessionId,
      ...params
    }: { sessionId: string } & QuickPlayTurnParams) => {
      const res = await apiRequest(
        "POST",
        `/api/lab/quickplay/${sessionId}/enter-era`,
        Object.keys(params).length > 0 ? params : undefined
      );
      return res.json();
    },
  });
}

export function useQuickPlayChoose() {
  return useMutation({
    mutationFn: async ({
      sessionId,
      choice,
      ...params
    }: {
      sessionId: string;
      choice: string;
    } & QuickPlayTurnParams) => {
      const res = await apiRequest(
        "POST",
        `/api/lab/quickplay/${sessionId}/choose`,
        { choice, ...params }
      );
      return res.json();
    },
  });
}

export function useQuickPlayContinue() {
  return useMutation({
    mutationFn: async ({
      sessionId,
      ...params
    }: { sessionId: string } & QuickPlayTurnParams) => {
      const res = await apiRequest(
        "POST",
        `/api/lab/quickplay/${sessionId}/continue`,
        Object.keys(params).length > 0 ? params : undefined
      );
      return res.json();
    },
  });
}

export function useQuickPlayUpdateParams() {
  return useMutation({
    mutationFn: async ({
      sessionId,
      ...params
    }: {
      sessionId: string;
      system_prompt_variant_id?: string;
      turn_prompt_variant_id?: string;
      arrival_prompt_variant_id?: string;
      window_prompt_variant_id?: string;
      model?: string;
      temperature?: number;
      dice_roll?: number;
    }) => {
      const res = await apiRequest(
        "PATCH",
        `/api/lab/quickplay/${sessionId}/update-params`,
        params
      );
      return res.json();
    },
  });
}
