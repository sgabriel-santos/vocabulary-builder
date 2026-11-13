import { $api } from "@/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const LABELS = {
  ok: "ok",
  degraded: "degradada",
  unavailable: "indisponível",
} as const;

export function HealthStatus() {
  const health = $api.useQuery("get", "/api/v1/health");

  let text: string;
  if (health.isPending) text = "Verificando…";
  else if (health.isError) text = "Backend indisponível";
  else text = `API: ${LABELS[health.data.status]} · Banco: ${LABELS[health.data.database]}`;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Status do backend</CardTitle>
      </CardHeader>
      <CardContent>
        <p role="status">{text}</p>
      </CardContent>
    </Card>
  );
}
