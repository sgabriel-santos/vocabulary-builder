import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { meQueryOptions } from "@/api/client";
import { Button } from "@/components/ui/button";
import { useLogout } from "@/features/auth/useLogout";

export function AppShell({ children }: { children: ReactNode }) {
  const me = useQuery(meQueryOptions());
  const logout = useLogout();

  return (
    <div className="min-h-dvh">
      <header className="flex items-center justify-between gap-2 border-b px-4 py-3">
        <span className="font-semibold">Vocabulary Builder</span>
        <div className="flex min-w-0 items-center gap-2">
          <span className="text-muted-foreground truncate text-sm">{me.data?.email}</span>
          <Button
            variant="outline"
            size="sm"
            disabled={logout.isPending}
            onClick={() => {
              logout.mutate({});
            }}
          >
            Sair
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-2xl p-4">{children}</main>
    </div>
  );
}
