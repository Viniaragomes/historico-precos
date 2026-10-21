"""Abre páginas permitidas de Big Box e Fort num Chromium identificado e registra os pedidos de dados que a página faz
(endereço, status e um trecho da resposta), procurando código de barras (EAN) e preço. Respeita o robots.txt de cada host."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from investigar_navegador import robots  # noqa: E402
from historico_precos.rede import USER_AGENT  # noqa: E402

PAGINAS = ["https://www.fortatacadista.com.br/categorias", "https://fortatacadista.com.br/produtos/8227963/bebcervimperio-350ml-puro-malte",
           "https://bigboxdelivery.com.br/p/3-Coracoes-Cafe-Cappuccino-400g"]
for host in ["https://api.fortatacadista.com.br", "https://api.ibecom.com.br", "https://api-legada.ibecom.com.br"]:
    rp, st = robots(host + "/x")
    print(f"robots de {host}: HTTP {st}; permite /: {rp.can_fetch(USER_AGENT, host + '/')}")

from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as p:
    nav = p.chromium.launch()
    ua = nav.new_page().evaluate("navigator.userAgent").replace("HeadlessChrome", "Chrome") + f" {USER_AGENT}"
    ctx = nav.new_context(user_agent=ua, locale="pt-BR")
    for url in PAGINAS:
        rp, _ = robots(url)
        if not rp.can_fetch(USER_AGENT, url):
            print("\n== robots.txt não permite:", url)
            continue
        pedidos = []
        pagina = ctx.new_page()

        def ao_responder(r):
            if r.request.resource_type in ("xhr", "fetch"):
                try:
                    corpo = r.text()[:3000]
                except Exception:
                    corpo = ""
                pedidos.append((r.status, r.request.method, r.url, corpo))

        pagina.on("response", ao_responder)
        try:
            resp = pagina.goto(url, wait_until="networkidle", timeout=60000)
            print(f"\n== {url}: HTTP {resp.status if resp else '?'} | título: {pagina.title()}")
        except Exception as e:
            print(f"\n== {url}: erro {str(e)[:200]}")
            continue
        texto = pagina.inner_text("body")[:100000]
        print("   EAN de 13 dígitos no texto:", sorted(set(re.findall(r"\b78\d{11}\b", texto)))[:5])
        links = sorted(set(re.findall(r'href="(/(?:categorias|produtos)/[^"]+)"', pagina.content())))
        print("   links de categoria/produto:", len(links), links[:8])
        for st, metodo, u, corpo in pedidos[:25]:
            eans = sorted(set(re.findall(r'"(?:ean|gtin|codigoBarras|barcode|codigo_barras)[^"]*"\s*:\s*"?(\d{8,14})', corpo, re.I)))[:3]
            print(f"   {st} {metodo} {u[:150]} | EAN: {eans} | {corpo[:200]!r}")
        pagina.close()
    nav.close()
