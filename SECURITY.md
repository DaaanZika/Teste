# Segurança

Postura de segurança do sistema como um todo. Para a auditoria completa
que produziu a maior parte do que está aqui — metodologia, achados
corrigidos e o que foi verificado sem achado — ver
`docs/audit/FASE-H-security-audit.md`. Este documento é o resumo vivo;
aquele é o registro histórico da auditoria dedicada.

## Autenticação

- **`AUTH_PROVIDER=local`** (padrão): nenhuma senha, nenhum login — um
  operador único com papel ADMIN, dentro de uma organização implícita.
  Adequado para um único responsável operando a campanha na própria
  máquina; não segrega usuários.
- **`AUTH_PROVIDER=google`**: OAuth 2.0 real (`app/services/auth/google_oauth.py`),
  sem SDK — chamadas diretas ao endpoint do Google via `httpx`. Estado
  (`state`) gerado com `secrets.token_urlsafe`, guardado num cookie
  `httponly` e conferido por igualdade no callback (proteção CSRF do
  fluxo OAuth em si, independente do CSRF de sessão abaixo).
- **Login por senha** (`POST /auth/login`, disponível sempre que
  `AUTH_PROVIDER` não é `local`): senha com hash bcrypt (12 rounds,
  `app/core/password.py`), nunca texto puro em lugar nenhum. Resposta
  idêntica para e-mail inexistente e senha errada — nenhuma enumeração de
  contas. Bloqueio de conta por 15 minutos após 5 tentativas seguidas
  erradas (`User.failed_login_attempts`/`locked_until`), além do rate
  limit por IP já existente em `/auth/login`. Reset de senha
  (`/auth/forgot-password` → `/auth/reset-password`) usa um token de uso
  único com hash SHA-256 guardado (mesmo princípio do token de sessão
  abaixo) e 30 minutos de validade; a resposta de `forgot-password` é
  sempre a mesma, exista ou não o e-mail.
- **Sessão**: token opaco de 256 bits (`secrets.token_urlsafe(32)`) num
  cookie `httponly` + `secure` (fora de `DEBUG`) + `samesite=lax`. O
  banco guarda só o hash SHA-256 do token — um vazamento do banco sozinho
  não é reutilizável como sessão válida. **Não** é um JWT nem um token
  assinado; `SECRET_KEY` não protege nada hoje (ver nota em
  `app/core/config.py` — mantido como placeholder obrigatório-de-rotacionar
  para um esquema futuro, não como algo já em uso). Login por Google e
  por senha criam o mesmo tipo de sessão — nunca dois sistemas paralelos.
- **Primeiro SUPER_ADMIN**: bootstrap explícito por variável de ambiente
  (`SUPER_ADMIN_BOOTSTRAP_EMAIL`/`PASSWORD`, `python -m app.services.admin.bootstrap`)
  — nenhuma senha fixa no código, idempotente (nunca cria um segundo,
  nunca reseta a senha de um já existente). Ver `backend/README.md`.

## Autorização (RBAC) e multi-tenant

Papéis × permissões vivem só em `app/core/rbac.py` (fonte única),
aplicado por `Depends(require_permission(...))` em cada rota — nunca
checado manualmente com `if role == ...` espalhado pelo código. Toda
rota que muda estado exige uma permissão explícita; leitura exige a
permissão `VIEW_*`/granular correspondente. `SUPER_ADMIN` é a exceção
deliberada: nunca passa por esse mapa de permissões — `/admin/*` é
protegido por uma checagem de **papel** (`require_super_admin`), nunca
de permissão, para que nenhuma combinação de permissões concedidas possa
acidentalmente destravar a área da plataforma.

**Isolamento entre organizações** (resolvido — antes um gap conhecido,
ver `docs/audit/FASE-D-gaps.md`): cada `Campaign` pertence a uma
`Organization`; todo documento/despesa/receita/alerta pertence a uma
campanha, e por isso a uma organização. Todo endpoint deriva a
organização do usuário autenticado (`app/core/tenancy.py`) — nunca de um
valor enviado pelo cliente; um `organization_id`/`campaign_id` de outra
organização é sempre recusado (404, nunca confirmando que o registro
existe). Testado contra duas organizações reais em
`backend/tests/test_multi_tenant_isolation.py` — inclusive que criar um
registro nunca aceita a organização de outra pessoa vinda do payload, e
que a checagem de duplicidade de documentos (hash e campos extraídos)
também é escopada por organização (achado real durante o PROMPT 4: sem
isso, um hash coincidente entre organizações vazava o documento da
outra).

Um guard específico impede deixar uma organização sem nenhum
OWNER/ADMIN ativo (`PATCH /users/{id}` recusa com 409 se a mudança
removeria o último — achado e corrigido na FASE H para o caso de
usuário único, estendido ao multi-tenant no PROMPT 4,
`app/api/routes/users.py`).

## CSRF

Mitigado pela combinação de `samesite=lax` no cookie de sessão + CORS
restrito a origens explícitas (`CORS_ORIGINS`, nunca `*` — um wildcard
com `allow_credentials=True` é rejeitado pelo próprio navegador). Não há
um token CSRF separado porque seria redundante com essa combinação.

## Rate limiting

`app/core/rate_limit.py` — limitador em memória por (rota, IP), aplicado
em `/auth/google/login` (10/60s) e `/auth/google/callback` (20/60s). É
por processo, não compartilhado entre réplicas via um store como Redis —
limitação conhecida para quem rodar múltiplas réplicas atrás de um load
balancer (o limite efetivo vira `tentativas × réplicas`).

## Upload de arquivos

- Extensão e MIME type validados contra uma lista fixa
  (`.jpg`/.jpeg/.png/.webp/.pdf`).
- Tamanho máximo configurável (`MAX_UPLOAD_SIZE_BYTES`).
- Nome do arquivo sanitizado e gravado com nome gerado (UUID) — o nome
  original do usuário nunca vira um caminho no disco
  (`app/utils/files.py::sanitize_filename`, `resolve_within`) — defesa
  contra path traversal, verificada por teste, não só por desenho.

## Segredos

- Nenhum segredo committado no repositório — `.env`/`.env.local`
  ignorados em todo nível (raiz, backend, frontend); verificado por
  varredura de padrões de chave conhecidos, nenhum encontrado.
- `docker-compose.prod.yml` recusa subir sem `SECRET_KEY`/`POSTGRES_PASSWORD`
  definidos (sintaxe `${VAR:?mensagem}` do Compose) — o overlay de
  produção não herda mais os defaults de desenvolvimento do
  `docker-compose.yml` base, que existem só para `docker compose up`
  sem esse overlay.
- Nenhum token OAuth (Google/Drive/Gmail) aparece em schema de resposta
  de API nem em log — verificado grepando todo o código por chamadas de
  log perto de onde tokens são manipulados.

## Injeção e XSS

- **SQL**: nenhuma query crua com interpolação de string em todo o
  backend — só o SQLAlchemy query builder (parâmetros vinculados). A
  única exceção verificada (`app/services/backup/backup_service.py`,
  contagem de linhas por tabela) interpola um nome de tabela que vem da
  reflexão do próprio banco, nunca de entrada externa.
- **XSS**: nenhum uso de `dangerouslySetInnerHTML`/`innerHTML =` no
  frontend — React escapa por padrão.
- **Command injection**: nenhum `subprocess`/`os.system`/`shell=True` no
  código da aplicação; Tesseract é invocado pela biblioteca `pytesseract`
  (lista de argumentos, não uma shell); `pg_dump`/`pg_restore` (backup)
  também recebem argumentos como lista, nunca uma string montada.

## O que este sistema explicitamente NÃO é

- Não é o CONTA+JE — não envia, não simula enviar, e nenhum arquivo
  gerado (relatório, exportação) afirma ser uma prestação de contas
  oficial ao TSE (ver `backend/README.md`, seção de exportação de
  relatórios).
- Não hospeda nem processa dados fora do ambiente configurado por quem
  opera — Google Drive/Gmail só são usados quando explicitamente
  conectados por um ADMIN, e o sistema continua funcionando 100% local
  sem eles.

## Reportando um problema de segurança

Este é um projeto sem um canal formal de disclosure — abra uma issue no
repositório descrevendo o problema. Para algo sensível, evite detalhar
publicamente um caminho de exploração antes de dar chance de correção.
