"""Como ler as fontes novas do estudo: sitemaps, páginas de produto, APIs e folhetos (só leitura pública, robots respeitado)."""

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos.rede import USER_AGENT  # noqa: E402

_rob = {}


def pode(url):
    p = urlsplit(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _rob:
        st, txt = pegar(base + "/robots.txt", checar=False)
        rp = RobotFileParser()
        rp.parse(txt.splitlines() if st == 200 else [])
        _rob[base] = (st, rp, txt)
    return _rob[base][1].can_fetch(USER_AGENT, url)


def pegar(url, t=25, checar=True):
    if checar and not pode(url):
        return -1, "robots.txt não permite"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR"})
    try:
        with urllib.request.urlopen(req, timeout=t) as r:
            return r.status, r.read(3_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, repr(e)[:100]


def jsonld(html):
    saida = []
    for b in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html, re.S):
        try:
            saida.append(json.loads(b))
        except Exception:
            pass
    return saida


def secao(t):
    print(f"\n===== {t}")


for loja in ["https://superveneza.instabuy.com.br", "https://supervenezacruzeiro811.instabuy.com.br", "https://bigboxdelivery.com.br"]:
    secao(loja)
    pode(loja + "/")
    print("robots.txt:", _rob[loja][2][:400].replace("\n", " | "))
    for sm in ["/sitemap.xml", "/sitemap_index.xml", "/sitemaps/sitemap.xml"]:
        st, x = pegar(loja + sm)
        locs = re.findall(r"<loc>([^<]+)</loc>", x)
        print(f"  {sm}: HTTP {st}, {len(locs)} locs, exemplos {locs[:4]}")
        if locs:
            sub = [l for l in locs if l.endswith(".xml")][:1]
            for s in sub:
                st2, x2 = pegar(s)
                l2 = re.findall(r"<loc>([^<]+)</loc>", x2)
                print(f"    sub {s}: HTTP {st2}, {len(l2)} locs, ex {l2[:3]}")
                locs = l2 or locs
            prod = next((l for l in locs if "/p/" in l), None)
            if prod:
                st3, h = pegar(prod)
                lds = jsonld(h)
                print(f"    produto {prod}: HTTP {st3}; JSON-LD tipos {[d.get('@type') for d in lds if isinstance(d, dict)]}")
                for d in lds:
                    if isinstance(d, dict) and d.get("@type") == "Product":
                        print("     ", json.dumps({k: d.get(k) for k in ("name", "brand", "gtin13", "gtin", "sku", "offers")}, ensure_ascii=False)[:500])
            break
    st, h = pegar(loja + "/")
    print(f"  home HTTP {st}; preços no HTML {len(re.findall(r'R\\$', h))}; links /p/: {sorted(set(re.findall(r'href=\"(/p/[^\"]+)\"', h)))[:3]}")

secao("Ultrabox (VTEX?)")
for u in ["https://www.ultraboxatacado.com.br/api/catalog_system/pub/category/tree/1",
          "https://www.ultraboxatacado.com.br/api/catalog_system/pub/products/search?_from=0&_to=2",
          "https://www.ultraboxatacado.com.br/"]:
    st, x = pegar(u)
    print(f"  {u}: HTTP {st} {x[:300]!r}")
    if st == 200 and x.startswith("["):
        try:
            d = json.loads(x)
            if d and "items" in d[0]:
                it = d[0]["items"][0]
                print("   EAN:", it.get("ean"), "| nome:", d[0].get("productName"), "| preço:",
                      it.get("sellers", [{}])[0].get("commertialOffer", {}).get("Price"))
        except Exception as e:
            print("   json:", e)
st, h = pegar("https://www.ultraboxatacado.com.br/")
print("  links da home:", sorted(set(re.findall(r'href="(https?://[^"]+)"', h)))[:25])
print("  robots:", _rob.get("https://www.ultraboxatacado.com.br", (0, 0, ""))[2][:400].replace("\n", " | "))

secao("Pão de Açúcar")
pode("https://www.paodeacucar.com/")
print("robots:", _rob["https://www.paodeacucar.com"][2][:700].replace("\n", " | "))
st, x = pegar("https://www.paodeacucar.com/sitemap.xml")
locs = re.findall(r"<loc>([^<]+)</loc>", x)
print(f"  sitemap HTTP {st}, {len(locs)} locs, ex {locs[:5]}")
st, h = pegar("https://www.paodeacucar.com/")
prods = sorted(set(re.findall(r'href="(/produto/[^"]+)"', h)))[:3]
print("  links /produto/ na home:", prods)
for p in prods[:1]:
    st, hp = pegar(urljoin("https://www.paodeacucar.com/", p))
    print(f"  produto HTTP {st}; JSON-LD: {json.dumps(jsonld(hp), ensure_ascii=False)[:600]}")
    print("  gtin/ean no HTML:", re.findall(r'"(?:gtin13|gtin|ean)"\s*:\s*"?(\d{8,14})', hp)[:3], "| R$:", len(re.findall(r"R\$", hp)))

secao("Tatico (WordPress)")
for u in ["https://www.taticobaratotododia.com.br/wp-json/wp/v2/pages?per_page=50&_fields=slug,link,title",
          "https://www.taticobaratotododia.com.br/wp-json/wp/v2/media?per_page=10&_fields=source_url,date,mime_type",
          "https://www.taticobaratotododia.com.br/wp-json/wp/v2/types"]:
    st, x = pegar(u)
    print(f"  {u.split('.br')[1]}: HTTP {st} {x[:700]!r}")
st, h = pegar("https://www.taticobaratotododia.com.br/")
print("  links com encarte/oferta/tabloide:", sorted(set(re.findall(r'href="([^"]*(?:encarte|oferta|tabloide|folheto)[^"]*)"', h, re.I)))[:10])
print("  pdfs:", sorted(set(re.findall(r'(https?://[^"\'\s]+\.pdf)', h)))[:5])

for nome, u in [("Portafolhetos", "https://www.portafolhetos.com.br/"), ("Kimbino Brasília", "https://www.kimbino.com.br/brasilia/")]:
    secao(nome)
    pode(u)
    print("robots:", _rob[f"https://{urlsplit(u).netloc}"][2][:500].replace("\n", " | "))
    st, h = pegar(u)
    print(f"  HTTP {st}; pdfs: {sorted(set(re.findall(r'(https?://[^\"\\s]+\\.pdf)', h)))[:6]}")
    print("  links de redes:", sorted(set(re.findall(r'href="([^"]*(?:brasilia|df|distrito|assai|atacadao|carrefour|tatico|comper|superveneza|big-box)[^"]*)"', h, re.I)))[:15])
