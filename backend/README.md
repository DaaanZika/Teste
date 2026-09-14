# Backend V1 — Organização Financeira e Documental de Campanhas Eleitorais

Backend local (sem Docker, sem nuvem, sem integrações externas) para
recebimento e processamento de documentos, lançamentos financeiros e
geração de dados para relatórios de campanhas eleitorais brasileiras.

> **Importante sobre regras eleitorais:** esta versão **não** contém
> valores, limites, prazos ou artigos legais cadastrados. A arquitetura de
> conformidade (`app/rules/electoral/`, `compliance_rules`) está pronta,
> mas vazia até que cada regra seja confirmada em fonte oficial do TSE.
> Ver `app/rules/electoral/README.md`.

## Requisitos

- Python 3.11+
- Tesseract OCR instalado no sistema (ver abaixo). Sem ele, o backend
  continua funcionando normalmente — documentos ficam marcados como
  `HUMAN_REVIEW` em vez de falhar.

Nenhum banco externo, Docker, Redis ou serviço de nuvem é necessário
nesta fase.

## Instalação

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Instalação do Tesseract OCR

O pacote `pytesseract` é apenas um wrapper: o motor de OCR (`tesseract`)
precisa estar instalado separadamente no sistema operacional.

- **Ubuntu/Debian:**
  ```bash
  sudo apt-get update
  sudo apt-get install tesseract-ocr tesseract-ocr-por
  ```
- **macOS (Homebrew):**
  ```bash
  brew install tesseract tesseract-lang
  ```
- **Windows:** baixe o instalador em
  https://github.com/UB-Mannheim/tesseract/wiki e, se o executável não
  estiver no PATH, configure `TESSERACT_CMD` no `.env` apontando para o
  `tesseract.exe`.

Verifique a instalação com `tesseract --version`. O pacote de idioma
`por` (português) é usado por padrão (`OCR_LANGUAGE`).

## Configuração

```bash
cp .env.example .env
```

Todas as variáveis têm um padrão funcional para uso local — o `.env` só é
necessário para customizar caminhos, o idioma do OCR, ou (futuramente) a
URL de um banco PostgreSQL. Ver `app/core/config.py` para a lista
completa e `.env.example` para os comentários de cada variável.

## Banco de dados e migrations

O schema é criado e versionado via Alembic — nunca manualmente.

```bash
alembic upgrade head
```

Isso cria `storage/app.db` (SQLite) com todas as tabelas. Para gerar uma
nova migration depois de alterar um model:

```bash
alembic revision --autogenerate -m "descrição da mudança"
alembic upgrade head
```

### PostgreSQL

Basta trocar `DATABASE_URL` no `.env` para uma URL PostgreSQL (ex.:
`postgresql+psycopg://user:senha@host/banco`) — o driver (`psycopg[binary]`)
já está em `requirements.txt`. Nenhum model, service ou rota muda — a
camada de persistência (`app/core/database.py`) é desacoplada do dialeto
do banco, e isso é testado de verdade (não só por design): ver
`DATABASE.md` para como rodar a suíte de testes contra Postgres.

Com Docker (`docker compose up` na raiz do projeto), o Postgres já sobe
configurado automaticamente — ver `../README.md`.

Backup e restauração (banco + documentos), incluindo como a restauração é
de fato verificada: ver `BACKUP.md`.

## Execução

```bash
uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Documentação interativa (Swagger): http://127.0.0.1:8000/docs
- Especificação OpenAPI: http://127.0.0.1:8000/openapi.json

## Testes

```bash
pytest
```

Os testes usam um banco SQLite e um diretório de armazenamento
temporários (ver `tests/conftest.py`), isolados do `storage/` real do
projeto. Cobrem: extração de OCR (sem inventar campos), confiança do OCR,
motor financeiro (`Decimal`, sem `float`), o parser de lançamento rápido de
despesas, upload/hash/duplicidade de documentos e os principais endpoints
da API.

## Arquitetura

```text
backend/
├── app/
│   ├── main.py                 # App FastAPI, CORS, exception handlers, rotas
│   ├── api/routes/              # Endpoints HTTP (health, documents, expenses, ...)
│   ├── core/                    # Config, banco (SQLAlchemy), erros, auth local
│   ├── models/                  # Tabelas (SQLAlchemy ORM)
│   ├── schemas/                 # Contratos de request/response (Pydantic)
│   ├── services/
│   │   ├── ocr/                 # Motor Tesseract, extração de campos, confiança
│   │   ├── documents/            # Storage, hashing, duplicidade, pipeline de documento
│   │   ├── finance/              # Calculadora financeira (Decimal), parser de texto livre
│   │   ├── compliance/           # Motor de regras (arquitetura; regras vazias na V1)
│   │   ├── reports/              # Agregação de dados para /reports
│   │   └── audit/                # Log de auditoria (append-only)
│   ├── rules/electoral/          # Regras eleitorais como dados (vazio na V1 — ver README lá)
│   ├── integrations/             # Adapters plugáveis: storage local/Google Drive, OAuth, Gmail (leitura) +
│   │   └── future/               # Interfaces para storage em nuvem genérico e exportação TSE (NÃO implementadas)
│   └── utils/                    # Sanitização de arquivos, parsing de texto/data/moeda
├── storage/{originals,processed,temporary}/   # Arquivos locais
├── alembic/                      # Migrations do banco
├── tests/
└── requirements.txt
```

### Por que essa separação

- **`services/ocr` nunca é chamado diretamente pelas rotas** — apenas por
  `services/documents/document_service.py`, que orquestra todo o
  pipeline (upload → hash → duplicidade → OCR → extração → validação →
  banco) descrito no PROMPT 1.
- **`finance/calculator.py` é a única fonte de verdade matemática.** Nenhuma
  rota, serviço ou (futuramente) frontend deve recalcular saldo, total ou
  percentual por conta própria. Todo valor monetário usa `Decimal`, nunca
  `float`.
- **`integrations/`** isola tudo que hoje é local (`LocalStorage`,
  `LocalAuthProvider`) atrás de uma interface. As integrações futuras
  (`app/integrations/future/`) já têm a assinatura esperada, mas lançam
  `NotImplementedError` — nada de rede, credenciais ou SDKs de nuvem
  nesta fase.
- **`rules/electoral/` e `compliance_rules` começam vazios.** Regras são
  dados, não código: nenhum valor, prazo, artigo ou limite legal foi
  inventado. Ativar uma regra no futuro não exige reescrever o backend.

## Endpoints principais

| Método | Rota | Descrição |
| --- | --- | --- |
| GET | `/health` | Liveness — processo no ar (não checa dependências) |
| GET | `/ready` | Readiness — checa banco (e Redis, se `QUEUE_BACKEND=redis`) |
| GET | `/auth/status` | Nunca exige sessão; diz se há login e se Google está configurado |
| GET | `/auth/google/login`, `/auth/google/callback` | Fluxo OAuth (exige `GOOGLE_CLIENT_ID`/`SECRET`) |
| POST | `/auth/logout` | Revoga a sessão atual |
| GET | `/auth/me` | Usuário autenticado |
| GET | `/users`, `PATCH /users/{id}` | Gestão de usuários (somente ADMIN) |
| GET/POST/PUT | `/campaigns`, `/campaigns/{id}` | Campanhas (múltiplas campanhas, ver seção RBAC abaixo) |
| GET | `/integrations/status` | Estado real de Google Drive, Gmail, backup, banco e OCR |
| GET | `/integrations/google-drive/connect` | Inicia a conexão do Google Drive (somente ADMIN) |
| POST | `/integrations/google-drive/disconnect` | Desconecta o Google Drive (somente ADMIN) |
| GET | `/integrations/gmail/connect` | Inicia a conexão do Gmail, leitura apenas (somente ADMIN) |
| POST | `/integrations/gmail/disconnect` | Desconecta o Gmail (somente ADMIN) |
| POST | `/integrations/gmail/scan` | Busca anexos que parecem comprovante/nota fiscal — nunca importa sozinho |
| GET | `/integrations/gmail/suggestions` | Lista sugestões detectadas (filtro `status`) |
| POST | `/integrations/gmail/suggestions/{id}/confirm` | Confirma: baixa o anexo de verdade e cria o Documento |
| POST | `/integrations/gmail/suggestions/{id}/reject` | Rejeita a sugestão — nunca toca a caixa de entrada |
| POST | `/documents/upload` | Upload de documento (multipart) |
| GET | `/documents` | Lista documentos (filtros: `status`, `campaign_id`) |
| GET | `/documents/{id}` | Detalhe de um documento |
| POST | `/documents/{id}/process` | Executa OCR + extração + validação |
| POST | `/documents/{id}/ocr` | Alias de `/process` (OCR e extração rodam juntos na V1) |
| PATCH | `/documents/{id}/correct` | Correção manual de campos extraídos (audita a mudança) |
| POST | `/expenses` | Cria despesa (estruturada) |
| POST | `/expenses/quick` | Cria despesa a partir de texto livre |
| GET/PUT | `/expenses`, `/expenses/{id}` | Lista, detalha e atualiza despesas |
| POST/GET | `/revenues`, `/revenues/{id}` | Cria/lista/detalha receitas |
| GET | `/finance/summary`, `/finance/balance` | Totais e saldo (fonte da verdade) |
| GET | `/finance/totals/{period,category,supplier}` | Agregações financeiras |
| GET | `/reports/{summary,expenses,revenues,documents}` | Dados estruturados para relatórios |
| GET | `/reports/{summary,expenses,revenues,documents}/export?format=csv\|xlsx\|pdf` | Exporta o mesmo relatório como arquivo — sempre rotulado "RELATÓRIO AUXILIAR" |
| GET | `/compliance/alerts`, `/compliance/rules` | Alertas e regras de conformidade |
| GET | `/compliance/rules/{rule_id}/history` | Todas as versões de uma regra, mais antiga primeiro |
| POST | `/compliance/rules` | Cria a 1ª versão de uma regra (somente ADMIN, sempre inativa) |
| POST | `/compliance/rules/{rule_id}/supersede` | Nova versão de uma regra existente (somente ADMIN) |
| POST | `/compliance/rules/{id}/activate`, `/deactivate` | Liga/desliga uma versão específica (somente ADMIN) |
| GET | `/audit` | Log de auditoria (filtros: `entity`, `entity_id`) |

A lista completa e interativa está em `/docs`.

## Autenticação e permissões (RBAC)

Dois modos, escolhidos por `AUTH_PROVIDER`:

- **`local`** (padrão): sem login, exatamente como a V1. Um único
  operador local é criado automaticamente com papel `ADMIN` — todas as
  permissões liberadas, nada muda no comportamento anterior.
- **`google`**: login real via Google OAuth (`app/services/auth/`). No
  primeiro login o usuário é criado com o papel mais restrito
  (`VIEWER`); um `ADMIN` precisa promovê-lo em `PATCH /users/{id}`.
  Sem `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`/`GOOGLE_REDIRECT_URI`
  configurados, os endpoints de login retornam `503 NOT_CONFIGURED` —
  nunca simulam um login bem-sucedido.

Papéis e permissões (`app/core/rbac.py`):

| Papel | Pode |
| --- | --- |
| `ADMIN` | Tudo, incluindo gerenciar usuários e regras eleitorais |
| `CAMPAIGN_MANAGER` | Gerenciar campanha, despesas, receitas, documentos |
| `FINANCIAL` | Lançar despesas/receitas, gerenciar documentos |
| `ACCOUNTANT` | Revisar/corrigir documentos, sem originar lançamentos |
| `VIEWER` | Somente visualizar |

**Limitação conhecida desta fase:** o RBAC controla *o que* um papel pode
fazer, mas ainda não restringe *quais campanhas* um usuário enxerga —
qualquer usuário autenticado vê dados de todas as campanhas. Escopo por
campanha (`campaign_members`) é uma funcionalidade separada, ainda não
implementada — ver `docs/audit/`.

## Tratamento de erros

Nenhum erro derruba a API. Toda falha de domínio retorna:

```json
{
  "success": false,
  "error": "DOCUMENT_PROCESSING_FAILED",
  "message": "Não foi possível processar o documento.",
  "requires_human_review": true
}
```

Stack traces nunca são expostos ao cliente; erros inesperados são
logados no servidor (ver `app/core/exceptions.py`).

## Segurança local (V1)

- Extensão e MIME type validados na entrada (`.jpg`, `.jpeg`, `.png`,
  `.webp`, `.pdf`).
- Tamanho máximo de upload configurável (`MAX_UPLOAD_SIZE_BYTES`).
- Nomes de arquivo sanitizados e gravados com nome gerado (UUID), nunca o
  nome original enviado pelo usuário — evita path traversal.
- Arquivos originais nunca são executados nem sobrescritos.
- `storage/temporary/` é isolado de `storage/originals/`.

## Armazenamento e backup (opcional)

`STORAGE_PROVIDER` seleciona onde um documento *novo* é gravado —
`local` (padrão, disco) ou `google_drive` (requer um ADMIN logado via
Google OAuth ter conectado o Drive em `GET /integrations/google-drive/connect`).
Documentos já existentes continuam lidos pelo provider com que foram
gravados (`Document.storage_provider`), mesmo que a configuração global
mude depois — ver `app/integrations/storage_adapter.py`.

`BACKUP_STORAGE_PROVIDER` é uma cópia secundária independente e
totalmente opcional: se não configurado, `Document.backup_status` fica
`NOT_CONFIGURED`; se configurado mas a cópia falhar (Drive desconectado,
erro de rede), o documento é marcado `backup_status=FAILED` com um alerta
`WARNING` — o upload original, já salvo no storage primário, nunca é
afetado (`app/services/documents/backup_service.py`).

Sem nenhuma dessas variáveis configuradas, o sistema roda 100% local,
exatamente como a V1.

## Detecção de comprovantes no Gmail (opcional)

Com o Gmail conectado (`GET /integrations/gmail/connect`, somente ADMIN,
escopo `gmail.readonly` — nunca envia, apaga ou modifica nada na caixa de
entrada), `POST /integrations/gmail/scan` procura e-mails com anexo cujo
assunto/corpo sugere nota fiscal, recibo, fatura, boleto ou comprovante e
grava uma sugestão `PENDING` por anexo (`GmailSuggestion`). Isso é só uma
heurística de busca — nenhuma sugestão vira `Document` sozinha.

Um humano decide: `POST /integrations/gmail/suggestions/{id}/confirm`
baixa o anexo de verdade e roda pelo mesmo pipeline de upload manual
(mesma validação, mesma detecção de duplicidade, mesmo log de auditoria);
`POST .../reject` descarta a sugestão sem tocar na caixa de entrada. Uma
nova busca nunca sugere de novo o mesmo anexo (`app/services/integrations/gmail_service.py`).

## Fila assíncrona (opcional)

`QUEUE_BACKEND=inline` (padrão) roda o OCR de forma síncrona dentro da
própria requisição de `POST /documents/{id}/process` — exatamente como a
V1, sem exigir Redis. `QUEUE_BACKEND=redis` (exige `REDIS_URL`) faz esse
mesmo endpoint só enfileirar o job e responder na hora com o documento em
`PROCESSING`; um processo separado consome a fila e roda o mesmo pipeline:

```bash
QUEUE_BACKEND=redis REDIS_URL=redis://localhost:6379/0 python -m app.queue.worker
```

(no Docker Compose isso é o serviço `worker`, que só sobe com
`docker compose --profile queue up`.) O worker nunca duplica a lógica de
OCR: ele chama a mesma `document_service.process_document` que o modo
`inline` chama diretamente — só *quando* ela roda muda. Uma falha em um
job é logada e o worker segue para o próximo, nunca derruba o processo
(`app/queue/worker.py`). `GET /integrations/status` reporta o estado real
da fila (`queue`), incluindo se o Redis configurado está de fato
alcançável.

## Exportação de relatórios (CSV/XLSX/PDF)

Todo relatório em `/reports/*` tem um endpoint irmão `/export` que gera o
mesmo conteúdo como arquivo (`app/services/reports/export_service.py`).
Os três formatos incluem, dentro do próprio arquivo (não só na interface),
o aviso:

> RELATÓRIO AUXILIAR — uso interno da campanha. Este documento NÃO é uma
> prestação de contas oficial ao TSE, não foi enviado a nenhum sistema
> oficial e não segue necessariamente o layout exigido pelo CONTA+JE.

Nenhum desses arquivos é, ou afirma ser, uma prestação de contas oficial
— este sistema não é o CONTA+JE e não simula envio a nenhum sistema do
TSE. Valores monetários são gravados como `Decimal` também na exportação
(CSV/PDF como texto formatado, XLSX como número exato — nunca um `float`
arredondado), mantendo a mesma garantia de precisão financeira do resto
do backend.

## Próximos passos (fora do escopo desta fase)

Ver `app/integrations/future/README.md`: exportação no formato oficial do
TSE — sem código funcional ainda. Regras eleitorais versionadas também
seguem pendentes (ver o histórico de commits/fases no topo deste
repositório).
