import { QueryClient } from "@tanstack/react-query";

import { isUnauthorized } from "./client";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 401 não melhora com nova tentativa; o resto tenta mais duas vezes.
      retry: (failureCount, error) => failureCount < 2 && !isUnauthorized(error),
      staleTime: 30_000,
    },
  },
});
