"""Quais redes de supermercado do DF têm catálogo online legível de forma legítima?

Para cada site: robots.txt, tecnologia (VTEX tem API pública de catálogo), teste da API de busca VTEX (se o
robots permitir), sitemap com páginas de produto e uma amostra lida (JSON-LD com GTIN e preço).
Sem contornar nada: robots respeitado, robô identificado, desafio anti-robô só registrado.
"""

import json
import re
import sys
import time
from pathlib import Path
from urllib.robotparser import RobotFileParser

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import investigar_fontes as inv  # noqa: E402
from historico_precos.rede import USER_AGENT  # noqa: E402

MERCADOS = {
    "Atacadão Dia a Dia": ["https://www.atacadaodiaadia.com.br", "https://atacadaodiaadia.com.br"],
    "Assaí Atacadista": ["https://www.assai.com.br"],
    "Big Box": ["https://www.bigboxdelivery.com.br", "https://bigboxdelivery.com.br"],
    "Dona (Dona Fazbem)": ["https://donafazbem.com.br", "https://www.donadelivery.com.br"],
    "Pague Pouco": ["https://www.paguepouco.com.br", "https://paguepouco.com.br"],
    "Fort Atacadista": ["https://www.fortatacadista.com.br"],
    "Tatico": ["https://www.tatico.com.br", "https://supermercadostatico.com.br"],
    "Super Adega": ["https://www.superadega.com.br"],
    "Ultrabox": ["https://www.ultrabox.com.br"],
    "Oba Hortifruti": ["https://www.obahortifruti.com.br"],
    "Veneza": ["https://www.supermercadoveneza.com.br"],
    "Superbom": ["https://www.superbom.com.br"],
    "Carrefour Mercado": ["https://mercado.carrefour.com.br"],
    "Atacadão (Carrefour)": ["https://www.atacadao.com.br"],
    "Pão de Açúcar": ["https://www.paodeacucar.com"],
    "Comper": ["https://www.comper.com.br"],
}


def investigar(base: str) -> dict:
    r = {"base": base}
    robots = inv.baixar(base + "/robots.txt")
    r["robots_status"] = robots["status"]
    if robots["status"] == 0:
        r["erro"] = robots.get("erro")
        return r
    rp = RobotFileParser()
    texto_robots = robots.get("texto", "") if robots["status"] == 200 and "<html" not in robots.get("texto", "")[:300].lower() else ""
    rp.parse(texto_robots.splitlines() if robots["status"] == 200 else (["User-agent: *", "Disallow: /"] if robots["status"] in (401, 403) else []))
    r["robots_trecho"] = texto_robots[:400]
    if not rp.can_fetch(USER_AGENT, base + "/"):
        r["nota"] = "robots.txt não permite a página inicial"
        return r
    time.sleep(2)
    inicio = inv.baixar(base + "/")
    a = inv.analisar(inicio)
    r.update({k: a.get(k) for k in ("status", "titulo", "antirrobo", "tecnologia", "erro")})
    if "vtex" in (a.get("tecnologia") or []) or "vtex" in (inicio.get("texto") or "")[:200000].lower():
        api = base + "/api/catalog_system/pub/products/search?ft=leite&_from=0&_to=2"
        if rp.can_fetch(USER_AGENT, api):
            time.sleep(2)
            resp = inv.baixar(api)
            r["vtex_api"] = resp["status"]
            try:
                itens = json.loads(resp.get("texto") or "[]")
                r["vtex_exemplo"] = [{"nome": i.get("productName"), "ean": (i.get("items") or [{}])[0].get("ean"),
                                      "preco": (((i.get("items") or [{}])[0].get("sellers") or [{}])[0].get("commertialOffer") or {}).get("Price")}
                                     for i in itens[:2]]
            except (json.JSONDecodeError, AttributeError):
                r["vtex_resposta"] = (resp.get("texto") or "")[:200]
        else:
            r["vtex_api"] = "robots.txt não permite /api/"
    if robots["status"] == 200:
        try:
            sm = inv.explorar_sitemap(texto_robots, base, rp, Path("relatorios/mercados"), max_arquivos=4)
            r["sitemap"] = {"urls": sm["urls_listadas"], "produtos": sm["paginas_de_produto"], "exemplos": sm["exemplos"][:2],
                            "amostras": [{"status": x["status"], "json_ld": (x.get("dados") or {}).get("produtos_json_ld", [])[:1]}
                                         for x in sm["amostras"]]}
        except Exception as e:
            r["sitemap"] = {"erro": str(e)[:200]}
    return r


Path("relatorios/mercados").mkdir(parents=True, exist_ok=True)
saida = {}
for nome, bases in MERCADOS.items():
    for base in bases:
        r = investigar(base)
        if r.get("status") or r.get("robots_status") not in (0, None):
            break
    saida[nome] = r
    sm = r.get("sitemap") or {}
    print(f"\n== {nome} ({r['base']}): robots {r.get('robots_status')} | página {r.get('status')} {r.get('titulo') or ''} | "
          f"tec {r.get('tecnologia')} | anti-robô {r.get('antirrobo')} {r.get('nota') or r.get('erro') or ''}")
    if "vtex_api" in r:
        print(f"   VTEX API: {r['vtex_api']} {r.get('vtex_exemplo') or r.get('vtex_resposta') or ''}")
    if sm:
        print(f"   sitemap: {sm.get('urls')} URLs, {sm.get('produtos')} de produto; amostra: {sm.get('amostras') or sm.get('erro')}")
Path("relatorios/mercados/mercados.json").write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
