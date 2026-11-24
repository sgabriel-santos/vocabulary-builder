import { createRouter } from "@tanstack/react-router";

import { meQueryOptions, setUnauthorizedHandler } from "@/api/client";
import { queryClient } from "@/api/query-client";

import { routeTree } from "./routeTree.gen";

export const router = createRouter({
  routeTree,
  context: { queryClient },
  defaultPreload: "intent",
});

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

// Sessão expirada no meio do uso: esquece o usuário e volta ao login.
setUnauthorizedHandler(() => {
  queryClient.removeQueries({ queryKey: meQueryOptions().queryKey });
  void router.navigate({
    to: "/login",
    search: { redirect: router.state.location.href },
  });
});
