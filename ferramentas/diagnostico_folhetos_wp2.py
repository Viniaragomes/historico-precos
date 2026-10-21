"""Ofertas do Dia a Dia (tipo 'ofertas') e o folheto da Dona (como a página carrega as imagens)."""

import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos.rede import USER_AGENT  # noqa: E402


def pegar(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


d = json.loads(pegar("https://ofertas.diaadiaatacadista.com.br/wp-json/wp/v2/ofertas?per_page=40"))
print(len(d), "ofertas")
for x in d[:40]:
    print(x["id"], x["date"], x["slug"], "|", x["title"]["rendered"], "| acf:", json.dumps(x.get("acf"), ensure_ascii=False)[:500],
          "| futuro:", json.dumps(x.get("publishpress_future_action"), ensure_ascii=False)[:150],
          "| tax:", {k: v for k, v in x.items() if isinstance(v, list) and k not in ("class_list",) and v}, "| classes:", x.get("class_list"))
print("\nchaves:", sorted(d[0].keys()))
print("conteúdo do 1º:", json.dumps(d[0].get("content"), ensure_ascii=False)[:600])
for tax in ["regiao", "regioes", "loja", "lojas", "cidade", "estado"]:
    try:
        print(tax, pegar(f"https://ofertas.diaadiaatacadista.com.br/wp-json/wp/v2/{tax}?per_page=100")[:1500])
    except Exception as e:
        print(tax, "->", repr(e)[:60])

print("\n== Dona: página do folheto")
h = pegar("https://donafazbem.com.br/folheto/ofertas/")
for padrao in [r'https?:[^"\'\s]+?\.pdf', r'https?:[^"\'\s]+?wp-content/uploads/[^"\'\s]+?\.(?:jpe?g|png|webp)', r'(?:flipbook|dflip|real3d|issuu|calameo|yumpu|publitas|heyzine|fliphtml5)[^"\'\s<>]{0,120}']:
    print(padrao[:30], sorted(set(re.findall(padrao, h.replace("\\/", "/"), re.I)))[:15])
i = h.find("folheto")
print(" ", " ".join(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S)).split())[:1200])
