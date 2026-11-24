import { useQueryClient } from "@tanstack/react-query";

import { $api, meQueryOptions } from "@/api/client";

export function useLogin() {
  const queryClient = useQueryClient();
  return $api.useMutation("post", "/api/v1/auth/login", {
    onSuccess: () => queryClient.invalidateQueries({ queryKey: meQueryOptions().queryKey }),
  });
}
