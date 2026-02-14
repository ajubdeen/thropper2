import { useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { FlaskConical, ArrowLeft } from "lucide-react";
import SnapshotLibrary from "@/components/lab/snapshot-library";
import GeneratePanel from "@/components/lab/generate-panel";
import ComparisonView from "@/components/lab/comparison-view";
import PromptLibrary from "@/components/lab/prompt-library";
import GenerationHistory from "@/components/lab/generation-history";
import QuickPlayPanel from "@/components/lab/quick-play-panel";

const ADMIN_EMAIL = "aju.bdeen@gmail.com";

export default function NarrativeLab() {
  const { user, isLoading } = useAuth();
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string | null>(
    null
  );
  const [comparisonGroup, setComparisonGroup] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("snapshots");

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen text-muted-foreground">
        Loading...
      </div>
    );
  }

  if (!user || user.email !== ADMIN_EMAIL) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen gap-4">
        <p className="text-muted-foreground">Access restricted.</p>
        <a href="/">
          <Button variant="outline">
            <ArrowLeft className="h-4 w-4 mr-1" /> Back to game
          </Button>
        </a>
      </div>
    );
  }

  const handleBranchSnapshot = (snapshotId: string) => {
    setSelectedSnapshotId(snapshotId);
    setActiveTab("generate");
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FlaskConical className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-semibold">Narrative Lab</h1>
          </div>
          <a href="/">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-1" /> Game
            </Button>
          </a>
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-7xl mx-auto px-4 py-4">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-6">
            <TabsTrigger value="snapshots">Snapshots</TabsTrigger>
            <TabsTrigger value="generate">Generate</TabsTrigger>
            <TabsTrigger value="compare">Compare</TabsTrigger>
            <TabsTrigger value="prompts">Prompts</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
            <TabsTrigger value="quickplay">Quick Play</TabsTrigger>
          </TabsList>

          <div className="mt-4">
            <TabsContent value="snapshots">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div>
                  <h2 className="text-sm font-semibold mb-3">
                    Snapshot Library
                  </h2>
                  <SnapshotLibrary
                    selectedSnapshotId={selectedSnapshotId}
                    onSelectSnapshot={(id) => {
                      setSelectedSnapshotId(id);
                    }}
                  />
                </div>
                <div>
                  <h2 className="text-sm font-semibold mb-3">
                    Quick Generate
                  </h2>
                  <GeneratePanel
                    snapshotId={selectedSnapshotId}
                    onComparisonCreated={setComparisonGroup}
                  />
                </div>
              </div>
            </TabsContent>

            <TabsContent value="generate">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div>
                  <h2 className="text-sm font-semibold mb-3">Snapshots</h2>
                  <SnapshotLibrary
                    selectedSnapshotId={selectedSnapshotId}
                    onSelectSnapshot={setSelectedSnapshotId}
                  />
                </div>
                <div className="lg:col-span-2">
                  <h2 className="text-sm font-semibold mb-3">
                    Configure & Generate
                  </h2>
                  <GeneratePanel
                    snapshotId={selectedSnapshotId}
                    onComparisonCreated={(group) => {
                      setComparisonGroup(group);
                    }}
                  />
                </div>
              </div>
            </TabsContent>

            <TabsContent value="compare">
              <ComparisonView comparisonGroup={comparisonGroup} />
            </TabsContent>

            <TabsContent value="prompts">
              <PromptLibrary />
            </TabsContent>

            <TabsContent value="history">
              <GenerationHistory />
            </TabsContent>

            <TabsContent value="quickplay">
              <QuickPlayPanel onBranchSnapshot={handleBranchSnapshot} />
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  );
}
