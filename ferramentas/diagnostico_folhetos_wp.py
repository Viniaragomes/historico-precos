"""JSON público (WordPress) dos folhetos da Dona e das ofertas do Dia a Dia."""

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


for url in ["https://donafazbem.com.br/wp-json/wp/v2/folheto?per_page=5",
            "https://donafazbem.com.br/wp-json/wp/v2/folheto/6741",
            "https://donafazbem.com.br/wp-json/wp/v2/types",
            "https://ofertas.diaadiaatacadista.com.br/wp-json/wp/v2/types",
            "https://ofertas.diaadiaatacadista.com.br/wp-json/wp/v2/posts?per_page=5",
            "https://ofertas.diaadiaatacadista.com.br/wp-json/wp/v2/media?per_page=10"]:
    print("\n==", url)
    try:
        t = pegar(url)
    except Exception as e:
        print("  falhou", repr(e)[:150])
        continue
    try:
        d = json.loads(t)
    except Exception:
        print("  não é JSON:", t[:300])
        continue
    itens = d if isinstance(d, list) else [d]
    if isinstance(d, dict) and "id" not in d:
        print("  tipos:", {k: v.get("rest_base") for k, v in d.items() if isinstance(v, dict)})
        continue
    for x in itens[:5]:
        print("  id", x.get("id"), x.get("date"), x.get("link"), "| título:", (x.get("title") or {}).get("rendered"))
        print("    chaves:", sorted(x.keys())[:40])
        for k in ("acf", "meta", "metadata"):
            if x.get(k):
                print("   ", k, json.dumps(x[k], ensure_ascii=False)[:800])
        html = (x.get("content") or {}).get("rendered", "") + json.dumps(x.get("acf") or {})
        imgs = sorted(set(re.findall(r'(https?:[^"\'\s]+?\.(?:jpe?g|png|webp|pdf))', html.replace("\\/", "/"), re.I)))
        print("    imagens/pdf:", len(imgs), imgs[:8])
        print("    texto:", " ".join(re.sub(r"<[^>]+>", " ", html).split())[:300])
        if x.get("source_url"):
            print("    mídia:", x["source_url"], x.get("media_details", {}).get("width"), x.get("media_details", {}).get("height"))

print("\n== página do Dia a Dia (estrutura)")
h = pegar("https://ofertas.diaadiaatacadista.com.br/")
for m in sorted(set(re.findall(r'(?:src|href|data-src)="([^"]+)"', h)))[:80]:
    if not re.search(r"\.css|fav/|\.js", m):
        print("  ", m)
print(" ", " ".join(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S)).split())[:1500])
