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

## Sem UI de administração no frontend

O frontend não tem tela para: gerenciar usuários/papéis, criar/selecionar
campanha, ou configurar Google OAuth — só o essencial (login/logout,
status de autenticação) foi adicionado ao `Topbar`. As rotas de backend
(`/users`, `/campaigns`) existem e são testadas, mas ainda sem interface.

## Sem rate limiting no login

`POST /auth/google/callback` e `/auth/google/login` não têm limite de
tentativas. Fica registrado para a fase de segurança (FASE H).
