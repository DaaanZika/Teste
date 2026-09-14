# Segurança

Postura de segurança do sistema como um todo. Para a auditoria completa
que produziu a maior parte do que está aqui — metodologia, achados
corrigidos e o que foi verificado sem achado — ver
`docs/audit/FASE-H-security-audit.md`. Este documento é o resumo vivo;
aquele é o registro histórico da auditoria dedicada.

## Autenticação

- **`AUTH_PROVIDER=local`** (padrão): nenhuma senha, nenhum login — um
  operador único com papel ADMIN. Adequado para um único responsável
  operando a campanha na própria máquina; não segrega usuários.
- **`AUTH_PROVIDER=google`**: OAuth 2.0 real (`app/services/auth/google_oauth.py`),
  sem SDK — chamadas diretas ao endpoint do Google via `httpx`. Estado
  (`state`) gerado com `secrets.token_urlsafe`, guardado num cookie
  `httponly` e conferido por igualdade no callback (proteção CSRF do
  fluxo OAuth em si, independente do CSRF de sessão abaixo).
- **Sessão**: token opaco de 256 bits (`secrets.token_urlsafe(32)`) num
  cookie `httponly` + `secure` (fora de `DEBUG`) + `samesite=lax`. O
  banco guarda só o hash SHA-256 do token — um vazamento do banco sozinho
  não é reutilizável como sessão válida. **Não** é um JWT nem um token
  assinado; `SECRET_KEY` não protege nada hoje (ver nota em
  `app/core/config.py` — mantido como placeholder obrigatório-de-rotacionar
  para um esquema futuro, não como algo já em uso).

## Autorização (RBAC)

5 papéis × 9 permissões (`app/core/rbac.py`), aplicado por
`Depends(require_permission(...))` em cada rota — nunca checado
manualmente com `if role == ...` espalhado pelo código. Toda rota que
muda estado exige uma permissão explícita; leitura exige a permissão
`VIEW_*` correspondente.

**Limitação conhecida**: RBAC controla *o que* um papel pode fazer, não
*quais campanhas* ele vê — todo usuário autenticado enxerga dados de
todas as campanhas no banco. Só importa em `AUTH_PROVIDER=google` com
múltiplos usuários reais; documentado em `docs/audit/FASE-D-gaps.md`.

Um guard específico impede deixar o sistema sem nenhum ADMIN ativo
(`PATCH /users/{id}` recusa com 409 se a mudança removeria o último —
achado e corrigido na FASE H, `app/api/routes/users.py`).

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
