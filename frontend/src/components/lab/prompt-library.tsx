import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Save, Rocket, RotateCcw, Database } from "lucide-react";
import {
  usePromptVariants,
  useCreatePromptVariant,
  useUpdatePromptVariant,
  usePushLive,
  useRevertPrompt,
  useLiveStatus,
  useBaselinePrompt,
  useSeedBaselines,
} from "@/hooks/use-lab";

const PROMPT_TYPES = [
  { id: "system", label: "System Prompt" },
  { id: "turn", label: "Turn Prompt" },
  { id: "arrival", label: "Arrival Prompt" },
  { id: "window", label: "Window Prompt" },
];

export default function PromptLibrary() {
  const seedBaselines = useSeedBaselines();
  const [promptType, setPromptType] = useState("system");

  const promptLabel =
    PROMPT_TYPES.find((p) => p.id === promptType)?.label ?? promptType;

  return (
    <div className="space-y-3 w-full">
      {/* Top bar: prompt type selector + seed button */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Label className="text-sm font-medium shrink-0">Prompt Type</Label>
          <Select value={promptType} onValueChange={setPromptType}>
            <SelectTrigger className="w-[200px] h-9">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PROMPT_TYPES.map((pt) => (
                <SelectItem key={pt.id} value={pt.id}>
                  {pt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex-1" />
        <Button
          variant="outline"
          size="sm"
          onClick={() => seedBaselines.mutate()}
          disabled={seedBaselines.isPending}
        >
          <Database className="h-4 w-4 mr-1" />
          {seedBaselines.isPending ? "Seeding..." : "Seed Baselines"}
        </Button>
      </div>

      {/* Single full-width editor for the selected prompt type */}
      <PromptEditor
        key={promptType}
        promptType={promptType}
        label={promptLabel}
      />
    </div>
  );
}

function PromptEditor({
  promptType,
  label,
}: {
  promptType: string;
  label: string;
}) {
  const { data: variants } = usePromptVariants(promptType);
  const { data: baseline } = useBaselinePrompt(promptType);
  const { data: liveStatus } = useLiveStatus();
  const createVariant = useCreatePromptVariant();
  const updateVariant = useUpdatePromptVariant();
  const pushLive = usePushLive();
  const revertPrompt = useRevertPrompt();

  const [selectedVariantId, setSelectedVariantId] = useState<string | null>(
    null
  );
  const [template, setTemplate] = useState("");
  const [variantName, setVariantName] = useState("");
  const [savedId, setSavedId] = useState<string | null>(null);
  const [pushed, setPushed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);

  const isLive = liveStatus?.[promptType]?.is_live ?? false;
  const isEditingExisting =
    selectedVariantId !== "baseline" &&
    variants?.some((v) => v.id === selectedVariantId && !v.is_default);

  const selectedVariant =
    selectedVariantId && selectedVariantId !== "baseline"
      ? variants?.find((v) => v.id === selectedVariantId)
      : null;

  // Auto-select the most recently updated variant (or baseline if none)
  useEffect(() => {
    if (initialized || !variants) return;

    const userVariants = variants.filter((v) => !v.is_default);
    if (userVariants.length > 0) {
      // Pick the one with the latest updated_at
      const latest = userVariants.reduce((best, v) =>
        v.updated_at > best.updated_at ? v : best
      );
      setSelectedVariantId(latest.id);
      setTemplate(latest.template);
      setVariantName(latest.name);
    } else {
      setSelectedVariantId("baseline");
      setTemplate(baseline?.template || "");
      const maxVersion = variants.reduce(
        (max, v) => Math.max(max, v.version_number),
        0
      );
      setVariantName(`${label.split(" ")[0]} v${maxVersion + 1}`);
    }
    setInitialized(true);
  }, [variants, baseline?.template, initialized, label]);

  // Load baseline template when baseline data arrives and baseline is selected
  useEffect(() => {
    if (baseline?.template && selectedVariantId === "baseline" && initialized) {
      setTemplate(baseline.template);
    }
  }, [baseline?.template, selectedVariantId, initialized]);

  const handleVariantChange = (id: string) => {
    setSelectedVariantId(id);
    setSavedId(null);
    setPushed(false);
    setError(null);
    if (id === "baseline") {
      setTemplate(baseline?.template || "");
      if (variants) {
        const maxVersion = variants.reduce(
          (max, v) => Math.max(max, v.version_number),
          0
        );
        setVariantName(`${label.split(" ")[0]} v${maxVersion + 1}`);
      }
    } else {
      const variant = variants?.find((v) => v.id === id);
      if (variant) {
        setTemplate(variant.template);
        setVariantName(variant.name);
      }
    }
  };

  const handleSave = () => {
    if (!variantName.trim() || !template.trim()) return;
    setError(null);

    if (isEditingExisting) {
      updateVariant.mutate(
        {
          id: selectedVariantId!,
          name: variantName.trim(),
          template: template,
        },
        {
          onSuccess: (data) => {
            setSavedId(data.id);
            setPushed(false);
          },
          onError: (err) => setError(err.message),
        }
      );
    } else {
      createVariant.mutate(
        {
          name: variantName.trim(),
          prompt_type: promptType,
          template: template,
        },
        {
          onSuccess: (data) => {
            setSavedId(data.id);
            setPushed(false);
            setSelectedVariantId(data.id);
            setVariantName(data.name);
          },
          onError: (err) => setError(err.message),
        }
      );
    }
  };

  const handlePush = () => {
    if (!savedId) return;
    if (
      !confirm(
        `Push "${variantName}" live for ${promptType}? This will affect the live game.`
      )
    )
      return;
    pushLive.mutate(savedId, {
      onSuccess: () => setPushed(true),
    });
  };

  const handleRevert = () => {
    if (
      !confirm(
        `Revert ${promptType} to baseline? The game will use the default prompt.`
      )
    )
      return;
    revertPrompt.mutate(promptType);
  };

  const isSaving = createVariant.isPending || updateVariant.isPending;

  return (
    <div className="flex flex-col gap-3 w-full">
      {/* Version selector row */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Label className="text-sm shrink-0">Version</Label>
          <Select
            value={selectedVariantId || "baseline"}
            onValueChange={handleVariantChange}
          >
            <SelectTrigger className="w-[300px] h-9">
              <SelectValue placeholder="Select variant..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="baseline">Baseline (default)</SelectItem>
              {variants
                ?.filter((v) => !v.is_default)
                .map((v) => (
                  <SelectItem key={v.id} value={v.id}>
                    {v.name}
                    {v.is_live ? " (LIVE)" : ""}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>

        {/* Status badges */}
        {isLive && (
          <Badge className="text-[10px] bg-green-600">LIVE</Badge>
        )}
        {savedId && !pushed && (
          <Badge variant="secondary" className="text-[10px]">
            Saved
          </Badge>
        )}
        {pushed && (
          <Badge className="text-[10px] bg-green-600">Pushed</Badge>
        )}
      </div>

      {/* Full-width textarea */}
      <Textarea
        value={template}
        onChange={(e) => {
          setTemplate(e.target.value);
          setSavedId(null);
          setPushed(false);
        }}
        className="w-full min-h-[calc(100vh-360px)] text-xs font-mono resize-y"
        placeholder="Loading template..."
      />

      {/* Error display */}
      {error && <p className="text-xs text-destructive">{error}</p>}

      {/* Controls row */}
      <div className="flex items-center gap-2">
        <Input
          value={variantName}
          onChange={(e) => setVariantName(e.target.value)}
          placeholder="Variant name..."
          className="w-[300px] h-9"
        />
        <Button
          size="sm"
          className="h-9"
          onClick={handleSave}
          disabled={!variantName.trim() || !template.trim() || isSaving}
        >
          <Save className="h-4 w-4 mr-1" />
          {isSaving
            ? "Saving..."
            : isEditingExisting
              ? "Update"
              : "Save New"}
        </Button>

        {savedId && !pushed && (
          <Button
            size="sm"
            variant="outline"
            className="h-9"
            onClick={handlePush}
            disabled={pushLive.isPending}
          >
            <Rocket className="h-4 w-4 mr-1" />
            {pushLive.isPending ? "Pushing..." : "Push Live"}
          </Button>
        )}

        {isLive && (
          <Button
            size="sm"
            variant="outline"
            className="h-9 border-orange-500/50 text-orange-600"
            onClick={handleRevert}
            disabled={revertPrompt.isPending}
          >
            <RotateCcw className="h-4 w-4 mr-1" />
            {revertPrompt.isPending ? "..." : "Revert to Baseline"}
          </Button>
        )}
      </div>

      {/* Diff from baseline */}
      {selectedVariant?.change_summary && (
        <div className="border rounded-md p-3 bg-muted/30">
          <p className="text-xs font-medium text-muted-foreground mb-1">
            Difference from baseline
          </p>
          <p className="text-sm">{selectedVariant.change_summary}</p>
        </div>
      )}
    </div>
  );
}
