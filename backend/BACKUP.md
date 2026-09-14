# Backup e restauração

O backup cobre as duas coisas que realmente importam para recuperar o
sistema: o **banco de dados** (todas as tabelas) e os **documentos
originais/processados** em `storage/originals` e `storage/processed`.
`storage/temporary` nunca é incluído — é transitório por desenho (arquivos
lá são apagados depois de usados, ver
`app/integrations/storage_adapter.py`), e incluí-lo só restauraria lixo.

Implementação: `app/services/backup/backup_service.py` (Postgres via
`pg_dump`/`pg_restore` — os binários já estão na imagem Docker, ver
`Dockerfile`; SQLite via `sqlite3.Connection.backup()` da biblioteca
padrão, sem depender do executável `sqlite3` estar instalado).

## Como fazer backup

```bash
# Local (fora do Docker), a partir da raiz do repositório:
./scripts/backup.sh

# Dentro do container (Docker Compose):
docker compose exec backend python -m app.services.backup.cli backup
```

Gera `backend/backups/campanhas-backup-<timestamp>.tar.gz`, contendo:

- o dump do banco (`database.dump` no Postgres, `database.sqlite3` no
  SQLite);
- `storage.tar.gz` com `originals/` e `processed/`;
- `manifest.json` com a contagem de linhas de cada tabela no momento do
  backup — usado pela restauração para se auto-verificar (ver abaixo).

`backend/backups/` nunca é commitado (contém dados reais de campanha —
ver `.gitignore`).

## Como restaurar

```bash
./scripts/restore.sh backend/backups/campanhas-backup-20260101-000000.tar.gz

# ou, dentro do container:
docker compose exec backend python -m app.services.backup.cli restore <caminho>
```

A restauração:

1. Extrai o backup para um diretório temporário.
2. Restaura o banco (`pg_restore --clean --if-exists` no Postgres —
   recria os objetos sem exigir um banco vazio antes; cópia direta no
   SQLite).
3. Restaura `storage/originals` e `storage/processed`.
4. **Verifica de verdade**: conta as linhas de cada tabela no banco
   recém-restaurado e compara com o que o `manifest.json` do backup
   registrou. Se não bater, o comando termina com código de saída `2` e
   imprime os dois valores — nunca reporta sucesso silenciosamente diante
   de uma restauração incompleta.

## Por que isso conta como "testado", não só "o arquivo foi criado"

`tests/test_backup_restore.py` não confia no caminho de backup sozinho —
para cada cenário (SQLite e um Postgres real), o teste:

1. Cria linhas reais (`Campaign`, `Document`) num banco de verdade.
2. Roda o backup de verdade.
3. **Destrói os dados de verdade** — no Postgres, `DROP SCHEMA public
   CASCADE` (não apenas simula uma falha); no SQLite, apaga o arquivo do
   banco.
4. Roda a restauração de verdade.
5. Consulta o banco restaurado e confirma que a linha específica voltou
   com o valor exato — não só que `verified=True`.

Um teste adicional (`test_sqlite_restore_flags_mismatch_when_manifest_is_tampered`)
adultera o manifesto dentro de um backup de propósito e confirma que a
restauração realmente detecta a divergência (`verified=False`), provando
que a verificação não é uma constante disfarçada.

Isso foi executado contra um Postgres real neste ambiente, não simulado —
e revelou um bug real na primeira tentativa: `pg_dump`/`pg_restore`
recebiam a URL no formato do SQLAlchemy (`postgresql+psycopg://...`), que
o libpq não reconhece, e falhavam tentando conectar como o usuário `root`
do sistema operacional em vez de usar as credenciais da URL. Corrigido
convertendo para o formato `postgresql://...` antes de invocar os
binários (`_libpq_url` em `backup_service.py`).

## Agendamento (opcional)

Nenhum serviço de cron roda dentro do Docker Compose por padrão — isso
fica a critério de quem opera o servidor. Exemplo de `crontab` para um
backup diário às 3h:

```cron
0 3 * * * cd /caminho/do/repositorio && ./scripts/backup.sh >> /var/log/campanhas-backup.log 2>&1
```

Para reter só os últimos N backups, um `find backend/backups -name
'campanhas-backup-*.tar.gz' -mtime +30 -delete` (30 dias, por exemplo)
pode ser adicionado à mesma linha de cron ou a uma separada.

## Limitações conhecidas

- O backup não é atômico em relação a escritas concorrentes: o dump do
  banco e o `tar` de `storage/` são feitos em sequência, não numa
  transação única — um documento gravado entre os dois passos pode ficar
  de fora do backup daquela execução (aparecerá no próximo).
- `pg_dump`/`pg_restore` exigem os binários do cliente Postgres
  instalados (já estão na imagem Docker deste projeto).
