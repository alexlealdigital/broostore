"""/api/validar_chave (ativação por dispositivo, validade, rate limit) e rotas de admin das chaves."""
from datetime import datetime, timedelta

import pytest

from broostore_api import extensions
from broostore_api.models import AtivacaoLicenca, ChaveLicenca
from broostore_api.services.licencas_chave import gerar_chave
from tests.helpers import add_chave_vendida, add_plano_chave, add_produto

ADMIN = {"X-Admin-Key": "segredo-admin-fake"}


@pytest.fixture(autouse=True)
def _admin_key(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET_KEY", "segredo-admin-fake")


@pytest.fixture
def chave(db_session):
    """Produto 5 com plano mensal de 1 dispositivo e uma chave vigente."""
    add_produto(5, nome="MeuApp Mensal", tipo="app")
    add_plano_chave(5, dias=30, rotulo="mensal", max_dispositivos=1)
    serial = gerar_chave()
    add_chave_vendida(5, serial, email="cli@example.test", expira_em=datetime.utcnow() + timedelta(days=10, hours=1))
    return serial


def validar(client, serial, produto=5, device="PC-1"):
    return client.post("/api/validar_chave", json={"chave_serial": serial, "product_id": produto, "device_id": device})


class TestValidarChave:
    def test_ativacao_ok_devolve_validade(self, client, chave):
        r = validar(client, chave)
        j = r.get_json()
        assert r.status_code == 200 and j["status"] == "valid" and j["codigo"] == "ok"
        lic = j["licenca"]
        assert lic["chave"] == chave and lic["cliente"] == "cli@example.test" and lic["plano"] == "mensal"
        assert lic["vitalicia"] is False and lic["dias_restantes"] == 11
        assert lic["dispositivos"] == {"usados": 1, "maximo": 1}

    def test_mesma_maquina_pode_validar_de_novo(self, client, chave):
        assert validar(client, chave).status_code == 200
        assert validar(client, chave).status_code == 200
        assert AtivacaoLicenca.query.count() == 1

    def test_outra_maquina_bate_no_limite(self, client, chave):
        validar(client, chave)
        r = validar(client, chave, device="PC-2")
        assert r.status_code == 403 and r.get_json()["codigo"] == "limite_dispositivos"

    def test_plano_com_dois_dispositivos(self, client, db_session):
        add_produto(6, tipo="app")
        add_plano_chave(6, dias=None, rotulo="vitalicia", max_dispositivos=2)
        serial = gerar_chave()
        add_chave_vendida(6, serial, expira_em=None, plano="vitalicia")
        assert validar(client, serial, 6, "A").status_code == 200
        assert validar(client, serial, 6, "B").status_code == 200
        r = validar(client, serial, 6, "C")
        assert r.status_code == 403 and r.get_json()["codigo"] == "limite_dispositivos"

    def test_vitalicia_nunca_expira(self, client, db_session):
        add_produto(6, tipo="app")
        serial = gerar_chave()
        add_chave_vendida(6, serial, expira_em=None, plano="vitalicia")
        j = validar(client, serial, 6).get_json()
        assert j["licenca"]["vitalicia"] is True and j["licenca"]["expira_em"] is None and j["licenca"]["dias_restantes"] is None

    def test_chave_expirada(self, client, db_session):
        add_produto(6, tipo="app")
        serial = gerar_chave()
        add_chave_vendida(6, serial, expira_em=datetime.utcnow() - timedelta(days=1))
        r = validar(client, serial, 6)
        assert r.status_code == 403 and r.get_json()["status"] == "expired" and r.get_json()["codigo"] == "expirada"

    def test_chave_revogada(self, client, db_session):
        add_produto(6, tipo="app")
        serial = gerar_chave()
        add_chave_vendida(6, serial, revogada=True)
        r = validar(client, serial, 6)
        assert r.status_code == 403 and r.get_json()["codigo"] == "revogada"

    def test_chave_nao_paga(self, client, db_session):
        add_produto(6, tipo="app")
        serial = gerar_chave()
        add_chave_vendida(6, serial, vendida=False)
        assert validar(client, serial, 6).get_json()["codigo"] == "nao_paga"

    def test_produto_diferente(self, client, chave):
        r = validar(client, chave, produto=99)
        assert r.status_code == 403 and r.get_json()["codigo"] == "produto_diferente"

    def test_chave_inexistente_com_formato_correto(self, client, chave):
        r = validar(client, gerar_chave())
        assert r.status_code == 404 and r.get_json()["codigo"] == "nao_encontrada"

    def test_digito_verificador_errado_nem_consulta_o_banco(self, client, chave, monkeypatch):
        errada = chave[:-1] + ("A" if chave[-1] != "A" else "B")
        monkeypatch.setattr(ChaveLicenca, "query", property(lambda self: (_ for _ in ()).throw(AssertionError("banco"))),
                            raising=False)
        r = validar(client, errada)
        assert r.status_code == 404 and r.get_json()["codigo"] == "formato_invalido"

    def test_chave_do_estoque_antigo_continua_valida(self, client, db_session):
        add_produto(3, tipo="game")
        add_chave_vendida(3, "KEY-AAA-1111-2222", plano=None, expira_em=None)
        r = validar(client, "KEY-AAA-1111-2222", 3)
        assert r.status_code == 200 and r.get_json()["licenca"]["vitalicia"] is True

    def test_aceita_minuscula_e_espacos(self, client, chave):
        assert validar(client, "  " + chave.lower() + " ").status_code == 200

    def test_campos_faltando(self, client):
        assert client.post("/api/validar_chave", json={"chave_serial": "X"}).get_json()["codigo"] == "incompleto"
        assert client.post("/api/validar_chave", json={"product_id": 1}).status_code == 400
        assert client.post("/api/validar_chave", data="nao e json").status_code == 400

    def test_erro_interno_nao_vaza_detalhes(self, client, chave, monkeypatch):
        def quebra(*a, **k):
            raise RuntimeError("segredo do banco")
        monkeypatch.setattr("broostore_api.blueprints.chaves.situacao_licenca", quebra)
        r = validar(client, chave)
        assert r.status_code == 500 and "segredo" not in r.get_data(as_text=True)

    def test_rate_limit_por_ip_e_falha_aberta(self, client, chave, world):
        class Conn:
            def __init__(self):
                self.n = 0
                self.expirou = []

            def incr(self, k):
                self.n += 1
                return self.n

            def expire(self, k, s):
                self.expirou.append((k, s))

        conn = Conn()
        world.queue.connection = conn
        for _ in range(30):
            assert validar(client, chave).status_code == 200
        r = validar(client, chave)
        assert r.status_code == 429 and r.get_json()["codigo"] == "rate_limited"
        assert conn.expirou == [("rl:validar_chave:127.0.0.1", 60)]

        class Quebrado:
            def incr(self, k):
                raise ConnectionError("redis fora")
        world.queue.connection = Quebrado()
        assert validar(client, chave).status_code == 200           # Redis fora do ar: não bloqueia

    def test_sem_redis_nao_bloqueia(self, client, chave):
        extensions.set_queue(None)                                  # get_queue() falha (conftest bloqueia o Redis)
        assert validar(client, chave).status_code == 200


class TestAdmin:
    def test_sem_chave_de_admin_e_negado(self, client, chave):
        assert client.get("/api/admin/chaves").status_code == 401
        assert client.get("/api/admin/chaves", headers={"X-Admin-Key": "errada"}).status_code == 401
        assert client.post("/api/admin/chaves/emitir", json={}).status_code == 401
        assert client.post("/api/admin/chaves/revogar", json={}).status_code == 401
        assert client.post("/api/admin/chaves/resetar-dispositivos", json={}).status_code == 401

    def test_sem_variavel_configurada_ninguem_entra(self, client, monkeypatch):
        monkeypatch.delenv("ADMIN_SECRET_KEY")
        assert client.get("/api/admin/chaves", headers={"X-Admin-Key": ""}).status_code == 401
        assert client.get("/api/admin/chaves", headers=ADMIN).status_code == 401

    def test_emitir_e_validar_ponta_a_ponta(self, client, db_session):
        add_produto(5, tipo="app")
        add_plano_chave(5, dias=30, rotulo="mensal")
        r = client.post("/api/admin/chaves/emitir", headers=ADMIN, json={"produto_id": 5, "email": "Teste@Example.test"})
        assert r.status_code == 201
        nova = r.get_json()["chave"]
        assert nova["cliente_email"] == "teste@example.test" and nova["plano"] == "mensal" and nova["vendida"] is True
        assert validar(client, nova["chave"]).get_json()["status"] == "valid"

    def test_emitir_vitalicia_com_dias_zero(self, client, db_session):
        add_produto(5, tipo="app")
        add_plano_chave(5, dias=30)
        r = client.post("/api/admin/chaves/emitir", headers=ADMIN, json={"produto_id": 5, "email": "a@x.test", "dias": 0})
        assert r.get_json()["chave"]["expira_em"] is None

    def test_emitir_valida_os_dados(self, client, db_session):
        add_produto(5, tipo="app")
        assert client.post("/api/admin/chaves/emitir", headers=ADMIN, json={"produto_id": "x", "email": "a@x.test"}).status_code == 400
        assert client.post("/api/admin/chaves/emitir", headers=ADMIN, json={"produto_id": 5, "email": "sem-arroba"}).status_code == 400
        assert client.post("/api/admin/chaves/emitir", headers=ADMIN, json={"produto_id": 5, "email": "a@x.test"}).status_code == 404
        add_plano_chave(5)
        assert client.post("/api/admin/chaves/emitir", headers=ADMIN,
                           json={"produto_id": 5, "email": "a@x.test", "dias": "abc"}).status_code == 400

    def test_revogar_e_restaurar(self, client, chave):
        r = client.post("/api/admin/chaves/revogar", headers=ADMIN, json={"chave": chave.lower()})
        assert r.get_json()["chave"]["revogada"] is True
        assert validar(client, chave).get_json()["codigo"] == "revogada"
        client.post("/api/admin/chaves/revogar", headers=ADMIN, json={"chave": chave, "revogada": False})
        assert validar(client, chave).status_code == 200
        assert client.post("/api/admin/chaves/revogar", headers=ADMIN, json={"chave": "NAO-EXISTE"}).status_code == 404

    def test_resetar_dispositivos_libera_troca_de_pc(self, client, chave):
        validar(client, chave, device="PC-1")
        assert validar(client, chave, device="PC-2").status_code == 403
        r = client.post("/api/admin/chaves/resetar-dispositivos", headers=ADMIN, json={"chave": chave})
        assert r.get_json()["dispositivos_liberados"] == 1
        assert validar(client, chave, device="PC-2").status_code == 200
        assert client.post("/api/admin/chaves/resetar-dispositivos", headers=ADMIN, json={"chave": "NAO"}).status_code == 404

    def test_listar_por_email_produto_e_chave(self, client, chave):
        add_chave_vendida(5, gerar_chave(), email="outro@example.test")
        add_chave_vendida(5, gerar_chave(), email="naovendida@example.test", vendida=False)
        todas = client.get("/api/admin/chaves", headers=ADMIN).get_json()
        assert len(todas) == 2                                       # não lista chave não vendida
        so_cli = client.get("/api/admin/chaves?email=CLI@example.test", headers=ADMIN).get_json()
        assert [c["chave"] for c in so_cli] == [chave]
        assert len(client.get("/api/admin/chaves?produto_id=5", headers=ADMIN).get_json()) == 2
        assert [c["chave"] for c in client.get(f"/api/admin/chaves?chave={chave.lower()}", headers=ADMIN).get_json()] == [chave]
