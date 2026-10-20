"""Investiga por que uma fonte não responde, lendo só o que é público e permitido.

Para cada site: robots.txt, página inicial (se o robots permitir), cabeçalhos que indicam proteção
contra robôs (Cloudflare, Akamai), tecnologia do site e endereços de dados citados no HTML.
Não tenta contornar nada: se o robots.txt proíbe ou há desafio anti-robô, apenas registra.

Uso: python ferramentas/investigar_fontes.py relatorios/investigacao
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from historico_precos.rede import USER_AGENT, Navegador  # noqa: E402

ALVOS = {
    "Carrefour Mercado": ["https://mercado.carrefour.com.br/", "https://mercado.carrefour.com.br/api/catalog_system/pub/products/search?_from=0&_to=0"],
    "Carrefour (loja geral)": ["https://www.carrefour.com.br/"],
    "Pão de Açúcar": ["https://www.paodeacucar.com/", "https://www.paodeacucar.com/busca?terms=cafe"],
    "Comper": ["https://www.comper.com.br/"],
    "Diário Oficial da União": ["https://www.in.gov.br/", "https://www.in.gov.br/consulta/-/buscar/dou?q=ICMS"],
    "LexML (leis, Senado)": ["https://www.lexml.gov.br/busca/SRU?operation=searchRetrieve&version=1.1&query=urn%3D%22lei%22%20and%20description%3Dicms&maximumRecords=3"],
    "Confaz (convênios ICMS)": ["https://www.confaz.fazenda.gov.br/legislacao/convenios"],
    "Painéis da Secretaria de Economia do DF": ["https://paineis.fazenda.df.gov.br/", "https://paineis.fazenda.df.gov.br/mapadeprecos/"],
    "Receita do DF": ["https://www.receita.fazenda.df.gov.br/"],
}

SINAIS_ANTIROBO = {
    "cloudflare": ["cf-ray", "cf-mitigated", "just a moment", "challenge-platform", "__cf_chl"],
    "akamai": ["akamai", "x-akamai", "reference #", "access denied"],
    "datadome": ["datadome"],
    "perimeterx/human": ["px-captcha", "_pxhd", "perimeterx"],
    "captcha": ["captcha", "recaptcha", "hcaptcha"],
}
TECNOLOGIAS = {
    "vtex": ["vtex", "vteximg", "vtexassets"],
    "next.js": ["__next_data__", "/_next/"],
    "nuxt": ["__nuxt", "/_nuxt/"],
    "angular": ["ng-version", "ng-app"],
    "power bi": ["powerbi"],
    "qlik": ["qlik"],
}


def baixar(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    inicio = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            corpo, status, cab = r.read(), r.status, dict(r.headers)
    except urllib.error.HTTPError as e:
        corpo, status, cab = e.read(), e.code, dict(e.headers or {})
    except Exception as e:  # rede, TLS, tempo esgotado
        return {"url": url, "status": 0, "erro": str(e)[:300], "ms": int((time.monotonic() - inicio) * 1000)}
    texto = Navegador._decodificar(Navegador._descomprimir(corpo, cab.get("Content-Encoding")), None)
    return {"url": url, "status": status, "ms": int((time.monotonic() - inicio) * 1000), "cabecalhos": cab, "texto": texto}


def analisar(resposta: dict) -> dict:
    if resposta["status"] == 0:
        return {k: resposta[k] for k in ("url", "status", "erro", "ms")}
    texto = resposta["texto"]
    baixo = (texto[:20000] + " " + " ".join(f"{k}: {v}" for k, v in resposta["cabecalhos"].items())).lower()
    titulo = re.search(r"<title[^>]*>(.*?)</title>", texto, re.S | re.I)
    hosts = sorted({urlsplit(u).netloc for u in re.findall(r"https?://[a-z0-9.-]+\.[a-z]{2,}[^\s\"'<>)]*", texto)
                    if any(p in u for p in ("api", "search", "busca", "catalog", "graphql"))})
    return {
        "url": resposta["url"],
        "status": resposta["status"],
        "ms": resposta["ms"],
        "titulo": " ".join(titulo.group(1).split())[:120] if titulo else None,
        "servidor": resposta["cabecalhos"].get("Server") or resposta["cabecalhos"].get("server"),
        "antirrobo": [nome for nome, sinais in SINAIS_ANTIROBO.items() if any(s in baixo for s in sinais)],
        "tecnologia": [nome for nome, sinais in TECNOLOGIAS.items() if any(s in baixo for s in sinais)],
        "tem_json_ld": "application/ld+json" in baixo,
        "enderecos_de_dados": hosts[:15],
        "inicio_do_texto": " ".join(re.sub(r"<[^>]+>", " ", texto).split())[:400],
    }


def investigar(pasta: Path) -> dict:
    pasta.mkdir(parents=True, exist_ok=True)
    resultado = {}
    for nome, urls in ALVOS.items():
        base = "{0.scheme}://{0.netloc}".format(urlsplit(urls[0]))
        robots = baixar(base + "/robots.txt")
        rp = RobotFileParser()
        rp.parse(robots.get("texto", "").splitlines() if robots["status"] == 200 else [])
        bloqueado_robots = robots["status"] in (401, 403)
        item = {"robots": {"status": robots["status"], "erro": robots.get("erro"),
                           "conteudo": (robots.get("texto") or "")[:3000] if robots["status"] == 200 else None,
                           "analise": analisar(robots) if robots["status"] not in (0, 200) else None},
                "paginas": []}
        for url in urls:
            permitido = not bloqueado_robots and rp.can_fetch(USER_AGENT, url)
            if not permitido:
                item["paginas"].append({"url": url, "status": None, "nota": "robots.txt não permite: não acessado"})
                continue
            time.sleep(3)
            resp = baixar(url)
            item["paginas"].append(analisar(resp))
            if resp["status"] and resp.get("texto"):
                arquivo = re.sub(r"[^a-z0-9]+", "-", url.lower())[:80] + ".html"
                (pasta / arquivo).write_text(resp["texto"][:400000], encoding="utf-8")
        resultado[nome] = item
        time.sleep(2)
    (pasta / "investigacao.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return resultado


if __name__ == "__main__":
    r = investigar(Path(sys.argv[1] if len(sys.argv) > 1 else "relatorios/investigacao"))
    for nome, item in r.items():
        print(f"\n== {nome}: robots {item['robots']['status']}")
        for p in item["paginas"]:
            print(f"   {p.get('status')} {p['url'][:80]} {p.get('antirrobo') or ''} {p.get('tecnologia') or ''} {p.get('nota') or p.get('erro') or ''}")
