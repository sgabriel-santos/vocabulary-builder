import createFetchClient, { type Middleware } from "openapi-fetch";
import createClient from "openapi-react-query";

import type { paths } from "./schema";

/** Erro de qualquer resposta não-2xx da API, com o status HTTP preservado. */
export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(status: number, body: unknown) {
    super(`API respondeu ${String(status)}`);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

// Nessas rotas o 401 é uma resposta esperada, tratada pela tela que as chama.
const AUTH_PATHS_WITHOUT_REDIRECT = ["/api/v1/auth/me", "/api/v1/auth/login"];

let onUnauthorized: (() => void) | undefined;

/** Registrado pelo router: o que fazer quando a sessão expira no meio do uso. */
export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler;
}

const errorMiddleware: Middleware = {
  async onResponse({ response, schemaPath }) {
    if (response.ok) return undefined;
    if (response.status === 401 && !AUTH_PATHS_WITHOUT_REDIRECT.includes(schemaPath)) {
      onUnauthorized?.();
    }
    const body: unknown = await response
      .clone()
      .json()
      .catch(() => undefined);
    throw new ApiError(response.status, body);
  },
};

export const fetchClient = createFetchClient<paths>({
  baseUrl: window.location.origin, // mesma origem; absoluto para funcionar também no jsdom
  credentials: "same-origin",
  // Resolve o fetch a cada chamada (e não na importação), para que o MSW,
  // instalado depois nos testes, consiga interceptar as requisições.
  fetch: (request) => globalThis.fetch(request),
});
fetchClient.use(errorMiddleware);

export const $api = createClient(fetchClient);

export const meQueryOptions = () => $api.queryOptions("get", "/api/v1/auth/me");
