# Banco de dados

## SQLite (desenvolvimento) vs PostgreSQL (produção)

O backend nunca depende do dialeto do banco: `app/core/database.py` cria o
`engine` a partir de uma única `DATABASE_URL`, e todo o ORM/Alembic é
agnóstico de dialeto. Não há SQL bruto nem sintaxe específica de um banco
em nenhum model ou service.

```bash
# Desenvolvimento (padrão, zero configuração)
DATABASE_URL=sqlite:///./storage/app.db

# Produção
DATABASE_URL=postgresql+psycopg://usuario:senha@host:5432/banco
```

Trocar de um para o outro é só isso — nenhum código muda. Isso foi
verificado de verdade (não só por inspeção): a suíte de 44 testes do
backend passa, sem nenhuma alteração de código, tanto contra SQLite quanto
contra um PostgreSQL 16 real, incluindo `alembic upgrade head` criando as
14 tabelas corretamente em ambos.

## Rodando os testes contra PostgreSQL

Por padrão a suíte usa um arquivo SQLite temporário (isolado, descartado a
cada execução). Para rodar exatamente a mesma suíte contra PostgreSQL:

```bash
export TEST_DATABASE_URL="postgresql+psycopg://usuario:senha@localhost:5432/banco_de_teste"
pytest
```

Diferente do arquivo SQLite (sempre novo), um Postgres é persistente entre
execuções — por isso `tests/conftest.py` faz `DROP` + `CREATE` do schema no
início da sessão de testes quando `TEST_DATABASE_URL` está definida, para
garantir um estado limpo a cada rodada.

### Por que isso importa: SQLite não aplica foreign keys por padrão

Rodar a suíte contra Postgres pegou um bug real que o SQLite escondia:
alguns testes inseriam uma `Transaction` referenciando um `campaign_id`
aleatório que nunca existia na tabela `campaigns`. O SQLite aceita isso
silenciosamente (chaves estrangeiras são desativadas por padrão); o
Postgres rejeita corretamente com `ForeignKeyViolation`. A correção não foi
no código do backend — foi no teste, que passou a criar uma `Campaign`
real antes de referenciá-la (`tests/test_finance_calculator.py`).

Conclusão prática: **sempre rode a suíte contra Postgres antes de
confiar em uma migration ou em uma mudança de schema** — o SQLite não é
suficiente para validar integridade referencial.

## Migrations

Nunca criar tabela manualmente. Toda alteração estrutural é uma migration
Alembic:

```bash
alembic revision --autogenerate -m "descrição da mudança"
alembic upgrade head
```

Em Docker, `docker-entrypoint.sh` roda `alembic upgrade head`
automaticamente antes de subir a API — não é preciso rodar manualmente ao
usar `docker compose up`.

## Redis

Redis é opcional e não é um banco de dados relacional — não guarda nenhum
dado que não possa ser reconstruído. É usado apenas pela fila assíncrona de
processamento de documentos (`QUEUE_BACKEND=redis`, ver `backend/app/queue/`).
Quando `QUEUE_BACKEND=inline` (padrão), o Redis não é necessário para nada
e `GET /ready` nem tenta se conectar a ele.
