"""Cupom fiscal (NFC-e) do DF, enviado por quem comprou: preço de prateleira de verdade, em qualquer mercado.

A pessoa escaneia o QR code do próprio cupom no app. O link abre a consulta pública da Secretaria de Fazenda do DF
(www.fazenda.df.gov.br/nfce/qrcode?p=...). A coleta lê essa página e extrai: mercado (nome, CNPJ, endereço),
data de emissão e itens (descrição, código, quantidade, unidade, valor unitário).

Privacidade: a parte do consumidor (CPF, nome) nunca é lida nem guardada, e o link do cupom não é publicado.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape

_TAGS = re.compile(r"<[^>]+>")


def _texto(html: str) -> str:
    return " ".join(unescape(_TAGS.sub(" ", html or "")).split())


def _numero(t: str | None) -> float | None:
    if not t:
        return None
    t = t.strip().replace(".", "").replace(",", ".")
    try:
        return float(re.search(r"-?\d+(?:\.\d+)?", t).group(0))
    except (AttributeError, ValueError):
        return None


@dataclass
class ItemCupom:
    descricao: str
    codigo: str | None
    quantidade: float | None
    unidade: str | None
    valor_unitario: float | None
    valor_total: float | None


@dataclass
class Cupom:
    mercado: str | None
    cnpj: str | None
    endereco: str | None
    emissao: str | None  # AAAA-MM-DD
    itens: list[ItemCupom] = field(default_factory=list)


def ler_cupom(html: str) -> Cupom:
    """Lê a consulta pública da NFC-e no formato nacional (tabela tabResult)."""
    topo = re.search(r'class="txtTopo"[^>]*>(.*?)</div>', html, re.S)
    cnpj = re.search(r"CNPJ:?\s*([\d./-]{14,18})", _texto(html))
    # endereço: o div de texto logo depois do CNPJ, no cabeçalho do emitente
    cabecalho = re.search(r'class="txtTopo".*?</div>(.*?)</div>\s*</div>', html, re.S)
    endereco = None
    if cabecalho:
        partes = [p for p in (_texto(x) for x in re.findall(r'<div class="text"[^>]*>(.*?)</div>', cabecalho.group(0), re.S)) if p]
        endereco = next((p for p in partes if "CNPJ" not in p.upper()), None)
    emissao = re.search(r"Emiss[ãa]o:?\s*(?:</strong>)?\s*(\d{2})/(\d{2})/(\d{4})", html)
    itens = []
    for linha in re.findall(r"<tr[^>]*id=\"Item[^\"]*\"[^>]*>(.*?)</tr>", html, re.S | re.I):
        nome = re.search(r'class="txtTit[^"]*"[^>]*>(.*?)</span>', linha, re.S)
        codigo = re.search(r"C[óo]digo:\s*([0-9A-Za-z.-]+)", _texto(linha))
        qtd = re.search(r'class="Rqtd"[^>]*>(.*?)</span>', linha, re.S)
        un = re.search(r'class="RUN"[^>]*>(.*?)</span>', linha, re.S)
        unit = re.search(r'class="RvlUnit"[^>]*>(.*?)</span>', linha, re.S)
        total = re.search(r'class="valor"[^>]*>(.*?)</span>', linha, re.S)
        if not nome:
            continue
        itens.append(ItemCupom(
            descricao=_texto(nome.group(1)),
            codigo=codigo.group(1).strip() if codigo else None,
            quantidade=_numero(_texto(qtd.group(1)).split(":")[-1]) if qtd else None,
            unidade=_texto(un.group(1)).split(":")[-1].strip() if un else None,
            valor_unitario=_numero(_texto(unit.group(1)).split(":")[-1]) if unit else None,
            valor_total=_numero(_texto(total.group(1))) if total else None,
        ))
    return Cupom(
        mercado=_texto(topo.group(1)) if topo else None,
        cnpj=re.sub(r"\D", "", cnpj.group(1)) if cnpj else None,
        endereco=endereco,
        emissao=f"{emissao[3]}-{emissao[2]}-{emissao[1]}" if emissao else None,
        itens=itens,
    )


def pontos_do_cupom(cupom: Cupom, catalogo=None, chave_resumo: str = "") -> list:
    """Transforma os itens em preços. Código de barras válido vale direto; sem ele, tenta o vínculo por nome."""
    from ..modelo import PontoDePreco
    from .pagina_produto import ean_valido

    if not (cupom.mercado and cupom.emissao):
        return []
    pontos = []
    for item in cupom.itens:
        preco = item.valor_unitario or (item.valor_total / item.quantidade if item.valor_total and item.quantidade else None)
        if not preco or preco <= 0:
            continue
        codigo = re.sub(r"\D", "", item.codigo or "")
        ean, metodo = (codigo, "nfce-codigo") if ean_valido(codigo) else (None, None)
        if not ean and catalogo is not None:
            v = catalogo.vincular(item.descricao)
            if v:
                ean, metodo = v.ean, "nfce-vinculo-nome"
        if not ean:
            continue
        pontos.append(PontoDePreco(
            ean=ean, preco=round(preco, 2), data_observada=cupom.emissao, fonte="cupom", loja=cupom.mercado,
            cidade="Brasília", url_origem=f"cupom fiscal {chave_resumo[:10]}",
            # o link do cupom não é publicado (pode conter CPF); a prova é a consulta pública pela chave de acesso
            url_evidencia="https://www.fazenda.df.gov.br/nfce/consulta", metodo=metodo, descricao=item.descricao,
        ))
    return pontos
