import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown, ChevronRight, User, Gamepad2, Trophy, BookOpen, Clock } from "lucide-react";

interface UserData {
  id: string;
  email: string | null;
  firstName: string | null;
  lastName: string | null;
  createdAt: string | null;
}

interface GameSave {
  id: string;
  gameId: string;
  playerName: string | null;
  currentEra: string | null;
  phase: string | null;
  state: Record<string, unknown>;
  savedAt: string | null;
  startedAt: string | null;
}

interface GameHistory {
  id: string;
  gameId: string;
  playerName: string | null;
  startedAt: string | null;
  endedAt: string | null;
  eras: unknown[];
  finalScore: Record<string, unknown> | null;
  endingType: string | null;
  blurb: string | null;
}

interface LeaderboardEntry {
  id: string;
  gameId: string | null;
  playerName: string;
  turnsSurvived: number | null;
  erasVisited: number | null;
  belongingScore: number | null;
  legacyScore: number | null;
  freedomScore: number | null;
  totalScore: number | null;
  endingType: string | null;
  finalEra: string | null;
  blurb: string | null;
  endingNarrative: string | null;
  createdAt: string | null;
}

interface AoaEntry {
  id: string;
  entryId: string;
  gameId: string | null;
  playerName: string | null;
  characterName: string | null;
  finalEra: string | null;
  finalEraYear: number | null;
  erasVisited: number | null;
  turnsSurvived: number | null;
  endingType: string | null;
  belongingScore: number | null;
  legacyScore: number | null;
  freedomScore: number | null;
  totalScore: number | null;
  keyNpcs: string[];
  definingMoments: string[];
  wisdomMoments: string[];
  itemsUsed: string[];
  playerNarrative: string | null;
  historianNarrative: string | null;
  createdAt: string | null;
}

interface EraHistory {
  era_name?: string;
  era_year?: number;
  era_location?: string;
  narrative?: string;
}

interface ParsedChoice {
  letter: string;
  text: string;
}

interface ParsedTurn {
  narrative: string;
  choices: ParsedChoice[];
  anchors: string | null;
}

function parseNarrative(fullNarrative: string): ParsedTurn[] {
  const turns: ParsedTurn[] = [];
  
  const anchorSplit = fullNarrative.split(/<anchors>[^<]*<\/anchors>/);
  const anchorMatches = fullNarrative.match(/<anchors>([^<]+)<\/anchors>/g) || [];
  
  for (let i = 0; i < anchorSplit.length; i++) {
    const part = anchorSplit[i];
    if (!part.trim()) continue;
    
    const choices: ParsedChoice[] = [];
    let narrativeText = part;
    
    const choiceBlockMatch = part.match(/\[A\][\s\S]*$/);
    if (choiceBlockMatch) {
      const choiceBlock = choiceBlockMatch[0];
      narrativeText = part.slice(0, part.indexOf('[A]'));
      
      const choicePattern = /\[([A-C])\]\s*([^\[]*?)(?=\n\n\[([A-C])\]|\n\[([A-C])\]|$)/g;
      let match;
      while ((match = choicePattern.exec(choiceBlock)) !== null) {
        choices.push({ letter: match[1], text: match[2].trim() });
      }
    }
    
    const anchors = anchorMatches[i] 
      ? anchorMatches[i].replace(/<\/?anchors>/g, '') 
      : null;
    
    if (narrativeText.trim() || choices.length > 0) {
      turns.push({
        narrative: narrativeText.trim(),
        choices,
        anchors
      });
    }
  }
  
  if (turns.length === 0 && fullNarrative.trim()) {
    turns.push({ narrative: fullNarrative, choices: [], anchors: null });
  }
  
  return turns;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "N/A";
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function UserCard({ user, isSelected, onClick }: { user: UserData; isSelected: boolean; onClick: () => void }) {
  return (
    <div
      onClick={onClick}
      className={`p-3 cursor-pointer border-b border-border transition-colors ${
        isSelected ? "bg-accent" : "hover-elevate"
      }`}
      data-testid={`user-card-${user.id}`}
    >
      <div className="flex items-center gap-2">
        <User className="h-4 w-4 text-muted-foreground" />
        <span className="font-medium text-sm">
          {user.firstName || user.lastName
            ? `${user.firstName || ""} ${user.lastName || ""}`.trim()
            : "Anonymous"}
        </span>
      </div>
      <div className="text-xs text-muted-foreground mt-1">{user.email || "No email"}</div>
      <div className="text-xs text-muted-foreground">ID: {user.id.slice(0, 8)}...</div>
    </div>
  );
}

function GameStateViewer({ state }: { state: Record<string, unknown> }) {
  const [isOpen, setIsOpen] = useState(false);
  const [showNarratives, setShowNarratives] = useState(false);

  const timeMachine = state.time_machine as Record<string, unknown> | undefined;
  const fulfillment = state.fulfillment as Record<string, unknown> | undefined;
  const inventory = state.inventory as Record<string, unknown> | undefined;
  const conversationHistory = state.conversation_history as Array<{ role: string; content: string }> | undefined;
  const currentEra = state.current_era as Record<string, unknown> | undefined;

  const narratives = conversationHistory
    ?.filter(msg => msg.role === "assistant")
    .map(msg => msg.content) || [];

  return (
    <div className="space-y-2">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
          {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          View State Details
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-2 space-y-2">
          {currentEra && (
            <div className="text-xs bg-muted/50 p-2 rounded">
              <div className="font-medium mb-1">Current Era</div>
              <div>{String(currentEra.era_name || "Unknown")} ({String(currentEra.era_year || "?")})</div>
              <div>Character: {String(currentEra.character_name || "Unknown")}</div>
              <div>Turns in era: {String(currentEra.turns_in_era || 0)}</div>
            </div>
          )}
          {timeMachine && (
            <div className="text-xs bg-muted/50 p-2 rounded">
              <div className="font-medium mb-1">Time Machine</div>
              <div>Total Turns: {String(timeMachine.total_turns || 0)}</div>
              <div>Eras Visited: {(timeMachine.eras_visited as string[] || []).length}</div>
            </div>
          )}
          {fulfillment && (
            <div className="text-xs bg-muted/50 p-2 rounded">
              <div className="font-medium mb-1">Fulfillment</div>
              <div>Belonging: {String((fulfillment.belonging as Record<string, unknown>)?.value || 0)}</div>
              <div>Legacy: {String((fulfillment.legacy as Record<string, unknown>)?.value || 0)}</div>
              <div>Freedom: {String((fulfillment.freedom as Record<string, unknown>)?.value || 0)}</div>
            </div>
          )}
          {inventory && (
            <div className="text-xs bg-muted/50 p-2 rounded">
              <div className="font-medium mb-1">Items</div>
              {((inventory.items as Array<{ id?: string; name?: string }>) || []).map((item, i) => (
                <div key={i}>{item.id || item.name || "Unknown item"}</div>
              ))}
            </div>
          )}
        </CollapsibleContent>
      </Collapsible>
      
      {narratives.length > 0 && (
        <Collapsible open={showNarratives} onOpenChange={setShowNarratives}>
          <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
            {showNarratives ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
            View Narratives ({narratives.length} turns)
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-2 space-y-3">
            {narratives.map((narrative, idx) => {
              const parsed = parseNarrative(narrative);
              return (
                <div key={idx} className="space-y-2 border-l-2 border-primary/20 pl-3">
                  <div className="text-xs font-medium text-primary/80">Turn {idx + 1}</div>
                  {parsed.map((turn, turnIdx) => (
                    <div key={turnIdx} className="space-y-1">
                      {turn.narrative && (
                        <div className="text-xs text-muted-foreground whitespace-pre-wrap bg-muted/20 p-2 rounded">
                          {turn.narrative.slice(0, 800)}
                          {turn.narrative.length > 800 && "..."}
                        </div>
                      )}
                      {turn.choices.length > 0 && (
                        <div className="space-y-1 pl-2 bg-accent/30 p-2 rounded">
                          <div className="text-xs font-medium">Choices:</div>
                          {turn.choices.map((choice, cIdx) => (
                            <div key={cIdx} className="text-xs text-muted-foreground">
                              <span className="font-medium text-primary/70">[{choice.letter}]</span> {choice.text.slice(0, 150)}{choice.text.length > 150 && "..."}
                            </div>
                          ))}
                        </div>
                      )}
                      {turn.anchors && (
                        <div className="text-xs text-muted-foreground/70 italic">
                          Anchors: {turn.anchors}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              );
            })}
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  );
}

function EraHistoryViewer({ eras }: { eras: unknown[] }) {
  const [openEras, setOpenEras] = useState<Set<number>>(new Set());

  const toggleEra = (index: number) => {
    const newOpen = new Set(openEras);
    if (newOpen.has(index)) {
      newOpen.delete(index);
    } else {
      newOpen.add(index);
    }
    setOpenEras(newOpen);
  };

  const eraList = eras as EraHistory[];

  return (
    <div className="space-y-2">
      {eraList.map((era, index) => {
        const turns = era.narrative ? parseNarrative(era.narrative) : [];
        
        return (
          <Collapsible key={index} open={openEras.has(index)} onOpenChange={() => toggleEra(index)}>
            <CollapsibleTrigger className="flex items-center gap-2 w-full text-left p-2 bg-muted/30 rounded hover-elevate">
              {openEras.has(index) ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
              <span className="font-medium text-sm">{era.era_name || `Era ${index + 1}`}</span>
              {era.era_year && <Badge variant="secondary" className="text-xs">{era.era_year}</Badge>}
              {era.era_location && <Badge variant="outline" className="text-xs">{era.era_location}</Badge>}
              <Badge variant="outline" className="text-xs">{turns.length} turns</Badge>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2 ml-6 space-y-3">
              {turns.map((turn, turnIdx) => (
                <div key={turnIdx} className="space-y-2 border-l-2 border-primary/20 pl-3">
                  <div className="text-xs font-medium text-primary/80">Turn {turnIdx + 1}</div>
                  {turn.narrative && (
                    <div className="text-xs text-muted-foreground whitespace-pre-wrap bg-muted/20 p-2 rounded">
                      {turn.narrative.slice(0, 1000)}
                      {turn.narrative.length > 1000 && "..."}
                    </div>
                  )}
                  {turn.choices.length > 0 && (
                    <div className="space-y-1 pl-2 bg-accent/30 p-2 rounded">
                      <div className="text-xs font-medium">Choices Offered:</div>
                      {turn.choices.map((choice, cIdx) => (
                        <div key={cIdx} className="text-xs text-muted-foreground">
                          <span className="font-medium text-primary/70">[{choice.letter}]</span> {choice.text.slice(0, 200)}{choice.text.length > 200 && "..."}
                        </div>
                      ))}
                    </div>
                  )}
                  {turn.anchors && (
                    <div className="text-xs text-muted-foreground/70 italic bg-muted/10 p-1 rounded">
                      Anchor changes: {turn.anchors}
                    </div>
                  )}
                </div>
              ))}
              {!era.narrative && (
                <div className="text-xs text-muted-foreground italic">No narrative recorded</div>
              )}
            </CollapsibleContent>
          </Collapsible>
        );
      })}
    </div>
  );
}

function UserDetails({ userId }: { userId: string }) {
  const { data: saves, isLoading: savesLoading } = useQuery<GameSave[]>({
    queryKey: ["/api/nexus/user", userId, "saves"],
    queryFn: () => fetch(`/api/nexus/user/${userId}/saves`).then(r => r.json()),
  });

  const { data: histories, isLoading: historiesLoading } = useQuery<GameHistory[]>({
    queryKey: ["/api/nexus/user", userId, "histories"],
    queryFn: () => fetch(`/api/nexus/user/${userId}/histories`).then(r => r.json()),
  });

  const { data: leaderboard, isLoading: leaderboardLoading } = useQuery<LeaderboardEntry[]>({
    queryKey: ["/api/nexus/user", userId, "leaderboard"],
    queryFn: () => fetch(`/api/nexus/user/${userId}/leaderboard`).then(r => r.json()),
  });

  const { data: aoa, isLoading: aoaLoading } = useQuery<AoaEntry[]>({
    queryKey: ["/api/nexus/user", userId, "aoa"],
    queryFn: () => fetch(`/api/nexus/user/${userId}/aoa`).then(r => r.json()),
  });

  const isLoading = savesLoading || historiesLoading || leaderboardLoading || aoaLoading;

  if (isLoading) {
    return <div className="p-4 text-muted-foreground">Loading user data...</div>;
  }

  return (
    <div className="space-y-4 p-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Gamepad2 className="h-4 w-4" />
            Active Saves ({saves?.length || 0})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {saves && saves.length > 0 ? (
            saves.map(save => (
              <div key={save.id} className="border rounded p-3 space-y-2">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <span className="font-medium text-sm">{save.playerName || "Unnamed"}</span>
                  <Badge variant="outline" className="text-xs">{save.phase || "unknown"}</Badge>
                </div>
                <div className="text-xs text-muted-foreground">Era: {save.currentEra || "None"}</div>
                <div className="text-xs text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Saved: {formatDate(save.savedAt)}
                </div>
                <GameStateViewer state={save.state} />
              </div>
            ))
          ) : (
            <div className="text-sm text-muted-foreground">No active saves</div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <BookOpen className="h-4 w-4" />
            Game Histories ({histories?.length || 0})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {histories && histories.length > 0 ? (
            histories.map(history => (
              <Collapsible key={history.id}>
                <CollapsibleTrigger className="w-full text-left border rounded p-3 hover-elevate">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <span className="font-medium text-sm">{history.playerName || "Unnamed"}</span>
                    {history.endingType && (
                      <Badge variant="secondary" className="text-xs">{history.endingType}</Badge>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {formatDate(history.startedAt)} - {formatDate(history.endedAt)}
                  </div>
                  {history.blurb && (
                    <div className="text-xs text-muted-foreground mt-1 italic">
                      {history.blurb.slice(0, 100)}...
                    </div>
                  )}
                </CollapsibleTrigger>
                <CollapsibleContent className="mt-2 ml-2">
                  {history.eras && Array.isArray(history.eras) && history.eras.length > 0 && (
                    <EraHistoryViewer eras={history.eras} />
                  )}
                  {history.finalScore && (
                    <div className="mt-2 text-xs bg-muted/30 p-2 rounded">
                      <div className="font-medium">Final Score</div>
                      <pre className="text-xs overflow-auto">
                        {JSON.stringify(history.finalScore, null, 2)}
                      </pre>
                    </div>
                  )}
                </CollapsibleContent>
              </Collapsible>
            ))
          ) : (
            <div className="text-sm text-muted-foreground">No game histories</div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Trophy className="h-4 w-4" />
            Leaderboard Entries ({leaderboard?.length || 0})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {leaderboard && leaderboard.length > 0 ? (
            leaderboard.map(entry => (
              <div key={entry.id} className="border rounded p-3 space-y-2">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <span className="font-medium text-sm">{entry.playerName}</span>
                  <Badge className="text-xs">{entry.totalScore || 0} pts</Badge>
                </div>
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div>Belonging: {entry.belongingScore || 0}</div>
                  <div>Legacy: {entry.legacyScore || 0}</div>
                  <div>Freedom: {entry.freedomScore || 0}</div>
                </div>
                <div className="text-xs text-muted-foreground">
                  {entry.erasVisited || 0} eras, {entry.turnsSurvived || 0} turns
                </div>
                {entry.finalEra && (
                  <div className="text-xs text-muted-foreground">Final Era: {entry.finalEra}</div>
                )}
                {entry.endingNarrative && (
                  <div className="text-xs text-muted-foreground mt-1 italic border-l-2 border-primary/30 pl-2">
                    {entry.endingNarrative.slice(0, 200)}...
                  </div>
                )}
              </div>
            ))
          ) : (
            <div className="text-sm text-muted-foreground">No leaderboard entries</div>
          )}
        </CardContent>
      </Card>

      {aoa && aoa.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Annals of Anachron ({aoa.length})</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {aoa.map(entry => (
              <Collapsible key={entry.id}>
                <CollapsibleTrigger className="w-full text-left border rounded p-3 hover-elevate">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <span className="font-medium text-sm">{entry.characterName || entry.playerName || "Unnamed"}</span>
                    <Badge className="text-xs">{entry.totalScore || 0} pts</Badge>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {entry.finalEra} ({entry.finalEraYear})
                  </div>
                </CollapsibleTrigger>
                <CollapsibleContent className="mt-2 p-3 bg-muted/20 rounded space-y-2">
                  {entry.keyNpcs && entry.keyNpcs.length > 0 && (
                    <div className="text-xs">
                      <span className="font-medium">Key NPCs: </span>
                      {entry.keyNpcs.join(", ")}
                    </div>
                  )}
                  {entry.definingMoments && entry.definingMoments.length > 0 && (
                    <div className="text-xs">
                      <span className="font-medium">Defining Moments: </span>
                      {entry.definingMoments.join("; ")}
                    </div>
                  )}
                  {entry.playerNarrative && (
                    <div className="text-xs italic border-l-2 border-primary/30 pl-2">
                      {entry.playerNarrative}
                    </div>
                  )}
                </CollapsibleContent>
              </Collapsible>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default function ChronicleNexus() {
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);

  const { data: users, isLoading } = useQuery<UserData[]>({
    queryKey: ["/api/nexus/users"],
    queryFn: () => fetch("/api/nexus/users").then(r => r.json()),
  });

  return (
    <div className="flex h-screen bg-background" data-testid="chronicle-nexus-page">
      <div className="w-64 border-r border-border flex flex-col">
        <div className="p-3 border-b border-border">
          <h1 className="text-sm font-bold text-muted-foreground">Chronicle Nexus</h1>
          <div className="text-xs text-muted-foreground">{users?.length || 0} players</div>
        </div>
        <ScrollArea className="flex-1">
          {isLoading ? (
            <div className="p-4 text-muted-foreground text-sm">Loading...</div>
          ) : (
            users?.map(user => (
              <UserCard
                key={user.id}
                user={user}
                isSelected={selectedUserId === user.id}
                onClick={() => setSelectedUserId(user.id)}
              />
            ))
          )}
        </ScrollArea>
      </div>

      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          {selectedUserId ? (
            <UserDetails userId={selectedUserId} />
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              Select a player to view their games
            </div>
          )}
        </ScrollArea>
      </div>
    </div>
  );
}
