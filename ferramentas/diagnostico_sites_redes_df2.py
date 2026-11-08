"""Pendências: sitemaps osuper (União, Bistecão), páginas de ofertas/tabloide (Costa, Primor, Melhor, Varejão, Cristal)."""

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.robotparser import RobotFileParser

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos.rede import USER_AGENT  # noqa: E402


def pegar(url, t=20):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR"})
    try:
        with urllib.request.urlopen(req, timeout=t) as r:
            return r.status, r.read(3_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, repr(e)[:90]


def pode(base, url):
    st, txt = pegar(base + "/robots.txt")
    rp = RobotFileParser()
    rp.parse(txt.splitlines() if st == 200 else [])
    return rp.can_fetch(USER_AGENT, url), st, txt[:300].replace("\n", " | ")


for base in ["https://www.uniaosupermercados.com", "https://supermercadobistecao.com", "https://www.fortatacadista.com.br"]:
    print(f"\n===== {base} robots: {pode(base, base + '/produtos/x')}")
    for sm in ["/sitemap.xml", "/sitemap_index.xml", "/sitemaps/sitemap.xml"]:
        st, x = pegar(base + sm)
        locs = re.findall(r"<loc>([^<]+)</loc>", x)
        print(f"  {sm}: HTTP {st}, {len(locs)} locs {locs[:3]}")
        if locs:
            sub = [l for l in locs if l.endswith(".xml")]
            for s in sub[:3]:
                st2, x2 = pegar(s)
                l2 = re.findall(r"<loc>([^<]+)</loc>", x2)
                print(f"    {s}: {len(l2)} locs {l2[:2]}")
            break
    st, h = pegar(base + "/")
    print("  loja/cidade:", re.findall(r'"(?:storeName|name)":"([^"]{3,60})"', h)[:5], "| cidades:", re.findall(r"(Bras[ií]lia|S[ãa]o Sebasti[ãa]o|Ceil[âa]ndia|Samambaia|Gama|Taguatinga)", h)[:5])

for url in ["https://costaatacadao.com.br/ofertas/", "https://primorsupermercado.com.br/ofertas/",
            "https://melhoratacadista.com.br/tabloide/", "https://melhoratacadista.com.br/tabloide/areal-guara-2-riacho-fundo-2/",
            "https://www.varejaodafartura.com/ofertas", "https://www.supermercadoscristal.com.br/encarte"]:
    st, h = pegar(url)
    imgs = [i for i in sorted(set(re.findall(r'(https?://[^"\'\s]+?\.(?:jpe?g|png|webp|pdf))', h, re.I)))
            if not re.search(r"logo|icon|favicon|banner|avatar", i, re.I)]
    texto = " ".join(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S)).split())
    print(f"\n===== {url}: HTTP {st}, {len(imgs)} imagens/pdf")
    for i in imgs[:10]:
        print("   ", i)
    print("   cidades:", sorted(set(re.findall(r"(Bras[ií]lia|Guar[áa]|Riacho Fundo|Samambaia|Ceil[âa]ndia|Taguatinga|Gama|Sobradinho|Planaltina|Valpara[íi]so|Luzi[âa]nia|Cidade Ocidental|Novo Gama|[ÁA]guas Lindas|Santa Maria|Recanto)", texto))))
    print("   validade:", re.findall(r"(?:v[áa]lid[oa]s?|at[ée])[^.]{0,40}\d{1,2}/\d{1,2}", texto)[:3])
for base in ["https://costaatacadao.com.br", "https://primorsupermercado.com.br", "https://melhoratacadista.com.br"]:
    st, m = pegar(base + "/wp-json/wp/v2/media?per_page=15&_fields=source_url,date")
    if st == 200 and m.startswith("["):
        print(f"\n{base} mídia recente:", [(x["date"][:10], x["source_url"].rsplit("/", 1)[-1]) for x in json.loads(m)][:15])
