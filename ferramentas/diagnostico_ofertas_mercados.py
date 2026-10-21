"""Páginas de ofertas/encartes nos sites dos mercados do DF: o que dá para ler (robots, preços, imagens, APIs)."""

import re
import sys
import time
import urllib.request
from pathlib import Path
from urllib.robotparser import RobotFileParser
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos.rede import USER_AGENT  # noqa: E402

URLS = [
    "https://donafazbem.com.br/ofertas", "https://donafazbem.com.br/folheto/ofertas",
    "https://www.fortatacadista.com.br/encartes", "https://www.fortatacadista.com.br/promocoes",
    "https://www.bigboxdelivery.com.br/promocoes",
    "https://ofertas.diaadiaatacadista.com.br", "https://diaadiaatacadista.com.br/clube-dd/ofertas-selecionadas",
    "https://www.superadega.com.br/ofertas/", "https://www.atacadao.com.br/ofertas", "https://www.veneza.com.br",
    "https://www.superbom.com.br",
]
_robots = {}


def pegar(url, t=30):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR"})
    with urllib.request.urlopen(req, timeout=t) as r:
        return r.status, r.geturl(), r.read().decode("utf-8", "replace")


def pode(url):
    p = urlsplit(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        try:
            _, _, txt = pegar(base + "/robots.txt", 20)
            rp = RobotFileParser()
            rp.parse(txt.splitlines())
            _robots[base] = rp
        except Exception as e:
            _robots[base] = f"robots: {e!r}"[:60]
    rp = _robots[base]
    return rp if isinstance(rp, str) else rp.can_fetch(USER_AGENT, url)


for url in URLS:
    print("\n==", url, "| robots permite:", pode(url))
    try:
        st, final, html = pegar(url)
    except Exception as e:
        print("   falhou", repr(e)[:150])
        continue
    texto = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    texto = " ".join(re.sub(r"<[^>]+>", " ", texto).split())
    precos = re.findall(r"R\$\s*\d{1,4},\d{2}", texto)
    print("  ", st, final, len(html), "bytes;", len(precos), "preços no texto; __NEXT_DATA__:", "__NEXT_DATA__" in html,
          "; ld+json:", html.count("application/ld+json"), "; __NUXT__:", "__NUXT__" in html)
    for m in list(re.finditer(r"R\$\s*\d{1,4},\d{2}", texto))[:8]:
        print("    ·", texto[max(0, m.start() - 90):m.end()])
    imgs = sorted(set(re.findall(r'(?:src|href|data-src)="([^"]+\.(?:jpe?g|png|webp|pdf)[^"]*)"', html, re.I)))
    enc = [i for i in imgs if re.search(r"encarte|folheto|tabloid|oferta|promo", i, re.I)]
    print("   imagens/pdf de encarte:", len(enc), enc[:6])
    apis = sorted(set(re.findall(r'https?://[a-z0-9.-]+/(?:api|graphql|v\d)[^"\'\s<>]{0,80}', html)))[:8]
    print("   apis citadas:", apis)
    for href in sorted(set(re.findall(r'href="([^"]*(?:encarte|folheto|tabloide|ofertas?|promoc)[^"]*)"', html, re.I)))[:10]:
        print("   link:", href)
    time.sleep(3)
