"""Exportação completa do Open Food Facts (caminho oficial para uso em massa): robots, tamanho e colunas."""

import gzip
import io
import urllib.request
from urllib.robotparser import RobotFileParser

UA = "HistoricoPrecosBot/0.1 (pesquisa de precos ao consumidor; respeita robots.txt)"
for base in ["https://static.openfoodfacts.org", "https://world.openfoodfacts.org"]:
    rp = RobotFileParser(base + "/robots.txt")
    rp.read()
    for caminho in ["/data/en.openfoodfacts.org.products.csv.gz", "/api/v2/search?countries_tags_en=brazil"]:
        print(base + caminho, "permitido:", rp.can_fetch(UA, base + caminho))
url = "https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz"
req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
with urllib.request.urlopen(req, timeout=60) as r:
    print("tamanho:", int(r.headers.get("Content-Length", 0)) / 1e6, "MB", "| modificado:", r.headers.get("Last-Modified"))
req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-400000"})
with urllib.request.urlopen(req, timeout=60) as r:
    pedaco = r.read()
try:
    texto = gzip.GzipFile(fileobj=io.BytesIO(pedaco)).read(200000).decode("utf-8", "replace")
except EOFError as e:
    texto = ""
    print("pedaço incompleto (esperado):", e)
d = gzip.decompressobj(16 + 15)
texto = d.decompress(pedaco)[:200000].decode("utf-8", "replace")
cab = texto.splitlines()[0].split("\t")
print("colunas:", len(cab), [c for c in cab if c in ("code", "product_name", "brands", "quantity", "countries_tags", "countries_en", "product_name_pt")])
