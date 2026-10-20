"""Preços enviados por pessoas ao Open Prices (projeto aberto do Open Food Facts), sem chave."""

from __future__ import annotations

from ..modelo import PontoDePreco
from ..rede import Navegador

URL = "https://prices.openfoodfacts.org/api/v1/prices?product_code={ean}&size=100&order_by=-date"


def buscar(nav: Navegador, ean: str) -> list[PontoDePreco]:
    dado = nav.get_json(URL.format(ean=ean))
    if not isinstance(dado, dict):
        return []
    pontos = []
    for item in dado.get("items", []):
        if item.get("currency") != "BRL" or not item.get("price") or not item.get("date"):
            continue
        local = item.get("location") or {}
        sem_desconto = item.get("price_without_discount")
        pontos.append(
            PontoDePreco(
                ean=ean,
                preco=float(item["price"]),
                preco_de=float(sem_desconto) if sem_desconto else None,
                data_observada=item["date"][:10],
                fonte="open_prices",
                loja=local.get("osm_name") or "desconhecida",
                cidade=local.get("osm_address_city"),
                url_origem="https://prices.openfoodfacts.org",
                url_evidencia=f"https://prices.openfoodfacts.org/api/v1/prices/{item.get('id')}",
                metodo="open-prices-api",
            )
        )
    return pontos
