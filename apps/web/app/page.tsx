import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { StateCard } from "@/components/ui/StateCard";

export default function Home() {
  return (
    <div className="space-y-6">
      <section>
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-semibold text-white">
            Scientific Dashboard
          </h2>

          <Badge variant="success">MVP</Badge>
        </div>

        <p className="mt-2 text-sm text-zinc-400">
          Flame in Freefall research and analysis platform.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <MetricCard
          label="Documents"
          value="—"
          description="Scientific documents indexed"
        />

        <MetricCard
          label="Experiments"
          value="—"
          description="Available experiments"
        />

        <MetricCard
          label="Analyses"
          value="—"
          description="Completed flame analyses"
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="text-sm font-medium text-white">
            Research Workflow
          </h3>

          <p className="mt-2 text-sm text-zinc-400">
            Search scientific knowledge, inspect evidence, analyze flame
            imagery, and trace results back to their sources.
          </p>
        </Card>

        <StateCard
          title="Frontend Status"
          message="Next.js application shell is running successfully."
          status="success"
        />
      </section>
    </div>
  );
}
