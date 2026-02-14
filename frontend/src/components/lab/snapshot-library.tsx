import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Trash2, Import, Plus, FlaskConical, Search } from "lucide-react";
import {
  useSnapshots,
  useDeleteSnapshot,
  useAllSaves,
  useImportSnapshot,
  useCreateSyntheticSnapshot,
  useEras,
} from "@/hooks/use-lab";
import type { LabSnapshot, LabEra } from "@/types/lab";

interface Props {
  selectedSnapshotId: string | null;
  onSelectSnapshot: (id: string) => void;
}

export default function SnapshotLibrary({
  selectedSnapshotId,
  onSelectSnapshot,
}: Props) {
  const [search, setSearch] = useState("");
  const [eraFilter, setEraFilter] = useState<string>("");
  const { data, isLoading } = useSnapshots({
    search: search || undefined,
    era_id: eraFilter || undefined,
    limit: 50,
  });
  const { data: eras } = useEras();
  const deleteSnapshot = useDeleteSnapshot();

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search snapshots..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>
        <Select value={eraFilter} onValueChange={setEraFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All eras" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All eras</SelectItem>
            {eras?.map((era) => (
              <SelectItem key={era.id} value={era.id}>
                {era.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex gap-2">
        <ImportDialog eras={eras || []} />
        <SyntheticDialog eras={eras || []} />
      </div>

      <ScrollArea className="h-[500px]">
        {isLoading ? (
          <p className="text-sm text-muted-foreground p-4">Loading...</p>
        ) : !data?.snapshots?.length ? (
          <p className="text-sm text-muted-foreground p-4">
            No snapshots yet. Import a save or create a synthetic snapshot.
          </p>
        ) : (
          <div className="space-y-2">
            {data.snapshots.map((snap) => (
              <Card
                key={snap.id}
                className={`cursor-pointer transition-colors ${
                  selectedSnapshotId === snap.id
                    ? "border-primary bg-primary/5"
                    : "hover:bg-muted/50"
                }`}
                onClick={() => onSelectSnapshot(snap.id)}
              >
                <CardContent className="p-3">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <p className="font-medium text-sm">{snap.label}</p>
                      <p className="text-xs text-muted-foreground">
                        {snap.era_name || "Unknown era"} &middot;{" "}
                        {snap.total_turns} turns &middot;{" "}
                        {snap.player_name || "Unknown"}
                      </p>
                      <div className="flex gap-1">
                        <Badge variant="secondary" className="text-[10px]">
                          B:{snap.belonging_value}
                        </Badge>
                        <Badge variant="secondary" className="text-[10px]">
                          L:{snap.legacy_value}
                        </Badge>
                        <Badge variant="secondary" className="text-[10px]">
                          F:{snap.freedom_value}
                        </Badge>
                        {snap.tags?.map((t) => (
                          <Badge
                            key={t}
                            variant="outline"
                            className="text-[10px]"
                          >
                            {t}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 shrink-0"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm("Delete this snapshot?"))
                          deleteSnapshot.mutate(snap.id);
                      }}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}

function ImportDialog({ eras }: { eras: LabEra[] }) {
  const [open, setOpen] = useState(false);
  const { data: saves, isLoading } = useAllSaves();
  const importSnapshot = useImportSnapshot();

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Import className="h-4 w-4 mr-1" /> Import Save
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Import from Player Save</DialogTitle>
        </DialogHeader>
        <ScrollArea className="h-[400px]">
          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading saves...</p>
          ) : !saves?.length ? (
            <p className="text-sm text-muted-foreground">No saves found.</p>
          ) : (
            <div className="space-y-2">
              {saves.map((s, i) => (
                <Card key={i} className="cursor-pointer hover:bg-muted/50">
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium">
                          {s.player_name || "Unknown"} &middot;{" "}
                          {s.current_era || "?"}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {s.email || s.user_id} &middot; {s.phase}
                        </p>
                      </div>
                      <Button
                        size="sm"
                        disabled={importSnapshot.isPending}
                        onClick={() =>
                          importSnapshot.mutate(
                            {
                              user_id: s.user_id,
                              game_id: s.game_id,
                              label: `Import: ${s.player_name} - ${s.current_era}`,
                            },
                            { onSuccess: () => setOpen(false) }
                          )
                        }
                      >
                        Import
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}

function SyntheticDialog({ eras }: { eras: LabEra[] }) {
  const [open, setOpen] = useState(false);
  const [label, setLabel] = useState("Synthetic test");
  const [eraId, setEraId] = useState("");
  const [turns, setTurns] = useState(5);
  const [belonging, setBelonging] = useState(30);
  const [legacy, setLegacy] = useState(20);
  const [freedom, setFreedom] = useState(25);
  const createSynthetic = useCreateSyntheticSnapshot();

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <FlaskConical className="h-4 w-4 mr-1" /> Synthetic
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Synthetic Snapshot</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label>Label</Label>
            <Input value={label} onChange={(e) => setLabel(e.target.value)} />
          </div>
          <div>
            <Label>Era</Label>
            <Select value={eraId} onValueChange={setEraId}>
              <SelectTrigger>
                <SelectValue placeholder="Select era..." />
              </SelectTrigger>
              <SelectContent>
                {eras.map((era) => (
                  <SelectItem key={era.id} value={era.id}>
                    {era.name} ({era.year})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Turns: {turns}</Label>
            <Slider
              value={[turns]}
              onValueChange={([v]: number[]) => setTurns(v)}
              min={1}
              max={20}
              step={1}
            />
          </div>
          <div>
            <Label>Belonging: {belonging}</Label>
            <Slider
              value={[belonging]}
              onValueChange={([v]: number[]) => setBelonging(v)}
              min={0}
              max={100}
            />
          </div>
          <div>
            <Label>Legacy: {legacy}</Label>
            <Slider
              value={[legacy]}
              onValueChange={([v]: number[]) => setLegacy(v)}
              min={0}
              max={100}
            />
          </div>
          <div>
            <Label>Freedom: {freedom}</Label>
            <Slider
              value={[freedom]}
              onValueChange={([v]: number[]) => setFreedom(v)}
              min={0}
              max={100}
            />
          </div>
          <Button
            className="w-full"
            disabled={!eraId || createSynthetic.isPending}
            onClick={() =>
              createSynthetic.mutate(
                { label, era_id: eraId, total_turns: turns, belonging, legacy, freedom },
                { onSuccess: () => setOpen(false) }
              )
            }
          >
            {createSynthetic.isPending ? "Creating..." : "Create Snapshot"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
