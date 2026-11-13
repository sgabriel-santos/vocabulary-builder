import { HttpResponse } from "msw";
import { createOpenApiHttp } from "openapi-msw";

import type { paths } from "@/api/schema";

export const http = createOpenApiHttp<paths>({ baseUrl: "http://localhost:5173" });

/** Erro no formato padrão do FastAPI (o corpo de 401/429 não está no OpenAPI). */
export function apiError(status: number, detail: string) {
  return HttpResponse.json({ detail }, { status });
}

/** Estado padrão: API saudável e usuário não autenticado. Cada teste sobrescreve o que precisar. */
export const handlers = [
  http.get("/api/v1/health", ({ response }) =>
    response(200).json({ status: "ok", database: "ok" }),
  ),
  http.get("/api/v1/auth/me", ({ response }) =>
    response.untyped(apiError(401, "Not authenticated")),
  ),
];
