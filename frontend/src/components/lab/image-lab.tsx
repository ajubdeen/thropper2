import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2, ImageIcon } from "lucide-react";
import { useGenerateImage, useNarratives, useExtractScene } from "@/hooks/use-lab";

// Default prompt — matches the current STYLE_BLOCK from portrait_generator.py
const DEFAULT_PROMPT = `STYLE:
Painted 1980s epic adventure movie poster.
Thick visible oil brushstrokes.
Rich saturated pigments.
Hand-painted illustration.
Not photorealistic.

Ultra-wide 3:2 landscape.

LIGHTING:
Warm golden chiaroscuro like a richly lit oil painting.
Single powerful warm spotlight from above the central group.
Figures glow with golden highlights on faces, hands, and fabric.
Sculpted shadows under chins and behind bodies add depth.
The background is warmly lit but secondary — architectural details, wall decorations, and furniture are clearly visible in warm amber tones.
The room feels like a candlelit interior with warm ambient glow throughout.
Figures are the brightest part of the image but the room is NOT dark — it has rich warm light.
Brightness contrast is moderate — figures are about 2x brighter than the room.
Everything warm and golden. No cold or harsh lighting.

COMPOSITION:
Ultra-wide establishing shot pulled far back.
The architecture dominates the frame — 70-75% of the image is room and background.
The figures occupy the center but are dwarfed by the vast space around them.
Floor visible.
Ceiling visible in shadow.
One central seated figure in ornate chair at exact center.
Only one person seated.
All others stand behind in loose V-formation.
Heights varied naturally.
Everyone faces generally forward.

MOOD:
Contented pride. Dignified. Composed.
Chins raised. Shoulders back. Strong posture.
Expressions are calm and settled — the look of people who have earned their place.
Mouths closed or nearly closed. No broad grins, no open smiles.
Some characters may have a smile just beginning to form at the corners of the mouth — the feeling of quiet joy held in check.
Central figure: strong, composed, serene confidence with warmth in the eyes. Maximum age 50. Not elderly. Not frail. Strong and vital with distinguished silver-touched hair.
The overall feeling is a family portrait of quiet triumph — people who have nothing left to prove.

NO text, NO titles, NO logos, NO borders, NO watermarks.`;

const MODELS = [
  { value: "gpt-image-1.5", label: "gpt-image-1.5" },
  { value: "gpt-image-1", label: "gpt-image-1" },
  { value: "dall-e-3", label: "dall-e-3" },
];

const QUALITIES = [
  { value: "medium", label: "medium" },
  { value: "high", label: "high" },
  { value: "low", label: "low" },
];

const SIZES = [
  { value: "1536x1024", label: "1536×1024 (landscape 3:2)" },
  { value: "1024x1024", label: "1024×1024 (square)" },
  { value: "1024x1536", label: "1024×1536 (portrait)" },
];

export function ImageLab() {
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [model, setModel] = useState("gpt-image-1.5");
  const [quality, setQuality] = useState("medium");
  const [size, setSize] = useState("1536x1024");
  const [selectedNarrative, setSelectedNarrative] = useState("");
  const [result, setResult] = useState<{
    image_path: string;
    generatedAt: string;
    model: string;
    quality: string;
    size: string;
  } | null>(null);

  const { data: narrativesData } = useNarratives();
  const narratives = narrativesData?.narratives ?? [];

  const generate = useGenerateImage();
  const extractScene = useExtractScene();

  function handleNarrativeSelect(entry_id: string) {
    setSelectedNarrative(entry_id);
    if (!entry_id) {
      setPrompt(DEFAULT_PROMPT);
      return;
    }
    extractScene.mutate(
      { entry_id },
      {
        onSuccess: (data) => setPrompt(data.prompt_text),
      }
    );
  }

  function handleGenerate() {
    generate.mutate(
      { prompt, model, quality, size },
      {
        onSuccess: (data) => {
          setResult({
            image_path: data.image_path,
            generatedAt: new Date().toLocaleTimeString(),
            model,
            quality,
            size,
          });
        },
      }
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[30%_70%] gap-6 h-full">
      {/* Left pane — Prompt Editor */}
      <div className="flex flex-col gap-3">

        {/* Narrative dropdown */}
        <Select value={selectedNarrative} onValueChange={handleNarrativeSelect}>
          <SelectTrigger className="w-full h-8 text-xs">
            <SelectValue placeholder="— Select a narrative —" />
          </SelectTrigger>
          <SelectContent className="max-h-72">
            <SelectItem value="" className="text-xs text-muted-foreground">
              — Select a narrative —
            </SelectItem>
            {narratives.map((n) => (
              <SelectItem key={n.entry_id} value={n.entry_id} className="text-xs">
                <span title={n.player_narrative || undefined}>
                  {n.character_name} — {n.final_era}
                  {n.final_era_year ? ` (${n.final_era_year})` : ""}
                  {"  "}[{n.total_score}]
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {extractScene.isError && (
          <p className="text-xs text-destructive">{extractScene.error.message}</p>
        )}

        {/* Parameter dropdowns + Generate button */}
        <div className="flex flex-wrap gap-2 items-center">
          <Select value={model} onValueChange={setModel}>
            <SelectTrigger className="w-[160px] h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MODELS.map((m) => (
                <SelectItem key={m.value} value={m.value} className="text-xs">
                  {m.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={quality} onValueChange={setQuality}>
            <SelectTrigger className="w-[110px] h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {QUALITIES.map((q) => (
                <SelectItem key={q.value} value={q.value} className="text-xs">
                  {q.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={size} onValueChange={setSize}>
            <SelectTrigger className="w-[190px] h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SIZES.map((s) => (
                <SelectItem key={s.value} value={s.value} className="text-xs">
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button
            size="sm"
            onClick={handleGenerate}
            disabled={generate.isPending || extractScene.isPending || !prompt.trim()}
            className="ml-auto h-8"
          >
            {generate.isPending ? (
              <>
                <Loader2 className="h-3 w-3 animate-spin mr-1" />
                Generating…
              </>
            ) : (
              "Generate"
            )}
          </Button>
        </div>

        {/* Prompt textarea with extraction overlay */}
        <div className="relative flex-1">
          <Textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className={`h-full min-h-[calc(100vh-280px)] resize-none font-mono text-xs leading-relaxed ${
              extractScene.isPending ? "opacity-40 pointer-events-none" : ""
            }`}
            placeholder="Enter image generation prompt…"
          />
          {extractScene.isPending && (
            <div className="absolute inset-0 flex items-center justify-center">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              <span className="ml-2 text-sm text-muted-foreground">Extracting scene…</span>
            </div>
          )}
        </div>

        {generate.isError && (
          <p className="text-xs text-destructive">{generate.error.message}</p>
        )}
      </div>

      {/* Right pane — Image Display */}
      <div className="flex flex-col gap-3">
        {generate.isPending ? (
          <div className="flex flex-col items-center justify-center h-full min-h-[400px] rounded-lg border border-dashed border-muted-foreground/30 bg-muted/20 gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Generating image…</p>
            <p className="text-xs text-muted-foreground/60">This takes 15–30 seconds</p>
          </div>
        ) : result ? (
          <>
            <img
              src={result.image_path}
              alt="Generated portrait"
              className="w-full rounded-lg border border-border object-contain"
            />
            <p className="text-xs text-muted-foreground">
              {result.model} · {result.quality} · {result.size} · {result.generatedAt}
            </p>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full min-h-[400px] rounded-lg border border-dashed border-muted-foreground/30 bg-muted/20 gap-3">
            <ImageIcon className="h-10 w-10 text-muted-foreground/40" />
            <p className="text-sm text-muted-foreground">Generate an image to see it here</p>
          </div>
        )}
      </div>
    </div>
  );
}
