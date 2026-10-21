"""Encartes publicados nos sites dos próprios mercados do DF (sem intermediário).

- Atacadão Dia a Dia: ofertas.diaadiaatacadista.com.br é um WordPress com o tipo de conteúdo "ofertas"; o JSON público
  traz, para cada tabloide, a região (DF), as lojas, o PDF, as imagens das páginas e a data em que a oferta sai do ar.
- Dona: a página donafazbem.com.br/folheto/ofertas/ tem o link do PDF do folheto vigente; o nome do arquivo traz o
  período ("...-19-a-21-10-2026.pdf").
robots.txt dos dois libera essas páginas.
"""

from __future__ import annotations

import re
from datetime import date
from html import unescape

from ..rede import Navegador
from .encartesdf import Encarte

DIA_A_DIA = "https://ofertas.diaadiaatacadista.com.br/wp-json/wp/v2/ofertas?per_page=50"
DONA = "https://donafazbem.com.br/folheto/ofertas/"
_RE_PDF_DONA = re.compile(r"https?://donafazbem\.com\.br/wp-content/uploads/(\d{4})/(\d{2})/[^\"'\s<>]+?\.pdf", re.I)


def dia_a_dia(nav: Navegador) -> list[Encarte]:
    ofertas = nav.get_json(DIA_A_DIA)
    saida = []
    for x in ofertas if isinstance(ofertas, list) else []:
        acf = x.get("acf") or {}
        if "DF" not in (acf.get("regiao") or []):
            continue
        futuro = x.get("publishpress_future_action") or {}
        fim = (futuro.get("date") or "")[:10] if futuro.get("enabled") else None
        lojas = acf.get("segmentacao_df") or []
        titulo = " ".join(unescape((x.get("title") or {}).get("rendered", "")).split())
        for t in acf.get("tabloide") or []:
            imagens = [i for i in (t.get("paginas_do_tabloide") or []) if isinstance(i, str)]
            if imagens or t.get("pdf_do_tabloide"):
                saida.append(Encarte(post=x.get("link") or "https://ofertas.diaadiaatacadista.com.br/",
                                     titulo=f"{titulo} ({len(lojas)} lojas)" if lojas else titulo,
                                     mercado="Atacadão Dia a Dia", publicado=(x.get("date") or "")[:10],
                                     validade_fim=fim or None, imagens=imagens, pdf=t.get("pdf_do_tabloide") or None))
    return saida


def validade_do_arquivo(nome: str) -> str | None:
    """'DONA-Festival-Carrinho-Cheio-19-a-21-10-2026.pdf' -> '2026-10-21' (último dia do período no nome)."""
    datas = re.findall(r"(?<!\d)(\d{1,2})[-_.](\d{1,2})[-_.](20\d{2})(?!\d)", nome)
    if not datas:
        return None
    d, m, a = (int(v) for v in datas[-1])
    try:
        return date(a, m, d).isoformat()
    except ValueError:
        return None


def dona(nav: Navegador) -> list[Encarte]:
    html = nav.get_texto(DONA) or ""
    saida, vistos = [], set()
    for achado in _RE_PDF_DONA.finditer(html):
        url = achado.group(0)
        if url in vistos:
            continue
        vistos.add(url)
        nome = url.rsplit("/", 1)[-1]
        saida.append(Encarte(post=DONA, titulo=nome.rsplit(".", 1)[0].replace("-", " "), mercado="Dona",
                             publicado=f"{achado.group(1)}-{achado.group(2)}-01", validade_fim=validade_do_arquivo(nome),
                             imagens=[], pdf=url))
    return saida


def todos(nav: Navegador) -> list[Encarte]:
    saida = []
    for fonte in (dia_a_dia, dona):
        try:
            saida += fonte(nav)
        except Exception as e:  # uma rede fora do ar não derruba as outras
            print(f"encartes de {fonte.__name__}: {e!r}")
    return saida
