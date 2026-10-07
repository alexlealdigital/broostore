"""Compressão de PDF (produto 99) e de imagens (produto 98): validação de código + compressão."""
import logging
import os
import os.path as osp
import tempfile

from flask import Blueprint, jsonify, request, send_file
from sqlalchemy import or_

from ..extensions import db
from ..models import Cobranca

logger = logging.getLogger("broostore")

bp = Blueprint("compressao", __name__)

FORMATOS_ACEITOS_IMAGEM = {"image/jpeg", "image/png", "image/webp"}
EXTENSOES_ACEITAS_IMAGEM = {".jpg", ".jpeg", ".png", ".webp"}


def _cobranca_paga(codigo):
    return Cobranca.query.filter(
        Cobranca.external_reference == codigo,
        or_(Cobranca.status == "approved", Cobranca.status == "delivered")
    ).first()


# ═══════════════════════════════════════════════════════════
# COMPRESSOR DE PDF — validação de código + compressão
# ═══════════════════════════════════════════════════════════
@bp.route("/api/validar-codigo-compressao", methods=["POST"])
def validar_codigo_compressao():
    """Verifica se o external_reference corresponde a um pagamento
    aprovado do produto 99 (compressão de PDF)."""
    try:
        dados = request.get_json()
        codigo = (dados.get("codigo") or "").strip()
        if not codigo:
            return jsonify({"status": "erro", "message": "Código não informado."}), 400

        cobranca = _cobranca_paga(codigo)

        if not cobranca:
            return jsonify({"status": "erro",
                            "message": "Código inválido ou pagamento ainda não confirmado."}), 404

        # Garante que é realmente uma cobrança de compressão de PDF
        if cobranca.product_id not in [99, None]:
            return jsonify({"status": "erro",
                            "message": "Código inválido para este serviço."}), 400

        # Verifica se o código já foi usado para uma compressão
        if getattr(cobranca, "compressao_usada", False):
            return jsonify({"status": "erro",
                            "message": "Este código já foi utilizado."}), 400

        return jsonify({"status": "ok", "message": "Código válido."}), 200

    except Exception as e:
        logger.error(f"ERRO validar_codigo_compressao: {e}")
        return jsonify({"status": "erro", "message": str(e)}), 500


@bp.route("/api/comprimir-pdf", methods=["POST", "OPTIONS"])
def comprimir_pdf():
    """Recebe o PDF e o código de liberação, comprime e devolve o arquivo."""
    try:
        codigo = (request.form.get("codigo") or "").strip()
        pdf = request.files.get("pdf")

        if not codigo:
            return jsonify({"status": "erro", "message": "Código não informado."}), 400
        if not pdf:
            return jsonify({"status": "erro", "message": "Nenhum arquivo enviado."}), 400

        # Valida código novamente (segurança)
        cobranca = _cobranca_paga(codigo)

        if not cobranca or cobranca.product_id not in [99, None]:
            return jsonify({"status": "erro",
                            "message": "Código inválido ou pagamento não confirmado."}), 403

        if getattr(cobranca, "compressao_usada", False):
            return jsonify({"status": "erro",
                            "message": "Este código já foi utilizado."}), 400

        # Salva o PDF recebido em arquivo temporário
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_in:
            pdf.save(tmp_in.name)
            tmp_in_path = tmp_in.name

        tmp_out_path = tmp_in_path.replace(".pdf", "_out.pdf")

        try:
            import pikepdf

            # Usa pikepdf — leve e eficiente no plano free (512MB RAM)
            logger.info("[COMPRIMIR] Comprimindo com pikepdf...")
            with pikepdf.open(tmp_in_path) as pdf_doc:
                pdf_doc.save(
                    tmp_out_path,
                    compress_streams=True,
                    object_stream_mode=pikepdf.ObjectStreamMode.generate,
                    linearize=True
                )
            if not os.path.exists(tmp_out_path):
                raise Exception("Falha ao gerar o arquivo comprimido.")
            logger.info("[COMPRIMIR] ✅ Concluído.")

            # Marca código como usado
            try:
                cobranca.compressao_usada = True
                db.session.commit()
            except Exception:
                pass  # campo pode não existir ainda; não bloqueia a entrega

            # Retorna o PDF comprimido
            return send_file(
                tmp_out_path,
                mimetype="application/pdf",
                as_attachment=True,
                download_name="comprimido.pdf"
            )

        finally:
            for p in [tmp_in_path]:
                try:
                    os.unlink(p)
                except Exception:
                    pass

    except Exception as e:
        logger.error(f"ERRO comprimir_pdf: {e}")
        return jsonify({"status": "erro", "message": str(e)}), 500


# ═══════════════════════════════════════════════════════════
# COMPRESSOR DE IMAGENS — validação de código + compressão
# ═══════════════════════════════════════════════════════════
def _comprimir_imagem_bytes(file_storage, qualidade=82, max_px=1920, alvo_kb=900):
    """Redimensiona e comprime uma imagem para JPEG, respeitando alvo_kb."""
    import io

    from PIL import Image

    img = Image.open(file_storage)

    # Converte modos especiais para RGB (ex: RGBA, P)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Redimensiona mantendo proporção se maior que max_px
    img.thumbnail((max_px, max_px), Image.LANCZOS)

    # Tenta qualidade desejada; reduz até ficar abaixo do alvo
    for q in [qualidade, 75, 65, 55]:
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=q, optimize=True, progressive=True)
        tamanho_kb = buf.tell() / 1024
        if tamanho_kb <= alvo_kb:
            break

    buf.seek(0)
    return buf, tamanho_kb


@bp.route("/api/validar-codigo-compressao-imagem", methods=["POST"])
def validar_codigo_compressao_imagem():
    """Verifica se o external_reference é válido para o serviço de compressão de imagens (produto 98)."""
    try:
        dados = request.get_json()
        codigo = (dados.get("codigo") or "").strip()
        if not codigo:
            return jsonify({"status": "erro", "message": "Código não informado."}), 400

        cobranca = _cobranca_paga(codigo)

        if not cobranca:
            return jsonify({"status": "erro",
                            "message": "Código inválido ou pagamento ainda não confirmado."}), 404

        if cobranca.product_id not in [98, None]:
            return jsonify({"status": "erro",
                            "message": "Código inválido para este serviço."}), 400

        if getattr(cobranca, "compressao_img_usada", False):
            return jsonify({"status": "erro",
                            "message": "Este código já foi utilizado."}), 400

        return jsonify({"status": "ok", "message": "Código válido."}), 200

    except Exception as e:
        logger.error(f"ERRO validar_codigo_compressao_imagem: {e}")
        return jsonify({"status": "erro", "message": str(e)}), 500


@bp.route("/api/comprimir-imagem", methods=["POST", "OPTIONS"])
def comprimir_imagem():
    """Recebe uma imagem (JPEG/PNG/WebP) e o código de liberação,
    comprime para JPEG ≤ 900 KB e devolve o arquivo."""
    try:
        codigo = (request.form.get("codigo") or "").strip()
        imagem = request.files.get("imagem")

        if not codigo:
            return jsonify({"status": "erro", "message": "Código não informado."}), 400
        if not imagem:
            return jsonify({"status": "erro", "message": "Nenhuma imagem enviada."}), 400

        # Valida tipo de arquivo
        ext = osp.splitext(imagem.filename or "")[1].lower()
        if imagem.mimetype not in FORMATOS_ACEITOS_IMAGEM and ext not in EXTENSOES_ACEITAS_IMAGEM:
            return jsonify({"status": "erro",
                            "message": "Formato não suportado. Use JPEG, PNG ou WebP."}), 400

        # Valida código (segurança)
        cobranca = _cobranca_paga(codigo)

        if not cobranca or cobranca.product_id not in [98, None]:
            return jsonify({"status": "erro",
                            "message": "Código inválido ou pagamento não confirmado."}), 403

        if getattr(cobranca, "compressao_img_usada", False):
            return jsonify({"status": "erro",
                            "message": "Este código já foi utilizado."}), 400

        # Comprime
        logger.info(f"[COMPRIMIR-IMG] Comprimindo '{imagem.filename}'...")
        buf, tamanho_kb = _comprimir_imagem_bytes(imagem)
        logger.info(f"[COMPRIMIR-IMG] ✅ Resultado: {tamanho_kb:.0f} KB")

        # Marca código como usado
        try:
            cobranca.compressao_img_usada = True
            db.session.commit()
        except Exception:
            pass  # campo pode não existir ainda; não bloqueia a entrega

        return send_file(
            buf,
            mimetype="image/jpeg",
            as_attachment=True,
            download_name="imagem_comprimida.jpg"
        )

    except Exception as e:
        logger.error(f"ERRO comprimir_imagem: {e}")
        return jsonify({"status": "erro", "message": str(e)}), 500
