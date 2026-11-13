import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";

import { meQueryOptions } from "@/api/client";
import { AppShell } from "@/components/layout/AppShell";

export const Route = createFileRoute("/_authenticated")({
  beforeLoad: async ({ context, location }) => {
    try {
      // staleTime "static": usa o usuário em cache se houver; só busca na primeira vez.
      await context.queryClient.query({ ...meQueryOptions(), staleTime: "static" });
    } catch {
      // eslint-disable-next-line @typescript-eslint/only-throw-error -- padrão do TanStack Router
      throw redirect({ to: "/login", search: { redirect: location.href } });
    }
  },
  component: AuthenticatedLayout,
});

function AuthenticatedLayout() {
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}
