"""Onde o monitor procura normas. Todas as fontes são públicas e sem chave."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from html import unescape
from urllib.parse import urlencode, urljoin

from ..rede import Navegador


@dataclass
class Publicacao:
    fonte: str
    titulo: str
    url: str
    data: str  # AAAA-MM-DD
    texto: str  # ementa/trecho; o texto completo pode ser lido depois pela URL
    uf: str  # DF, BR (federal) ou CONFAZ


# ---------- Diário Oficial da União (busca pública da Imprensa Nacional) ----------

DOU_BUSCA = "https://www.in.gov.br/consulta/-/buscar/dou"
_RE_DOU_JSON = re.compile(
    r'<script[^>]*id="_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params"[^>]*>(.*?)</script>', re.S
)
_RE_TAGS = re.compile(r"<[^>]+>")


def _limpar(html: str) -> str:
    return " ".join(unescape(_RE_TAGS.sub(" ", html or "")).split())


def _data_br(texto: str) -> str:
    d, m, a = texto.split("/")
    return f"{a}-{int(m):02d}-{int(d):02d}"


def buscar_dou(nav: Navegador, termo: str, desde: date, ate: date, secao: str = "do1") -> list[Publicacao]:
    params = {
        "q": termo,
        "s": secao,
        "exactDate": "personalizado",
        "publishFrom": desde.strftime("%d-%m-%Y"),
        "publishTo": ate.strftime("%d-%m-%Y"),
        "sortType": "0",
        "delta": "75",
    }
    html = nav.get_texto(f"{DOU_BUSCA}?{urlencode(params)}")
    if not html:
        return []
    achado = _RE_DOU_JSON.search(html)
    if not achado:
        return []
    try:
        dado = json.loads(achado.group(1))
    except json.JSONDecodeError:
        return []
    pubs = []
    for item in dado.get("jsonArray", []):
        hierarquia = item.get("hierarchyStr", "")
        titulo = _limpar(item.get("title", ""))
        confaz = "Conselho Nacional de Política Fazendária" in hierarquia or "CONVÊNIO ICMS" in titulo.upper()
        try:
            data = _data_br(item.get("pubDate", ""))
        except ValueError:
            data = ""
        pubs.append(
            Publicacao(
                fonte="DOU",
                titulo=titulo,
                url=f"https://www.in.gov.br/web/dou/-/{item.get('urlTitle', '')}",
                data=data,
                texto=f"{titulo}. {hierarquia}. {_limpar(item.get('content', ''))}",
                uf="CONFAZ" if confaz else "BR",
            )
        )
    return pubs


# ---------- Querido Diário (diários oficiais abertos, Open Knowledge Brasil) ----------

QUERIDO_DIARIO = "https://api.queridodiario.ok.org.br/gazettes"


def buscar_querido_diario(nav: Navegador, territorio: str, termo: str, desde: date, ate: date, uf: str) -> list[Publicacao]:
    params = {
        "territory_ids": territorio,
        "querystring": termo,
        "published_since": desde.isoformat(),
        "published_until": ate.isoformat(),
        "excerpt_size": "600",
        "number_of_excerpts": "3",
        "size": "100",
    }
    dado = nav.get_json(f"{QUERIDO_DIARIO}?{urlencode(params)}")
    pubs = []
    for g in (dado or {}).get("gazettes", []):
        trechos = " ... ".join(g.get("excerpts", []))
        pubs.append(
            Publicacao(
                fonte="Querido Diário",
                titulo=f"Diário oficial de {g.get('territory_name', territorio)} ({g.get('date', '')})",
                url=g.get("url") or g.get("txt_url", ""),
                data=g.get("date", ""),
                texto=trechos,
                uf=uf,
            )
        )
    return pubs


# ---------- Página qualquer (lista de legislação, notícias da Receita etc.) ----------

_RE_LINK = re.compile(r'<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.S | re.I)


def links_da_pagina(nav: Navegador, url: str, palavras: list[str], uf: str, nome: str) -> list[Publicacao]:
    """Devolve os links cujo texto contém alguma das palavras. O monitor guarda os já vistos."""
    html = nav.get_texto(url)
    if not html:
        return []
    alvos = [p.lower() for p in palavras]
    pubs = []
    for href, texto in _RE_LINK.findall(html):
        texto = _limpar(texto)
        if not texto or not any(p in texto.lower() for p in alvos):
            continue
        pubs.append(Publicacao(fonte=nome, titulo=texto, url=urljoin(url, href), data="", texto=texto, uf=uf))
    return pubs
