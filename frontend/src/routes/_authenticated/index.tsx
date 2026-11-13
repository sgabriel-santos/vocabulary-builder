import { createFileRoute } from "@tanstack/react-router";

import { HealthStatus } from "@/features/health/HealthStatus";

export const Route = createFileRoute("/_authenticated/")({
  component: HomePage,
});

function HomePage() {
  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold">Início</h1>
      <HealthStatus />
    </section>
  );
}
