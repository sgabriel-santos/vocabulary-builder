import { screen } from "@testing-library/react";

import { http } from "@/test/handlers";
import { renderWithQuery } from "@/test/render";
import { server } from "@/test/server";

import { HealthStatus } from "./HealthStatus";

describe("HealthStatus", () => {
  it("mostra API e banco ok quando o backend está saudável", async () => {
    renderWithQuery(<HealthStatus />);

    expect(screen.getByRole("status")).toHaveTextContent("Verificando…");
    expect(await screen.findByText("API: ok · Banco: ok")).toBeInTheDocument();
  });

  it("mostra backend indisponível quando a API responde 503", async () => {
    server.use(
      http.get("/api/v1/health", ({ response }) =>
        response(503).json({ status: "degraded", database: "unavailable" }),
      ),
    );
    renderWithQuery(<HealthStatus />);

    expect(await screen.findByText("Backend indisponível")).toBeInTheDocument();
  });
});
