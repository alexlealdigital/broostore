"""Regras de cupom usadas pelo checkout (PIX e cartão)."""
from ..extensions import db
from ..models import Cupom


def aplicar_cupom_checkout(cupom_id_recebido, product_id_recebido, valor_original):
    """Retorna ``(cupom_obj, valor_final)``.

    Comportamento idêntico ao original: o cupom só é APLICADO (desconto + contador
    de usos) se estiver válido e compatível com o produto, mas ``cupom_obj`` é
    devolvido sempre que o id existir (mesmo sem aplicar) — o chamador usa isso na
    descrição/``cupom_id``. ``int(...)`` inválido levanta (a rota devolve 500).
    """
    cupom_obj = None
    valor_final = valor_original
    if cupom_id_recebido:
        cupom_obj = Cupom.query.get(int(cupom_id_recebido))
        if cupom_obj:
            valido, _ = cupom_obj.esta_valido()
            if valido and (cupom_obj.produto_id is None or cupom_obj.produto_id == int(product_id_recebido)):
                resultado = cupom_obj.calcular_desconto(valor_original)
                valor_final = resultado["valor_final"]
                cupom_obj.usos_atuais += 1
                db.session.add(cupom_obj)
    return cupom_obj, valor_final


def desconto_aplicado(cupom_obj, valor_original, valor_final):
    return {
        "cupom_codigo": cupom_obj.codigo,
        "tipo": cupom_obj.tipo,
        "valor_desconto": round(valor_original - valor_final, 2),
        "valor_original": round(valor_original, 2),
        "valor_final": round(valor_final, 2)
    }
