import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { FlaskConical, ArrowLeft } from "lucide-react";
import SnapshotLibrary from "@/components/lab/snapshot-library";
import GeneratePanel from "@/components/lab/generate-panel";
import ComparisonView from "@/components/lab/comparison-view";
import PromptLibrary from "@/components/lab/prompt-library";
import GenerationHistory from "@/components/lab/generation-history";
import QuickPlayPanel from "@/components/lab/quick-play-panel";
import QuickPlayHistory from "@/components/lab/quickplay-history";
import { ImageLab } from "@/components/lab/image-lab";


export default function NarrativeLab() {
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string | null>(
    null
  );
  const [comparisonGroup, setComparisonGroup] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("snapshots");
  const [historySubTab, setHistorySubTab] = useState<"quickplay" | "generations">("quickplay");

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
          <TabsList className="grid w-full grid-cols-7">
            <TabsTrigger value="snapshots">Snapshots</TabsTrigger>
            <TabsTrigger value="generate">Generate</TabsTrigger>
            <TabsTrigger value="compare">Compare</TabsTrigger>
            <TabsTrigger value="prompts">Prompts</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
            <TabsTrigger value="quickplay">Quick Play</TabsTrigger>
            <TabsTrigger value="image-lab">Image Lab</TabsTrigger>
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
              <div className="space-y-3">
                <div className="flex gap-2">
                  <Button
                    variant={historySubTab === "quickplay" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setHistorySubTab("quickplay")}
                  >
                    Quick Play
                  </Button>
                  <Button
                    variant={historySubTab === "generations" ? "default" : "outline"}
                    size="sm"
                    onClick={() => setHistorySubTab("generations")}
                  >
                    Generations
                  </Button>
                </div>
                {historySubTab === "quickplay" ? (
                  <QuickPlayHistory onBranchSnapshot={handleBranchSnapshot} />
                ) : (
                  <GenerationHistory />
                )}
              </div>
            </TabsContent>

            <TabsContent value="quickplay">
              <QuickPlayPanel onBranchSnapshot={handleBranchSnapshot} />
            </TabsContent>

            <TabsContent value="image-lab">
              <ImageLab />
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  );
}
