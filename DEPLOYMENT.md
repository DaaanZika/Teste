# Deploy

Três formas de rodar o sistema, da mais simples à mais "produção":
localmente sem Docker, Docker Compose para desenvolvimento, e Docker
Compose com o overlay de produção. Nenhuma delas exige Postgres, Redis ou
Google configurados — todas funcionam 100% local por padrão.

## 1. Sem Docker (mais simples)

Ver `backend/README.md` e `frontend/README.md` — cada um roda
independentemente com SQLite local. Bom para desenvolvimento e para uma
campanha pequena rodando na própria máquina do operador.

## 2. Docker Compose — desenvolvimento

```bash
cp .env.example .env   # ajuste o que precisar — os defaults já funcionam
docker compose up
```

Sobe `db` (Postgres 16) e `backend`/`frontend` com hot-reload (código
montado como volume). `redis`/`worker` **não** sobem por padrão — só com
`docker compose --profile queue up` (fila assíncrona, ver
`backend/README.md`, "Fila assíncrona").

Toda variável documentada em `.env.example` é de fato repassada ao
container do backend (`docker-compose.yml`, serviço `backend`) — isso foi
uma lacuna real corrigida na FASE M: `CORS_ORIGINS`, `FRONTEND_URL`,
`STORAGE_BUCKET`/`STORAGE_REGION`/`BACKUP_STORAGE_PROVIDER` e as
variáveis de SMTP estavam documentadas mas nunca chegavam ao container —
defini-las no `.env` não tinha efeito nenhum. O serviço `worker` também
ganhou as variáveis de storage/Google que precisa para processar
documentos com o mesmo provider que o backend usa.

Migrations rodam automaticamente na subida do container
(`backend/docker-entrypoint.sh` → `alembic upgrade head` antes do
`uvicorn` iniciar) — nunca é preciso rodar `alembic upgrade` manualmente
num deploy via Docker.

## 3. Docker Compose — produção

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

Diferenças do modo desenvolvimento:

- Sem volumes de código-fonte — a imagem já é o artefato final.
- Frontend compilado como bundle estático servido por nginx, não o
  servidor de dev do Vite.
- Backend sem `--reload`, com `--workers 2`.
- `SECRET_KEY` e `POSTGRES_PASSWORD` são **obrigatórios** — o Compose
  recusa subir sem eles (`${VAR:?mensagem}`), em vez de usar os defaults
  de desenvolvimento do arquivo base silenciosamente. Verificado com
  `docker compose config` falhando sem as variáveis e funcionando com
  elas (ver `docs/audit/FASE-H-security-audit.md`).

Variáveis mínimas para um `.env` de produção (além das que já têm
default seguro): `SECRET_KEY`, `POSTGRES_PASSWORD`, `CORS_ORIGINS`
(o domínio real do frontend, nunca `*`), `FRONTEND_URL`,
`VITE_API_BASE_URL` (o domínio real do backend, alcançável pelo
navegador do usuário — não o nome do serviço Docker).

## Checklist antes de ir ao ar

- [ ] `SECRET_KEY` real, gerado com `python -c "import secrets; print(secrets.token_urlsafe(32))"` (ou equivalente) — nunca o placeholder.
- [ ] `POSTGRES_PASSWORD` real, não `campanhas`.
- [ ] `CORS_ORIGINS` apontando para o domínio real do frontend em produção (HTTPS).
- [ ] `DEBUG` não definido como `true` (o overlay de produção já fixa `DEBUG=false`, mas confirme se estiver customizando).
- [ ] Backup agendado — ver `backend/BACKUP.md` (não é automático; precisa de um cron ou equivalente).
- [ ] Se for usar Google OAuth/Drive/Gmail: `GOOGLE_CLIENT_ID`/`SECRET`/`REDIRECT_URI`
      reais, com o redirect URI cadastrado no Google Cloud Console apontando
      para o domínio real (`https://seu-dominio/auth/google/callback`).
- [ ] Rodar `docker compose -f docker-compose.yml -f docker-compose.prod.yml config`
      uma vez para conferir a interpolação final antes de subir de verdade.

## O que NÃO está automatizado

- **Backup agendado**: nenhum cron roda dentro do Compose — ver
  `backend/BACKUP.md`, seção "Agendamento".
- **HTTPS/TLS**: nenhum proxy reverso ou certificado está incluído — um
  Nginx/Caddy/Traefik na frente (ou o load balancer do provedor de nuvem)
  fica a critério de quem opera.
- **Múltiplas réplicas do backend**: o rate limiter (`app/core/rate_limit.py`)
  é em memória por processo — rodar mais de uma réplica atrás de um load
  balancer multiplica o limite efetivo. Documentado, não escondido (ver
  `SECURITY.md`).
- **RBAC por campanha**: qualquer usuário autenticado em
  `AUTH_PROVIDER=google` vê dados de todas as campanhas no banco — só
  importa com múltiplos usuários reais e mais de uma campanha (ver
  `docs/audit/FASE-D-gaps.md`).
