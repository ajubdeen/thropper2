import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  ThumbsUp,
  ThumbsDown,
  ChevronDown,
  Clock,
  Copy,
  Check,
} from "lucide-react";
import { useUpdateGeneration } from "@/hooks/use-lab";
import type { LabGeneration } from "@/types/lab";

interface Props {
  generation: LabGeneration;
  compact?: boolean;
}

export default function GenerationResult({ generation, compact }: Props) {
  const [showRaw, setShowRaw] = useState(false);
  const [notes, setNotes] = useState(generation.notes || "");
  const [copied, setCopied] = useState(false);
  const updateGen = useUpdateGeneration();

  const handleRate = (rating: number) => {
    const newRating = generation.rating === rating ? null : rating;
    updateGen.mutate({ id: generation.id, rating: newRating as any });
  };

  const handleSaveNotes = () => {
    updateGen.mutate({ id: generation.id, notes });
  };

  const copyNarrative = () => {
    navigator.clipboard.writeText(generation.narrative_text || generation.raw_response);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const modelShort = generation.model.split("-").slice(-2).join(" ");

  return (
    <Card
      className={
        generation.rating === 2
          ? "border-green-500/50"
          : generation.rating === 1
          ? "border-red-500/50"
          : ""
      }
    >
      <CardContent className="p-3 space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {generation.comparison_label && (
              <Badge>{generation.comparison_label}</Badge>
            )}
            <Badge variant="outline">{modelShort}</Badge>
            <Badge variant="secondary">
              T:{generation.temperature} D:{generation.dice_roll ?? "?"}
            </Badge>
            {generation.generation_time_ms && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {(generation.generation_time_ms / 1000).toFixed(1)}s
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant={generation.rating === 2 ? "default" : "ghost"}
              size="icon"
              className="h-7 w-7"
              onClick={() => handleRate(2)}
            >
              <ThumbsUp className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant={generation.rating === 1 ? "destructive" : "ghost"}
              size="icon"
              className="h-7 w-7"
              onClick={() => handleRate(1)}
            >
              <ThumbsDown className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={copyNarrative}
            >
              {copied ? (
                <Check className="h-3.5 w-3.5" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>
        </div>

        {/* Narrative text */}
        <ScrollArea className={compact ? "max-h-[200px]" : "max-h-[400px]"}>
          <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap text-sm">
            {generation.narrative_text || generation.raw_response}
          </div>
        </ScrollArea>

        {/* Parsed data */}
        <div className="flex flex-wrap gap-1">
          {generation.anchor_deltas &&
            Object.entries(generation.anchor_deltas).map(([key, val]) => (
              <Badge
                key={key}
                variant={
                  (val as number) > 0
                    ? "default"
                    : (val as number) < 0
                    ? "destructive"
                    : "secondary"
                }
                className="text-[10px]"
              >
                {key}: {(val as number) > 0 ? "+" : ""}
                {val as number}
              </Badge>
            ))}
          {generation.parsed_character_name && (
            <Badge variant="outline" className="text-[10px]">
              Char: {generation.parsed_character_name}
            </Badge>
          )}
          {generation.parsed_npcs?.map((npc: string) => (
            <Badge key={npc} variant="outline" className="text-[10px]">
              NPC: {npc}
            </Badge>
          ))}
          {generation.parsed_wisdom && (
            <Badge variant="outline" className="text-[10px]">
              Wisdom: {generation.parsed_wisdom}
            </Badge>
          )}
        </div>

        {/* Parsed choices */}
        {generation.parsed_choices?.length > 0 && (
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">
              Generated Choices:
            </p>
            {generation.parsed_choices.map((c) => (
              <p key={c.id} className="text-xs">
                [{c.id}] {c.text}
              </p>
            ))}
          </div>
        )}

        {/* Notes */}
        {!compact && (
          <div className="flex gap-2">
            <Textarea
              placeholder="Notes..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={1}
              className="text-xs"
            />
            <Button
              size="sm"
              variant="outline"
              onClick={handleSaveNotes}
              disabled={notes === (generation.notes || "")}
            >
              Save
            </Button>
          </div>
        )}

        {/* Raw response toggle */}
        {!compact && (
          <Collapsible open={showRaw} onOpenChange={setShowRaw}>
            <CollapsibleTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-between text-xs"
              >
                Raw Response
                <ChevronDown
                  className={`h-3 w-3 transition-transform ${
                    showRaw ? "rotate-180" : ""
                  }`}
                />
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <pre className="text-xs font-mono bg-muted p-2 rounded overflow-x-auto whitespace-pre-wrap">
                {generation.raw_response}
              </pre>
            </CollapsibleContent>
          </Collapsible>
        )}
      </CardContent>
    </Card>
  );
}
