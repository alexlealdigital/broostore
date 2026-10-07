# Snapshot do código ORIGINAL (somente leitura)

`app.py`, `worker.py`, `Dashboard_api.py` e `notificar_expiracao.py` são cópias **sem nenhuma alteração** dos arquivos do
repositório antigo (broorread). Servem apenas de referência para os testes de comparação
(`tests/golden/`): os testes copiam estes arquivos para uma pasta temporária, aplicam um único
patch (removem o `connect_args={"prepare_threshold": None}`, que só funciona no PostgreSQL) e
rodam as mesmas requisições contra o código original e contra a API nova.

Não edite estes arquivos. Podem ser apagados quando a migração estiver concluída e estável
(junto com `tests/golden/`).
