"""Cotação de frete — Melhor Envio.

Portado de app.py sem mudança de lógica; as variáveis MELHOR_ENVIO_* e CEP_ORIGEM
vêm de ``config.get_settings()`` (o original as lia no import do módulo).
"""
import logging

import requests

from ..config import get_settings

logger = logging.getLogger("broostore")


def _so_digitos(cep):
    return "".join(filter(str.isdigit, cep or ""))


def cotar_frete_melhor_envio(cep_destino, peso_kg, altura_cm, largura_cm,
                             comprimento_cm, valor_segurado=0.0):
    """Consulta o Melhor Envio e retorna (opcoes, erro).
    opcoes = lista de {id, nome, empresa, preco, prazo}; erro = None ou mensagem."""
    settings = get_settings()
    token = settings.melhor_envio_token
    if not token:
        return None, "MELHOR_ENVIO_TOKEN não configurado no servidor."
    if not settings.cep_origem:
        return None, "CEP_ORIGEM não configurado no servidor."

    cep_o = _so_digitos(settings.cep_origem)
    cep_d = _so_digitos(cep_destino)
    if len(cep_d) != 8:
        return None, "CEP de destino inválido."

    payload = {
        "from": {"postal_code": cep_o},
        "to":   {"postal_code": cep_d},
        "package": {
            "weight": float(peso_kg or 0.3),
            "width":  float(largura_cm or 11),
            "height": float(altura_cm or 2),
            "length": float(comprimento_cm or 16),
        },
        "options": {
            "insurance_value": float(valor_segurado or 0),
            "receipt": False,
            "own_hand": False,
        },
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": f"BrooStore ({settings.melhor_envio_email})",
    }

    try:
        resp = requests.post(
            f"{settings.melhor_envio_url}/me/shipment/calculate",
            json=payload, headers=headers, timeout=15
        )
    except Exception as e:
        return None, f"Falha ao consultar Melhor Envio: {e}"

    if resp.status_code == 401:
        return None, "Token do Melhor Envio inválido ou expirado (401)."
    if resp.status_code == 403:
        return None, "Token sem a permissão de cotação 'shipping-calculate' (403)."
    if resp.status_code != 200:
        return None, f"Melhor Envio respondeu {resp.status_code}: {resp.text[:200]}"

    try:
        dados = resp.json()
    except Exception:
        return None, "Resposta inválida do Melhor Envio."

    opcoes = []
    for item in dados:
        # Pula serviços indisponíveis (vêm com 'error' e sem 'price')
        if item.get("error") or not item.get("price"):
            continue
        try:
            preco = round(float(item["price"]), 2)
        except (TypeError, ValueError):
            continue
        opcoes.append({
            "id":      item.get("id"),
            "nome":    item.get("name", ""),
            "empresa": (item.get("company") or {}).get("name", ""),
            "preco":   preco,
            "prazo":   item.get("delivery_time"),
        })

    # Log de depuração: peso real vs cúbico
    try:
        pk = payload["package"]
        cubico = round((pk["height"] * pk["width"] * pk["length"]) / 6000.0, 3)
        logger.info(f"[FRETE] origem={cep_o} destino={cep_d} peso_real={pk['weight']}kg "
                    f"peso_cubico~{cubico}kg -> {len(opcoes)} opcoes")
    except Exception:
        pass

    return opcoes, None


def resolver_frete_fisico(p_supabase, cep_destino, servico_id, frete_fixo_fallback):
    """Produto fisico: recota no Melhor Envio e devolve o preco do servico escolhido.
    Cai no frete fixo (fallback) se nao der para cotar. Retorna (frete, descricao_servico)."""
    fallback = round(float(frete_fixo_fallback or 0), 2)
    dims_ok = all(p_supabase.get(c) for c in ("peso_kg", "altura_cm", "largura_cm", "comprimento_cm"))
    if not (servico_id and cep_destino and dims_ok):
        return fallback, None
    opcoes, erro = cotar_frete_melhor_envio(
        cep_destino=cep_destino,
        peso_kg=p_supabase["peso_kg"], altura_cm=p_supabase["altura_cm"],
        largura_cm=p_supabase["largura_cm"], comprimento_cm=p_supabase["comprimento_cm"],
        valor_segurado=float(p_supabase.get("price") or 0),
    )
    if erro or not opcoes:
        logger.info(f"[FRETE] recotacao indisponivel ({erro}); usando frete fixo R$ {fallback}")
        return fallback, None
    escolhido = next((o for o in opcoes if str(o["id"]) == str(servico_id)), None)
    if not escolhido:
        logger.info(f"[FRETE] servico_id {servico_id} nao encontrado; usando frete fixo R$ {fallback}")
        return fallback, None
    return round(float(escolhido["preco"]), 2), f"{escolhido['empresa']} {escolhido['nome']}"


def curar_opcoes(opcoes):
    """Seleciona ate 3 opcoes por custo-beneficio: mais barata, melhor equilibrio e mais rapida."""
    if not opcoes:
        return []
    FATOR_DIA = 2.0
    barata = min(opcoes, key=lambda o: (o["preco"], o["prazo"] or 999))
    rapida = min(opcoes, key=lambda o: (o["prazo"] or 999, o["preco"]))
    score = lambda o: o["preco"] + (o["prazo"] or 0) * FATOR_DIA  # noqa: E731
    ids = {barata["id"], rapida["id"]}
    restantes = [o for o in opcoes if o["id"] not in ids]
    equilibrio = min(restantes, key=score) if restantes else None
    selecionadas = []

    def _add(o, tag):
        if o and all(x["id"] != o["id"] for x in selecionadas):
            o2 = dict(o)
            o2["destaque"] = tag
            selecionadas.append(o2)
    _add(barata, "Mais barato")
    _add(equilibrio, "Custo-beneficio")
    _add(rapida, "Mais rapido")
    for o in opcoes:
        if len(selecionadas) >= 3:
            break
        _add(o, "")
    selecionadas.sort(key=lambda o: o["preco"])
    return selecionadas[:3]
