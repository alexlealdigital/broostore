"""Regras PURAS (sem Flask, sem banco) do sistema de chaves de licença dos apps.
Usadas pela web (validação) e pelo worker (geração na compra): as duas pontas
usam exatamente a mesma lógica.

Formato da chave:   BROO-XXXX-XXXX-XXXX-XXXX
  - 15 caracteres aleatórios (alfabeto de 32 símbolos, ~75 bits de entropia)
  - o 16º caractere é um dígito verificador, para o app rejeitar digitação
    errada sem precisar consultar o servidor
  - o alfabeto não tem 0, 1, I, O (evita confusão ao digitar)
"""

import re
import secrets
from datetime import timedelta

ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 32 símbolos, sem 0 1 I O
PREFIXO_PADRAO = "BROO"
_REGEX_FORMATO = re.compile(r"^[A-Z0-9]{2,8}(-[A-Z0-9]{4}){4}$")


def _digito_verificador(texto):
    """Soma ponderada dos caracteres, mapeada de volta para o alfabeto."""
    total = sum((i + 1) * ord(c) for i, c in enumerate(texto))
    return ALFABETO[total % len(ALFABETO)]


def gerar_chave(prefixo=PREFIXO_PADRAO):
    """Gera uma chave nova, ex.: BROO-7K2M-X9QP-4HD3-R8WN.

    Usa `secrets` (gerador criptográfico), nunca `random`.
    """
    prefixo = (prefixo or PREFIXO_PADRAO).strip().upper()
    corpo = "".join(secrets.choice(ALFABETO) for _ in range(15))
    corpo += _digito_verificador(prefixo + corpo)
    grupos = [corpo[i:i + 4] for i in range(0, 16, 4)]
    return "-".join([prefixo] + grupos)


def normalizar_chave(chave):
    """Maiúsculas, sem espaços nas pontas e traços tipográficos trocados."""
    if not chave:
        return ""
    chave = str(chave).strip().upper()
    for traco in ("‐", "‑", "‒", "–", "—", "_"):
        chave = chave.replace(traco, "-")
    return chave.replace(" ", "")


def formato_valido(chave):
    """True se a chave tem o formato novo E o dígito verificador confere.

    Chaves antigas (estoque pré-carregado) não seguem este formato; para elas
    o chamador deve pular esta checagem e ir direto ao banco.
    """
    chave = normalizar_chave(chave)
    if not _REGEX_FORMATO.match(chave):
        return False
    prefixo, *grupos = chave.split("-")
    corpo = "".join(grupos)
    return _digito_verificador(prefixo + corpo[:-1]) == corpo[-1]


def tem_formato_novo(chave):
    """True se a chave parece do formato novo (para decidir se valida o dígito)."""
    return bool(_REGEX_FORMATO.match(normalizar_chave(chave)))


def calcular_expiracao(dias, expira_atual, agora):
    """Nova data de expiração ao comprar/renovar um plano.

    - dias None ou 0  -> licença vitalícia (devolve None)
    - se a licença ainda está válida, soma a partir da expiração atual
      (quem renova antes do prazo não perde os dias que sobraram)
    - se já venceu (ou é a primeira compra), conta a partir de `agora`
    """
    if not dias:
        return None
    base = expira_atual if (expira_atual and expira_atual > agora) else agora
    return base + timedelta(days=int(dias))


def situacao_licenca(expira_em, agora):
    """Devolve (vigente: bool, dias_restantes: int | None).

    expira_em None = vitalícia: sempre vigente, sem contagem de dias.
    """
    if expira_em is None:
        return True, None
    if expira_em > agora:
        # arredonda para cima: faltando 2h ainda mostra "1 dia"
        segundos = (expira_em - agora).total_seconds()
        return True, int(-(-segundos // 86400))
    return False, 0
