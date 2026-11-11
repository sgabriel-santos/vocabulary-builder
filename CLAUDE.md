# CLAUDE.md

Instruções para agentes de IA que trabalham neste repositório.

## Contexto do projeto

- Visão, escopo, modelo de domínio e roadmap: [`docs/project-overview.md`](docs/project-overview.md)
- Plano de entregas: [`docs/delivery-plan.md`](docs/delivery-plan.md)

## Commits

### Fluxo de aprovação

1. Antes de qualquer commit, apresente ao usuário:
   - os arquivos que serão incluídos (`git add ...`);
   - a mensagem completa do commit (título e corpo).
2. **Aguarde a aprovação explícita do usuário.** Não faça commit sem ela.
3. Só depois da aprovação, execute o commit exatamente como foi aprovado. Se o usuário pedir ajustes, apresente a nova versão e aguarde outra aprovação.

Uma aprovação vale apenas para o commit apresentado. Não vale para commits seguintes.

### Formato da mensagem

- **Idioma:** inglês.
- **Padrão:** [Conventional Commits](https://www.conventionalcommits.org/): `<type>(<scope opcional>): <descrição>`.
  - Tipos usuais: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `style`, `perf`, `build`, `ci`.
- **Título:** no imperativo, em minúsculas após o tipo, sem ponto final, com até ~72 caracteres.
- **Corpo (opcional):** uma linha em branco depois do título, seguida de tópicos (`- ...`) explicando o que mudou e por quê.
- Referencie funcionalidades pelos códigos `F-xx` quando aplicável (ex.: `feat(review): add FSRS scheduling (F-05)`).

### Sem atribuição de autoria da IA

A mensagem de commit deve ser **limpa**. Não inclua:

- linhas `Co-Authored-By:` referentes a agentes de IA;
- rodapés como "Generated with ..." ou menções à ferramenta de IA.

Exemplo de mensagem esperada:

```
chore: initial project setup with docs and Claude Code skills

- Add project overview (vision, scope, domain model, roadmap)
- Add delivery plan for Phase 0 and Phase 1 (MVP)
- Add Claude Code skills for the scaffolding and feature pipelines
```
