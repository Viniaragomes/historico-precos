"""Fontes de encartes do DF acessíveis do GitHub: robots.txt, estrutura das páginas e links de ofertas."""

import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from urllib.robotparser import RobotFileParser

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos.rede import USER_AGENT  # noqa: E402


def pegar(url, t=30):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR"})
    with urllib.request.urlopen(req, timeout=t) as r:
        return r.status, r.read().decode("utf-8", "replace")


def robots(base, caminho):
    try:
        _, txt = pegar(base + "/robots.txt")
        rp = RobotFileParser()
        rp.parse(txt.splitlines())
        return rp.can_fetch(USER_AGENT, base + caminho), rp.crawl_delay(USER_AGENT)
    except Exception as e:
        return f"robots erro {e!r}"[:80], None


print("== encartesdf.com.br, 5 tentativas espaçadas")
for i in range(5):
    t = time.time()
    try:
        st, html = pegar("https://encartesdf.com.br/wp-json/wp/v2/posts?per_page=3&_fields=date,title", 40)
        print(" ", st, f"{time.time() - t:.1f}s", html[:200])
        break
    except Exception as e:
        print("  falhou", repr(e)[:100], f"{time.time() - t:.1f}s")
        time.sleep(20)

print("\n== Tiendeo")
for c in ["/brasilia/supermercados", "/brasilia/atacadao", "/brasilia/carrefour", "/brasilia/comper", "/brasilia/big-box", "/brasilia/assai"]:
    print(c, "robots:", robots("https://www.tiendeo.com.br", c))
    try:
        st, html = pegar("https://www.tiendeo.com.br" + c)
        nd = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        print("  ", st, len(html), "bytes; __NEXT_DATA__:", bool(nd), "; ld+json:", html.count("application/ld+json"))
        if nd:
            d = json.loads(nd.group(1))
            txt = json.dumps(d, ensure_ascii=False)
            print("   chaves:", list(d.get("props", {}).get("pageProps", {}).keys())[:20])
            for m in list(re.finditer(r'"(?:price|preco|salePrice|currentPrice)"\s*:\s*"?([\d.,]+)', txt))[:5]:
                print("   preço:", txt[max(0, m.start() - 200):m.end() + 20].replace("\n", " "))
            for m in list(re.finditer(r'"(?:validTo|endDate|expirationDate|validUntil|endsAt)"\s*:\s*"([^"]+)"', txt))[:3]:
                print("   validade:", m.group(1))
        for href in sorted(set(re.findall(r'href="(/[^"]*(?:catalogo|catalogos|folheto|ofert)[^"]*)"', html)))[:8]:
            print("   link:", href)
    except Exception as e:
        print("   falhou", repr(e)[:120])
    time.sleep(5)

print("\n== Sites próprios das redes do DF (procura página de encarte/ofertas)")
for base in ["https://www.tatico.com.br", "https://tatico.com.br", "https://www.supermercadotatico.com.br",
             "https://www.donadecasa.com.br", "https://www.supermercadodonadecasa.com.br", "https://www.paguepouco.com.br",
             "https://www.superpaguepouco.com.br", "https://www.ultrabox.com.br", "https://www.ultraboxsupermercados.com.br",
             "https://www.superadega.com.br", "https://www.superbom.com.br", "https://www.veneza.com.br",
             "https://www.supermercadosveneza.com.br", "https://www.comper.com.br", "https://www.assai.com.br",
             "https://www.atacadao.com.br", "https://www.bigboxdelivery.com.br", "https://www.fortatacadista.com.br",
             "https://www.atacadaodiaadia.com.br", "https://www.supermercadosdona.com.br", "https://www.olimpicosupermercados.com.br",
             "https://www.supermercadosnorte.com.br", "https://www.leaosupermercados.com.br", "https://www.mercadosuperbom.com.br"]:
    try:
        st, html = pegar(base, 20)
        links = sorted(set(re.findall(r'href="([^"]*(?:encarte|tabloide|ofertas|folheto|promoc)[^"]*)"', html, re.I)))[:6]
        pdfs = sorted(set(re.findall(r'(https?://[^"\']+\.pdf)', html)))[:3]
        print(base, st, len(html), "| links:", links, "| pdfs:", pdfs, "| robots /:", robots(base, "/")[0])
    except Exception as e:
        print(base, "falhou", repr(e)[:90])
