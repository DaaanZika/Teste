# API

Referência humana da API. Para o contrato completo, sempre atualizado
automaticamente (todo campo de todo schema, exemplos, tente na hora):
suba o backend e abra `/docs` (Swagger UI) ou `/redoc`. Este documento é
um mapa por recurso, não um substituto daquele.

## Formato de resposta

Toda rota com `response_model` retorna o objeto/lista diretamente (sem
envelope). As poucas rotas que retornam `dict` puro (`/health`, `/logout`,
disconnect de integrações) usam `{"success": true, "data": {...}}`. Todo
erro de domínio, de qualquer rota, tem o mesmo formato:

```json
{
  "success": false,
  "error": "DOCUMENT_PROCESSING_FAILED",
  "message": "Não foi possível processar o documento.",
  "requires_human_review": true
}
```

`error` é um código estável (`app/core/exceptions.py`) — o frontend nunca
faz parsing de `message` para decidir o que fazer, só para exibir.

## Autenticação e RBAC

Toda rota (exceto `/health`, `/ready`, `/auth/status`,
`/auth/google/login`, `/auth/google/callback`) exige uma sessão válida
(cookie `httponly`, automática em `AUTH_PROVIDER=local`) e a permissão
correspondente (`app/core/rbac.py`) — ver `SECURITY.md` para o modelo
completo. Abaixo, "ADMIN" significa que só esse papel tem a permissão
necessária; as demais rotas aceitam qualquer papel com a permissão
`VIEW_*`/`MANAGE_*` indicada.

## `/auth` — sessão e login

| Método | Rota | Observação |
| --- | --- | --- |
| GET | `/auth/status` | Nunca exige sessão — o frontend chama antes de saber se há login |
| GET | `/auth/google/login` | Redireciona ao Google (limitado a 10 tentativas/60s) |
| GET | `/auth/google/callback` | Um único redirect URI serve login, conectar Drive e conectar Gmail (limitado a 20/60s) |
| POST | `/auth/logout` | |
| GET | `/auth/me` | |

## `/users` — ADMIN

| Método | Rota | Observação |
| --- | --- | --- |
| GET | `/users` | |
| PATCH | `/users/{id}` | Muda papel/ativo — recusa (409) se removeria o último ADMIN ativo |

## `/campaigns`

| Método | Rota | Permissão |
| --- | --- | --- |
| GET | `/campaigns`, `/campaigns/{id}` | VIEW_FINANCE |
| POST | `/campaigns` | MANAGE_CAMPAIGNS |
| PUT | `/campaigns/{id}` | MANAGE_CAMPAIGNS |

## `/documents`

| Método | Rota | Permissão |
| --- | --- | --- |
| POST | `/documents/upload` | MANAGE_DOCUMENTS |
| GET | `/documents`, `/documents/{id}` | VIEW_DOCUMENTS |
| GET | `/documents/{id}/file` | VIEW_DOCUMENTS — bytes originais |
| POST | `/documents/{id}/process` (alias `/ocr`) | MANAGE_DOCUMENTS — síncrono por padrão; enfileira se `QUEUE_BACKEND=redis` |
| PATCH | `/documents/{id}/correct` | MANAGE_DOCUMENTS — corrige campo extraído, sempre auditado |

## `/expenses`, `/revenues`

| Método | Rota | Permissão |
| --- | --- | --- |
| POST | `/expenses`, `/expenses/quick` | MANAGE_FINANCE |
| GET | `/expenses`, `/expenses/{id}` | VIEW_FINANCE |
| PUT | `/expenses/{id}` | MANAGE_FINANCE — vincular `document_id` grava `LINK_DOCUMENT` na auditoria em vez de `UPDATE` |
| POST | `/revenues` | MANAGE_FINANCE |
| GET | `/revenues`, `/revenues/{id}` | VIEW_FINANCE |

`revenues` não tem `PUT` — não há edição depois de criada nesta versão.

## `/finance`

| Método | Rota | Observação |
| --- | --- | --- |
| GET | `/finance/summary` | Aceita `start_date`/`end_date`; contagens de pendência são sempre da campanha inteira |
| GET | `/finance/balance` | |
| GET | `/finance/totals/{period,category,supplier}` | Agregações |

## `/compliance`

| Método | Rota | Observação |
| --- | --- | --- |
| GET | `/compliance/alerts` | |
| GET | `/compliance/rules` | `current_only=true` (padrão) esconde versões supersedidas |
| GET | `/compliance/rules/{rule_id}/history` | Toda versão já cadastrada, mais antiga primeiro |
| POST | `/compliance/rules` | MANAGE_RULES (ADMIN) — cria a 1ª versão, sempre inativa |
| POST | `/compliance/rules/{rule_id}/supersede` | MANAGE_RULES — nova versão, nunca edita a antiga |
| POST | `/compliance/rules/{id}/activate`, `/deactivate` | MANAGE_RULES |

Tabela vazia por desenho — ver `app/rules/electoral/README.md` e
`ELECTORAL_RULES.md`.

## `/reports`

| Método | Rota | Observação |
| --- | --- | --- |
| GET | `/reports/{summary,expenses,revenues,documents}` | JSON |
| GET | `/reports/{summary,expenses,revenues,documents}/export?format=csv\|xlsx\|pdf` | Arquivo, sempre rotulado "RELATÓRIO AUXILIAR" — nunca um layout oficial do TSE/CONTA+JE |

## `/audit` — VIEW_AUDIT

`GET /audit?entity=...&entity_id=...` — log completo, nunca editado nem
apagado.

## `/integrations`

| Método | Rota | Permissão |
| --- | --- | --- |
| GET | `/integrations/status` | VIEW_REPORTS — estado real de Google, Drive, Gmail, backup, banco, OCR, fila |
| GET | `/integrations/google-drive/connect`, `/gmail/connect` | MANAGE_INTEGRATIONS (ADMIN) |
| POST | `/integrations/google-drive/disconnect`, `/gmail/disconnect` | MANAGE_INTEGRATIONS |
| POST | `/integrations/gmail/scan` | MANAGE_DOCUMENTS — só detecta, nunca importa sozinho |
| GET | `/integrations/gmail/suggestions` | VIEW_DOCUMENTS |
| POST | `/integrations/gmail/suggestions/{id}/confirm`, `/reject` | MANAGE_DOCUMENTS |

## `/health`, `/ready`

Sem autenticação. `/health` é liveness puro (nunca toca banco/Redis);
`/ready` checa banco sempre, Redis só se `QUEUE_BACKEND=redis`.

## Backup e restauração

Não são rotas HTTP — CLI (`python -m app.services.backup.cli`) e scripts
(`scripts/backup.sh`/`restore.sh`). Ver `backend/BACKUP.md`.
