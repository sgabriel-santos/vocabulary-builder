import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";

import { $api } from "@/api/client";

export function useLogout() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  return $api.useMutation("post", "/api/v1/auth/logout", {
    // Mesmo se a chamada falhar, o estado local do usuário é descartado.
    onSettled: () => {
      queryClient.clear();
      void navigate({ to: "/login" });
    },
  });
}
