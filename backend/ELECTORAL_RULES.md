# Regras eleitorais

Este documento existe para deixar absolutamente claro, para quem for
avaliar ou confiar neste sistema, o que ele **é** e o que ele
**explicitamente não é** em relação à legislação eleitoral brasileira.

## O que este sistema não é

- **Não é o CONTA+JE** (o sistema oficial de prestação de contas do TSE).
- **Não envia dados a nenhum sistema do TSE**, nunca simula esse envio, e
  nenhum relatório ou exportação gerado aqui (`GET /reports/*/export`)
  afirma seguir o layout oficial exigido pela Justiça Eleitoral — todo
  arquivo exportado é rotulado, no próprio conteúdo, como "RELATÓRIO
  AUXILIAR" (ver `app/services/reports/export_service.py`).
- **Não decide** se um gasto é lícito, se um limite foi ultrapassado, ou
  se uma doação é permitida. Isso é uma decisão jurídica que cabe a um
  profissional habilitado (contador/advogado eleitoral da campanha), não
  a este software.

## O que este sistema é

Uma ferramenta de **organização e conferência** — ajuda a capturar,
armazenar, categorizar e conferir documentos e lançamentos financeiros de
uma campanha, para facilitar o trabalho de quem depois vai, de fato,
prestar contas pelos canais oficiais.

## Por que a base de regras começa vazia

`compliance_rules` (a tabela que guardaria limites, prazos e citações
legais reais) está **vazia por desenho** desde a V1 e continua vazia
depois de todas as fases de evolução deste projeto. Regra absoluta deste
projeto: **nenhum valor, limite, prazo ou dispositivo legal é inventado
ou presumido**. Cada linha cadastrada precisaria vir acompanhada de:

- `legal_source` — a norma oficial exata (ex.: "Resolução TSE nº
  23.610/2019"), nunca uma paráfrase ou um "geralmente é assim".
- `article`/`paragraph`/`inciso` — a localização exata do dispositivo.
- `effective_from` — a partir de quando essa versão da regra vale (ver
  "Versionamento" abaixo).
- confirmação de que a fonte é oficial, priorizando publicações do
  próprio TSE.

Qualquer regra sem essas informações confirmadas por uma pessoa
responsável fica marcada **REVISÃO HUMANA** e nunca é ativada
(`active=False`, o padrão de toda regra recém-cadastrada — ver
`app/services/compliance/rule_registry.py`).

## Como uma regra passaria a valer (arquitetura pronta, conteúdo vazio)

1. `POST /compliance/rules` (ADMIN) cria a primeira versão — sempre
   inativa.
2. Um validador correspondente ao `validation_logic` da regra é
   implementado em `app/services/compliance/engine.py::VALIDATORS`.
3. Só depois de revisão humana confirmando a fonte oficial, a regra é
   ativada via `POST /compliance/rules/{id}/activate`. O motor
   (`run_active_rules`) passa a executá-la automaticamente.

Nenhum desses três passos acontece sozinho — cada um é uma ação
deliberada de um ADMIN, nunca uma consequência automática de outra coisa.

## Versionamento: uma lei muda, o registro nunca "esquece" a anterior

Quando uma resolução do TSE muda um valor ou um texto, a regra antiga
**nunca é editada** — `POST /compliance/rules/{rule_id}/supersede` fecha
a versão atual (`effective_until`) e cria uma nova, ligada à anterior por
`supersedes_id`. Isso importa porque a regra que vale para julgar um
lançamento é a que estava em vigor **na data do lançamento**, não a de
hoje — `app/services/compliance/engine.py::get_active_rules` já escolhe a
versão certa por data, não a mais recente. `GET
/compliance/rules/{rule_id}/history` mostra a cadeia completa, para
auditoria.

## Responsabilidade

A responsabilidade pela exatidão de qualquer regra cadastrada é de quem a
cadastrou e confirmou a fonte — não deste software, que só garante que
nenhuma regra chega ao banco sem essas informações e que nenhuma regra
roda sem ativação humana explícita.
