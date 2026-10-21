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


# ---------- referência para o vínculo por nome: produtos vendidos no Brasil, os mais escaneados primeiro ----------

REFERENCIA = ("https://world.openfoodfacts.org/api/v2/search?countries_tags_en=brazil&sort_by=unique_scans_n"
              "&fields=code,product_name,product_name_pt,brands,quantity&page_size=100&page={pagina}")


def _nome_com_tamanho(p: dict) -> str | None:
    nome = (p.get("product_name_pt") or p.get("product_name") or "").strip()
    if len([c for c in nome if c.isalpha()]) < 3:
        return None
    qtd = (p.get("quantity") or "").strip()
    return f"{nome} {qtd}" if qtd and qtd.lower() not in nome.lower() else nome


def referencia_brasil(nav: Navegador, pagina: int) -> list[Produto] | None:
    """Uma página (100 produtos) da busca pública por produtos do Brasil. None = falhou (tentar de novo depois)."""
    dado = nav.get_json(REFERENCIA.format(pagina=pagina))
    if not isinstance(dado, dict):
        return None
    saida = []
    for p in dado.get("products", []):
        codigo = str(p.get("code") or "")
        nome = _nome_com_tamanho(p)
        if codigo.isdigit() and 8 <= len(codigo) <= 14 and nome:
            marca = (p.get("brands") or "").split(",")[0].strip() or None
            saida.append(Produto(codigo, nome=nome, marca=marca, fonte="Open Food Facts"))
    return saida
