"""Investiga cada fonte e procura os dados direto nas páginas públicas, sem depender de API.

Para cada site: robots.txt, página inicial e cabeçalhos (proteção anti-robô, tecnologia). Depois procura
dados que o próprio site entrega a qualquer visitante:
  - dados estruturados embutidos na página (JSON-LD de produto, com nome, GTIN e preço);
  - estado da aplicação embutido no HTML (__NEXT_DATA__, __NUXT__, __APOLLO_STATE__ e outros JSON em <script>);
  - endereços de dados citados nos scripts públicos do site (o mesmo que a página chama);
  - mapa do site (sitemap), para achar páginas de produto que o robots.txt libera.
Não contorna nada: respeita o robots.txt, se identifica como robô e, se há desafio anti-robô, só registra.

Uso: python ferramentas/investigar_fontes.py relatorios/investigacao
"""

from __future__ import annotations

import gzip
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
    "LexML (leis, Senado)": ["https://www.lexml.gov.br/sru?operation=searchRetrieve&version=1.1&query=urn%3D%22lei%22%20and%20description%3Dicms&maximumRecords=3"],
    "Confaz (convênios ICMS)": ["https://www.confaz.fazenda.gov.br/legislacao/convenios"],
    "Painéis da Secretaria de Economia do DF": ["https://paineis.fazenda.df.gov.br/", "https://paineis.fazenda.df.gov.br/mapadeprecos/"],
    "Mapa de Preços DF (script do painel)": ["https://paineis.fazenda.df.gov.br/mapadeprecos/assets/js/app.js"],
    "Servidor Qlik da Fazenda DF": ["https://qap.fazenda.df.gov.br/paineis/resources/assets/external/requirejs/require.js"],
    "Receita do DF": ["https://www.receita.fazenda.df.gov.br/"],
}

# sites em que vale procurar páginas de produto pelo sitemap
EXPLORAR_SITEMAP = {"Carrefour Mercado", "Pão de Açúcar", "Comper"}
PADRAO_PRODUTO = re.compile(r"(/p$|/p/|/produto/|/produtos/\d|/prod/)", re.I)

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
    "wordpress": ["wp-content", "wp-json"],
}
ESTADOS_EMBUTIDOS = ["__NEXT_DATA__", "__NUXT__", "__APOLLO_STATE__", "__PRELOADED_STATE__", "__INITIAL_STATE__",
                     "__STATE__", "__RUNTIME__", "__REDUX_STATE__"]


def baixar(url: str, limite: int = 3_000_000) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*", "Accept-Encoding": "gzip"})
    inicio = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            corpo, status, cab = r.read(limite), r.status, dict(r.headers)
    except urllib.error.HTTPError as e:
        corpo, status, cab = e.read(200_000), e.code, dict(e.headers or {})
    except Exception as e:  # rede, TLS, tempo esgotado
        return {"url": url, "status": 0, "erro": str(e)[:300], "ms": int((time.monotonic() - inicio) * 1000)}
    if url.endswith(".gz") and corpo[:2] == b"\x1f\x8b":
        corpo = gzip.decompress(corpo)
    texto = Navegador._decodificar(Navegador._descomprimir(corpo, cab.get("Content-Encoding")), None)
    return {"url": url, "status": status, "ms": int((time.monotonic() - inicio) * 1000), "cabecalhos": cab, "texto": texto}


def _arquivo(url: str, sufixo: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", url.lower())[:80] + sufixo


# ---------------- dados embutidos na página ----------------

def _produtos_json_ld(no, saida: list) -> None:
    if isinstance(no, list):
        for x in no:
            _produtos_json_ld(x, saida)
    elif isinstance(no, dict):
        tipo = no.get("@type")
        if "Product" in (tipo if isinstance(tipo, list) else [tipo]):
            ofertas = no.get("offers") or {}
            ofertas = ofertas[0] if isinstance(ofertas, list) and ofertas else ofertas
            if isinstance(ofertas, dict) and isinstance(ofertas.get("offers"), list) and ofertas["offers"]:
                ofertas = ofertas["offers"][0]
            ofertas = ofertas if isinstance(ofertas, dict) else {}
            marca = no.get("brand")
            saida.append({
                "nome": no.get("name"),
                "gtin": no.get("gtin13") or no.get("gtin") or no.get("gtin14") or no.get("gtin8") or no.get("sku"),
                "marca": marca.get("name") if isinstance(marca, dict) else marca,
                "preco": ofertas.get("price") or ofertas.get("lowPrice"),
                "moeda": ofertas.get("priceCurrency"),
                "disponibilidade": ofertas.get("availability"),
            })
        for v in no.values():
            if isinstance(v, (dict, list)):
                _produtos_json_ld(v, saida)


def _chaves_com(no, alvos: tuple, caminho: str = "", achados: list | None = None, prof: int = 0, dentro: bool = False) -> list:
    """Caminhos de chaves que parecem preço/GTIN dentro de um JSON (para saber onde o dado está).
    Se a chave é um objeto (ex.: price: {value: 9.99}), os valores dentro dele também entram."""
    achados = [] if achados is None else achados
    if prof > 12 or len(achados) >= 25:
        return achados
    if isinstance(no, dict):
        for k, v in no.items():
            c = f"{caminho}.{k}"
            casa = dentro or any(a in str(k).lower() for a in alvos)
            if casa and not isinstance(v, (dict, list)):
                achados.append(f"{c} = {str(v)[:60]}")
            _chaves_com(v, alvos, c, achados, prof + 1, casa)
    elif isinstance(no, list):
        for i, v in enumerate(no[:5]):
            _chaves_com(v, alvos, f"{caminho}[{i}]", achados, prof + 1, dentro)
    return achados


def dados_embutidos(texto: str) -> dict:
    """O que a própria página já entrega em dados, sem chamar API nenhuma."""
    produtos, tipos = [], set()
    for bloco in re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', texto, re.S | re.I):
        try:
            dado = json.loads(bloco.strip())
        except json.JSONDecodeError:
            continue
        for x in dado if isinstance(dado, list) else [dado]:
            if isinstance(x, dict):
                for y in [x] + [g for g in x.get("@graph", []) if isinstance(g, dict)]:
                    t = y.get("@type")
                    tipos.update(str(i) for i in (t if isinstance(t, list) else [t]) if i)
        _produtos_json_ld(dado, produtos)

    estados = {}
    for nome in ESTADOS_EMBUTIDOS:
        if nome not in texto:
            continue
        info: dict = {"presente": True}
        bloco = re.search(rf'<script[^>]*id=["\']{nome}["\'][^>]*>(.*?)</script>', texto, re.S)
        if bloco:
            info["tamanho"] = len(bloco.group(1))
            try:
                info["campos_de_preco_ou_gtin"] = _chaves_com(json.loads(bloco.group(1)), ("price", "preco", "gtin", "ean"))
            except json.JSONDecodeError:
                info["json_valido"] = False
        estados[nome] = info

    return {
        "json_ld_tipos": sorted(tipos),
        "produtos_json_ld": produtos[:5],
        "estados_embutidos": estados,
        "outros_json_em_script": re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*id=["\']([^"\']+)', texto, re.I)[:15],
        "meta_preco": re.findall(r'<meta[^>]+(?:property|itemprop)=["\'](?:product:price:amount|price)["\'][^>]+content=["\']([^"\']+)', texto, re.I)[:3],
    }


# ---------------- scripts públicos: endereços de dados e identificadores ----------------

_RE_ENDERECO = re.compile(r"""["'`]((?:https?://[a-z0-9.-]+)?/[a-z0-9_./{}$-]*(?:api|graphql|search|busca|catalog|produto|product|price|preco|qrs|sense)[a-z0-9_./{}$?=&-]*)["'`]""", re.I)
_RE_GUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)


def pistas_do_script(texto: str) -> dict:
    """Endereços e identificadores que o script do site usa para buscar os próprios dados."""
    enderecos = sorted({e for e in _RE_ENDERECO.findall(texto) if len(e) < 200 and not e.endswith((".png", ".svg", ".css", ".jpg"))})
    qlik = None
    if "openApp" in texto or "getObject(" in texto:
        qlik = {
            "app_ids": sorted(set(_RE_GUID.findall(texto)))[:20],
            "objetos": sorted(set(re.findall(r"getObject\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]", texto)))[:40],
            "config": re.findall(r"(host|prefix|port|isSecure)\s*:\s*['\"]?([^,'\"}\s]+)", texto)[:10],
        }
    return {"enderecos": enderecos[:40], "qlik": qlik}


def scripts_do_site(html: str, base: str) -> list[str]:
    host = urlsplit(base).netloc
    urls = [urljoin(base, s) for s in re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.I)]
    return [u for u in urls if urlsplit(u).netloc == host and not re.search(r"jquery|bootstrap|vendor|polyfill|gtag", u, re.I)]


# ---------------- sitemap ----------------

def explorar_sitemap(robots_txt: str, base: str, rp: RobotFileParser, pasta: Path, max_arquivos: int = 6) -> dict:
    """Segue o sitemap indicado no robots.txt, conta páginas de produto e lê duas delas (se permitidas)."""
    fila = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots_txt) or [base + "/sitemap.xml"]
    vistos, produtos, total, avisos = [], [], 0, []
    while fila and len(vistos) < max_arquivos:
        url = fila.pop(0)
        if not rp.can_fetch(USER_AGENT, url):
            avisos.append(f"robots não permite {url}")
            continue
        time.sleep(3)
        r = baixar(url, limite=20_000_000)
        vistos.append({"url": url, "status": r["status"], "erro": r.get("erro")})
        if r["status"] != 200:
            continue
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r["texto"])
        if "<sitemapindex" in r["texto"]:
            locs.sort(key=lambda u: 0 if re.search(r"product|produto|sku|catalog", u, re.I) else 1)
            fila = locs + fila
        else:
            total += len(locs)
            produtos += [u for u in locs if PADRAO_PRODUTO.search(urlsplit(u).path)]
    amostras = []
    for url in [u for u in produtos if rp.can_fetch(USER_AGENT, u)][:2]:
        time.sleep(3)
        r = baixar(url)
        item = {"url": url, "status": r["status"], "erro": r.get("erro")}
        if r.get("texto"):
            item["antirrobo"] = analisar(r).get("antirrobo")
            item["dados"] = dados_embutidos(r["texto"])
            (pasta / _arquivo(url, ".html")).write_text(r["texto"][:400000], encoding="utf-8")
        amostras.append(item)
    return {"arquivos_lidos": vistos, "urls_listadas": total, "paginas_de_produto": len(produtos),
            "exemplos": produtos[:5], "amostras": amostras, "avisos": avisos}


# ---------------- análise geral ----------------

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
                "paginas": [], "scripts": []}
        scripts = []
        for url in urls:
            if bloqueado_robots or not rp.can_fetch(USER_AGENT, url):
                item["paginas"].append({"url": url, "status": None, "nota": "robots.txt não permite: não acessado"})
                continue
            time.sleep(3)
            resp = baixar(url)
            info = analisar(resp)
            if resp.get("texto"):
                e_script = urlsplit(url).path.endswith(".js")
                if e_script:
                    info["pistas"] = pistas_do_script(resp["texto"])
                else:
                    info["dados_embutidos"] = dados_embutidos(resp["texto"])
                    scripts += scripts_do_site(resp["texto"], url)
                (pasta / _arquivo(url, ".js" if e_script else ".html")).write_text(resp["texto"][:400000], encoding="utf-8")
            item["paginas"].append(info)
        # scripts do próprio site (no máximo 4): que endereços de dados a página usa?
        for s in [s for s in dict.fromkeys(scripts) if s not in urls][:4]:
            if bloqueado_robots or not rp.can_fetch(USER_AGENT, s):
                continue
            time.sleep(2)
            r = baixar(s)
            item["scripts"].append({"url": s, **pistas_do_script(r["texto"])} if r["status"] == 200 else {"url": s, "status": r["status"]})
        if nome in EXPLORAR_SITEMAP and not bloqueado_robots and robots["status"] == 200:
            item["sitemap"] = explorar_sitemap(robots["texto"], base, rp, pasta)
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
            d = p.get("dados_embutidos") or {}
            if d.get("produtos_json_ld") or d.get("estados_embutidos"):
                print(f"      dados na página: JSON-LD {d.get('json_ld_tipos')} estados {list(d.get('estados_embutidos', {}))}")
        for s in item["scripts"]:
            if s.get("enderecos") or s.get("qlik"):
                print(f"      script {s['url'][:80]}: {len(s.get('enderecos', []))} endereço(s) de dados {'+ Qlik' if s.get('qlik') else ''}")
        if "sitemap" in item:
            sm = item["sitemap"]
            print(f"   sitemap: {sm['urls_listadas']} URLs, {sm['paginas_de_produto']} de produto; amostras: "
                  + "; ".join(f"{a['status']} com {len((a.get('dados') or {}).get('produtos_json_ld', []))} produto(s) no JSON-LD" for a in sm["amostras"]))
