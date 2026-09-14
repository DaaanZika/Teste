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

### Migrando de SQLite para PostgreSQL no futuro

Basta trocar `DATABASE_URL` no `.env` para uma URL PostgreSQL (ex.:
`postgresql+psycopg://user:senha@host/banco`) e instalar o driver
(`psycopg[binary]`). Nenhum model, service ou rota precisa mudar — a
camada de persistência (`app/core/database.py`) já é desacoplada do
dialeto do banco.

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
│   ├── integrations/             # Adapters plugáveis (storage local hoje) +
│   │   └── future/               # Interfaces para Google Drive, Gmail, OAuth, TSE (NÃO implementadas)
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
| GET | `/health` | Status da API |
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
| GET | `/compliance/alerts`, `/compliance/rules` | Alertas e regras de conformidade |
| GET | `/audit` | Log de auditoria (filtros: `entity`, `entity_id`) |

A lista completa e interativa está em `/docs`.

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

## Próximos passos (fora do escopo desta V1)

Ver `app/integrations/future/README.md`: armazenamento em nuvem (Google
Drive), ingestão por e-mail (Gmail), login (Google OAuth) e exportação no
formato oficial do TSE. Nenhum desses itens tem código funcional nesta
fase — apenas interfaces que a V2 pode implementar sem redesenhar o
restante do backend.
