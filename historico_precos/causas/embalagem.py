"""Detecta 'reduflação': a embalagem encolhe e o preço por quilo/litro sobe sem o preço mudar tanto."""

from __future__ import annotations

import re

_RE_QTD = re.compile(r"(\d+(?:[.,]\d+)?)\s*(kg|g|gr|mg|l|lt|litros?|ml)\b", re.I)
_PARA_BASE = {"kg": 1000, "g": 1, "gr": 1, "mg": 0.001, "l": 1000, "lt": 1000, "litro": 1000, "litros": 1000, "ml": 1}


def quantidade(texto: str | None) -> tuple[float, str] | None:
    """'Café Torrado 500g' -> (500.0, 'g'); 'Óleo 0,9L' -> (900.0, 'ml'). Unidade base: g ou ml."""
    if not texto:
        return None
    achados = _RE_QTD.findall(texto)
    if not achados:
        return None
    numero, unidade = achados[-1]  # a quantidade costuma vir no fim do nome
    unidade = unidade.lower()
    valor = float(numero.replace(",", ".")) * _PARA_BASE[unidade]
    base = "ml" if unidade in ("l", "lt", "litro", "litros", "ml") else "g"
    return valor, base


def comparar(desc_antes: str | None, desc_depois: str | None, preco_antes: float, preco_depois: float):
    """Devolve (qtd_antes, qtd_depois, unidade, variação % do preço por unidade) se a embalagem mudou."""
    qa, qd = quantidade(desc_antes), quantidade(desc_depois)
    if not qa or not qd or qa[1] != qd[1] or abs(qa[0] - qd[0]) < 1e-9:
        return None
    unitario_antes = preco_antes / qa[0]
    unitario_depois = preco_depois / qd[0]
    return qa[0], qd[0], qa[1], (unitario_depois / unitario_antes - 1) * 100
