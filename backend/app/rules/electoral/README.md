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

1. A regra é inserida na tabela `compliance_rules` (via migration de dados
   ou endpoint administrativo futuro) com `active=False`.
2. Um validador correspondente ao `validation_logic` da regra é
   implementado e registrado em
   `app/services/compliance/engine.py::VALIDATORS`.
3. Após revisão humana confirmando a fonte oficial, a regra é ativada
   (`active=True`). O motor (`run_active_rules`) passa a executá-la
   automaticamente — nenhuma outra mudança de código é necessária.

## Por que a arquitetura existe antes das regras

Separar regra (dado) de motor (código) permite atualizar/corrigir uma
regra — por exemplo, após uma nova resolução do TSE — sem reescrever o
backend.
