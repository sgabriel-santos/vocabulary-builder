import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { apiError, http } from "@/test/handlers";
import { renderWithQuery } from "@/test/render";
import { server } from "@/test/server";

import { LoginForm } from "./LoginForm";

async function submitLogin(email = "dev@example.com", password = "dev-password-123") {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText("E-mail"), email);
  await user.type(screen.getByLabelText("Senha"), password);
  await user.click(screen.getByRole("button", { name: "Entrar" }));
}

describe("LoginForm", () => {
  it("envia as credenciais e chama onLoggedIn no sucesso", async () => {
    let sentBody: unknown;
    server.use(
      http.post("/api/v1/auth/login", async ({ request, response }) => {
        sentBody = await request.json();
        return response(204).empty();
      }),
    );
    const onLoggedIn = vi.fn();
    renderWithQuery(<LoginForm onLoggedIn={onLoggedIn} />);

    await submitLogin();

    await vi.waitFor(() => {
      expect(onLoggedIn).toHaveBeenCalledOnce();
    });
    expect(sentBody).toEqual({ email: "dev@example.com", password: "dev-password-123" });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("mostra mensagem genérica quando as credenciais são inválidas (401)", async () => {
    server.use(
      http.post("/api/v1/auth/login", ({ response }) =>
        response.untyped(apiError(401, "Invalid email or password")),
      ),
    );
    const onLoggedIn = vi.fn();
    renderWithQuery(<LoginForm onLoggedIn={onLoggedIn} />);

    await submitLogin("dev@example.com", "senha-errada");

    expect(await screen.findByRole("alert")).toHaveTextContent("E-mail ou senha inválidos.");
    expect(onLoggedIn).not.toHaveBeenCalled();
  });

  it("mostra a mensagem de limite de tentativas (429)", async () => {
    server.use(
      http.post("/api/v1/auth/login", ({ response }) =>
        response.untyped(apiError(429, "Too many login attempts")),
      ),
    );
    renderWithQuery(<LoginForm onLoggedIn={vi.fn()} />);

    await submitLogin();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Muitas tentativas. Aguarde um minuto e tente de novo.",
    );
  });
});
