"""Testa os sites oficiais das redes do DF: robots, plataforma, preços, sitemap de produtos, encarte (WordPress/PDF)."""

import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos.rede import USER_AGENT  # noqa: E402

SITES = """https://www.uniaosupermercados.com
https://supercei.com.br
https://bellaviajardimbotanico.instabuy.com.br
https://bellaviasupermercados.com.br
https://supermercadobistecao.com
https://www.supermercadoscristal.com.br
https://www.varejaodafartura.com
https://primorsupermercado.com.br
https://costaatacadao.com.br
https://www.supermercadocaprichoso.com.br
https://grupovivendas.com.br
https://melhoratacadista.com.br
https://bonamixatacarejo.com.br
https://superdonadecasa.com.br
https://donadecasasupermercados.com.br
https://mercadopontoalto.com.br
https://www.extramercado.com.br
https://www.clubeextra.com.br
https://qi23.bigboxdelivery.com.br
https://105sudoeste.bigboxdelivery.com.br
https://lagosul.bigboxdelivery.com.br
https://loja.obahortifruti.com.br""".split()


def pegar(url, t=20):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR"})
    try:
        with urllib.request.urlopen(req, timeout=t) as r:
            return r.status, r.geturl(), r.read(2_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, url, ""
    except Exception as e:
        return 0, url, repr(e)[:90]


for site in SITES:
    base = f"{urlsplit(site).scheme}://{urlsplit(site).netloc}"
    st_r, _, robots = pegar(base + "/robots.txt")
    rp = RobotFileParser()
    rp.parse(robots.splitlines() if st_r == 200 else [])
    if st_r in (401, 403):
        print(f"\n{site}: robots.txt HTTP {st_r} (recusa robôs)")
        continue
    st, final, h = pegar(site)
    plat = [n for n, pad in [("VTEX", r"vtex"), ("Instabuy", r"instabuy|ibecom"), ("VipCommerce", r"vipcommerce"),
                             ("osuper", r"osuper"), ("Shopify", r"cdn\.shopify"), ("WordPress", r"wp-content|wp-json"),
                             ("Wix", r"wixstatic|_wix"), ("LojaIntegrada", r"lojaintegrada"), ("Tray", r"tray\.com")] if re.search(pad, h, re.I)]
    sinal = re.findall(r"Content-Signal:\s*([^\n]+)", robots)
    print(f"\n{site} -> HTTP {st} {final if final != site else ''} | robots {st_r} permite home: {rp.can_fetch(USER_AGENT, site)}"
          f"{' | sinal ' + sinal[0] if sinal else ''} | plataforma {plat or '-'} | R$ no HTML: {len(re.findall(r'R\\$', h))}"
          + (f" | erro {h}" if st == 0 else ""))
    links = sorted(set(re.findall(r'href="([^"]*(?:encarte|oferta|tabloide|folheto|promoc)[^"]*)"', h, re.I)))[:6]
    pdfs = sorted(set(re.findall(r'(https?://[^"\'\s]+\.pdf)', h)))[:4]
    if links or pdfs:
        print("   ofertas:", links, "pdfs:", pdfs)
    if "WordPress" in plat:
        sm, _, m = pegar(base + "/wp-json/wp/v2/media?per_page=6&_fields=source_url,date")
        if sm == 200 and m.startswith("["):
            print("   mídia WP:", [(x.get("date", "")[:10], x.get("source_url", "").rsplit("/", 1)[-1]) for x in json.loads(m)])
    ss, _, x = pegar(base + "/sitemap.xml")
    locs = re.findall(r"<loc>([^<]+)</loc>", x)
    if ss == 200 and locs:
        prods = [l for l in locs if "/p/" in l]
        print(f"   sitemap: {len(locs)} endereços, {len(prods)} de produto (/p/)")
        if "Instabuy" in plat and prods:
            sp, _, hp = pegar(prods[min(5, len(prods) - 1)])
            for b in re.findall(r'<script[^>]+ld\+json[^>]*>(.*?)</script>', hp, re.S):
                try:
                    d = json.loads(b)
                except Exception:
                    continue
                if isinstance(d, dict) and d.get("@type") == "Product":
                    print("   produto:", d.get("name"), (d.get("offers") or {}).get("price"), "| loja:",
                          re.search(r'"name":"([^"]+)","description', hp).group(1) if re.search(r'"name":"([^"]+)","description', hp) else "")
    time.sleep(1)

print("\n===== Big Box: mesmo produto em lojas diferentes (preço por loja?)")
prod = "/p/3-Coracoes-Cafe-Cappuccino-400g"
for sub in ["https://bigboxdelivery.com.br", "https://qi23.bigboxdelivery.com.br", "https://105sudoeste.bigboxdelivery.com.br",
            "https://lagosul.bigboxdelivery.com.br"]:
    st, _, h = pegar(sub + prod)
    preco = re.findall(r'"price":\s*"?([\d.]+)', h)[:1]
    loja = re.findall(r'"name":"(BIG BOX[^"]+)"', h)[:1]
    print(f"  {sub}: HTTP {st} preço {preco} loja {loja}")
st, _, h = pegar("https://bigboxdelivery.com.br/")
subs = sorted(set(re.findall(r"https?://([a-z0-9-]+)\.bigboxdelivery\.com\.br", h)))
print("  subdomínios citados na home:", subs)
