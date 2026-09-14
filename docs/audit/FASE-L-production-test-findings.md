# FASE L — achados da auditoria de cobertura de testes

Metodologia: conferência da suíte de testes existente contra a lista de
áreas da FASE L (login, permissões, upload, OCR, documentos, despesas,
receitas, cálculos, duplicidade, vínculo de documento, backup,
restauração, Google, Gmail, Drive, filas, relatórios, regras eleitorais),
seguida de um smoke test real com Playwright — backend e frontend rodando
de verdade, navegando pelas telas — não só a suíte automatizada.

## Gaps de cobertura fechados

- **Duplicidade lógica** (`app/services/documents/duplicate_detector.py::find_logical_duplicate`):
  só o caminho de hash de arquivo idêntico tinha teste; o caminho que
  compara data+valor+identificador (CNPJ/CPF/número do documento/nome do
  fornecedor) entre arquivos diferentes nunca foi exercitado. 13 testes
  novos em `backend/tests/test_duplicate_detector.py`.
- **`PUT /expenses/{id}`**: rota sem nenhum teste, incluindo a distinção
  de auditoria `LINK_DOCUMENT` (vincular um documento depois da criação)
  vs. `UPDATE` comum, que existia no código mas nunca era verificada.
  6 testes novos em `backend/tests/test_expense_update.py`.

## Bug real encontrado ao vivo (não só pela suíte automatizada)

Rodando o app inteiro (backend + frontend, servidores reais) e navegando
até `/relatorios` com Playwright, o card "Resumo financeiro" mostrava
**"Despesas sem documento: undefined"**.

Causa: `GET /reports/summary` (usado pela página Relatórios) nunca
incluía o campo `expenses_without_document` — só `GET /finance/summary`
(usado por Dashboard e Pendências) calculava esse número, numa query
separada dentro de `app/api/routes/finance.py`. O frontend sempre tratou
os dois endpoints como tendo o mesmo formato (`FinanceSummary`), então o
campo ausente virava `undefined` na tela.

Corrigido movendo o cálculo para dentro de
`app/services/reports/report_service.py::summary_report()` — fonte única
para os dois endpoints, sem duplicar a query. Reproduzido e reverificado
ao vivo no navegador antes e depois da correção (screenshot do "undefined"
e do valor correto depois). Teste de regressão:
`test_reports_summary_includes_expenses_without_document_like_finance_summary`
em `backend/tests/test_api_endpoints.py`, que compara os dois endpoints
diretamente para que uma divergência futura quebre a suíte, não só apareça
em produção.

## Por que isso importa além do bug em si

A suíte de testes (215 testes até este ponto) passava inteira com o bug
presente — nenhum teste chamava `/reports/summary` e conferia o campo
`expenses_without_document`, porque nenhum teste sabia que o frontend
esperava esse campo especificamente ali. Isso é o argumento para não parar
só na suíte automatizada numa fase de "testes de produção": um smoke test
real, navegando pelo app rodando de verdade, encontra uma classe de bug
diferente — contrato frontend/backend que diverge silenciosamente — que
testes unitários de cada lado, isolados, não capturam.
