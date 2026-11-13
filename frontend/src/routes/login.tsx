import { createFileRoute, redirect } from "@tanstack/react-router";

import { meQueryOptions } from "@/api/client";
import { LoginForm } from "@/features/auth/LoginForm";
import { isSafeRedirect } from "@/features/auth/safe-redirect";

interface LoginSearch {
  redirect?: string;
}

export const Route = createFileRoute("/login")({
  validateSearch: (search: Record<string, unknown>): LoginSearch => {
    const target = search.redirect;
    return typeof target === "string" && isSafeRedirect(target) ? { redirect: target } : {};
  },
  beforeLoad: ({ context, search }) => {
    // Já autenticado: não mostra o login de novo.
    if (context.queryClient.getQueryData(meQueryOptions().queryKey)) {
      // eslint-disable-next-line @typescript-eslint/only-throw-error -- padrão do TanStack Router
      throw redirect({ href: search.redirect ?? "/" });
    }
  },
  component: LoginPage,
});

function LoginPage() {
  const { redirect: target } = Route.useSearch();
  const navigate = Route.useNavigate();

  return (
    <main className="flex min-h-dvh items-center justify-center p-4">
      <LoginForm onLoggedIn={() => void navigate({ href: target ?? "/" })} />
    </main>
  );
}
