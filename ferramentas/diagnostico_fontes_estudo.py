"""Checagem das fontes candidatas do estudo: responde? robots.txt permite? plataforma? (só leitura pública)."""

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from historico_precos.rede import USER_AGENT  # noqa: E402

CANDIDATOS = [
    "https://superveneza.instabuy.com.br/", "https://supervenezacruzeiro811.instabuy.com.br/",
    "https://ofertas.comper.com.br/cidade/distrito-federal/", "https://www.comper.com.br/",
    "https://www.paodeacucar.com/", "https://www.taticobaratotododia.com.br/", "https://www.supermaia.com.br/",
    "https://www.ultraboxatacado.com.br/", "https://www.megaboxatacado.com.br/", "https://www.supermercadobistecao.com/",
    "https://www.supermercadosmineirao.com.br/", "https://linktr.ee/supercei", "https://superdf.com.br/",
    "https://superdf.com.br/feed/", "https://encartesdf.com.br/feed/", "https://www.kimbino.com.br/brasilia/",
    "https://www.shopfully.com.br/", "https://www.catalogosofertas.com.br/", "https://www.portafolhetos.com.br/",
    "https://www.shopper.com.br/", "https://www.ifood.com.br/", "https://www.rappi.com.br/", "https://mercado.carrefour.com.br/",
    "https://www.ubereats.com/br/city/brasilia-df", "https://api.sefaz.al.gov.br/sfz-economiza-alagoas-api/api/public/",
    "https://www.procon.df.gov.br/", "https://apisidra.ibge.gov.br/values/t/7060/n7/5301/v/63/p/last%201/c315/7169",
    "https://www.dieese.org.br/analisecestabasica/", "https://dados.df.gov.br/", "https://precodahora.ba.gov.br/",
    "https://menorpreco.notaparana.pr.gov.br/",
]


def pegar(url, t=20):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-BR"})
    try:
        with urllib.request.urlopen(req, timeout=t) as r:
            return r.status, r.read(400000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, repr(e)[:80]


for url in CANDIDATOS:
    p = urlsplit(url)
    st_r, robots = pegar(f"{p.scheme}://{p.netloc}/robots.txt")
    if st_r == 200:
        rp = RobotFileParser()
        rp.parse(robots.splitlines())
        permite = rp.can_fetch(USER_AGENT, url)
    else:
        permite = "sem robots (permitido)" if st_r == 404 else f"robots HTTP {st_r}"
    st, html = pegar(url)
    plat = [n for n, pad in [("VTEX", r"vtex"), ("Instabuy", r"instabuy|ibecom"), ("VipCommerce", r"vipcommerce"),
                             ("osuper", r"osuper"), ("Shopify", r"shopify"), ("WordPress", r"wp-content|wp-json"),
                             ("Magento", r"mage/|magento"), ("Next.js", r"__next")] if re.search(pad, html, re.I)]
    precos = len(re.findall(r"R\$\s*\d{1,4},\d{2}", html))
    gtin = bool(re.search(r'"gtin\d*"|"ean"\s*:', html, re.I))
    pdfs = len(set(re.findall(r'https?://[^"\'\s]+\.pdf', html)))
    print(f"{url}\n   página HTTP {st} | robots: {permite} | plataforma: {plat or '-'} | preços R$ no HTML: {precos} | gtin: {gtin} | pdfs: {pdfs}"
          + (f" | erro: {html}" if st == 0 else ""))
