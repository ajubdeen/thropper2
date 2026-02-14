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
  usePushLive,
  useRevertPrompt,
  useLiveStatus,
  useBaselinePrompt,
  useSeedBaselines,
} from "@/hooks/use-lab";

const COLUMNS: { promptType: string; label: string }[] = [
  { promptType: "system", label: "System Prompt" },
  { promptType: "turn", label: "Turn Prompt" },
  { promptType: "arrival", label: "Arrival Prompt" },
  { promptType: "window", label: "Window Prompt" },
];

export default function PromptLibrary() {
  const seedBaselines = useSeedBaselines();

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          View and edit prompt templates. Save variants and push live to
          override the default prompts in the game.
        </p>
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
      <div className="grid grid-cols-4 gap-3">
        {COLUMNS.map((col) => (
          <PromptColumn
            key={col.promptType}
            promptType={col.promptType}
            label={col.label}
          />
        ))}
      </div>
    </div>
  );
}

function PromptColumn({
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
  const pushLive = usePushLive();
  const revertPrompt = useRevertPrompt();

  const [selectedVariantId, setSelectedVariantId] = useState("baseline");
  const [template, setTemplate] = useState("");
  const [variantName, setVariantName] = useState("");
  const [savedId, setSavedId] = useState<string | null>(null);
  const [pushed, setPushed] = useState(false);

  const isLive = liveStatus?.[promptType]?.is_live ?? false;

  // Load baseline on mount / when baseline data arrives
  useEffect(() => {
    if (baseline?.template && selectedVariantId === "baseline") {
      setTemplate(baseline.template);
    }
  }, [baseline?.template, selectedVariantId]);

  // Auto-suggest next variant name
  useEffect(() => {
    if (variants) {
      const maxVersion = variants.reduce(
        (max, v) => Math.max(max, v.version_number),
        0
      );
      setVariantName(`${label.split(" ")[0]} v${maxVersion + 1}`);
    }
  }, [variants, label]);

  const handleVariantChange = (id: string) => {
    setSelectedVariantId(id);
    setSavedId(null);
    setPushed(false);
    if (id === "baseline") {
      setTemplate(baseline?.template || "");
    } else {
      const variant = variants?.find((v) => v.id === id);
      if (variant) setTemplate(variant.template);
    }
  };

  const handleSave = () => {
    if (!variantName.trim() || !template.trim()) return;
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
        },
      }
    );
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

  return (
    <div className="flex flex-col gap-2 min-w-0">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Label className="font-semibold text-sm">{label}</Label>
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

      {/* Variant selector */}
      <Select value={selectedVariantId} onValueChange={handleVariantChange}>
        <SelectTrigger className="h-8 text-xs">
          <SelectValue placeholder="Select variant..." />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="baseline">Baseline (default)</SelectItem>
          {variants?.map((v) => (
            <SelectItem key={v.id} value={v.id}>
              {v.name}
              {v.is_live ? " (LIVE)" : ""}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Tall textarea */}
      <Textarea
        value={template}
        onChange={(e) => {
          setTemplate(e.target.value);
          setSavedId(null);
          setPushed(false);
        }}
        className="flex-1 min-h-[600px] text-xs font-mono resize-y"
        placeholder="Loading template..."
      />

      {/* Save controls */}
      <div className="flex items-center gap-1">
        <Input
          value={variantName}
          onChange={(e) => setVariantName(e.target.value)}
          placeholder="Variant name..."
          className="flex-1 h-8 text-xs"
        />
        <Button
          size="sm"
          className="h-8 shrink-0"
          onClick={handleSave}
          disabled={
            !variantName.trim() ||
            !template.trim() ||
            createVariant.isPending
          }
        >
          <Save className="h-3 w-3 mr-1" />
          {createVariant.isPending ? "..." : "Save"}
        </Button>
      </div>

      {/* Push Live / Revert */}
      <div className="flex items-center gap-1">
        {savedId && !pushed && (
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs flex-1"
            onClick={handlePush}
            disabled={pushLive.isPending}
          >
            <Rocket className="h-3 w-3 mr-1" />
            {pushLive.isPending ? "Pushing..." : "Push Live"}
          </Button>
        )}
        {isLive && (
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs flex-1 border-orange-500/50 text-orange-600"
            onClick={handleRevert}
            disabled={revertPrompt.isPending}
          >
            <RotateCcw className="h-3 w-3 mr-1" />
            {revertPrompt.isPending ? "..." : "Revert to Baseline"}
          </Button>
        )}
      </div>
    </div>
  );
}
