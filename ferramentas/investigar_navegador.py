"""Abre as fontes num navegador de verdade (Chromium), como uma pessoa faria, e registra o que a página carrega.

Serve para sites que só mostram os dados depois de rodar JavaScript: o navegador carrega a página, espera,
e anota cada pedido de dados que a própria página faz (JSON, planilha, CSV). Esses são os endereços que uma
pessoa usaria sem saber; com eles dá para coletar sem navegador depois.

Regras (as mesmas do resto do projeto):
  - respeita o robots.txt antes de abrir qualquer endereço;
  - o navegador se identifica: o User-Agent do Chromium leva o nome do projeto no fim;
  - se aparecer desafio anti-robô (Cloudflare, captcha), para e registra. Não resolve desafio nem finge ser humano.

Também faz o diagnóstico de rede de cada site (DNS, conexão, certificado), para saber se a falha é bloqueio
de acesso de fora do Brasil, certificado inválido ou site fora do ar.

Uso (precisa de: pip install playwright && playwright install --with-deps chromium):
    python ferramentas/investigar_navegador.py relatorios/navegador
"""

from __future__ import annotations

import json
import re
import socket
import ssl
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from historico_precos.rede import USER_AGENT  # noqa: E402

ALVOS = {
    "CEPEA": [
        "https://www.cepea.org.br/br/licenca-de-uso-de-dados.aspx",
        "https://cepea.esalq.usp.br/br/licenca-de-uso-de-dados.aspx",
        "https://www.cepea.org.br/br/indicador/cafe.aspx",
        "https://www.cepea.org.br/br/indicador/series/cafe.aspx?id=23",
    ],
    "CEASA-DF": ["https://www.ceasa.df.gov.br/", "http://www.ceasa.df.gov.br/"],
    "IPE-DF": ["https://www.ipe.df.gov.br/", "http://www.ipe.df.gov.br/"],
    "Conab Prohort": ["https://prohort.conab.gov.br/", "https://www.conab.gov.br/info-agro/hortigranjeiros-prohort"],
    "Conab Portal de Informações": ["https://portaldeinformacoes.conab.gov.br/", "https://portaldeinformacoes.conab.gov.br/download-arquivos.html"],
}

# portais de dados abertos: feitos para acesso automatizado (API CKAN)
PORTAIS = {
    "Dados abertos do DF (CEASA)": "https://dados.df.gov.br/api/3/action/package_search?q=ceasa&rows=20",
    "Dados abertos do DF (IPE-DF)": "https://dados.df.gov.br/api/3/action/package_search?q=ipedf&rows=20",
    "Dados abertos do DF (preços)": "https://dados.df.gov.br/api/3/action/package_search?q=pre%C3%A7os&rows=20",
    "Dados abertos federal (Conab)": "https://dados.gov.br/api/3/action/package_search?q=conab%20pre%C3%A7os&rows=20",
}

DESAFIO = re.compile(r"just a moment|cf-chl|challenge-platform|captcha|verify you are human|attention required", re.I)
DADO = re.compile(r"\.(json|csv|xlsx?|txt|zip|ods)(\?|$)|/api/|ajax|service|handler|\.ashx|\.asmx|webmethod", re.I)


def diagnostico_rede(host: str) -> dict:
    """DNS, conexão TCP (443 e 80) e certificado TLS, cada um com o tempo gasto."""
    d: dict = {"host": host}
    t = time.monotonic()
    try:
        d["ips"] = sorted({i[4][0] for i in socket.getaddrinfo(host, 443, proto=socket.IPPROTO_TCP)})
        d["dns_ms"] = int((time.monotonic() - t) * 1000)
    except OSError as e:
        d["dns_erro"] = str(e)
        return d
    for porta in (443, 80):
        t = time.monotonic()
        try:
            with socket.create_connection((host, porta), timeout=15):
                d[f"tcp_{porta}"] = f"ok em {int((time.monotonic() - t) * 1000)} ms"
        except OSError as e:
            d[f"tcp_{porta}"] = f"falhou: {e}"
    t = time.monotonic()
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False  # só para LER o certificado e explicar o erro; a coleta nunca desliga a verificação
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((host, 443), timeout=20) as s, ctx.wrap_socket(s, server_hostname=host) as tls:
            der = tls.getpeercert(binary_form=True)
            d["tls"] = f"handshake ok em {int((time.monotonic() - t) * 1000)} ms ({tls.version()})"
        pem = ssl.DER_cert_to_PEM_cert(der)
        nomes = re.findall(rb"(?:DNS:)?([a-z0-9*.-]+\.(?:gov\.br|org\.br|usp\.br|com\.br|br|com))", der)
        d["nomes_no_certificado"] = sorted({n.decode() for n in nomes})[:15]
        d["certificado_pem_inicio"] = pem[:80]
    except OSError as e:
        d["tls"] = f"falhou: {e}"
    try:
        ssl.create_default_context().wrap_socket(socket.create_connection((host, 443), timeout=20), server_hostname=host).close()
        d["tls_verificado"] = "certificado válido para o nome"
    except (OSError, ssl.SSLError) as e:
        d["tls_verificado"] = f"inválido: {e}"
    return d


def robots(url: str) -> tuple[RobotFileParser, int]:
    base = "{0.scheme}://{0.netloc}".format(urlsplit(url))
    rp = RobotFileParser()
    try:
        req = urllib.request.Request(base + "/robots.txt", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as r:
            rp.parse(r.read().decode("utf-8", "replace").splitlines())
            return rp, r.status
    except urllib.error.HTTPError as e:
        rp.parse([] if e.code == 404 else ["User-agent: *", "Disallow: /"] if e.code in (401, 403) else [])
        return rp, e.code
    except Exception:
        rp.parse([])
        return rp, 0


def abrir(pagina, url: str, pasta: Path) -> dict:
    pedidos = []
    pagina.on("response", lambda r: pedidos.append({"url": r.url, "status": r.status, "tipo": r.request.resource_type,
                                                    "conteudo": r.headers.get("content-type", "")}))
    info: dict = {"url": url}
    t = time.monotonic()
    try:
        resp = pagina.goto(url, wait_until="networkidle", timeout=60000)
        info["status"] = resp.status if resp else None
    except Exception as e:  # tempo esgotado, certificado, conexão
        info["erro"] = str(e).splitlines()[0][:300]
        return info
    info["ms"] = int((time.monotonic() - t) * 1000)
    texto = pagina.inner_text("body")[:200000] if pagina.query_selector("body") else ""
    html = pagina.content()
    info["titulo"] = pagina.title()
    info["desafio_antirrobo"] = bool(DESAFIO.search(html[:50000]))
    info["texto_inicio"] = " ".join(texto.split())[:1500]
    info["links_de_dados"] = sorted({a for a in re.findall(r'href=["\']([^"\']+)["\']', html) if DADO.search(a)})[:30]
    info["pedidos_de_dados"] = [p for p in pedidos if p["tipo"] in ("xhr", "fetch") or DADO.search(p["url"])][:40]
    nome = re.sub(r"[^a-z0-9]+", "-", url.lower())[:80]
    (pasta / f"{nome}.txt").write_text(texto, encoding="utf-8")
    try:
        pagina.screenshot(path=str(pasta / f"{nome}.png"), full_page=False)
    except Exception:
        pass
    return info


def investigar(pasta: Path) -> dict:
    from playwright.sync_api import sync_playwright

    pasta.mkdir(parents=True, exist_ok=True)
    resultado: dict = {"sites": {}, "portais": {}}
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        ua = navegador.new_page().evaluate("navigator.userAgent").replace("HeadlessChrome", "Chrome") + f" {USER_AGENT}"
        contexto = navegador.new_context(user_agent=ua, locale="pt-BR")
        resultado["user_agent_usado"] = ua
        for nome, urls in ALVOS.items():
            item = {"rede": diagnostico_rede(urlsplit(urls[0]).hostname), "paginas": []}
            for url in urls:
                rp, status_robots = robots(url)
                if not rp.can_fetch(USER_AGENT, url):
                    item["paginas"].append({"url": url, "robots": status_robots, "nota": "robots.txt não permite: não aberto"})
                    continue
                pagina = contexto.new_page()
                info = abrir(pagina, url, pasta)
                info["robots"] = status_robots
                if info.get("desafio_antirrobo"):
                    info["nota"] = "desafio anti-robô na página: parado aqui, sem tentar passar"
                item["paginas"].append(info)
                pagina.close()
                time.sleep(4)
            resultado["sites"][nome] = item
        navegador.close()
    for nome, url in PORTAIS.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=40) as r:
                dado = json.loads(r.read().decode("utf-8", "replace"))
            res = dado.get("result", {})
            resultado["portais"][nome] = {"total": res.get("count"), "conjuntos": [
                {"titulo": c.get("title"), "orgao": (c.get("organization") or {}).get("title"), "atualizado": c.get("metadata_modified"),
                 "recursos": [{"nome": r.get("name"), "formato": r.get("format"), "url": r.get("url")} for r in c.get("resources", [])][:8]}
                for c in res.get("results", [])]}
        except Exception as e:
            resultado["portais"][nome] = {"erro": str(e)[:300]}
        time.sleep(2)
    (pasta / "navegador.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return resultado


if __name__ == "__main__":
    r = investigar(Path(sys.argv[1] if len(sys.argv) > 1 else "relatorios/navegador"))
    print("User-Agent:", r["user_agent_usado"])
    for nome, item in r["sites"].items():
        rede = item["rede"]
        print(f"\n== {nome}: DNS {rede.get('ips') or rede.get('dns_erro')} | 443 {rede.get('tcp_443')} | 80 {rede.get('tcp_80')} | TLS {rede.get('tls')} | {rede.get('tls_verificado')}")
        for p in item["paginas"]:
            print(f"   {p.get('status')} {p['url'][:90]} {p.get('nota') or p.get('erro') or ''} "
                  f"{len(p.get('pedidos_de_dados', []))} pedido(s) de dados, {len(p.get('links_de_dados', []))} link(s) de dados")
    for nome, item in r["portais"].items():
        print(f"\n-- {nome}: {item.get('total', item.get('erro'))}")
        for c in item.get("conjuntos", [])[:8]:
            print(f"     {c['titulo']} ({c['orgao']}) {[x['formato'] for x in c['recursos']]}")
