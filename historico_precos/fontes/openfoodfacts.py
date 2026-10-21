"""Identifica o produto pelo código de barras no Open Food Facts (base aberta, sem chave)."""

from __future__ import annotations

from urllib.parse import quote

from ..modelo import Produto
from ..rede import Navegador

URL = "https://world.openfoodfacts.org/api/v2/product/{ean}.json?fields=product_name,product_name_pt,brands,quantity"


def identificar(nav: Navegador, ean: str) -> Produto:
    dado = nav.get_json(URL.format(ean=ean))
    if not dado or dado.get("status") != 1:
        return Produto(ean=ean)
    p = dado.get("product", {})
    return Produto(
        ean=ean,
        nome=p.get("product_name_pt") or p.get("product_name") or None,
        marca=p.get("brands") or None,
        quantidade=p.get("quantity") or None,
        fonte="open_food_facts",
    )


# a busca por texto (cgi/search.pl) é proibida no robots.txt do Open Food Facts;
# a API v2 permite filtrar por categoria e país
BUSCA = (
    "https://world.openfoodfacts.org/api/v2/search?countries_tags_en=brazil&categories_tags_en={categoria}"
    "&fields=code,product_name&page_size={limite}"
)
CATEGORIAS = {
    "cafe": "coffees", "arroz": "rices", "feijao": "beans", "leite": "milks", "oleo de soja": "soybean-oils",
    "acucar": "sugars", "macarrao": "pastas", "farinha de trigo": "wheat-flours", "biscoito": "biscuits",
    "manteiga": "butters",
}


def buscar_texto(nav: Navegador, termo: str, limite: int = 5) -> list[tuple[str, str]]:
    """Produtos vendidos no Brasil da categoria do termo. Prefixo 789/790 = código registrado no Brasil."""
    from ..causas.series import normalizar

    categoria = CATEGORIAS.get(normalizar(termo))
    if not categoria:
        return []
    dado = nav.get_json(BUSCA.format(categoria=categoria, limite=limite * 3))
    achados = []
    for p in (dado or {}).get("products", []):
        codigo = str(p.get("code", ""))
        if codigo.startswith(("789", "790")) and len(codigo) == 13:
            achados.append((codigo, p.get("product_name", "")))
    return achados[:limite]


# ---------- referência para o vínculo por nome: exportação completa (caminho oficial para uso em massa) ----------
# A busca da API é proibida no robots.txt; o Open Food Facts pede que uso em massa seja feito pela exportação.

EXPORTACAO = "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"


def _nome_com_tamanho(nome: str, qtd: str) -> str | None:
    nome = (nome or "").strip()
    if len([c for c in nome if c.isalpha()]) < 3:
        return None
    from ..causas import embalagem

    qtd = (qtd or "").strip()
    return f"{nome} {qtd}" if qtd and not embalagem.quantidade(nome) else nome


def linhas_do_brasil(fluxo):
    """Lê o CSV (tabulado, gzip) em fluxo e devolve Produto dos itens vendidos no Brasil."""
    import csv
    import io
    import sys
    import zlib

    csv.field_size_limit(sys.maxsize)
    descompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)

    def texto():
        while True:
            pedaco = fluxo.read(1 << 20)
            if not pedaco:
                yield descompressor.flush().decode("utf-8", "replace")
                return
            yield descompressor.decompress(pedaco).decode("utf-8", "replace")

    class Linhas(io.TextIOBase):
        def __init__(self):
            self.ger, self.resto = texto(), ""

        def __iter__(self):
            for parte in self.ger:
                parte = self.resto + parte
                *completas, self.resto = parte.split("\n")
                yield from completas
            if self.resto:
                yield self.resto

    leitor = csv.reader(Linhas(), delimiter="\t", quoting=csv.QUOTE_NONE)
    cab = next(leitor)
    col = {nome: i for i, nome in enumerate(cab)}
    i_cod, i_nome, i_marca, i_qtd, i_pais = (col.get(c) for c in ("code", "product_name", "brands", "quantity", "countries_tags"))
    for linha in leitor:
        if i_pais is None or len(linha) <= max(i_cod, i_nome, i_pais) or "en:brazil" not in linha[i_pais]:
            continue
        codigo = linha[i_cod].strip()
        nome = _nome_com_tamanho(linha[i_nome], linha[i_qtd] if i_qtd is not None and i_qtd < len(linha) else "")
        if codigo.isdigit() and 8 <= len(codigo) <= 14 and nome:
            marca = (linha[i_marca] if i_marca is not None and i_marca < len(linha) else "").split(",")[0].strip() or None
            yield Produto(codigo, nome=nome, marca=marca, fonte="Open Food Facts")


def referencia_brasil(nav: Navegador, url: str = EXPORTACAO):
    """Baixa a exportação em fluxo (respeitando o robots.txt) e devolve os produtos do Brasil."""
    import urllib.request

    if not nav.permitido(url):
        raise PermissionError("robots.txt não permite a exportação")
    req = urllib.request.Request(url, headers={"User-Agent": nav.user_agent})
    with urllib.request.urlopen(req, timeout=120) as resposta:
        yield from linhas_do_brasil(resposta)
