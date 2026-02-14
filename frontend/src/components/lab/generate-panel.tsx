import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
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
  Play,
  Loader2,
  Columns,
  Trash2,
  Save,
  Rocket,
  Check,
} from "lucide-react";
import {
  useSnapshot,
  useModels,
  useLabConfig,
  useGenerateNarrative,
  useGenerateBatch,
  usePreviewPrompts,
  useCreatePromptVariant,
  usePushLive,
} from "@/hooks/use-lab";
import type { LabGeneration, LabChoice } from "@/types/lab";
import GenerationResult from "./generation-result";

function getLuckLabel(roll: number): string {
  if (roll <= 5) return "Unlucky \u2014 complications arise";
  if (roll <= 8) return "Slightly Unlucky \u2014 minor setbacks";
  if (roll <= 12) return "Neutral \u2014 things go as expected";
  if (roll <= 16) return "Lucky \u2014 better than expected";
  return "Very Lucky \u2014 doors open";
}

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
  const [diceRoll, setDiceRoll] = useState(10);
  const [systemPrompt, setSystemPrompt] = useState("");
  const [turnPrompt, setTurnPrompt] = useState("");

  // Track whether user has manually edited prompts (to avoid overwriting edits)
  const userEditedSystem = useRef(false);
  const userEditedTurn = useRef(false);

  // Save state
  const [savingSystem, setSavingSystem] = useState(false);
  const [savingTurn, setSavingTurn] = useState(false);
  const [systemVariantName, setSystemVariantName] = useState("");
  const [turnVariantName, setTurnVariantName] = useState("");
  const [savedSystemId, setSavedSystemId] = useState<string | null>(null);
  const [savedTurnId, setSavedTurnId] = useState<string | null>(null);
  const [pushedSystem, setPushedSystem] = useState(false);
  const [pushedTurn, setPushedTurn] = useState(false);

  const [variants, setVariants] = useState<LabGeneration[]>([]);

  const generate = useGenerateNarrative();
  const generateBatch = useGenerateBatch();
  const createVariant = useCreatePromptVariant();
  const pushLive = usePushLive();

  // Fetch the actual prompts that would be used
  const { data: previewData } = usePreviewPrompts(
    snapshotId,
    selectedChoice,
    diceRoll
  );

  // Pre-populate system template when preview data loads (only if user hasn't edited)
  useEffect(() => {
    if (previewData?.system_template && !userEditedSystem.current) {
      setSystemPrompt(previewData.system_template);
    }
  }, [previewData?.system_template]);

  // Pre-populate turn template when preview data loads (only if user hasn't edited)
  useEffect(() => {
    if (previewData?.turn_template && !userEditedTurn.current) {
      setTurnPrompt(previewData.turn_template);
    }
  }, [previewData?.turn_template]);

  // Reset edit flags when snapshot changes
  useEffect(() => {
    userEditedSystem.current = false;
    userEditedTurn.current = false;
    setSavedSystemId(null);
    setSavedTurnId(null);
    setSavingSystem(false);
    setSavingTurn(false);
    setPushedSystem(false);
    setPushedTurn(false);
  }, [snapshotId]);

  // Reset turn edit flag when choice or dice roll changes
  useEffect(() => {
    userEditedTurn.current = false;
  }, [selectedChoice, diceRoll]);

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

  // Extract the seed narrative — last assistant message in conversation history
  const seedNarrative = snapshot.conversation_history
    ?.filter((m) => m.role === "assistant")
    .pop()?.content;

  const handleGenerate = () => {
    generate.mutate(
      {
        snapshot_id: snapshotId!,
        choice_id: selectedChoice,
        model: model || undefined,
        temperature,
        max_tokens: maxTokens,
        dice_roll: diceRoll,
        system_prompt: systemPrompt || undefined,
        turn_prompt: turnPrompt || undefined,
      },
      { onSuccess: (data) => setVariants((prev) => [...prev, data]) }
    );
  };

  const handleBatchGenerate = () => {
    if (!models?.length) return;

    const batchVariants = models.map((m) => ({
      label: m.label,
      model: m.id,
      temperature,
      max_tokens: maxTokens,
      dice_roll: diceRoll,
      system_prompt: systemPrompt || undefined,
      turn_prompt: turnPrompt || undefined,
    }));

    generateBatch.mutate(
      {
        snapshot_id: snapshotId!,
        choice_id: selectedChoice,
        variants: batchVariants,
      },
      {
        onSuccess: (data) => {
          setVariants((prev) => [...prev, ...data.generations]);
          onComparisonCreated?.(data.comparison_group);
        },
      }
    );
  };

  const handleSaveVariant = (promptType: "system" | "turn") => {
    const template = promptType === "system" ? systemPrompt : turnPrompt;
    const name =
      promptType === "system"
        ? systemVariantName || "System variant"
        : turnVariantName || "Turn variant";

    createVariant.mutate(
      { name, prompt_type: promptType, template },
      {
        onSuccess: (data) => {
          if (promptType === "system") {
            setSavedSystemId(data.id);
            setSavingSystem(false);
          } else {
            setSavedTurnId(data.id);
            setSavingTurn(false);
          }
        },
      }
    );
  };

  const handlePushLive = (variantId: string, promptType: "system" | "turn") => {
    pushLive.mutate(variantId, {
      onSuccess: () => {
        if (promptType === "system") setPushedSystem(true);
        else setPushedTurn(true);
      },
    });
  };

  const isPending = generate.isPending || generateBatch.isPending;

  return (
    <div className="space-y-4">
      {/* Snapshot context + seed narrative */}
      <Card>
        <CardContent className="p-3 space-y-2">
          <div>
            <p className="text-sm font-medium">{snapshot.label}</p>
            <p className="text-xs text-muted-foreground">
              {snapshot.era_name} &middot; Turn {snapshot.total_turns} &middot;{" "}
              B:{snapshot.belonging_value} L:{snapshot.legacy_value} F:
              {snapshot.freedom_value}
            </p>
          </div>
          {seedNarrative && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1">
                Seed Narrative (Turn {snapshot.total_turns})
              </p>
              <ScrollArea className="max-h-[200px]">
                <div className="text-xs whitespace-pre-wrap bg-muted/50 rounded p-2">
                  {seedNarrative}
                </div>
              </ScrollArea>
            </div>
          )}
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
        <div className="col-span-2">
          <Label>
            Luck: {diceRoll}/20 — {getLuckLabel(diceRoll)}
          </Label>
          <Slider
            value={[diceRoll]}
            onValueChange={([v]: number[]) => setDiceRoll(v)}
            min={1}
            max={20}
            step={1}
          />
        </div>
      </div>

      {/* System Prompt */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>System Prompt</Label>
          <div className="flex items-center gap-1">
            {savedSystemId ? (
              <>
                {pushedSystem ? (
                  <Badge variant="default" className="text-[10px]">
                    <Check className="h-3 w-3 mr-1" />
                    Live
                  </Badge>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-6 text-xs"
                    onClick={() => handlePushLive(savedSystemId, "system")}
                    disabled={pushLive.isPending}
                  >
                    <Rocket className="h-3 w-3 mr-1" />
                    Push Live
                  </Button>
                )}
                <Badge variant="secondary" className="text-[10px]">
                  Saved
                </Badge>
              </>
            ) : savingSystem ? (
              <div className="flex items-center gap-1">
                <Input
                  value={systemVariantName}
                  onChange={(e) => setSystemVariantName(e.target.value)}
                  placeholder="Variant name..."
                  className="h-6 text-xs w-32"
                />
                <Button
                  variant="default"
                  size="sm"
                  className="h-6 text-xs"
                  onClick={() => handleSaveVariant("system")}
                  disabled={createVariant.isPending}
                >
                  {createVariant.isPending ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    "Save"
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-xs"
                  onClick={() => setSavingSystem(false)}
                >
                  Cancel
                </Button>
              </div>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-xs"
                onClick={() => {
                  setSystemVariantName("");
                  setSavingSystem(true);
                }}
              >
                <Save className="h-3 w-3 mr-1" />
                Save as Variant
              </Button>
            )}
          </div>
        </div>
        <Textarea
          value={systemPrompt}
          onChange={(e) => {
            setSystemPrompt(e.target.value);
            userEditedSystem.current = true;
            setSavedSystemId(null);
            setPushedSystem(false);
          }}
          rows={12}
          className="text-xs font-mono"
        />
        {previewData?.system_variables &&
          Object.keys(previewData.system_variables).length > 0 && (
            <details className="text-xs">
              <summary className="text-muted-foreground cursor-pointer">
                Template Variables (
                {Object.keys(previewData.system_variables).length})
              </summary>
              <div className="mt-1 space-y-1 bg-muted/50 rounded p-2 max-h-[200px] overflow-auto">
                {Object.entries(previewData.system_variables).map(
                  ([key, value]) => (
                    <div key={key} className="flex gap-1">
                      <span className="font-mono text-primary shrink-0">{`{${key}}`}</span>
                      <span className="text-muted-foreground shrink-0">
                        {" = "}
                      </span>
                      <span className="break-all text-muted-foreground">
                        {String(value).slice(0, 200)}
                        {String(value).length > 200 ? "..." : ""}
                      </span>
                    </div>
                  )
                )}
              </div>
            </details>
          )}
      </div>

      {/* Turn Prompt */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label>Turn Prompt</Label>
          <div className="flex items-center gap-1">
            {savedTurnId ? (
              <>
                {pushedTurn ? (
                  <Badge variant="default" className="text-[10px]">
                    <Check className="h-3 w-3 mr-1" />
                    Live
                  </Badge>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-6 text-xs"
                    onClick={() => handlePushLive(savedTurnId, "turn")}
                    disabled={pushLive.isPending}
                  >
                    <Rocket className="h-3 w-3 mr-1" />
                    Push Live
                  </Button>
                )}
                <Badge variant="secondary" className="text-[10px]">
                  Saved
                </Badge>
              </>
            ) : savingTurn ? (
              <div className="flex items-center gap-1">
                <Input
                  value={turnVariantName}
                  onChange={(e) => setTurnVariantName(e.target.value)}
                  placeholder="Variant name..."
                  className="h-6 text-xs w-32"
                />
                <Button
                  variant="default"
                  size="sm"
                  className="h-6 text-xs"
                  onClick={() => handleSaveVariant("turn")}
                  disabled={createVariant.isPending}
                >
                  {createVariant.isPending ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    "Save"
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 text-xs"
                  onClick={() => setSavingTurn(false)}
                >
                  Cancel
                </Button>
              </div>
            ) : (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-xs"
                onClick={() => {
                  setTurnVariantName("");
                  setSavingTurn(true);
                }}
              >
                <Save className="h-3 w-3 mr-1" />
                Save as Variant
              </Button>
            )}
          </div>
        </div>
        <Textarea
          value={turnPrompt}
          onChange={(e) => {
            setTurnPrompt(e.target.value);
            userEditedTurn.current = true;
            setSavedTurnId(null);
            setPushedTurn(false);
          }}
          rows={8}
          className="text-xs font-mono"
        />
        {previewData?.turn_variables &&
          Object.keys(previewData.turn_variables).length > 0 && (
            <details className="text-xs">
              <summary className="text-muted-foreground cursor-pointer">
                Template Variables (
                {Object.keys(previewData.turn_variables).length})
              </summary>
              <div className="mt-1 space-y-1 bg-muted/50 rounded p-2 max-h-[200px] overflow-auto">
                {Object.entries(previewData.turn_variables).map(
                  ([key, value]) => (
                    <div key={key} className="flex gap-1">
                      <span className="font-mono text-primary shrink-0">{`{${key}}`}</span>
                      <span className="text-muted-foreground shrink-0">
                        {" = "}
                      </span>
                      <span className="break-all text-muted-foreground">
                        {String(value).slice(0, 200)}
                        {String(value).length > 200 ? "..." : ""}
                      </span>
                    </div>
                  )
                )}
              </div>
            </details>
          )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-2">
        <Button
          className="flex-1"
          onClick={handleGenerate}
          disabled={isPending}
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
          disabled={isPending}
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
      {generateBatch.isError && (
        <p className="text-sm text-destructive">
          Error: {generateBatch.error.message}
        </p>
      )}

      <Separator />

      {/* Accumulated variants */}
      {variants.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold">
              Variants ({variants.length})
            </h3>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs text-muted-foreground"
              onClick={() => setVariants([])}
            >
              <Trash2 className="h-3 w-3 mr-1" />
              Clear All
            </Button>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {variants.map((gen) => (
              <GenerationResult key={gen.id} generation={gen} compact />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
