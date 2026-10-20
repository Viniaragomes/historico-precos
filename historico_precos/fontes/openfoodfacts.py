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


BUSCA = (
    "https://world.openfoodfacts.org/cgi/search.pl?search_terms={termo}&tagtype_0=countries"
    "&tag_contains_0=contains&tag_0=brazil&json=1&page_size={limite}&fields=code,product_name"
)


def buscar_texto(nav: Navegador, termo: str, limite: int = 5) -> list[tuple[str, str]]:
    """Produtos vendidos no Brasil com o termo no nome. Prefixo 789/790 = código registrado no Brasil."""
    dado = nav.get_json(BUSCA.format(termo=quote(termo), limite=limite * 3))
    achados = []
    for p in (dado or {}).get("products", []):
        codigo = str(p.get("code", ""))
        if codigo.startswith(("789", "790")) and len(codigo) == 13:
            achados.append((codigo, p.get("product_name", "")))
    return achados[:limite]
