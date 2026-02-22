import { useState, useCallback, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Slider } from "@/components/ui/slider";
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
import { Play, Loader2, GitBranch, ChevronDown, Settings2, RotateCcw } from "lucide-react";
import {
  useQuickPlayStart,
  useQuickPlayEnterEra,
  useQuickPlayChoose,
  useQuickPlayContinue,
  useQuickPlayUpdateParams,
  usePromptVariants,
  useModels,
  useLabConfig,
} from "@/hooks/use-lab";
import type { QuickPlayTurnParams } from "@/hooks/use-lab";

interface GameMessage {
  type: string;
  data: Record<string, any>;
}

interface Props {
  onBranchSnapshot?: (snapshotId: string) => void;
}

const STORAGE_KEY = "anachron-quickplay-session";

interface PersistedState {
  sessionId: string | null;
  messages: GameMessage[];
  choices: Array<{ id: string; text: string }>;
  lastSnapshotId: string | null;
  waitingFor: string | null;
  gameState: Record<string, any> | null;
  playerName: string;
  region: string;
  systemVariantId: string;
  turnVariantId: string;
  arrivalVariantId: string;
  windowVariantId: string;
  model: string;
  temperature: number;
  diceRoll: number;
}

function loadPersistedState(): Partial<PersistedState> {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    // ignore
  }
  return {};
}

function savePersistedState(state: PersistedState) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // ignore quota errors
  }
}

function clearPersistedState() {
  sessionStorage.removeItem(STORAGE_KEY);
}

const DICE_LABELS: Record<number, string> = {
  1: "Catastrophic",
  5: "Unlucky",
  10: "Neutral",
  15: "Lucky",
  20: "Critical",
};

function getDiceLabel(value: number): string {
  if (value <= 1) return "1 — Catastrophic";
  if (value <= 3) return `${value} — Very Unlucky`;
  if (value <= 5) return `${value} — Unlucky`;
  if (value <= 8) return `${value} — Below Average`;
  if (value <= 12) return `${value} — Neutral`;
  if (value <= 15) return `${value} — Lucky`;
  if (value <= 18) return `${value} — Very Lucky`;
  if (value <= 19) return `${value} — Excellent`;
  return "20 — Critical Success";
}

export default function QuickPlayPanel({ onBranchSnapshot }: Props) {
  const persisted = useRef(loadPersistedState()).current;

  // Session state
  const [sessionId, setSessionId] = useState<string | null>(persisted.sessionId ?? null);
  const [messages, setMessages] = useState<GameMessage[]>(persisted.messages ?? []);
  const [choices, setChoices] = useState<Array<{ id: string; text: string }>>(persisted.choices ?? []);
  const [lastSnapshotId, setLastSnapshotId] = useState<string | null>(persisted.lastSnapshotId ?? null);
  const [waitingFor, setWaitingFor] = useState<string | null>(persisted.waitingFor ?? null);
  const [gameState, setGameState] = useState<Record<string, any> | null>(persisted.gameState ?? null);

  // Config state
  const [playerName, setPlayerName] = useState(persisted.playerName ?? "Lab Tester");
  const [region, setRegion] = useState(persisted.region ?? "european");
  const [systemVariantId, setSystemVariantId] = useState(persisted.systemVariantId ?? "");
  const [turnVariantId, setTurnVariantId] = useState(persisted.turnVariantId ?? "");
  const [arrivalVariantId, setArrivalVariantId] = useState(persisted.arrivalVariantId ?? "");
  const [windowVariantId, setWindowVariantId] = useState(persisted.windowVariantId ?? "");
  const [model, setModel] = useState(persisted.model ?? "");
  const [temperature, setTemperature] = useState(persisted.temperature ?? 1.0);
  const [diceRoll, setDiceRoll] = useState(persisted.diceRoll ?? 0);
  const [configOpen, setConfigOpen] = useState(!persisted.sessionId);

  // Data hooks
  const { data: systemVariants } = usePromptVariants("system");
  const { data: turnVariants } = usePromptVariants("turn");
  const { data: arrivalVariants } = usePromptVariants("arrival");
  const { data: windowVariants } = usePromptVariants("window");
  const { data: models } = useModels();
  const { data: config } = useLabConfig();

  // Mutation hooks
  const startMutation = useQuickPlayStart();
  const enterEraMutation = useQuickPlayEnterEra();
  const chooseMutation = useQuickPlayChoose();
  const continueMutation = useQuickPlayContinue();
  const updateParamsMutation = useQuickPlayUpdateParams();

  const isLoading =
    startMutation.isPending ||
    enterEraMutation.isPending ||
    chooseMutation.isPending ||
    continueMutation.isPending;

  // Persist state on every change
  useEffect(() => {
    savePersistedState({
      sessionId,
      messages,
      choices,
      lastSnapshotId,
      waitingFor,
      gameState,
      playerName,
      region,
      systemVariantId,
      turnVariantId,
      arrivalVariantId,
      windowVariantId,
      model,
      temperature,
      diceRoll,
    });
  }, [
    sessionId, messages, choices, lastSnapshotId, waitingFor, gameState,
    playerName, region, systemVariantId, turnVariantId, arrivalVariantId,
    windowVariantId, model, temperature, diceRoll,
  ]);

  const getTurnParams = useCallback((): QuickPlayTurnParams => {
    const params: QuickPlayTurnParams = {};
    if (model) params.model = model;
    if (temperature !== 1.0) params.temperature = temperature;
    if (diceRoll > 0) params.dice_roll = diceRoll;
    return params;
  }, [model, temperature, diceRoll]);

  const processResult = useCallback(
    (result: {
      messages: GameMessage[];
      snapshot_id?: string;
      state?: Record<string, any>;
    }) => {
      const newMessages = result.messages || [];
      setMessages((prev) => [...prev, ...newMessages]);

      if (result.snapshot_id) setLastSnapshotId(result.snapshot_id);
      if (result.state) setGameState(result.state);

      let newChoices: Array<{ id: string; text: string }> = [];
      let newWaiting: string | null = null;

      for (const msg of newMessages) {
        if (msg.type === "choices" && msg.data?.choices) {
          newChoices = msg.data.choices;
        }
        if (msg.type === "waiting_input" && msg.data?.action) {
          newWaiting = msg.data.action;
        }
      }

      setChoices(newChoices);
      setWaitingFor(newWaiting);
    },
    []
  );

  const handleStart = () => {
    startMutation.mutate(
      {
        player_name: playerName,
        region,
        system_prompt_variant_id: systemVariantId || undefined,
        turn_prompt_variant_id: turnVariantId || undefined,
        arrival_prompt_variant_id: arrivalVariantId || undefined,
        window_prompt_variant_id: windowVariantId || undefined,
        model: model || undefined,
        temperature: temperature !== 1.0 ? temperature : undefined,
        dice_roll: diceRoll > 0 ? diceRoll : undefined,
      },
      {
        onSuccess: (data) => {
          setSessionId(data.session_id);
          setMessages([]);
          setChoices([]);
          setWaitingFor("enter_era");
          if (data.state) setGameState(data.state);
          setConfigOpen(false);
        },
      }
    );
  };

  const handleEnterEra = () => {
    if (!sessionId) return;
    enterEraMutation.mutate(
      { sessionId, ...getTurnParams() },
      { onSuccess: (result) => processResult(result) }
    );
  };

  const handleChoice = (choice: string) => {
    if (!sessionId) return;
    chooseMutation.mutate(
      { sessionId, choice, ...getTurnParams() },
      { onSuccess: (result) => processResult(result) }
    );
  };

  const handleContinue = () => {
    if (!sessionId) return;
    continueMutation.mutate(
      { sessionId, ...getTurnParams() },
      { onSuccess: (result) => processResult(result) }
    );
  };

  const handleNewSession = () => {
    if (!confirm("Clear the current session and start a new one?")) return;
    setSessionId(null);
    setMessages([]);
    setChoices([]);
    setLastSnapshotId(null);
    setWaitingFor(null);
    setGameState(null);
    setConfigOpen(true);
    clearPersistedState();
  };

  // Shared prompt variant selector
  const PromptSelect = ({
    label,
    value,
    onChange,
    variants,
  }: {
    label: string;
    value: string;
    onChange: (v: string) => void;
    variants: Array<{ id: string; name: string; is_live: boolean }> | undefined;
  }) => (
    <div>
      <Label className="text-xs">{label}</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="h-8 text-xs">
          <SelectValue placeholder="Baseline" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="default">Baseline (default)</SelectItem>
          {variants?.map((v) => (
            <SelectItem key={v.id} value={v.id}>
              {v.name}
              {v.is_live ? " (LIVE)" : ""}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );

  const configPanel = (
    <div className="space-y-3">
      {/* Row 1: Player name + Region */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label className="text-xs">Player Name</Label>
          <Input
            value={playerName}
            onChange={(e) => setPlayerName(e.target.value)}
            className="h-8 text-xs"
          />
        </div>
        <div>
          <Label className="text-xs">Region</Label>
          <Select value={region} onValueChange={setRegion}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="european">European</SelectItem>
              <SelectItem value="worldwide">Worldwide</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Row 2: Four prompt selectors */}
      <div className="grid grid-cols-4 gap-2">
        <PromptSelect
          label="System Prompt"
          value={systemVariantId}
          onChange={setSystemVariantId}
          variants={systemVariants}
        />
        <PromptSelect
          label="Turn Prompt"
          value={turnVariantId}
          onChange={setTurnVariantId}
          variants={turnVariants}
        />
        <PromptSelect
          label="Arrival Prompt"
          value={arrivalVariantId}
          onChange={setArrivalVariantId}
          variants={arrivalVariants}
        />
        <PromptSelect
          label="Window Prompt"
          value={windowVariantId}
          onChange={setWindowVariantId}
          variants={windowVariants}
        />
      </div>

      {/* Row 3: Model + Temperature + Dice Roll */}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <Label className="text-xs">Model</Label>
          <Select value={model} onValueChange={setModel}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="Default" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="default">
                Default ({config?.default_model?.split("-").slice(1, 3).join(" ") || "Sonnet"})
              </SelectItem>
              {models?.map((m) => (
                <SelectItem key={m.id} value={m.id}>
                  {m.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label className="text-xs">
            Temperature: {temperature.toFixed(1)}
          </Label>
          <Slider
            value={[temperature]}
            onValueChange={([v]) => setTemperature(v)}
            min={0}
            max={1.5}
            step={0.1}
            className="mt-2"
          />
          <div className="flex justify-between text-[10px] text-muted-foreground mt-0.5">
            <span>Focused</span>
            <span>Creative</span>
          </div>
        </div>
        <div>
          <Label className="text-xs">
            Dice Roll: {diceRoll === 0 ? "Random" : getDiceLabel(diceRoll)}
          </Label>
          <Slider
            value={[diceRoll]}
            onValueChange={([v]) => setDiceRoll(v)}
            min={0}
            max={20}
            step={1}
            className="mt-2"
          />
          <div className="flex justify-between text-[10px] text-muted-foreground mt-0.5">
            <span>Random</span>
            <span>1=Bad</span>
            <span>10=Avg</span>
            <span>20=Crit</span>
          </div>
        </div>
      </div>
    </div>
  );

  // Not started yet — show full config + start button
  if (!sessionId) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Play through the game with auto-snapshots at every turn. Configure
          prompts, model, temperature, and dice luck below.
        </p>
        {configPanel}
        <Button onClick={handleStart} disabled={isLoading}>
          <Play className="h-4 w-4 mr-1" /> Start Quick Play
        </Button>
      </div>
    );
  }

  // Game in progress
  return (
    <div className="space-y-3">
      {/* Collapsible config panel */}
      <Collapsible open={configOpen} onOpenChange={setConfigOpen}>
        <CollapsibleTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-between text-xs"
          >
            <span className="flex items-center gap-1">
              <Settings2 className="h-3 w-3" />
              Session Parameters
            </span>
            <ChevronDown
              className={`h-3 w-3 transition-transform ${configOpen ? "rotate-180" : ""}`}
            />
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-2">
          {configPanel}
        </CollapsibleContent>
      </Collapsible>

      {/* Game state header */}
      {gameState && (
        <Card>
          <CardContent className="p-3 flex items-center justify-between">
            <div className="text-sm">
              <span className="font-medium">
                {gameState.era?.name || "Setup"}
              </span>
              {gameState.era && (
                <span className="text-muted-foreground">
                  {" "}
                  &middot; Turn {gameState.total_turns} &middot;{" "}
                  {gameState.era.location}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {diceRoll > 0 && (
                <Badge variant="outline" className="text-[10px]">
                  Dice: {diceRoll}
                </Badge>
              )}
              {model && model !== "default" && (
                <Badge variant="outline" className="text-[10px]">
                  {models?.find((m) => m.id === model)?.label || model}
                </Badge>
              )}
              {lastSnapshotId && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onBranchSnapshot?.(lastSnapshotId!)}
                >
                  <GitBranch className="h-3 w-3 mr-1" /> Branch Here
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={handleNewSession}
                className="border-orange-500/50 text-orange-600"
              >
                <RotateCcw className="h-3 w-3 mr-1" /> New Session
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Message log */}
      <ScrollArea className="h-[400px] border rounded-md p-3">
        <div className="space-y-2">
          {messages.map((msg, i) => (
            <MessageDisplay key={i} message={msg} />
          ))}
          {isLoading && (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm">Generating...</span>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Actions */}
      <div className="space-y-2">
        {waitingFor === "enter_era" || waitingFor === "continue_to_era" ? (
          <Button
            onClick={handleEnterEra}
            disabled={isLoading}
            className="w-full"
          >
            Enter Era
          </Button>
        ) : waitingFor === "continue_to_next_era" ? (
          <Button
            onClick={handleContinue}
            disabled={isLoading}
            className="w-full"
          >
            Continue to Next Era
          </Button>
        ) : null}

        {choices.length > 0 && (
          <div className="space-y-1">
            {choices.map((c) => (
              <Button
                key={c.id}
                variant="outline"
                className="w-full justify-start text-left h-auto py-2"
                disabled={isLoading}
                onClick={() => handleChoice(c.id)}
              >
                <Badge variant="secondary" className="mr-2 shrink-0">
                  {c.id}
                </Badge>
                <span className="text-sm">{c.text}</span>
              </Button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MessageDisplay({ message }: { message: GameMessage }) {
  const { type, data } = message;

  switch (type) {
    case "era_arrival":
      return (
        <div className="border-l-2 border-primary pl-3 py-1">
          <p className="text-sm font-semibold">
            {data.era_name} — {data.year_display}
          </p>
          <p className="text-xs text-muted-foreground">{data.location}</p>
        </div>
      );
    case "narrative":
      return (
        <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap text-sm">
          {data.text}
        </div>
      );
    case "narrative_chunk":
      return (
        <span className="text-sm whitespace-pre-wrap">{data.text}</span>
      );
    case "window_open":
      return (
        <Badge variant="destructive" className="my-1">
          {data.message}
        </Badge>
      );
    case "departure":
      return (
        <div className="border-l-2 border-yellow-500 pl-3 py-1">
          <p className="text-sm font-semibold">{data.title}</p>
          <p className="text-xs">{data.message}</p>
        </div>
      );
    case "device_status":
      return (
        <p className="text-xs text-muted-foreground italic">
          [{data.description}]
        </p>
      );
    case "loading":
      return (
        <p className="text-xs text-muted-foreground italic">
          {data.message}
        </p>
      );
    case "error":
      return (
        <p className="text-sm text-destructive">Error: {data.message}</p>
      );
    default:
      return null;
  }
}
