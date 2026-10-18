"""Chaves de licença dos apps: validação/ativação por dispositivo e rotas de administração."""
import hmac
import logging
from datetime import datetime

from flask import Blueprint, jsonify, request

from ..config import get_settings
from ..extensions import db, get_queue
from ..models import AtivacaoLicenca, ChaveLicenca, PlanoChave
from ..services.licencas_chave import (calcular_expiracao, formato_valido, gerar_chave,
                                       normalizar_chave, situacao_licenca, tem_formato_novo)

logger = logging.getLogger("broostore")

bp = Blueprint("chaves", __name__)


# ---------------------------------------------------------------------------
# Rate limit simples por IP (Redis). Se o Redis estiver fora do ar, NÃO bloqueia
# ninguém (falha aberta) — melhor do que derrubar a ativação.
# ---------------------------------------------------------------------------
def _ip_cliente():
    """IP real do cliente (o Render fica atrás de proxy)."""
    xff = request.headers.get("X-Forwarded-For", "")
    return (xff.split(",")[0].strip() if xff else request.remote_addr) or "?"


def _limite_excedido(escopo, maximo, janela_s=60):
    try:
        conn = getattr(get_queue(), "connection", None)
        if conn is None:
            return False
        chave = f"rl:{escopo}:{_ip_cliente()}"
        n = conn.incr(chave)
        if n == 1:
            conn.expire(chave, janela_s)
        return n > maximo
    except Exception:
        return False


def _resp_chave(status, codigo, mensagem, http, **extra):
    corpo = {"status": status, "codigo": codigo, "message": mensagem}
    corpo.update(extra)
    return jsonify(corpo), http


@bp.route("/api/validar_chave", methods=["POST"])
def validar_chave():
    """Valida e ativa a chave de um app. Chamada pelo app ao digitar a chave E a cada
    abertura (é assim que o vencimento é aplicado).

    Body JSON:
      chave_serial  (obrigatório)  ex.: BROO-7K2M-X9QP-4HD3-R8WN
      product_id    (obrigatório)  id do produto na BrooStore
      device_id     (recomendado)  identificador estável da máquina; sem ele todas as
                                   máquinas contam como uma só.
    """
    if _limite_excedido("validar_chave", maximo=30):
        return _resp_chave("error", "rate_limited", "Muitas tentativas. Aguarde um minuto.", 429)

    dados = request.get_json(silent=True) or {}
    chave_serial = normalizar_chave(dados.get("chave_serial"))
    device_id = str(dados.get("device_id") or "").strip()[:128] or "padrao"

    try:
        product_id = int(dados.get("product_id"))
    except (TypeError, ValueError):
        product_id = None

    if not chave_serial or product_id is None:
        return _resp_chave("error", "incompleto", "Chave serial e ID do produto incompletos.", 400)

    # Chave do formato novo com dígito verificador errado = erro de digitação.
    if tem_formato_novo(chave_serial) and not formato_valido(chave_serial):
        return _resp_chave("invalid", "formato_invalido",
                           "Chave inválida. Confira se digitou corretamente.", 404)

    try:
        chave = ChaveLicenca.query.filter_by(chave_serial=chave_serial).with_for_update().first()

        if not chave:
            return _resp_chave("invalid", "nao_encontrada", "Chave não encontrada.", 404)
        if chave.produto_id != product_id:
            return _resp_chave("invalid", "produto_diferente",
                               "Chave válida, mas para um produto diferente.", 403)
        if not chave.vendida:
            return _resp_chave("invalid", "nao_paga",
                               "Pagamento pendente ou chave não ativada.", 403)
        if chave.revogada:
            return _resp_chave("invalid", "revogada", "Esta chave foi cancelada.", 403)

        agora = datetime.utcnow()
        vigente, dias_restantes = situacao_licenca(chave.expira_em, agora)
        if not vigente:
            return _resp_chave("expired", "expirada",
                               "Licença expirada. Renove para continuar usando.", 403,
                               expira_em=chave.expira_em.isoformat())

        plano = db.session.get(PlanoChave, chave.produto_id)
        max_disp = plano.max_dispositivos if plano else 1

        ativacao = AtivacaoLicenca.query.filter_by(chave_id=chave.id, device_id=device_id).first()
        if ativacao:
            ativacao.ultimo_uso_em = agora  # mesma máquina voltando: sempre permitido
        else:
            usados = AtivacaoLicenca.query.filter_by(chave_id=chave.id).count()
            if usados >= max_disp:
                return _resp_chave("invalid", "limite_dispositivos",
                                   f"Esta chave já está ativa em {usados} dispositivo(s) — o limite do plano é {max_disp}. "
                                   "Fale com o suporte para trocar de computador.", 403)
            db.session.add(AtivacaoLicenca(chave_id=chave.id, device_id=device_id,
                                           ativada_em=agora, ultimo_uso_em=agora))
            if not chave.ativada_em:
                chave.ativada_em = agora
            chave.ativa_no_app = True

        db.session.commit()
        total_disp = AtivacaoLicenca.query.filter_by(chave_id=chave.id).count()

        return jsonify({
            "status": "valid",
            "codigo": "ok",
            "message": "Chave de licença ativa.",
            "licenca": {
                "chave": chave_serial,
                "cliente": chave.cliente_email,
                "data_ativacao": (chave.ativada_em or chave.vendida_em or agora).isoformat(),
                "status_uso": "Ativa",
                "plano": chave.plano,
                "vitalicia": chave.expira_em is None,
                "expira_em": chave.expira_em.isoformat() if chave.expira_em else None,
                "dias_restantes": dias_restantes,
                "dispositivos": {"usados": total_disp, "maximo": max_disp},
            }
        }), 200

    except Exception:
        db.session.rollback()
        logger.exception("ERRO CRÍTICO (VALIDAR CHAVE)")
        return _resp_chave("error", "erro_interno", "Erro interno na validação. Tente novamente.", 500)


# ---------------------------------------------------------------------------
# Admin das chaves (header X-Admin-Key == ADMIN_SECRET_KEY)
# ---------------------------------------------------------------------------
def _admin_ok():
    """Comparação em tempo constante. Sem ADMIN_SECRET_KEY configurada, ninguém entra."""
    segredo = get_settings().admin_secret_key
    enviado = request.headers.get("X-Admin-Key", "")
    return bool(segredo and enviado and hmac.compare_digest(enviado, segredo))


def _nao_autorizado():
    return jsonify({"status": "error", "message": "Não autorizado"}), 401


def _chave_to_dict(c):
    return {
        "id": c.id, "chave": c.chave_serial, "produto_id": c.produto_id,
        "cliente_email": c.cliente_email, "plano": c.plano, "vendida": c.vendida,
        "revogada": c.revogada,
        "expira_em": c.expira_em.isoformat() if c.expira_em else None,
        "ativada_em": c.ativada_em.isoformat() if c.ativada_em else None,
    }


@bp.route("/api/admin/chaves", methods=["GET"])
def admin_listar_chaves():
    """Lista chaves vendidas. Filtros opcionais: ?email=...&produto_id=...&chave=..."""
    if not _admin_ok():
        return _nao_autorizado()
    q = ChaveLicenca.query.filter(ChaveLicenca.vendida == True)  # noqa: E712
    email = (request.args.get("email") or "").strip().lower()
    if email:
        q = q.filter(ChaveLicenca.cliente_email == email)
    if request.args.get("produto_id", type=int):
        q = q.filter(ChaveLicenca.produto_id == request.args.get("produto_id", type=int))
    if request.args.get("chave"):
        q = q.filter(ChaveLicenca.chave_serial == normalizar_chave(request.args.get("chave")))
    return jsonify([_chave_to_dict(c) for c in q.order_by(ChaveLicenca.id.desc()).limit(50).all()]), 200


@bp.route("/api/admin/chaves/emitir", methods=["POST"])
def admin_emitir_chave():
    """Emite uma chave manualmente, sem pagamento (teste, cortesia, suporte).
    Body: {"produto_id": 12, "email": "cliente@x.com", "dias": 30}  (dias opcional:
    se omitido usa o do plano do produto; 0 = vitalícia)."""
    if not _admin_ok():
        return _nao_autorizado()
    dados = request.get_json(silent=True) or {}
    try:
        produto_id = int(dados.get("produto_id"))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "produto_id inválido"}), 400
    email = (dados.get("email") or "").strip().lower()
    if not email or "@" not in email:
        return jsonify({"status": "error", "message": "email inválido"}), 400
    plano = db.session.get(PlanoChave, produto_id)
    if not plano:
        return jsonify({"status": "error", "message": "Produto sem plano em planos_chave"}), 404
    try:
        dias = plano.dias if dados.get("dias") is None else int(dados.get("dias"))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "dias inválido"}), 400
    try:
        agora = datetime.utcnow()
        nova = ChaveLicenca(
            chave_serial=gerar_chave(plano.prefixo), produto_id=produto_id,
            vendida=True, vendida_em=agora, cliente_email=email,
            plano=plano.rotulo, expira_em=calcular_expiracao(dias, None, agora), revogada=False,
        )
        db.session.add(nova)
        db.session.commit()
        return jsonify({"status": "success", "chave": _chave_to_dict(nova)}), 201
    except Exception:
        db.session.rollback()
        logger.exception("ERRO (ADMIN EMITIR CHAVE)")
        return jsonify({"status": "error", "message": "Falha ao emitir chave"}), 500


@bp.route("/api/admin/chaves/revogar", methods=["POST"])
def admin_revogar_chave():
    """Revoga (ou restaura) uma chave — reembolso, fraude. Body: {"chave": "...", "revogada": true}."""
    if not _admin_ok():
        return _nao_autorizado()
    dados = request.get_json(silent=True) or {}
    chave = ChaveLicenca.query.filter_by(chave_serial=normalizar_chave(dados.get("chave"))).first()
    if not chave:
        return jsonify({"status": "error", "message": "Chave não encontrada"}), 404
    try:
        chave.revogada = bool(dados.get("revogada", True))
        db.session.commit()
        return jsonify({"status": "success", "chave": _chave_to_dict(chave)}), 200
    except Exception:
        db.session.rollback()
        logger.exception("ERRO (ADMIN REVOGAR CHAVE)")
        return jsonify({"status": "error", "message": "Falha ao atualizar chave"}), 500


@bp.route("/api/admin/chaves/resetar-dispositivos", methods=["POST"])
def admin_resetar_dispositivos():
    """Libera todos os dispositivos de uma chave (cliente trocou de computador).
    Body: {"chave": "BROO-..."}."""
    if not _admin_ok():
        return _nao_autorizado()
    dados = request.get_json(silent=True) or {}
    chave = ChaveLicenca.query.filter_by(chave_serial=normalizar_chave(dados.get("chave"))).first()
    if not chave:
        return jsonify({"status": "error", "message": "Chave não encontrada"}), 404
    try:
        removidos = AtivacaoLicenca.query.filter_by(chave_id=chave.id).delete()
        chave.ativa_no_app = False
        db.session.commit()
        return jsonify({"status": "success", "dispositivos_liberados": removidos}), 200
    except Exception:
        db.session.rollback()
        logger.exception("ERRO (ADMIN RESETAR DISPOSITIVOS)")
        return jsonify({"status": "error", "message": "Falha ao liberar dispositivos"}), 500
