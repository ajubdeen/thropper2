import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Card, CardContent } from "@/components/ui/card";
import { ChevronDown, ChevronLeft, ChevronRight, X } from "lucide-react";
import {
  useQuickPlayHistory,
  useQuickPlaySessions,
} from "@/hooks/use-lab";
import type { QuickPlayHistoryFilters, QuickPlayTurn } from "@/types/lab";

const TURN_TYPE_COLORS: Record<string, string> = {
  arrival: "bg-blue-600",
  choice: "bg-green-600",
  "new-era": "bg-orange-500",
};

const TURN_TYPE_LABELS: Record<string, string> = {
  arrival: "Arrival",
  choice: "Choice",
  "new-era": "New Era",
};

const PAGE_SIZE = 20;

interface Props {
  onBranchSnapshot?: (snapshotId: string) => void;
}

export default function QuickPlayHistory({ onBranchSnapshot }: Props) {
  const [filters, setFilters] = useState<QuickPlayHistoryFilters>({
    limit: PAGE_SIZE,
    offset: 0,
  });

  const { data, isLoading } = useQuickPlayHistory(filters);
  const { data: sessionsData } = useQuickPlaySessions();

  const filterOptions = data?.filters;
  const turns = data?.turns ?? [];
  const total = data?.total ?? 0;
  const page = Math.floor((filters.offset ?? 0) / PAGE_SIZE) + 1;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  const hasActiveFilters = !!(
    filters.session_id ||
    filters.era_id ||
    filters.model ||
    filters.region ||
    filters.system_prompt_variant_id ||
    filters.turn_prompt_variant_id ||
    filters.arrival_prompt_variant_id ||
    filters.window_prompt_variant_id ||
    filters.date_from ||
    filters.date_to
  );

  const updateFilter = (key: keyof QuickPlayHistoryFilters, value: string) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value === "all" ? undefined : value || undefined,
      offset: 0,
    }));
  };

  const clearFilters = () => {
    setFilters({ limit: PAGE_SIZE, offset: 0 });
  };

  const goToPage = (p: number) => {
    setFilters((prev) => ({ ...prev, offset: (p - 1) * PAGE_SIZE }));
  };

  return (
    <div className="space-y-4">
      {/* Filter Bar */}
      <Card>
        <CardContent className="p-3 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Filters</span>
            <div className="flex items-center gap-2">
              {hasActiveFilters && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearFilters}
                  className="h-7 text-xs"
                >
                  <X className="h-3 w-3 mr-1" /> Clear
                </Button>
              )}
              <Badge variant="secondary" className="text-xs">
                {total} turns
              </Badge>
            </div>
          </div>

          {/* Row 1: Session + Era + Region */}
          <div className="grid grid-cols-3 gap-2">
            <div>
              <Label className="text-xs">Session</Label>
              <Select
                value={filters.session_id ?? "all"}
                onValueChange={(v) => updateFilter("session_id", v)}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="All sessions" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All sessions</SelectItem>
                  {sessionsData?.sessions?.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.player_name || "Session"} —{" "}
                      {new Date(s.created_at).toLocaleDateString()}
                      {s.turn_count ? ` (${s.turn_count} turns)` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Era</Label>
              <Select
                value={filters.era_id ?? "all"}
                onValueChange={(v) => updateFilter("era_id", v)}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="All eras" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All eras</SelectItem>
                  {filterOptions?.eras?.map((e) => (
                    <SelectItem key={e.era_id} value={e.era_id}>
                      {e.era_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Region</Label>
              <Select
                value={filters.region ?? "all"}
                onValueChange={(v) => updateFilter("region", v)}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="All regions" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All regions</SelectItem>
                  {filterOptions?.regions?.map((r) => (
                    <SelectItem key={r} value={r}>
                      {r}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Row 2: Model + Prompt variant filters */}
          <div className="grid grid-cols-5 gap-2">
            <div>
              <Label className="text-xs">Model</Label>
              <Select
                value={filters.model ?? "all"}
                onValueChange={(v) => updateFilter("model", v)}
              >
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="All models" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All models</SelectItem>
                  {filterOptions?.models?.map((m) => (
                    <SelectItem key={m} value={m}>
                      {m.split("-").slice(1, 3).join(" ")}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {(["system", "turn", "arrival", "window"] as const).map((type) => (
              <div key={type}>
                <Label className="text-xs capitalize">{type} Prompt</Label>
                <Select
                  value={
                    filters[
                      `${type}_prompt_variant_id` as keyof QuickPlayHistoryFilters
                    ]?.toString() ?? "all"
                  }
                  onValueChange={(v) =>
                    updateFilter(
                      `${type}_prompt_variant_id` as keyof QuickPlayHistoryFilters,
                      v
                    )
                  }
                >
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue placeholder="All" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All</SelectItem>
                    {filterOptions?.variants?.[type]?.map((v) => (
                      <SelectItem key={v.id ?? "baseline"} value={v.id ?? "baseline"}>
                        {v.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            ))}
          </div>

          {/* Row 3: Date filters */}
          <div className="grid grid-cols-4 gap-2">
            <div>
              <Label className="text-xs">Date From</Label>
              <Input
                type="date"
                value={filters.date_from ?? ""}
                onChange={(e) => updateFilter("date_from", e.target.value)}
                className="h-8 text-xs"
              />
            </div>
            <div>
              <Label className="text-xs">Date To</Label>
              <Input
                type="date"
                value={filters.date_to ?? ""}
                onChange={(e) => updateFilter("date_to", e.target.value)}
                className="h-8 text-xs"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Turn list */}
      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : turns.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No turns found. Play a Quick Play session to see history here.
        </p>
      ) : (
        <div className="space-y-2">
          {turns.map((turn) => (
            <TurnCard
              key={turn.id}
              turn={turn}
              onBranchSnapshot={onBranchSnapshot}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">
            Showing {(filters.offset ?? 0) + 1}-
            {Math.min((filters.offset ?? 0) + PAGE_SIZE, total)} of {total}
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => goToPage(page - 1)}
              className="h-7"
            >
              <ChevronLeft className="h-3 w-3" />
            </Button>
            <span className="text-xs px-2">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => goToPage(page + 1)}
              className="h-7"
            >
              <ChevronRight className="h-3 w-3" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function TurnCard({
  turn,
  onBranchSnapshot,
}: {
  turn: QuickPlayTurn;
  onBranchSnapshot?: (snapshotId: string) => void;
}) {
  const [metaExpanded, setMetaExpanded] = useState(false);
  const date = new Date(turn.created_at);

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-3 space-y-2">
        {/* Header row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge className={`text-[10px] ${TURN_TYPE_COLORS[turn.turn_type] || "bg-gray-500"}`}>
              {TURN_TYPE_LABELS[turn.turn_type] || turn.turn_type}
            </Badge>
            <span className="text-xs font-medium">Turn {turn.turn_number}</span>
            {turn.era_name && (
              <span className="text-xs text-muted-foreground">
                {turn.era_name}
                {turn.era_year ? ` (${turn.era_year})` : ""}
                {turn.era_location ? ` — ${turn.era_location}` : ""}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {turn.snapshot_id && onBranchSnapshot && (
              <Button
                variant="outline"
                size="sm"
                className="h-6 text-xs"
                onClick={() => onBranchSnapshot(turn.snapshot_id!)}
              >
                Branch Here
              </Button>
            )}
            <span className="text-[10px] text-muted-foreground">
              {date.toLocaleDateString()} {date.toLocaleTimeString()}
            </span>
          </div>
        </div>

        {/* Choice made (what the player picked) */}
        {turn.choice_made && (
          <div className="border-l-2 border-primary pl-3 py-1">
            <p className="text-xs">
              <span className="text-muted-foreground font-medium">Player chose: </span>
              <span>{turn.choice_made}</span>
            </p>
          </div>
        )}

        {/* Narrative text - shown directly */}
        {turn.narrative_text && (
          <div className="p-3 bg-muted/30 rounded-md text-sm whitespace-pre-wrap leading-relaxed">
            {turn.narrative_text}
          </div>
        )}

        {/* Choices presented to player */}
        {turn.choices && turn.choices.length > 0 && (
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground font-medium">Choices presented:</p>
            {turn.choices.map((c) => (
              <div
                key={c.id}
                className="flex items-start gap-2 pl-2 text-xs"
              >
                <Badge variant="secondary" className="text-[10px] shrink-0 mt-0.5">
                  {c.id}
                </Badge>
                <span>{c.text}</span>
              </div>
            ))}
          </div>
        )}

        {/* Collapsible metadata */}
        <Collapsible open={metaExpanded} onOpenChange={setMetaExpanded}>
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 text-xs px-2"
            >
              <ChevronDown
                className={`h-3 w-3 mr-1 transition-transform ${metaExpanded ? "rotate-180" : ""}`}
              />
              {metaExpanded ? "Hide" : "Show"} Metadata
              <span className="ml-2 text-muted-foreground">
                {turn.model?.split("-").slice(1, 3).join(" ")}
                {turn.dice_roll != null ? ` · Dice ${turn.dice_roll}` : ""}
                {turn.temperature != null ? ` · Temp ${turn.temperature}` : ""}
              </span>
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 space-y-2">
            {/* Metadata badges */}
            <div className="flex flex-wrap gap-1.5">
              {turn.model && (
                <Badge variant="outline" className="text-[10px]">
                  {turn.model.split("-").slice(1, 3).join(" ")}
                </Badge>
              )}
              {turn.temperature != null && (
                <Badge variant="outline" className="text-[10px]">
                  Temp: {turn.temperature}
                </Badge>
              )}
              {turn.dice_roll != null && (
                <Badge variant="outline" className="text-[10px]">
                  Dice: {turn.dice_roll}
                </Badge>
              )}
              {turn.region && (
                <Badge variant="outline" className="text-[10px]">
                  {turn.region}
                </Badge>
              )}
            </div>

            {/* Prompt variants */}
            <div className="flex flex-wrap gap-1.5">
              <PromptBadge label="Sys" name={turn.system_prompt_variant_name} />
              <PromptBadge label="Turn" name={turn.turn_prompt_variant_name} />
              <PromptBadge label="Arr" name={turn.arrival_prompt_variant_name} />
              <PromptBadge label="Win" name={turn.window_prompt_variant_name} />
            </div>
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  );
}

function PromptBadge({ label, name }: { label: string; name: string }) {
  const isBaseline = name === "Baseline";
  return (
    <span
      className={`inline-flex items-center text-[10px] rounded px-1.5 py-0.5 ${
        isBaseline
          ? "bg-muted text-muted-foreground"
          : "bg-primary/10 text-primary font-medium"
      }`}
    >
      {label}: {name}
    </span>
  );
}
