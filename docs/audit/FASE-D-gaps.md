# FASE D — lacunas conhecidas (documentadas, não escondidas)

## RBAC não restringe por campanha ainda

`app/core/rbac.py` controla **o que** um papel pode fazer (`MANAGE_FINANCE`,
`VIEW_DOCUMENTS`, etc.), mas todo endpoint de leitura hoje retorna dados de
**todas** as campanhas para qualquer usuário autenticado — não existe uma
tabela `campaign_members` associando usuário ↔ campanha ↔ papel-por-campanha.

Isso significa que, no modo `AUTH_PROVIDER=google` com múltiplos usuários
reais, um `VIEWER` de uma campanha veria também os dados financeiros de
outra campanha no mesmo banco. Para uso local com um único operador
(`AUTH_PROVIDER=local`, o padrão) isso não é um problema, já que só existe
uma "campanha" de fato sendo usada.

**Antes de usar `AUTH_PROVIDER=google` com mais de uma campanha e mais de
um usuário em produção, isso precisa ser implementado.** Ficou fora desta
fase por ser, na prática, uma segunda feature grande (multi-tenancy por
linha), não uma extensão pequena do RBAC já feito.

## Sem UI de administração para usuários/campanhas/regras eleitorais

O frontend ainda não tem tela para: gerenciar usuários/papéis,
criar/selecionar campanha, ou cadastrar/versionar uma regra eleitoral —
as rotas de backend existem e são testadas (`/users`, `/campaigns`,
`/compliance/rules`), mas só via API/`/docs` até aqui. As integrações
Google (login, conectar Drive/Gmail, sugestões do Gmail) já têm UI
própria em Configurações desde as FASES D–F.

## ~~Sem rate limiting no login~~ — resolvido na FASE H

`POST /auth/google/callback` e `/auth/google/login` agora têm limite de
tentativas por IP (`app/core/rate_limit.py`, 20/60s e 10/60s
respectivamente). Detalhes em `docs/audit/FASE-H-security-audit.md`.
