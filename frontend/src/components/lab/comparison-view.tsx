import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useGenerations } from "@/hooks/use-lab";
import type { LabGeneration } from "@/types/lab";
import GenerationResult from "./generation-result";

interface Props {
  comparisonGroup?: string | null;
}

export default function ComparisonView({ comparisonGroup }: Props) {
  const [groupFilter, setGroupFilter] = useState(comparisonGroup || "");

  // Load all generations if no specific group, or load by group
  const { data, isLoading } = useGenerations(
    groupFilter ? { comparison_group: groupFilter, limit: 50 } : { limit: 50 }
  );

  // Group generations by comparison_group
  const groups = new Map<string, LabGeneration[]>();
  const ungrouped: LabGeneration[] = [];

  data?.generations?.forEach((gen) => {
    if (gen.comparison_group) {
      const existing = groups.get(gen.comparison_group) || [];
      existing.push(gen);
      groups.set(gen.comparison_group, existing);
    } else {
      ungrouped.push(gen);
    }
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        Loading generations...
      </div>
    );
  }

  if (groups.size === 0 && ungrouped.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground">
        No generations yet. Generate narratives from the Generate tab.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Comparison groups */}
      {Array.from(groups.entries()).map(([groupId, gens]) => (
        <Card key={groupId}>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              Comparison Group
              <Badge variant="outline" className="text-[10px] font-mono">
                {groupId.slice(0, 8)}
              </Badge>
              <span className="text-muted-foreground font-normal">
                {gens.length} variants
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div
              className={`grid gap-4 ${
                gens.length === 2
                  ? "grid-cols-2"
                  : gens.length >= 3
                  ? "grid-cols-1 lg:grid-cols-3"
                  : "grid-cols-1"
              }`}
            >
              {gens.map((gen) => (
                <GenerationResult key={gen.id} generation={gen} compact />
              ))}
            </div>
          </CardContent>
        </Card>
      ))}

      {/* Ungrouped generations */}
      {ungrouped.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold mb-2">
            Individual Generations
          </h3>
          <div className="space-y-3">
            {ungrouped.map((gen) => (
              <GenerationResult key={gen.id} generation={gen} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
