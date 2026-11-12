# 0003 — Autenticação por senha com sessão server-side

- **Status:** Aceita
- **Data:** 2026-11-12
- **Resolve:** questão em aberto q2 (overview §15)

## Contexto

Single-user, mas com `user_id` no modelo para não bloquear multiusuário. Frontend e API na mesma origem (ADR 0001). A PWA instalada no iOS roda em contexto separado do Safari: fluxos que saem do app (magic link, redirect OAuth) autenticam o navegador e não a PWA. Foram comparados magic link, OAuth, proteção no edge, JWT em `localStorage`, JWT em cookie e sessão server-side.

## Decisão

- **E-mail + senha** com hash **Argon2id**; usuários criados apenas por CLI (`create-user`), sem cadastro público; rate limit no login.
- **Sessão server-side**: token opaco aleatório em cookie `HttpOnly; Secure; SameSite=Lax; Path=/`; tabela `sessions` guarda apenas o hash (SHA-256) do token; expiração deslizante de ~60 dias; logout apaga a sessão.
- **CSRF**: `SameSite=Lax` + mesma origem + checagem do header `Origin` em métodos que alteram estado.
- Sem JWT e sem refresh token.

## Consequências

- Imune a roubo de token por XSS (nada em `localStorage`); revogação imediata e trivial.
- Frontend simples: sem guarda de token nem lógica de refresh.
- Uma consulta indexada ao banco por request (irrelevante nesta escala).
- Recuperação de senha via CLI; TOTP fica como evolução futura.
- Um cliente nativo futuro pode usar o mesmo token opaco como `Authorization: Bearer`.
