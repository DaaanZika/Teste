# Campanhas — Organização Financeira e Documental

Sistema de organização financeira e documental para campanhas eleitorais
brasileiras. Assistente de organização, conferência e auditoria — **não é**
o CONTA+JE nem substitui a prestação de contas oficial ao TSE.

- Backend: `backend/` (FastAPI + SQLAlchemy + Alembic) — ver `backend/README.md`.
- Frontend: `frontend/` (React + TypeScript + Vite) — ver `frontend/README.md`.
- Documentação de arquitetura/decisões: `docs/`.

## Rodar com Docker (recomendado)

Requer Docker e Docker Compose.

```bash
cp .env.example .env    # ajuste as senhas antes de usar em produção
docker compose up
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000 (docs em `/docs`)
- PostgreSQL sobe automaticamente (serviço `db`)
- Redis **não** sobe por padrão — só é necessário para a fila assíncrona de
  processamento de documentos:

  ```bash
  docker compose --profile queue up
  ```

Para um ambiente parecido com produção (build estático do frontend via
nginx, backend sem `--reload`, sem bind mount do código-fonte):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Rodar sem Docker

Siga `backend/README.md` e `frontend/README.md` — cada um roda de forma
independente com SQLite local, exatamente como na V1.

## Documentação

- `docs/audit/` — auditorias de arquitetura feitas antes de cada fase de evolução.
- `backend/app/rules/electoral/README.md` — por que a base de regras eleitorais começa vazia (e como o versionamento funciona).
- `backend/app/integrations/future/README.md` — o que ainda é planejado (exportação TSE) vs. o que já é real (Google OAuth, Drive, Gmail — ver `backend/README.md`).
- `backend/BACKUP.md` — backup e restauração (banco + documentos), com a restauração de fato verificada, não assumida.

## Princípios do projeto

- Nenhum dado financeiro é calculado no frontend — o backend é a fonte da verdade.
- Nenhuma regra eleitoral é cadastrada sem fonte oficial confirmada.
- Nenhuma integração externa (Google, nuvem) é obrigatória — o sistema
  continua funcionando 100% local quando elas não estão configuradas.
- Nenhum segredo (senha, chave, token) fica no código-fonte ou é commitado.
