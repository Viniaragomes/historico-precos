"""Extrai o preço de uma página HTML de produto (atual ou arquivada).

Ordem de tentativa:
1. JSON-LD schema.org (Product/Offer), usado pela maioria das lojas modernas;
2. skuJson do VTEX antigo (preços em centavos), comum em cópias antigas do Wayback;
3. microdados/meta tags (itemprop="price", product:price:amount).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

_RE_JSON_LD = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I
)
_RE_SKU_JSON = re.compile(r"var\s+skuJson_\d+\s*=\s*(\{.*?\})\s*;\s*(?:CATALOG_SDK|var|</script>)", re.S)
_RE_META_PRECO = [
    re.compile(r'itemprop=["\']price["\'][^>]*content=["\']([^"\']+)["\']', re.I),
    re.compile(r'content=["\']([^"\']+)["\'][^>]*itemprop=["\']price["\']', re.I),
    re.compile(r'property=["\']product:price:amount["\'][^>]*content=["\']([^"\']+)["\']', re.I),
    re.compile(r'content=["\']([^"\']+)["\'][^>]*property=["\']product:price:amount["\']', re.I),
]


@dataclass
class PrecoExtraido:
    preco: float
    preco_de: float | None
    metodo: str
    gtin: str | None = None
    nome: str | None = None


def para_float(valor) -> float | None:
    """Converte '12.99', '12,99', 'R$ 1.234,56', 12.99 em float."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor) if valor > 0 else None
    texto = re.sub(r"[^\d,.]", "", str(valor))
    if not texto:
        return None
    if "," in texto and "." in texto:
        # o separador que aparece por último é o decimal
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        numero = float(texto)
    except ValueError:
        return None
    return numero if numero > 0 else None


def _objetos_json_ld(dado):
    if isinstance(dado, list):
        for item in dado:
            yield from _objetos_json_ld(item)
    elif isinstance(dado, dict):
        yield dado
        if "@graph" in dado:
            yield from _objetos_json_ld(dado["@graph"])


def _eh_produto(obj: dict) -> bool:
    tipo = obj.get("@type")
    tipos = tipo if isinstance(tipo, list) else [tipo]
    return "Product" in tipos


def _precos_de_ofertas(ofertas) -> list[float]:
    lista = ofertas if isinstance(ofertas, list) else [ofertas]
    precos = []
    for oferta in lista:
        if not isinstance(oferta, dict):
            continue
        preco = para_float(oferta.get("price"))
        if preco is None:
            preco = para_float(oferta.get("lowPrice"))
        if preco is None and isinstance(oferta.get("priceSpecification"), dict):
            preco = para_float(oferta["priceSpecification"].get("price"))
        if preco is not None:
            precos.append(preco)
    return precos


def precos_json_ld(html: str) -> list[PrecoExtraido]:
    resultados = []
    for bloco in _RE_JSON_LD.findall(html):
        try:
            dado = json.loads(bloco.strip())
        except json.JSONDecodeError:
            continue
        for obj in _objetos_json_ld(dado):
            if not _eh_produto(obj):
                continue
            precos = _precos_de_ofertas(obj.get("offers"))
            if not precos:
                continue
            gtin = next(
                (str(obj[k]) for k in ("gtin13", "gtin", "gtin14", "gtin12", "gtin8", "ean") if obj.get(k)),
                None,
            )
            resultados.append(PrecoExtraido(min(precos), None, "json-ld", gtin, obj.get("name")))
    return resultados


def precos_sku_json(html: str) -> list[PrecoExtraido]:
    resultados = []
    for bloco in _RE_SKU_JSON.findall(html):
        try:
            dado = json.loads(bloco)
        except json.JSONDecodeError:
            continue
        for sku in dado.get("skus", []):
            melhor = sku.get("bestPrice")
            if not melhor or not sku.get("available", True):
                continue
            lista = sku.get("listPrice")
            preco_de = lista / 100 if lista and lista > melhor else None
            resultados.append(PrecoExtraido(melhor / 100, preco_de, "sku-json", nome=dado.get("name")))
    return resultados


def preco_meta(html: str) -> PrecoExtraido | None:
    for regex in _RE_META_PRECO:
        achado = regex.search(html)
        if achado:
            preco = para_float(achado.group(1))
            if preco is not None:
                return PrecoExtraido(preco, None, "meta")
    return None


def extrair_preco(html: str, ean: str | None = None) -> PrecoExtraido | None:
    candidatos = precos_json_ld(html)
    if ean and candidatos:
        do_ean = [c for c in candidatos if c.gtin and c.gtin.lstrip("0") == ean.lstrip("0")]
        if do_ean:
            return do_ean[0]
        # se a página declara GTINs e nenhum é o nosso, o preço é de outro produto
        if all(c.gtin for c in candidatos):
            return None
    if candidatos:
        return candidatos[0]
    sku = precos_sku_json(html)
    if sku:
        return sku[0]
    return preco_meta(html)
