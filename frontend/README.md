# Frontend V1 — Organização Financeira e Documental de Campanhas Eleitorais

Interface web (React + TypeScript + Vite) que consome a API do
`backend/` já existente neste repositório. Roda inteiramente local
nesta fase — sem Google OAuth, Gmail, Google Drive ou qualquer serviço
de nuvem (ver `SettingsPage`).

## Requisitos

- Node.js 20+
- O backend rodando localmente (ver `backend/README.md`). Por padrão a API
  é esperada em `http://127.0.0.1:8000`.

## Instalação

```bash
cd frontend
npm install
cp .env.example .env   # ajuste VITE_API_BASE_URL se necessário
```

## Execução

```bash
npm run dev
```

Abra `http://localhost:5173`. O backend precisa estar rodando (`uvicorn
app.main:app --reload` dentro de `backend/`) para qualquer tela funcionar —
este frontend nunca usa dados fictícios; toda informação vem da API.

## Build de produção

```bash
npm run build
npm run preview
```

## Testes

```bash
npm run test:run
```

Usa Vitest + Testing Library. Os testes mockam a camada `src/api/*`
(nunca fazem chamadas reais de rede) e cobrem: o fluxo de "Adicionar
Gasto" em modo rápido (incluindo o exemplo do PROMPT 2, `"R$ 850 gráfica
ABC"`), validação do formulário completo de despesa, o pipeline de
upload/processamento/revisão de documentos (incluindo o caso de
duplicidade exata de arquivo), os estados de loading/sucesso/erro do
dashboard, filtro de busca na lista de despesas, e a navegação mobile.

## Arquitetura

```text
frontend/
├── src/
│   ├── api/              # Única camada que fala com o backend (api.documents, api.expenses, ...)
│   ├── components/
│   │   ├── ui/            # Componentes genéricos: Button, Card, Modal, Input, Table, Badge, Alert, estados...
│   │   ├── layout/         # Sidebar, Topbar, navegação mobile, layout principal
│   │   ├── documents/      # Upload (drag&drop + câmera), fila de processamento, revisão de OCR
│   │   ├── expenses/        # Formulário completo e modo rápido de despesa
│   │   ├── revenues/        # Formulário de receita
│   │   └── StatusBadges.tsx # Tradução dos enums do backend para rótulos em português
│   ├── pages/              # Uma página por rota (Dashboard, Documentos, Despesas, ...)
│   ├── state/              # Contextos leves: modal global de "Adicionar Gasto" e toasts
│   ├── lib/                # http client (axios), formatação, normalização de erros, query client
│   └── types/api.ts        # Tipos espelhando exatamente os schemas Pydantic do backend
```

### Decisões de arquitetura

- **Estado de servidor via TanStack Query, estado local via `useState`.**
  Nenhuma biblioteca de estado global (Redux etc.) — desnecessária para o
  tamanho desta V1.
- **Nenhum cálculo financeiro acontece no frontend.** Toda soma, saldo e
  percentual vem pronto do backend (`/finance/*`, `/reports/*`); os
  arquivos em `src/lib/format.ts` só formatam para exibição.
- **Nenhum dado é inventado.** Toda lista vazia mostra um estado vazio
  explícito; toda falha de rede mostra uma mensagem em português com
  opção de tentar novamente — nunca uma tela em branco, nunca um valor
  fictício, nunca um stack trace.
- **Regras eleitorais nunca são recriadas aqui.** A tela de Conformidade
  só exibe o que a API retorna; nesta versão o backend não tem nenhuma
  regra cadastrada (ver `backend/app/rules/electoral/README.md`), e a
  tela deixa isso explícito ao usuário em vez de simular uma validação.
- **Duas telas convergem no mesmo formulário.** O modal global "+
  Adicionar Gasto" (acessível de qualquer página) e a página
  `/adicionar-gasto` usam exatamente os mesmos componentes
  (`QuickAddForm`, `ExpenseForm`), evitando duas implementações do
  mesmo fluxo.
- **Correções ao backend feitas durante esta etapa** (documentadas nos
  commits): endpoint para servir o arquivo original (`GET
  /documents/{id}/file`, necessário para o visualizador de documento),
  filtro de período/dia em `/finance/totals/period` e `/finance/summary`
  /`/finance/balance` (necessário para os filtros "hoje/7 dias/30
  dias/personalizado"), e parâmetro `type` em `/finance/totals/category`
  (necessário para alternar entre despesas e receitas na tela
  Financeiro).

## Fluxo principal implementado

```text
Usuário → Documentos → arrasta ou fotografa um recibo
        → upload (POST /documents/upload)
        → processamento (POST /documents/{id}/process — OCR + extração)
        → tela de revisão com confiança do OCR e campos editáveis
        → confirmação (PATCH /documents/{id}/correct) → documento validado
```

```text
Usuário → botão "+ Adicionar Gasto" (sempre visível)
        → modo rápido: "R$ 850 gráfica ABC"
        → POST /expenses/quick (o backend interpreta o texto)
        → resultado exibido exatamente como o backend retornou
        → despesa criada, com "documento pendente" se nenhum foi anexado
```

## Segurança

Nenhuma senha, chave de API ou token é armazenado neste frontend. A URL
do backend é a única configuração (`VITE_API_BASE_URL`). Autenticação
real (Google OAuth ou outra) ainda não existe — ver `SettingsPage` e
`backend/app/integrations/future/`.
