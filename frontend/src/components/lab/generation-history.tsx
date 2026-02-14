import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useGenerations, useModels } from "@/hooks/use-lab";
import GenerationResult from "./generation-result";

export default function GenerationHistory() {
  const [modelFilter, setModelFilter] = useState<string>("");
  const [ratingFilter, setRatingFilter] = useState<string>("");
  const { data: models } = useModels();
  const { data, isLoading } = useGenerations({
    model: modelFilter || undefined,
    rating:
      ratingFilter === "up" ? 2 : ratingFilter === "down" ? 1 : undefined,
    limit: 50,
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Select value={modelFilter} onValueChange={setModelFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All models" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All models</SelectItem>
            {models?.map((m) => (
              <SelectItem key={m.id} value={m.id}>
                {m.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={ratingFilter} onValueChange={setRatingFilter}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="All ratings" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All ratings</SelectItem>
            <SelectItem value="up">Thumbs up</SelectItem>
            <SelectItem value="down">Thumbs down</SelectItem>
          </SelectContent>
        </Select>
        {data && (
          <Badge variant="secondary">{data.total} generations</Badge>
        )}
      </div>

      <ScrollArea className="h-[600px]">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading...</p>
        ) : !data?.generations?.length ? (
          <p className="text-sm text-muted-foreground">
            No generations yet.
          </p>
        ) : (
          <div className="space-y-3">
            {data.generations.map((gen) => (
              <GenerationResult key={gen.id} generation={gen} />
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
