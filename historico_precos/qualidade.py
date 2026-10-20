"""Agente de qualidade: encontra preços suspeitos antes de chegarem ao app.

BLOQUEIO  o ponto não é exportado (erro quase certo: preço absurdo ou pico que volta logo)
AVISO     o ponto é exportado, mas o alerta fica registrado para alguém conferir
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import groupby

from .causas import embalagem
from .modelo import PontoDePreco

BLOQUEIO = "bloqueio"
AVISO = "aviso"

FATOR_ABSURDO = 3.0  # mais de 3x acima ou abaixo da mediana do produto
SALTO_SUSPEITO = 0.6  # variação de 60% ou mais entre duas observações da mesma loja
JANELA_PICO_DIAS = 45  # se o preço volta ao patamar anterior dentro disso, era pico
DIFERENCA_EMBALAGEM = 0.2  # tamanhos 20% diferentes no mesmo período


@dataclass
class Alerta:
    ean: str
    loja: str
    data: str
    preco: float
    tipo: str
    severidade: str
    mensagem: str
    evidencia: str

    def chave(self) -> tuple:
        return (self.loja, self.data, round(self.preco, 2))


def _dia(p: PontoDePreco) -> date:
    return date.fromisoformat(p.data_observada)


def _preco_absurdo(pontos: list[PontoDePreco]) -> list[Alerta]:
    if len(pontos) < 3:
        return []
    mediana = statistics.median(p.preco for p in pontos)
    alertas = []
    for p in pontos:
        if p.preco > mediana * FATOR_ABSURDO or p.preco < mediana / FATOR_ABSURDO:
            alertas.append(Alerta(p.ean, p.loja, p.data_observada, p.preco, "preco_absurdo", BLOQUEIO,
                                  f"R$ {p.preco:.2f} está muito longe da mediana do produto (R$ {mediana:.2f}).",
                                  p.url_evidencia))
    return alertas


def _picos(pontos: list[PontoDePreco], ignorar: set[tuple]) -> list[Alerta]:
    alertas = []
    por_loja = sorted(pontos, key=lambda p: (p.loja, p.data_observada))
    for _, grupo in groupby(por_loja, key=lambda p: p.loja):
        serie = [p for p in grupo if (p.loja, p.data_observada, round(p.preco, 2)) not in ignorar]
        for i in range(1, len(serie)):
            antes, atual = serie[i - 1], serie[i]
            variacao = atual.preco / antes.preco - 1
            if abs(variacao) < SALTO_SUSPEITO:
                continue
            # troca de embalagem explica o salto: não é erro
            if embalagem.comparar(antes.descricao, atual.descricao, antes.preco, atual.preco):
                continue
            depois = serie[i + 1] if i + 1 < len(serie) else None
            voltou = (
                depois is not None
                and (_dia(depois) - _dia(atual)) <= timedelta(days=JANELA_PICO_DIAS)
                and abs(depois.preco / antes.preco - 1) < SALTO_SUSPEITO / 3
            )
            severidade = BLOQUEIO if voltou else AVISO
            texto = "voltou ao patamar anterior logo depois" if voltou else "confira se a loja mudou mesmo o preço"
            alertas.append(Alerta(atual.ean, atual.loja, atual.data_observada, atual.preco, "salto_suspeito", severidade,
                                  f"Variação de {variacao * 100:+.0f}% em relação ao preço anterior; {texto}.",
                                  atual.url_evidencia))
    return alertas


def _produto_trocado(pontos: list[PontoDePreco]) -> list[Alerta]:
    """Lojas mostrando tamanhos diferentes para o mesmo código no mesmo período: EAN cadastrado errado."""
    com_qtd = [(p, embalagem.quantidade(p.descricao)) for p in pontos]
    com_qtd = [(p, q) for p, q in com_qtd if q]
    if len(com_qtd) < 2:
        return []
    alertas = []
    for p, (qtd, unidade) in com_qtd:
        outras_lojas = [q[0] for o, q in com_qtd
                        if o.loja != p.loja and q[1] == unidade and abs((_dia(o) - _dia(p)).days) <= 30]
        if len(outras_lojas) < 2:  # com só uma outra loja não dá para saber qual das duas está errada
            continue
        referencia = statistics.median(outras_lojas + [qtd])  # o tamanho mais comum no período
        if abs(qtd / referencia - 1) > DIFERENCA_EMBALAGEM:
            alertas.append(Alerta(p.ean, p.loja, p.data_observada, p.preco, "produto_trocado", AVISO,
                                  f"Esta loja mostra {qtd:g}{unidade}, outras lojas no mesmo período mostram {referencia:g}{unidade}. "
                                  "O código pode estar ligado ao produto errado.", p.url_evidencia))
    return alertas


def _preco_de_suspeito(pontos: list[PontoDePreco]) -> list[Alerta]:
    return [
        Alerta(p.ean, p.loja, p.data_observada, p.preco, "preco_de_suspeito", AVISO,
               f"Preço riscado de R$ {p.preco_de:.2f} é mais de 3 vezes o preço de venda.", p.url_evidencia)
        for p in pontos if p.preco_de and p.preco_de > p.preco * 3
    ]


def avaliar(pontos: list[PontoDePreco]) -> list[Alerta]:
    absurdos = _preco_absurdo(pontos)
    ignorar = {a.chave() for a in absurdos}  # o absurdo já foi tratado; não deve gerar salto falso nos vizinhos
    return absurdos + _picos(pontos, ignorar) + _produto_trocado(pontos) + _preco_de_suspeito(pontos)


def limpar(pontos: list[PontoDePreco]) -> tuple[list[PontoDePreco], list[Alerta]]:
    """Devolve os pontos sem os bloqueados, e todos os alertas."""
    alertas = avaliar(pontos)
    bloqueados = {a.chave() for a in alertas if a.severidade == BLOQUEIO}
    limpos = [p for p in pontos if (p.loja, p.data_observada, round(p.preco, 2)) not in bloqueados]
    return limpos, alertas
