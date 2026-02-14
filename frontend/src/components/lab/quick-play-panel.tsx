import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Play, Loader2, GitBranch } from "lucide-react";
import {
  useQuickPlayStart,
  useQuickPlayEnterEra,
  useQuickPlayChoose,
  useQuickPlayContinue,
} from "@/hooks/use-lab";

interface GameMessage {
  type: string;
  data: Record<string, any>;
}

interface Props {
  onBranchSnapshot?: (snapshotId: string) => void;
}

export default function QuickPlayPanel({ onBranchSnapshot }: Props) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [playerName, setPlayerName] = useState("Lab Tester");
  const [region, setRegion] = useState("european");
  const [messages, setMessages] = useState<GameMessage[]>([]);
  const [choices, setChoices] = useState<Array<{ id: string; text: string }>>(
    []
  );
  const [lastSnapshotId, setLastSnapshotId] = useState<string | null>(null);
  const [waitingFor, setWaitingFor] = useState<string | null>(null);
  const [gameState, setGameState] = useState<Record<string, any> | null>(null);

  const startMutation = useQuickPlayStart();
  const enterEraMutation = useQuickPlayEnterEra();
  const chooseMutation = useQuickPlayChoose();
  const continueMutation = useQuickPlayContinue();

  const isLoading =
    startMutation.isPending ||
    enterEraMutation.isPending ||
    chooseMutation.isPending ||
    continueMutation.isPending;

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

      // Extract choices and waiting state from messages
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
      { player_name: playerName, region },
      {
        onSuccess: (data) => {
          setSessionId(data.session_id);
          setMessages([]);
          setChoices([]);
          setWaitingFor("enter_era");
          if (data.state) setGameState(data.state);
        },
      }
    );
  };

  const handleEnterEra = () => {
    if (!sessionId) return;
    enterEraMutation.mutate(sessionId, {
      onSuccess: (result) => processResult(result),
    });
  };

  const handleChoice = (choice: string) => {
    if (!sessionId) return;
    chooseMutation.mutate(
      { sessionId, choice },
      { onSuccess: (result) => processResult(result) }
    );
  };

  const handleContinue = () => {
    if (!sessionId) return;
    continueMutation.mutate(sessionId, {
      onSuccess: (result) => processResult(result),
    });
  };

  // Not started yet
  if (!sessionId) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Play through the game with auto-snapshots at every turn. Branch from
          any point to test variations.
        </p>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label>Player Name</Label>
            <Input
              value={playerName}
              onChange={(e) => setPlayerName(e.target.value)}
            />
          </div>
          <div>
            <Label>Region</Label>
            <Select value={region} onValueChange={setRegion}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="european">European</SelectItem>
                <SelectItem value="worldwide">Worldwide</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <Button onClick={handleStart} disabled={isLoading}>
          <Play className="h-4 w-4 mr-1" /> Start Quick Play
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
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
            {lastSnapshotId && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onBranchSnapshot?.(lastSnapshotId!)}
              >
                <GitBranch className="h-3 w-3 mr-1" /> Branch Here
              </Button>
            )}
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
        {waitingFor === "enter_era" ||
        waitingFor === "continue_to_era" ? (
          <Button onClick={handleEnterEra} disabled={isLoading} className="w-full">
            Enter Era
          </Button>
        ) : waitingFor === "continue_to_next_era" ? (
          <Button onClick={handleContinue} disabled={isLoading} className="w-full">
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

  // Only render relevant message types
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
      // Chunks are accumulated in streaming; for REST they appear individually
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
