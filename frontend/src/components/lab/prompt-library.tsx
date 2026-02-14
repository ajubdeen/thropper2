import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
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
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Plus,
  Trash2,
  Save,
  Rocket,
  RotateCcw,
  ChevronDown,
  History,
  Database,
} from "lucide-react";
import {
  usePromptVariants,
  useCreatePromptVariant,
  useUpdatePromptVariant,
  useDeletePromptVariant,
  usePushLive,
  useRevertPrompt,
  useLiveStatus,
  useVersionHistory,
  useBaselinePrompt,
  useSeedBaselines,
} from "@/hooks/use-lab";
import type { LabPromptVariant } from "@/types/lab";

const PROMPT_TYPES = [
  { value: "system", label: "System" },
  { value: "turn", label: "Turn" },
  { value: "arrival", label: "Arrival" },
  { value: "window", label: "Window" },
];

export default function PromptLibrary() {
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTemplate, setEditTemplate] = useState("");
  const [editName, setEditName] = useState("");
  const [diffViewId, setDiffViewId] = useState<string | null>(null);
  const [historyType, setHistoryType] = useState<string | null>(null);

  const { data: variants, isLoading } = usePromptVariants(
    typeFilter || undefined
  );
  const { data: liveStatus } = useLiveStatus();
  const updateVariant = useUpdatePromptVariant();
  const deleteVariant = useDeletePromptVariant();
  const pushLive = usePushLive();
  const revertPrompt = useRevertPrompt();
  const seedBaselines = useSeedBaselines();

  const startEditing = (v: LabPromptVariant) => {
    setEditingId(v.id);
    setEditTemplate(v.template);
    setEditName(v.name);
  };

  const saveEditing = () => {
    if (!editingId) return;
    updateVariant.mutate(
      { id: editingId, name: editName, template: editTemplate },
      { onSuccess: () => setEditingId(null) }
    );
  };

  return (
    <div className="space-y-4">
      {/* Header: filters + actions */}
      <div className="flex items-center gap-2 flex-wrap">
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            {PROMPT_TYPES.map((t) => (
              <SelectItem key={t.value} value={t.value}>
                <span className="flex items-center gap-1.5">
                  {t.label}
                  {liveStatus?.[t.value]?.is_live && (
                    <span className="inline-block w-2 h-2 rounded-full bg-green-500" />
                  )}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <CreateVariantDialog />
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

      {/* Live status banner */}
      {liveStatus && Object.values(liveStatus).some((s) => s.is_live) && (
        <div className="bg-green-500/10 border border-green-500/30 rounded p-2">
          <p className="text-xs font-medium text-green-700 dark:text-green-400">
            Active overrides:{" "}
            {Object.entries(liveStatus)
              .filter(([, s]) => s.is_live)
              .map(
                ([pt, s]) =>
                  `${pt} (v${s.version_number} — ${s.variant_name})`
              )
              .join(", ")}
          </p>
        </div>
      )}

      {/* Version history panel */}
      {historyType && (
        <VersionHistoryPanel
          promptType={historyType}
          onClose={() => setHistoryType(null)}
        />
      )}

      <ScrollArea className="h-[600px]">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading...</p>
        ) : !variants?.length ? (
          <p className="text-sm text-muted-foreground">
            No prompt variants saved. Click "Seed Baselines" to create baseline entries, then
            create new variants from there.
          </p>
        ) : (
          <div className="space-y-3">
            {variants.map((v) => (
              <Card
                key={v.id}
                className={v.is_live ? "border-green-500/50" : ""}
              >
                <CardContent className="p-3 space-y-2">
                  {/* Header row */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 flex-wrap">
                      {editingId === v.id ? (
                        <Input
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          className="h-7 text-sm w-48"
                        />
                      ) : (
                        <span className="font-medium text-sm">{v.name}</span>
                      )}
                      <Badge variant="secondary" className="text-[10px]">
                        {v.prompt_type}
                      </Badge>
                      <Badge variant="outline" className="text-[10px]">
                        v{v.version_number}
                      </Badge>
                      {v.is_default && (
                        <Badge className="text-[10px]">baseline</Badge>
                      )}
                      {v.is_live && (
                        <Badge className="text-[10px] bg-green-600">
                          LIVE
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      {/* Push live / Revert */}
                      {!v.is_default && !v.is_live && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-xs h-7"
                          onClick={() => {
                            if (
                              confirm(
                                `Push "${v.name}" live for ${v.prompt_type}? This will affect the live game.`
                              )
                            )
                              pushLive.mutate(v.id);
                          }}
                          disabled={pushLive.isPending}
                        >
                          <Rocket className="h-3 w-3 mr-1" /> Push Live
                        </Button>
                      )}
                      {v.is_live && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="text-xs h-7 border-orange-500/50 text-orange-600"
                          onClick={() => {
                            if (
                              confirm(
                                `Revert ${v.prompt_type} to baseline? The game will use the default prompt.`
                              )
                            )
                              revertPrompt.mutate(v.prompt_type);
                          }}
                          disabled={revertPrompt.isPending}
                        >
                          <RotateCcw className="h-3 w-3 mr-1" /> Revert
                        </Button>
                      )}
                      {/* Version history */}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-xs h-7"
                        onClick={() => setHistoryType(v.prompt_type)}
                      >
                        <History className="h-3 w-3 mr-1" /> History
                      </Button>
                      {/* Edit */}
                      {editingId === v.id ? (
                        <Button size="sm" className="h-7" onClick={saveEditing}>
                          <Save className="h-3 w-3 mr-1" /> Save
                        </Button>
                      ) : (
                        !v.is_default && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7"
                            onClick={() => startEditing(v)}
                          >
                            Edit
                          </Button>
                        )
                      )}
                      {/* Delete */}
                      {!v.is_default && !v.is_live && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => {
                            if (confirm("Delete this variant?"))
                              deleteVariant.mutate(v.id);
                          }}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Change summary */}
                  {v.change_summary && !v.is_default && (
                    <p className="text-xs text-muted-foreground">
                      {v.change_summary}
                    </p>
                  )}

                  {/* Template editor/preview */}
                  {editingId === v.id ? (
                    <Textarea
                      value={editTemplate}
                      onChange={(e) => setEditTemplate(e.target.value)}
                      rows={12}
                      className="text-xs font-mono"
                    />
                  ) : (
                    <pre className="text-xs font-mono bg-muted p-2 rounded max-h-32 overflow-auto whitespace-pre-wrap">
                      {v.template.slice(0, 500)}
                      {v.template.length > 500 ? "..." : ""}
                    </pre>
                  )}

                  {/* Diff viewer (collapsible) */}
                  {(v.diff_vs_baseline || v.diff_vs_previous) && (
                    <Collapsible
                      open={diffViewId === v.id}
                      onOpenChange={(open) =>
                        setDiffViewId(open ? v.id : null)
                      }
                    >
                      <CollapsibleTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="w-full justify-between text-xs h-7"
                        >
                          View Diffs
                          <ChevronDown
                            className={`h-3 w-3 transition-transform ${
                              diffViewId === v.id ? "rotate-180" : ""
                            }`}
                          />
                        </Button>
                      </CollapsibleTrigger>
                      <CollapsibleContent className="space-y-2 mt-2">
                        {v.diff_vs_baseline && (
                          <div>
                            <p className="text-xs font-semibold mb-1">
                              Changes vs Baseline:
                            </p>
                            <DiffViewer diff={v.diff_vs_baseline} />
                          </div>
                        )}
                        {v.diff_vs_previous && (
                          <div>
                            <p className="text-xs font-semibold mb-1">
                              Changes vs Previous Version:
                            </p>
                            <DiffViewer diff={v.diff_vs_previous} />
                          </div>
                        )}
                      </CollapsibleContent>
                    </Collapsible>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}

function DiffViewer({ diff }: { diff: string }) {
  const lines = diff.split("\n");
  return (
    <ScrollArea className="max-h-48">
      <pre className="text-[10px] font-mono p-2 rounded bg-muted overflow-auto">
        {lines.map((line, i) => {
          let className = "";
          if (line.startsWith("+") && !line.startsWith("+++"))
            className = "text-green-600 dark:text-green-400 bg-green-500/10";
          else if (line.startsWith("-") && !line.startsWith("---"))
            className = "text-red-600 dark:text-red-400 bg-red-500/10";
          else if (line.startsWith("@@"))
            className = "text-blue-600 dark:text-blue-400";

          return (
            <div key={i} className={className}>
              {line}
            </div>
          );
        })}
      </pre>
    </ScrollArea>
  );
}

function VersionHistoryPanel({
  promptType,
  onClose,
}: {
  promptType: string;
  onClose: () => void;
}) {
  const { data: versions, isLoading } = useVersionHistory(promptType);

  return (
    <Card>
      <CardContent className="p-3">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold">
            Version History: {promptType}
          </h3>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
        {isLoading ? (
          <p className="text-xs text-muted-foreground">Loading...</p>
        ) : !versions?.length ? (
          <p className="text-xs text-muted-foreground">No versions found.</p>
        ) : (
          <div className="space-y-1">
            {versions.map((v) => (
              <div
                key={v.id}
                className="flex items-center gap-2 text-xs py-1 border-b last:border-0"
              >
                <Badge
                  variant="outline"
                  className="text-[10px] shrink-0"
                >
                  v{v.version_number}
                </Badge>
                <span className="font-medium truncate">{v.name}</span>
                {v.is_default && (
                  <Badge className="text-[10px] shrink-0">baseline</Badge>
                )}
                {v.is_live && (
                  <Badge className="text-[10px] bg-green-600 shrink-0">
                    LIVE
                  </Badge>
                )}
                <span className="text-muted-foreground truncate ml-auto">
                  {v.change_summary || ""}
                </span>
                <span className="text-muted-foreground shrink-0">
                  {new Date(v.created_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function CreateVariantDialog() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [promptType, setPromptType] = useState("system");
  const [template, setTemplate] = useState("");
  const [loadedBaseline, setLoadedBaseline] = useState(false);
  const create = useCreatePromptVariant();
  const { data: baseline } = useBaselinePrompt(open ? promptType : null);

  // Auto-load baseline template when type changes
  const loadBaseline = () => {
    if (baseline?.template) {
      setTemplate(baseline.template);
      setLoadedBaseline(true);
    }
  };

  const handleCreate = () => {
    create.mutate(
      {
        name,
        description: description || undefined,
        prompt_type: promptType,
        template,
      },
      {
        onSuccess: () => {
          setOpen(false);
          setName("");
          setDescription("");
          setTemplate("");
          setLoadedBaseline(false);
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="h-4 w-4 mr-1" /> New Variant
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Create Prompt Variant</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Name</Label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. More dramatic tone"
              />
            </div>
            <div>
              <Label>Type</Label>
              <Select
                value={promptType}
                onValueChange={(v) => {
                  setPromptType(v);
                  setLoadedBaseline(false);
                }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PROMPT_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div>
            <Label>Description</Label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What's different about this variant?"
            />
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <Label>Template</Label>
              {baseline && !loadedBaseline && (
                <Button
                  variant="outline"
                  size="sm"
                  className="text-xs h-6"
                  onClick={loadBaseline}
                >
                  Load Baseline
                </Button>
              )}
            </div>
            <Textarea
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              rows={14}
              className="text-xs font-mono"
              placeholder="Paste or edit the prompt template here. Use {variable_name} for dynamic values."
            />
          </div>
          <Button
            className="w-full"
            onClick={handleCreate}
            disabled={!name || !template || create.isPending}
          >
            {create.isPending ? "Creating..." : "Create Variant"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
