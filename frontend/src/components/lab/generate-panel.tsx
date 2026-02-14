import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
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
import { ChevronDown, Play, Loader2, Columns } from "lucide-react";
import {
  useSnapshot,
  useModels,
  useLabConfig,
  useGenerateNarrative,
  useGenerateBatch,
} from "@/hooks/use-lab";
import type { LabGeneration, LabChoice } from "@/types/lab";
import GenerationResult from "./generation-result";

interface Props {
  snapshotId: string | null;
  onComparisonCreated?: (group: string) => void;
}

export default function GeneratePanel({
  snapshotId,
  onComparisonCreated,
}: Props) {
  const { data: snapshot } = useSnapshot(snapshotId);
  const { data: models } = useModels();
  const { data: config } = useLabConfig();

  const [selectedChoice, setSelectedChoice] = useState<string>("A");
  const [model, setModel] = useState<string>("");
  const [temperature, setTemperature] = useState(1.0);
  const [maxTokens, setMaxTokens] = useState(1500);
  const [diceRoll, setDiceRoll] = useState<number | null>(null);
  const [systemPromptOverride, setSystemPromptOverride] = useState("");
  const [turnPromptOverride, setTurnPromptOverride] = useState("");
  const [promptsOpen, setPromptsOpen] = useState(false);

  const [result, setResult] = useState<LabGeneration | null>(null);
  const [batchResults, setBatchResults] = useState<LabGeneration[] | null>(null);

  const generate = useGenerateNarrative();
  const generateBatch = useGenerateBatch();

  if (!snapshotId) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        Select a snapshot from the library to begin generating.
      </div>
    );
  }

  if (!snapshot) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        Loading snapshot...
      </div>
    );
  }

  const choices: LabChoice[] = snapshot.available_choices || [];
  const effectiveModel = model || config?.default_model || "";

  const handleGenerate = () => {
    setResult(null);
    setBatchResults(null);
    generate.mutate(
      {
        snapshot_id: snapshotId!,
        choice_id: selectedChoice,
        model: model || undefined,
        temperature,
        max_tokens: maxTokens,
        dice_roll: diceRoll ?? undefined,
        system_prompt: systemPromptOverride || undefined,
        turn_prompt: turnPromptOverride || undefined,
      },
      { onSuccess: (data) => setResult(data) }
    );
  };

  const handleBatchGenerate = () => {
    if (!models?.length) return;
    setResult(null);
    setBatchResults(null);

    // Generate one variant per available model with same settings
    const variants = models.map((m) => ({
      label: m.label,
      model: m.id,
      temperature,
      max_tokens: maxTokens,
      dice_roll: diceRoll ?? undefined,
      system_prompt: systemPromptOverride || undefined,
      turn_prompt: turnPromptOverride || undefined,
    }));

    generateBatch.mutate(
      {
        snapshot_id: snapshotId!,
        choice_id: selectedChoice,
        variants,
      },
      {
        onSuccess: (data) => {
          setBatchResults(data.generations);
          onComparisonCreated?.(data.comparison_group);
        },
      }
    );
  };

  return (
    <div className="space-y-4">
      {/* Snapshot context */}
      <Card>
        <CardContent className="p-3">
          <p className="text-sm font-medium">{snapshot.label}</p>
          <p className="text-xs text-muted-foreground">
            {snapshot.era_name} &middot; Turn {snapshot.total_turns} &middot;{" "}
            B:{snapshot.belonging_value} L:{snapshot.legacy_value} F:
            {snapshot.freedom_value}
          </p>
        </CardContent>
      </Card>

      {/* Choice selection */}
      <div>
        <Label>Choice</Label>
        {choices.length ? (
          <div className="space-y-1 mt-1">
            {choices.map((c) => (
              <Button
                key={c.id}
                variant={selectedChoice === c.id ? "default" : "outline"}
                className="w-full justify-start text-left h-auto py-2"
                onClick={() => setSelectedChoice(c.id)}
              >
                <Badge variant="secondary" className="mr-2 shrink-0">
                  {c.id}
                </Badge>
                <span className="text-sm truncate">{c.text}</span>
              </Button>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground mt-1">
            No choices available in this snapshot.
          </p>
        )}
      </div>

      {/* Model selection */}
      <div>
        <Label>Model</Label>
        <Select value={model} onValueChange={setModel}>
          <SelectTrigger>
            <SelectValue placeholder="Default model" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="default">
              Default ({config?.default_model?.split("-").slice(-2).join(" ")})
            </SelectItem>
            {models?.map((m) => (
              <SelectItem key={m.id} value={m.id}>
                {m.label} — {m.description}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Parameters */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label>Temperature: {temperature.toFixed(1)}</Label>
          <Slider
            value={[temperature]}
            onValueChange={([v]: number[]) => setTemperature(v)}
            min={0}
            max={1.5}
            step={0.1}
          />
        </div>
        <div>
          <Label>Max Tokens: {maxTokens}</Label>
          <Slider
            value={[maxTokens]}
            onValueChange={([v]: number[]) => setMaxTokens(v)}
            min={500}
            max={4000}
            step={100}
          />
        </div>
        <div>
          <Label>
            Dice Roll: {diceRoll === null ? "Random" : diceRoll}
          </Label>
          <Slider
            value={[diceRoll ?? 10]}
            onValueChange={([v]: number[]) => setDiceRoll(v)}
            min={1}
            max={20}
            step={1}
          />
          {diceRoll !== null && (
            <Button
              variant="ghost"
              size="sm"
              className="text-xs p-0 h-auto"
              onClick={() => setDiceRoll(null)}
            >
              Reset to random
            </Button>
          )}
        </div>
      </div>

      {/* Prompt overrides */}
      <Collapsible open={promptsOpen} onOpenChange={setPromptsOpen}>
        <CollapsibleTrigger asChild>
          <Button variant="ghost" size="sm" className="w-full justify-between">
            Prompt Overrides
            <ChevronDown
              className={`h-4 w-4 transition-transform ${
                promptsOpen ? "rotate-180" : ""
              }`}
            />
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="space-y-3 mt-2">
          <div>
            <Label>System Prompt Override</Label>
            <Textarea
              placeholder="Leave empty to use default..."
              value={systemPromptOverride}
              onChange={(e) => setSystemPromptOverride(e.target.value)}
              rows={4}
              className="text-xs font-mono"
            />
          </div>
          <div>
            <Label>Turn Prompt Override</Label>
            <Textarea
              placeholder="Leave empty to use default..."
              value={turnPromptOverride}
              onChange={(e) => setTurnPromptOverride(e.target.value)}
              rows={4}
              className="text-xs font-mono"
            />
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* Action buttons */}
      <div className="flex gap-2">
        <Button
          className="flex-1"
          onClick={handleGenerate}
          disabled={generate.isPending || generateBatch.isPending}
        >
          {generate.isPending ? (
            <Loader2 className="h-4 w-4 mr-1 animate-spin" />
          ) : (
            <Play className="h-4 w-4 mr-1" />
          )}
          Generate
        </Button>
        <Button
          variant="secondary"
          onClick={handleBatchGenerate}
          disabled={generate.isPending || generateBatch.isPending}
        >
          {generateBatch.isPending ? (
            <Loader2 className="h-4 w-4 mr-1 animate-spin" />
          ) : (
            <Columns className="h-4 w-4 mr-1" />
          )}
          Compare Models
        </Button>
      </div>

      {generate.isError && (
        <p className="text-sm text-destructive">
          Error: {generate.error.message}
        </p>
      )}

      <Separator />

      {/* Results */}
      {result && (
        <div>
          <h3 className="text-sm font-semibold mb-2">Result</h3>
          <GenerationResult generation={result} />
        </div>
      )}

      {batchResults && (
        <div>
          <h3 className="text-sm font-semibold mb-2">
            Comparison ({batchResults.length} variants)
          </h3>
          <div className="grid grid-cols-1 gap-4">
            {batchResults.map((gen) => (
              <GenerationResult key={gen.id} generation={gen} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
