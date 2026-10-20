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
