# FASE D — lacunas conhecidas (documentadas, não escondidas)

## ~~RBAC não restringe por campanha ainda~~ — resolvido no PROMPT 4 (multi-tenant)

O gap original: `app/core/rbac.py` controlava **o que** um papel pode
fazer, mas todo endpoint de leitura retornava dados de **todas** as
campanhas para qualquer usuário autenticado.

Resolvido com uma fronteira de isolamento por **organização** (não por
`campaign_members` como este documento previa originalmente — o desenho
final ficou em `Organization` → `Campaign` → documento/despesa/receita,
ver `backend/README.md` "Multi-tenant"): todo endpoint deriva a
organização do usuário autenticado (`app/core/tenancy.py`), nunca de um
valor enviado pelo cliente. Testado contra duas organizações reais em
`backend/tests/test_multi_tenant_isolation.py`.

## ~~Sem UI de administração para usuários/campanhas/regras eleitorais~~ — usuários/organização resolvido no PROMPT 4

Gestão de usuários e da organização agora tem UI própria
(`/administracao` para OWNER/ADMIN, `/admin` para SUPER_ADMIN — ver
`frontend/src/pages/AdministracaoPage.tsx` e `PlatformAdminPage.tsx`).
Criar/selecionar campanha e cadastrar/versionar uma regra eleitoral
continuam só via API/`/docs` — fora do escopo do PROMPT 4. As integrações
Google (login, conectar Drive/Gmail, sugestões do Gmail) já têm UI
própria em Configurações desde as FASES D–F.

## ~~Sem rate limiting no login~~ — resolvido na FASE H

`POST /auth/google/callback` e `/auth/google/login` agora têm limite de
tentativas por IP (`app/core/rate_limit.py`, 20/60s e 10/60s
respectivamente). Detalhes em `docs/audit/FASE-H-security-audit.md`.
