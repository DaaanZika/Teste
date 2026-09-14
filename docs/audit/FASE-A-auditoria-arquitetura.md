# FASE A — Auditoria de Arquitetura (V1 → V2 profissional)

Data: conforme commit. Branch: `claude/backend-v1-campanhas-eleitorais-fl32zn`.

## 1. O que já existe (não recriar)

### Backend (`backend/`, FastAPI + SQLAlchemy + Alembic)
- **76 arquivos Python**, 9 arquivos de teste, **44 testes passando**.
- Camadas: `api/routes` (8 routers), `core` (config/database/exceptions/security/logging),
  `models` (11 tabelas), `schemas` (Pydantic), `services` (ocr, documents, finance,
  compliance, reports, audit), `rules/electoral` (vazio, arquitetura pronta),
  `integrations` (`storage_adapter.py` + `future/` com 5 stubs `NotImplementedError`),
  `utils`.
- Banco: SQLite local via `DATABASE_URL`, migrations Alembic já configuradas
  (`alembic/env.py` lê `Settings.database_url` — trocar para Postgres não exige
  mudança de código, só instalar driver e mudar a URL).
- Persistência desacoplada (`app/core/database.py`: `Base`, `engine`, `SessionLocal`
  criados a partir de uma única `DATABASE_URL`).
- Auth: `LocalAuthProvider` (`app/core/security.py`) — único usuário local,
  interface `AuthProvider.get_current_user_id()` já pronta para ser substituída.
- Storage: `StorageProvider` abstrato + `LocalStorage` real; `get_storage_provider()`
  seleciona por `Settings.storage_provider` e falha alto se não for `"local"`.
- Modelos existentes: `User` (id, name, email, role — role hoje é uma string livre,
  não enum RBAC), `Campaign` (nome, candidato, ano, cargo, partido — não tem os
  campos completos do PROMPT 3 §9), `Document`, `DocumentItem`, `Expense`, `Revenue`,
  `Transaction`, `Supplier`, `Category`, `ComplianceRule`, `ComplianceAlert`,
  `AuditLog`, `ProcessingJob`.
- `ComplianceRule` já tem a maioria dos campos pedidos em PROMPT 3 §18
  (`rule_id`, `election_year`, `description`, `legal_source`, `article`,
  `paragraph`, `inciso`, `severity`, `active`, `validation_logic`) — **falta**
  `effective_from`/`effective_until` (versionamento temporal, PROMPT 3 §19) e
  `source` estruturado (hoje é um único texto `legal_source`).
- `ProcessingJob` já existe como tabela mas roda **síncrono** dentro do request
  (nenhum worker/fila real ainda — PROMPT 3 §34/§35 pendente).
- Pipeline de documento: upload → hash SHA-256 → duplicidade exata + lógica
  (data+valor+CNPJ/CPF/nº doc) → OCR (Tesseract, com fallback gracioso se o
  binário não existir) → extração → confiança → `HUMAN_REVIEW` quando baixa.
- Auditoria: `AuditLog` append-only, sem soft-delete ainda em nenhuma tabela
  financeira (nenhum `DELETE` é exposto na API hoje, então o risco é baixo, mas
  não há `deleted_at` nas tabelas — PROMPT 3 §30 pendente).
- CORS liberado (`allow_origins=["*"]`) — aceitável só em V1 local, precisa
  restringir quando houver deploy real (PROMPT 3 §32).

### Frontend (`frontend/`, React 19 + TypeScript + Vite + Tailwind v4)
- **69 arquivos**, Vitest + Testing Library, **28 testes passando**.
- Camadas: `api/*` (client único por domínio), `components/ui` (genéricos),
  `components/layout` (sidebar/topbar/mobile nav), `pages` (uma por rota),
  `state` (contexto leve: modal global de Adicionar Gasto, toasts), `lib`
  (formatação, erros, query client), `types/api.ts` (espelha os schemas do
  backend 1:1).
- Nenhum estado global pesado (Redux etc.) — TanStack Query cobre estado de
  servidor, `useState` cobre estado local. Nenhum dado fictício em nenhuma tela.
- Não existe login nem seleção de campanha na UI (PROMPT 3 §43 pendente —
  fará sentido só depois que o backend tiver autenticação real).

### Integrações futuras já mapeadas (mas 100% `NotImplementedError`)
`google_drive_storage.py`, `gmail_provider.py`, `google_oauth_provider.py`,
`cloud_storage_provider.py`, `tse_exporter.py` — interfaces corretas
(`StorageProvider`, `AuthProvider`, `TSEExporter`), zero código de rede.

### Testes existentes
Backend: hashing/duplicidade, extração OCR (nunca inventa campo), motor
financeiro (Decimal, nunca float), parser de lançamento rápido, endpoints
principais, auditoria, granularidade de período. Frontend: fluxo de
"Adicionar Gasto" (`"R$ 850 gráfica ABC"` end-to-end), validação de
formulário, pipeline de upload/OCR/revisão, estados do dashboard, filtro de
lista, navegação mobile.

### Dependências
Backend: FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, pytesseract/Pillow/
OpenCV/PyMuPDF, pytest/httpx. **Nenhum driver Postgres, Redis, Celery/RQ,
google-*, boto3, reportlab/openpyxl ainda instalado.**
Frontend: react-query, axios, react-router, recharts, Tailwind v4, Vitest.

## 2. O que falta (gaps reais frente ao PROMPT 3)

| Área | Status |
|---|---|
| Docker / compose | Inexistente |
| PostgreSQL | Suportável via `DATABASE_URL`, nunca testado, driver não instalado |
| Redis / fila assíncrona | Inexistente; `ProcessingJob` existe mas roda síncrono |
| Google OAuth / sessões | Interface pronta, zero implementação |
| RBAC | `User.role` é string livre, nenhuma checagem de permissão em nenhuma rota |
| Multi-campanha / seleção de campanha | `Campaign` existe no banco mas nenhuma rota a expõe nem a API filtra por usuário↔campanha |
| Google Drive / Gmail | Zero implementação (stubs) |
| Backup/restore | Inexistente |
| Soft delete | Inexistente (`deleted_at` ausente) |
| Versionamento de regra eleitoral | `ComplianceRule` não tem `effective_from/until`; nenhuma regra cadastrada (correto, por falta de fonte oficial) |
| Relatórios PDF/XLSX/CSV | Só JSON hoje |
| `/health` e `/ready` | Só `/health` existe (simples) |
| Segurança (CORS restrito, rate limit, cabeçalhos) | Não auditado ainda |

## 3. Princípio de execução desta fase

Dado o tamanho do PROMPT 3 (60+ seções cobrindo infraestrutura, auth,
integrações Google, filas, regras eleitorais, relatórios, backup, segurança),
a implementação seguirá as fases B→N do próprio prompt, **sem tocar em nada
que já funciona** a não ser para *adicionar* a interface que falta (ex.:
adicionar `effective_from` em `ComplianceRule` via migration, nunca reescrever
o motor). Cada fase é implementada, testada e commitada isoladamente antes de
avançar (PROMPT 3 §61).

Integrações que exigem credenciais reais do Google (OAuth, Drive, Gmail) serão
implementadas com código de produção real (biblioteca oficial, fluxo OAuth
correto), mas **funcionalmente inertes sem `GOOGLE_CLIENT_ID`/`SECRET`
configurados** — reportando `not_configured` em vez de simular sucesso. Isso
respeita PROMPT 3 §45/§52 (sistema continua funcionando localmente sem Google)
e a regra geral do projeto de nunca fabricar dado ou resultado.
