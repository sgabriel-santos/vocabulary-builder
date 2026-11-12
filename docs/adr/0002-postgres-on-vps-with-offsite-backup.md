# 0002 — Postgres em container no VPS com backup externo

- **Status:** Aceita
- **Data:** 2026-11-12

## Contexto

O delivery plan previa "banco gerenciado" na E0. Com a hospedagem em VPS (ADR 0001), as opções eram Postgres gerenciado externo (ex.: Neon) ou Postgres no próprio VPS. O banco gerenciado adiciona latência por query (rede até outro provedor/região) e acorda do modo ocioso; o Postgres local tem latência praticamente zero, mas o backup passa a ser responsabilidade do projeto.

## Decisão

- **`postgres:18-alpine`** (minor fixada) em container no VPS, com volume nomeado montado em `/var/lib/postgresql` (layout do Postgres 18+). Mesma versão no dev e nos testes.
- **Backup diário** por `deploy/backup.sh` (systemd timer no host): `pg_dump -Fc` → criptografia com `age` → upload com `rclone` para Backblaze B2 ou Cloudflare R2, com retenção (14 diários + 6 mensais) e ping de monitoramento (Healthchecks.io).
- Procedimento de restore documentado e testado.
- **Quando:** o backup é implementado na **E1**, antes da importação da lista real de termos. Na E0 o banco contém apenas o usuário criado pela CLI, recriável em segundos, então o backup ali seria trabalho sem nada a proteger.

## Consequências

- Latência mínima entre API e banco; sem custo adicional.
- Risco de perda de até 24 h de dados em caso de falha do disco, aceitável para uso pessoal.
- A chave privada do `age` deve ficar fora do VPS.
- O texto "banco gerenciado" do delivery plan foi atualizado.
