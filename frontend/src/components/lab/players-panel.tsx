import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ArrowLeft, User, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Player {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  profile_image_url: string | null;
  created_at: string;
  save_count: number;
  completed_count: number;
}

interface Save {
  game_id: string;
  player_name: string | null;
  current_era: string | null;
  phase: string | null;
  saved_at: string;
}

interface CompletedGame {
  id: string;
  game_id: string;
  player_name: string | null;
  total: number;
  final_era: string | null;
  ending_type: string | null;
  belonging_score: number;
  legacy_score: number;
  freedom_score: number;
  total_turns: number;
  created_at: string;
  portrait_image_path: string | null;
  blurb: string | null;
}

interface PlayerGames {
  user: Player;
  saves: Save[];
  completed: CompletedGame[];
}

interface Era {
  era_name: string;
  era_year?: number;
  era_location?: string;
  narrative: string;
}

interface GameHistory {
  game_id: string;
  player_name: string | null;
  started_at: string | null;
  ended_at: string | null;
  ending_type: string | null;
  blurb: string | null;
  final_score: any;
  eras: Era[];
}

type View =
  | { type: "players" }
  | { type: "player"; id: string }
  | { type: "game"; game_id: string; playerId: string };

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric", month: "short", day: "numeric",
  });
}

export default function PlayersPanel() {
  const [view, setView] = useState<View>({ type: "players" });

  if (view.type === "game") {
    return (
      <GameDetail
        gameId={view.game_id}
        onBack={() => setView({ type: "player", id: view.playerId })}
      />
    );
  }

  if (view.type === "player") {
    return (
      <PlayerDetail
        playerId={view.id}
        onBack={() => setView({ type: "players" })}
        onOpenGame={(gameId) => setView({ type: "game", game_id: gameId, playerId: view.id })}
      />
    );
  }

  return <PlayerList onSelect={(id) => setView({ type: "player", id })} />;
}

// ── Player list ──────────────────────────────────────────────────────────────

function PlayerList({ onSelect }: { onSelect: (id: string) => void }) {
  const { data: players = [], isLoading } = useQuery<Player[]>({
    queryKey: ["/api/lab/players"],
    queryFn: () => fetch("/api/lab/players").then(r => r.json()),
  });

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        {isLoading ? "Loading..." : `${players.length} registered player${players.length !== 1 ? "s" : ""}`}
      </p>
      <div className="grid gap-2">
        {players.map(p => (
          <Card
            key={p.id}
            className="cursor-pointer hover:border-primary/50 transition-colors"
            onClick={() => onSelect(p.id)}
          >
            <CardContent className="p-4 flex items-center gap-4">
              {p.profile_image_url ? (
                <img src={p.profile_image_url} className="w-9 h-9 rounded-full object-cover" alt="" />
              ) : (
                <div className="w-9 h-9 rounded-full bg-muted flex items-center justify-center">
                  <User className="w-4 h-4 text-muted-foreground" />
                </div>
              )}
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm truncate">
                  {p.first_name || p.last_name
                    ? `${p.first_name ?? ""} ${p.last_name ?? ""}`.trim()
                    : "Anonymous"}
                </div>
                <div className="text-xs text-muted-foreground truncate">{p.email}</div>
              </div>
              <div className="flex gap-2 shrink-0">
                <Badge variant="secondary">{p.completed_count} finished</Badge>
                <Badge variant="outline">{p.save_count} saved</Badge>
              </div>
              <div className="text-xs text-muted-foreground shrink-0">{formatDate(p.created_at)}</div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ── Player detail ─────────────────────────────────────────────────────────────

function PlayerDetail({
  playerId, onBack, onOpenGame,
}: { playerId: string; onBack: () => void; onOpenGame: (gameId: string) => void }) {
  const { data, isLoading } = useQuery<PlayerGames>({
    queryKey: ["/api/lab/players", playerId, "games"],
    queryFn: () => fetch(`/api/lab/players/${playerId}/games`).then(r => r.json()),
  });

  if (isLoading || !data) return <p className="text-sm text-muted-foreground py-4">Loading...</p>;

  const { user, saves, completed } = data;
  const name = user.first_name || user.last_name
    ? `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim()
    : "Anonymous";

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft className="w-4 h-4 mr-1" /> Players
        </Button>
        <div className="flex items-center gap-2">
          {user.profile_image_url && (
            <img src={user.profile_image_url} className="w-7 h-7 rounded-full object-cover" alt="" />
          )}
          <span className="font-semibold">{name}</span>
          <span className="text-sm text-muted-foreground">{user.email}</span>
        </div>
      </div>

      {/* Completed games */}
      <div>
        <h3 className="text-sm font-semibold mb-2">Completed runs ({completed.length})</h3>
        {completed.length === 0 ? (
          <p className="text-sm text-muted-foreground">None yet.</p>
        ) : (
          <div className="space-y-2">
            {completed.map(g => (
              <Card
                key={g.id}
                className="cursor-pointer hover:border-primary/50 transition-colors"
                onClick={() => onOpenGame(g.game_id)}
              >
                <CardContent className="p-0 flex overflow-hidden rounded-lg">
                  {g.portrait_image_path && (
                    <img
                      src={g.portrait_image_path}
                      className="w-24 h-20 object-cover object-[center_20%] shrink-0"
                      alt=""
                    />
                  )}
                  <div className="p-3 flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium text-sm truncate">{g.player_name || "Unnamed"}</span>
                      <span className="text-amber-500 font-bold text-sm shrink-0">{g.total} pts</span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      {g.final_era} · <span className="capitalize">{g.ending_type}</span> · {g.total_turns} turns
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">
                      B:{g.belonging_score} L:{g.legacy_score} F:{g.freedom_score}
                    </div>
                    {g.blurb && <div className="text-xs text-muted-foreground italic mt-1 truncate">{g.blurb}</div>}
                    <div className="text-xs text-muted-foreground mt-1">{formatDate(g.created_at)}</div>
                  </div>
                  <div className="flex items-center pr-3">
                    <ChevronRight className="w-4 h-4 text-muted-foreground" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Saved games */}
      <div>
        <h3 className="text-sm font-semibold mb-2">Saved games ({saves.length})</h3>
        {saves.length === 0 ? (
          <p className="text-sm text-muted-foreground">None.</p>
        ) : (
          <div className="space-y-2">
            {saves.map(s => (
              <Card key={s.game_id}>
                <CardContent className="p-3 flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium">{s.player_name || "Unnamed"}</div>
                    <div className="text-xs text-muted-foreground">
                      {s.current_era || "—"} · <span className="capitalize">{s.phase || "unknown"}</span>
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground shrink-0">{formatDate(s.saved_at)}</div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Game detail ───────────────────────────────────────────────────────────────

function GameDetail({ gameId, onBack }: { gameId: string; onBack: () => void }) {
  const [openEra, setOpenEra] = useState<number | null>(null);

  const { data, isLoading } = useQuery<GameHistory>({
    queryKey: ["/api/history", gameId],
    queryFn: () => fetch(`/api/history/${gameId}`).then(r => r.json()),
  });

  if (isLoading || !data) return <p className="text-sm text-muted-foreground py-4">Loading...</p>;

  const eras: Era[] = Array.isArray(data.eras) ? data.eras : [];

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft className="w-4 h-4 mr-1" /> Back
        </Button>
        <div>
          <span className="font-semibold">{data.player_name || "Unnamed"}</span>
          <span className="text-sm text-muted-foreground ml-2 capitalize">{data.ending_type} ending</span>
        </div>
      </div>

      {data.blurb && (
        <p className="text-sm text-muted-foreground italic border-l-2 border-amber-500/40 pl-3">{data.blurb}</p>
      )}

      <div className="text-xs text-muted-foreground">
        {formatDate(data.started_at)} → {formatDate(data.ended_at)} · {eras.length} era{eras.length !== 1 ? "s" : ""}
      </div>

      <ScrollArea className="h-[calc(100vh-280px)]">
        <div className="space-y-2 pr-2">
          {eras.map((era, i) => (
            <Card key={i}>
              <CardContent className="p-0">
                <button
                  className="w-full p-3 flex items-center justify-between gap-3 text-left hover:bg-muted/40 transition-colors rounded-lg"
                  onClick={() => setOpenEra(openEra === i ? null : i)}
                >
                  <div>
                    <span className="font-medium text-sm">{era.era_name}</span>
                    {era.era_year && (
                      <span className="text-xs text-muted-foreground ml-2">{era.era_year}</span>
                    )}
                    {era.era_location && (
                      <span className="text-xs text-muted-foreground ml-1">· {era.era_location}</span>
                    )}
                  </div>
                  <ChevronRight
                    className={`w-4 h-4 text-muted-foreground shrink-0 transition-transform ${openEra === i ? "rotate-90" : ""}`}
                  />
                </button>
                {openEra === i && era.narrative && (
                  <div className="px-3 pb-3">
                    <div className="text-sm text-muted-foreground leading-relaxed whitespace-pre-wrap border-t border-border pt-3">
                      {era.narrative}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
