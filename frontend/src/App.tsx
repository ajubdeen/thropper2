import { Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/not-found";
import TerminalPage from "@/pages/terminal";
import ChronicleNexus from "@/pages/chronicle-nexus";

function Router() {
  return (
    <Switch>
      <Route path="/" component={TerminalPage} />
      <Route path="/chronicle/nexus" component={ChronicleNexus} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Router />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
