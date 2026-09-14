# FASE H — auditoria de segurança

Metodologia: leitura de todo o código de autenticação/autorização/upload,
`grep` sistemático por padrões de risco (SQL cru, `subprocess`/`shell=True`,
`dangerouslySetInnerHTML`, `localStorage`, segredos hardcoded), e checagem
manual de cada rota que aceita entrada não autenticada. Cada achado abaixo
foi corrigido e coberto por teste antes de ser marcado como resolvido —
nada aqui é "identificado mas não corrigido" sem dizer isso explicitamente.

## Achados corrigidos nesta fase

### 1. Sem rate limiting no login/callback OAuth (gap já rastreado em FASE-D-gaps.md)

`POST /auth/google/login` e `GET /auth/google/callback` são alcançáveis
sem sessão — sem limite, um cliente podia martelar essas rotas (custo para
este servidor e para o endpoint de token do Google). Corrigido com um
limitador em memória por (bucket, IP) — `app/core/rate_limit.py`,
`10 tentativas/60s` no login, `20/60s` no callback. É por processo (não
compartilhado entre réplicas via Redis) — documentado como limitação
conhecida no próprio módulo, não escondida. Testes: `tests/test_rate_limit.py`.

### 2. Comentário incorreto sobre `SECRET_KEY`

`app/core/config.py` afirmava "session cookies são assinados com
secret_key" — falso: sessões usam um token opaco de 256 bits
(`secrets.token_urlsafe(32)`) guardado só como hash SHA-256 no banco
(`app/services/auth/session_service.py`), nunca assinado com `SECRET_KEY`.
`SECRET_KEY` está, hoje, sem nenhum uso real no código. Corrigido: o
comentário agora descreve o mecanismo real e deixa explícito que
`SECRET_KEY` é mantido como placeholder obrigatório-de-rotacionar para um
esquema futuro, não como algo que já protege alguma coisa.

### 3. `PATCH /users/{id}` podia remover o último ADMIN ativo

A própria docstring da rota dizia "nunca permite remover/desativar o
último ADMIN por acidente" — mas nenhum código fazia essa checagem. Um
ADMIN podia se auto-rebaixar (ou desativar) sem qualquer outro ADMIN
ativo no sistema, travando a administração em `AUTH_PROVIDER=google` com
múltiplos usuários (em `AUTH_PROVIDER=local` o operador único sempre
reaparece como ADMIN, então o impacto prático fica limitado ao modo
multiusuário). Corrigido: antes de aplicar `role`/`active`, a rota conta
quantos outros ADMIN ativos existem e recusa com `409 CONFLICT` se a
mudança deixaria zero. Testes novos em `tests/test_users.py` (rota sem
nenhum teste antes desta fase).

### 4. `docker-compose.prod.yml` não impedia os defaults de dev em produção

O próprio comentário do arquivo afirmava "SECRET_KEY/POSTGRES_PASSWORD são
obrigatórios (sem fallback de dev)" — mas o arquivo não sobrescrevia essas
chaves, então os defaults do `docker-compose.yml` base
(`SECRET_KEY=change-me-in-production-local-dev-secret`,
`POSTGRES_PASSWORD=campanhas`) continuavam valendo mesmo com o overlay de
produção aplicado, se o `.env` não fosse preenchido. Corrigido usando a
sintaxe `${VAR:?mensagem}` do Compose, que falha a subida em vez de usar
um valor padrão inseguro. Verificado com `docker compose config` (não há
daemon Docker neste sandbox, mas `config` valida a interpolação de
variáveis sem precisar dele):

```
$ unset SECRET_KEY POSTGRES_PASSWORD
$ docker compose -f docker-compose.yml -f docker-compose.prod.yml config
error while interpolating services.db.environment.POSTGRES_PASSWORD:
required variable POSTGRES_PASSWORD is missing a value: Defina
POSTGRES_PASSWORD no .env de produção — não há valor padrão aqui.
```

e que, com as variáveis definidas, o merge continua correto (`DATABASE_URL`
recebe a senha real, `docker-compose.yml` sozinho — sem o overlay de
produção — continua funcionando com zero configuração, como antes).

## Verificado e sem achado

- **SQL injection**: nenhuma query crua com interpolação de string; toda
  consulta passa pelo query builder do SQLAlchemy (parâmetros vinculados).
  Única ocorrência de `text()` é `SELECT 1` fixo em `core/health.py`.
- **XSS**: nenhum uso de `dangerouslySetInnerHTML`/`innerHTML =` no
  frontend; React escapa por padrão.
- **CSRF**: cookies de sessão usam `samesite=lax` + `httponly` +
  `secure` (fora de `DEBUG`), e o CORS só libera credentials para as
  origens explícitas de `CORS_ORIGINS` (nunca `*`) — a combinação é a
  mitigação real, não um token CSRF separado (que seria redundante aqui).
- **Path traversal em upload/storage**: `sanitize_filename` remove
  componentes de diretório e caracteres fora de uma lista segura;
  `resolve_within` recusa qualquer caminho resolvido fora do diretório
  base. `LocalStorage.read`/`delete_temporary` só aceitam os buckets
  fixos (`originals`/`processed`/`temporary`) via lookup em dict, nunca
  concatenação direta de um bucket arbitrário do cliente.
- **Command injection**: nenhum `subprocess`/`os.system`/`shell=True` no
  código da aplicação; o Tesseract é invocado pela biblioteca
  `pytesseract`, que usa uma lista de argumentos (não uma shell).
- **Segredos no repositório**: nenhum padrão de chave conhecida (Google
  API key, chave privada PEM, token Slack/Stripe) encontrado em arquivos
  rastreados pelo git; `.env`/`.env.local` estão no `.gitignore` da raiz,
  do backend e do frontend.
- **Tokens em log**: nenhuma chamada de `logger.*` inclui token, senha ou
  segredo — `session_service.py` e `google_tokens.py` não logam nada.
- **Armazenamento de sessão no frontend**: nenhum uso de
  `localStorage`/`sessionStorage` — a sessão vive inteiramente num cookie
  `httponly` (inacessível a JavaScript, logo imune a roubo via XSS).

## Limitações conhecidas, não escondidas

- O rate limiter é em memória por processo — com múltiplas réplicas do
  backend atrás de um load balancer, o limite efetivo vira
  `max_attempts × réplicas`. Corrigir isso exigiria um store compartilhado
  (Redis), fora do escopo desta fase.
- RBAC ainda não restringe por campanha (gap já documentado em
  `FASE-D-gaps.md`) — continua valendo.
