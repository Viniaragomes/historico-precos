"""Encartes publicados nos sites dos próprios mercados do DF (sem intermediário).

- Atacadão Dia a Dia: ofertas.diaadiaatacadista.com.br é um WordPress com o tipo de conteúdo "ofertas"; o JSON público
  traz, para cada tabloide, a região (DF), as lojas, o PDF, as imagens das páginas e a data em que a oferta sai do ar.
- Dona: a página donafazbem.com.br/folheto/ofertas/ tem o link do PDF do folheto vigente; o nome do arquivo traz o
  período ("...-19-a-21-10-2026.pdf").
- Ultrabox: o WordPress do site (ultraboxatacado.com.br) publica as páginas do encarte como imagens na lista pública de
  mídia (/wp-json/wp/v2/media), com grupo de lojas e data no nome ("ultrabox-rede-2026-11-07-pagina-1.jpeg").
- Assaí DF: o site do Assaí recusa robôs; os folhetos "ofertas DF" diários são lidos no Portafolhetos
  (portafolhetos.com.br), que os republica. O robots.txt de lá permite a página de cada folheto e proíbe a paginação
  ("?page="); as imagens das páginas ficam num servidor de imagens que permite acesso, então são lidas direto de lá.
robots.txt de todos libera esses caminhos (conferido em 08/11/2026).
"""

from __future__ import annotations

import re
from datetime import date, timedelta
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


ULTRABOX_MIDIA = "https://ultraboxatacado.com.br/wp-json/wp/v2/media?per_page=60&_fields=source_url,date"
ULTRABOX_OFERTAS = "https://ultraboxatacado.com.br/ofertas/"
_RE_ULTRABOX = re.compile(r"/ultrabox-([a-z0-9-]+?)-(\d{4})-(\d{2})-(\d{2})-pagina-(\d+)\.(?:jpe?g|png|webp)$", re.I)


def ultrabox(nav: Navegador, hoje: date | None = None, dias: int = 6) -> list[Encarte]:
    """Páginas de encarte publicadas nos últimos `dias`, agrupadas por grupo de lojas e data do nome do arquivo."""
    hoje = hoje or date.today()
    midia = nav.get_json(ULTRABOX_MIDIA)
    grupos: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for m in midia if isinstance(midia, list) else []:
        url = (m.get("source_url") or "").strip()
        achado = _RE_ULTRABOX.search(url)
        if not achado:
            continue
        grupo, a, mes, d, pagina = achado.groups()
        try:
            dia = date(int(a), int(mes), int(d))
        except ValueError:
            continue
        if not (hoje - timedelta(days=dias) <= dia <= hoje + timedelta(days=7)):
            continue
        grupos.setdefault((grupo, dia.isoformat()), []).append((int(pagina), url))
    return [Encarte(post=ULTRABOX_OFERTAS, titulo=f"Ultrabox {grupo.replace('-', ' ')} {dia}", mercado="Supermercado Ultrabox",
                    publicado=dia, validade_fim=None, imagens=[u for _, u in sorted(set(paginas))])
            for (grupo, dia), paginas in sorted(grupos.items())]


PORTAFOLHETOS_ASSAI = "https://www.portafolhetos.com.br/assai-atacadista/"
_RE_FOLHETO_DF = re.compile(r'href="(/assai-atacadista/[^"]*?ofertas-df-de-[a-z-]*?(\d{2})-(\d{2})-(\d{4})-(\d+)/)"')
_RE_PAGINA_0 = re.compile(r"(https://na\.leafletscdn\.com/thumbor/[^\"'\s]+?/com\.br/data/\d+/\d+/)0\.jpg")


def assai_df(nav: Navegador, hoje: date | None = None) -> list[Encarte]:
    """Folhetos "Assaí ofertas DF" de hoje em diante, republicados no Portafolhetos. Lê só a página principal de cada
    folheto (a paginação "?page=" é proibida pelo robots.txt de lá) e a imagem da capa, direto do servidor de imagens."""
    hoje = hoje or date.today()
    html = nav.get_texto(PORTAFOLHETOS_ASSAI) or ""
    saida, vistos = [], set()
    for caminho, d, mes, a, _id in _RE_FOLHETO_DF.findall(html):
        if caminho in vistos:
            continue
        vistos.add(caminho)
        try:
            dia = date(int(a), int(mes), int(d))
        except ValueError:
            continue
        if dia < hoje - timedelta(days=1):
            continue
        url = "https://www.portafolhetos.com.br" + caminho
        pagina = nav.get_texto(url) or ""
        base = _RE_PAGINA_0.search(pagina)
        if not base:
            continue
        # validade: "válidas até 08/11/2026" quando a página diz; senão, o dia do folheto
        fim = dia
        for trecho in re.findall(r"v[áa]lid[oa]s?([^<\"]{0,80})", pagina):
            for d_, m_, a_ in re.findall(r"(\d{2})/(\d{2})/(\d{4})", trecho):
                try:
                    fim = max(fim, date(int(a_), int(m_), int(d_)))
                except ValueError:
                    pass
        # só a capa: cada página tem endereço assinado próprio (não dá para montar) e a paginação é proibida no robots.txt
        saida.append(Encarte(post=url, titulo=f"Assaí ofertas DF de {dia.strftime('%d/%m/%Y')}", mercado="Assaí Atacadista",
                             publicado=dia.isoformat(), validade_fim=fim.isoformat(), imagens=[base.group(0)]))
    return saida


def todos(nav: Navegador) -> list[Encarte]:
    saida = []
    for fonte in (dia_a_dia, dona, ultrabox, assai_df):
        try:
            saida += fonte(nav)
        except Exception as e:  # uma rede fora do ar não derruba as outras
            print(f"encartes de {fonte.__name__}: {e!r}")
    return saida
