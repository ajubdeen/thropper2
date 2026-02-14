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
import { Plus, Trash2, Save } from "lucide-react";
import {
  usePromptVariants,
  useCreatePromptVariant,
  useUpdatePromptVariant,
  useDeletePromptVariant,
} from "@/hooks/use-lab";
import type { LabPromptVariant } from "@/types/lab";

const PROMPT_TYPES = [
  { value: "system", label: "System" },
  { value: "turn", label: "Turn" },
  { value: "arrival", label: "Arrival" },
  { value: "window", label: "Window" },
  { value: "staying_ending", label: "Staying Ending" },
];

export default function PromptLibrary() {
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTemplate, setEditTemplate] = useState("");
  const [editName, setEditName] = useState("");

  const { data: variants, isLoading } = usePromptVariants(
    typeFilter || undefined
  );
  const updateVariant = useUpdatePromptVariant();
  const deleteVariant = useDeletePromptVariant();

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
      <div className="flex items-center gap-2">
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            {PROMPT_TYPES.map((t) => (
              <SelectItem key={t.value} value={t.value}>
                {t.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <CreateVariantDialog />
      </div>

      <ScrollArea className="h-[600px]">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading...</p>
        ) : !variants?.length ? (
          <p className="text-sm text-muted-foreground">
            No prompt variants saved. Create one to get started.
          </p>
        ) : (
          <div className="space-y-3">
            {variants.map((v) => (
              <Card key={v.id}>
                <CardContent className="p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
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
                      {v.is_default && (
                        <Badge className="text-[10px]">default</Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      {editingId === v.id ? (
                        <Button size="sm" onClick={saveEditing}>
                          <Save className="h-3 w-3 mr-1" /> Save
                        </Button>
                      ) : (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => startEditing(v)}
                        >
                          Edit
                        </Button>
                      )}
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
                    </div>
                  </div>
                  {v.description && (
                    <p className="text-xs text-muted-foreground">
                      {v.description}
                    </p>
                  )}
                  {editingId === v.id ? (
                    <Textarea
                      value={editTemplate}
                      onChange={(e) => setEditTemplate(e.target.value)}
                      rows={10}
                      className="text-xs font-mono"
                    />
                  ) : (
                    <pre className="text-xs font-mono bg-muted p-2 rounded max-h-32 overflow-auto whitespace-pre-wrap">
                      {v.template.slice(0, 500)}
                      {v.template.length > 500 ? "..." : ""}
                    </pre>
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

function CreateVariantDialog() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [promptType, setPromptType] = useState("system");
  const [template, setTemplate] = useState("");
  const create = useCreatePromptVariant();

  const handleCreate = () => {
    create.mutate(
      { name, description: description || undefined, prompt_type: promptType, template },
      {
        onSuccess: () => {
          setOpen(false);
          setName("");
          setDescription("");
          setTemplate("");
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
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Prompt Variant</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <Label>Description</Label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div>
            <Label>Type</Label>
            <Select value={promptType} onValueChange={setPromptType}>
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
          <div>
            <Label>Template</Label>
            <Textarea
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              rows={10}
              className="text-xs font-mono"
            />
          </div>
          <Button
            className="w-full"
            onClick={handleCreate}
            disabled={!name || !template || create.isPending}
          >
            Create
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
