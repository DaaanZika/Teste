# Regras eleitorais

Este diretório é o local previsto para as regras de conformidade eleitoral
(`compliance_rules`), mantidas como **dados**, não como código.

## Status na V1: vazio, propositalmente

Nenhuma regra, valor, limite, prazo ou artigo foi cadastrado nesta fase.
Por instrução explícita do escopo deste projeto, nada relacionado a regras
eleitorais pode ser inventado ou presumido. Toda regra cadastrada aqui
deve vir acompanhada de:

- `legal_source` — a norma oficial (ex.: "Resolução TSE nº 23.610/2019")
- `article` / `paragraph` / `inciso` — a localização exata do dispositivo
- confirmação de que a fonte é oficial (priorizar publicações do TSE)

Qualquer regra sem essas informações confirmadas deve ficar marcada como
`REVISÃO HUMANA` e **não** deve ser ativada (`active=False`) até validação
por uma pessoa responsável.

## Como uma regra passa a valer

1. A regra é inserida via `POST /compliance/rules` (ADMIN, ver
   `app/services/compliance/rule_registry.py::create_rule`) com
   `active=False`.
2. Um validador correspondente ao `validation_logic` da regra é
   implementado e registrado em
   `app/services/compliance/engine.py::VALIDATORS`.
3. Após revisão humana confirmando a fonte oficial, a regra é ativada via
   `POST /compliance/rules/{id}/activate` (`active=True`). O motor
   (`run_active_rules`) passa a executá-la automaticamente — nenhuma outra
   mudança de código é necessária.

## Versionamento: uma regra nunca é editada, só substituída

Cada linha em `compliance_rules` é uma **versão** de uma regra, válida
num intervalo de datas (`effective_from`/`effective_until`). Quando uma
resolução do TSE muda o texto, o limite ou a citação de uma regra
existente, isso nunca vira um `UPDATE` na linha antiga — é sempre
`POST /compliance/rules/{rule_id}/supersede` (ADMIN,
`rule_registry.supersede_rule`), que:

- fecha a versão atual definindo seu `effective_until` (o dia anterior ao
  início da nova versão);
- insere uma linha nova, com `supersedes_id` apontando para a versão
  anterior, sempre `active=False` até revisão humana explícita.

A versão antiga nunca é apagada nem tem seu conteúdo jurídico alterado —
isso é o que permite julgar corretamente um documento datado de antes da
mudança: `GET /compliance/rules/{rule_id}/history` mostra a cadeia
completa, mais antiga primeiro, e o motor
(`app/services/compliance/engine.py::get_active_rules`) escolhe a versão
cujo intervalo cobre a data do documento/lançamento sendo validado — não a
versão vigente hoje.

## Por que a arquitetura existe antes das regras

Separar regra (dado) de motor (código) permite atualizar/corrigir uma
regra — por exemplo, após uma nova resolução do TSE — sem reescrever o
backend.
