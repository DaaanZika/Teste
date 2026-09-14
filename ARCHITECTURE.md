# Arquitetura

Visão geral do sistema depois das FASES A–L. Para o "porquê" de cada
decisão específica, ver `docs/audit/` (uma auditoria por fase) — este
documento é o mapa atual, não o histórico de como se chegou aqui.

## Visão geral

```
┌─────────────┐      HTTP/JSON       ┌──────────────┐      SQL       ┌────────────┐
│  Frontend    │ ───────────────────▶│   Backend     │ ──────────────▶│  Banco      │
│  React + TS  │◀─────────────────── │   FastAPI     │◀────────────── │  Postgres/  │
│  (Vite)      │   cookie de sessão  │               │                │  SQLite     │
└─────────────┘                      └──────┬────────┘                └────────────┘
                                             │
                     ┌───────────────────────┼───────────────────────┐
                     ▼                       ▼                       ▼
              storage/ (disco          Google (OAuth/          Redis (fila,
              local, padrão) ou        Drive/Gmail) —          opcional —
              Google Drive              todos opcionais         QUEUE_BACKEND=redis)
```

Tudo funciona 100% local por padrão (SQLite + disco + fila síncrona).
Postgres, Redis, Google OAuth/Drive/Gmail são opt-in, cada um configurado
por uma variável de ambiente própria — nenhum é obrigatório para o
sistema rodar (`backend/README.md`, seção "Configuração").

## Backend (`backend/app/`)

```
api/routes/        # uma rota FastAPI por recurso — HTTP em↔ saída,
                    # nenhuma regra de negócio aqui além de orquestrar
                    # o service certo e aplicar RBAC (dependencies=[...])
core/               # config (Settings), banco (engine/Session), exceções
                    # de domínio, segurança (sessão/RBAC), rate limiting
models/             # SQLAlchemy — o schema real do banco
schemas/            # Pydantic — o contrato de request/response de cada rota
services/           # a lógica de negócio de verdade, organizada por domínio:
  documents/          upload, hashing, duplicidade, pipeline OCR
  finance/            calculadora (Decimal), parser de texto livre, ledger
  compliance/         motor de regras + registro versionado de regras
  reports/            agregações para /reports/* + exportação CSV/XLSX/PDF
  audit/              log de auditoria (append-only)
  auth/               sessão + Google OAuth
  integrations/       tokens OAuth compartilhados (Drive/Gmail) + Gmail
  backup/             backup/restauração (banco + storage/)
integrations/       # StorageProvider: local (disco) ou Google Drive —
                    # trocar de provider não muda nenhum service acima
queue/              # fila opcional (Redis) para o processamento de OCR
rules/electoral/    # regras eleitorais como DADO, não código — vazio por
                    # desenho (ver rules/electoral/README.md)
```

**Por que services/ existe separado de api/routes/**: uma rota nunca
contém lógica de negócio diretamente — ela decodifica a requisição, chama
uma função de `services/`, e serializa a resposta. Isso significa que
qualquer regra (como "uma despesa sem documento gera um alerta") é
testável sem precisar de um cliente HTTP, e reutilizável por mais de uma
rota (o parser de texto livre da despesa rápida usa a mesma validação da
despesa estruturada).

**Camada de persistência desacoplada do dialeto**: `core/database.py`
não assume SQLite nem Postgres — a mesma suíte de 216 testes roda contra
os dois (ver `backend/DATABASE.md`), e isso é verificado de verdade a
cada fase que toca o schema, não só assumido pelo uso do SQLAlchemy.

## Como uma mudança de regra eleitoral é modelada

`ComplianceRule` guarda **versões**, não uma regra "atual" só. Cada linha
tem `effective_from`/`effective_until`; uma mudança de regra nunca edita a
linha antiga, sempre fecha o intervalo dela e insere uma nova (ver
`backend/app/services/compliance/rule_registry.py` e
`backend/app/rules/electoral/README.md`). Isso é o que permite julgar um
documento de antes de uma mudança pela regra que valia então — não a de
hoje.

## Storage: local por padrão, Google Drive como alternativa

`app/integrations/storage_adapter.py` define `StorageProvider` como
interface; `LocalStorage` (disco, `storage/{originals,processed,temporary}`)
é o padrão, `GoogleDriveStorage` implementa a mesma interface. Um
documento já salvo continua lido pelo provider com que foi gravado
(`Document.storage_provider`), mesmo que a configuração global mude depois
— trocar `STORAGE_PROVIDER` não quebra documentos antigos.

`BACKUP_STORAGE_PROVIDER` é uma cópia secundária independente e
totalmente opcional — uma falha nela nunca afeta o storage primário
(`app/services/documents/backup_service.py`).

## Autenticação e RBAC

- `AUTH_PROVIDER=local` (padrão): sem login, um operador único com papel
  ADMIN, exatamente como a V1.
- `AUTH_PROVIDER=google`: login real via OAuth (`app/services/auth/`),
  sessão em cookie `httponly` com token opaco de 256 bits guardado só
  como hash no banco (nunca assinado — ver `backend/README.md`, "Auth").
- RBAC: 5 papéis × 9 permissões (`app/core/rbac.py`), aplicado via
  `Depends(require_permission(...))` em cada rota — nunca um `if role ==
  ...` espalhado pelo código.

**Limitação conhecida**: RBAC controla *o que* um papel pode fazer, ainda
não *quais campanhas* ele vê (todo usuário autenticado vê todas as
campanhas). Documentado em `docs/audit/FASE-D-gaps.md`.

## Processamento assíncrono (opcional)

`QUEUE_BACKEND=inline` (padrão) roda o OCR de forma síncrona, sem Redis.
`QUEUE_BACKEND=redis` faz `POST /documents/{id}/process` só enfileirar o
job; um processo separado (`python -m app.services.backup...` — não, ver
`app/queue/worker.py`) consome a fila e chama a mesma função de
processamento que o modo síncrono chama direto — nenhuma lógica de OCR é
duplicada entre os dois modos (`backend/README.md`, "Fila assíncrona").

## Frontend (`frontend/src/`)

```
api/            # um arquivo por recurso — único lugar que fala com o
                # backend via axios (lib/http.ts); componentes nunca
                # chamam fetch/axios diretamente
pages/          # uma tela por rota do React Router
components/     # UI reutilizável (Card, Table, Badge, States, ...) +
                # componentes de domínio (StatusBadges, DocumentReviewPanel)
hooks/          # useAuthStatus, etc. — TanStack Query por cima de api/
state/          # contexto React para UI compartilhada (toast, quick-add)
types/api.ts    # o contrato TypeScript de cada resposta do backend —
                # espelha schemas/*.py manualmente (sem geração automática
                # de tipos ainda; um contrato que ficou desatualizado já
                # causou um bug real de produção — ver docs/audit/ da FASE L)
```

**Nenhum cálculo financeiro roda no frontend** — todo total/saldo vem do
backend (`Decimal`, nunca `float`) e é só formatado para exibição.

## Testes

- Backend: 216 testes (`pytest`), rodados contra SQLite e Postgres reais
  em cada fase que toca o schema ou uma integração externa (nunca só
  mockado quando um serviço real — Postgres, Redis, Google Drive via
  HTTP mockado onde apropriado — estava disponível para testar de
  verdade).
- Frontend: 42 testes (`vitest` + Testing Library).
- Ver `backend/BACKUP.md` para como a restauração de backup é verificada
  de fato (não só "o arquivo foi criado"), e
  `docs/audit/FASE-L-production-test-findings.md` para o smoke test
  end-to-end com Playwright que encontrou um bug real de
  `expenses_without_document` que a suíte automatizada sozinha não pegava.
