import importlib.util
import json
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location("inv", Path(__file__).resolve().parents[1] / "ferramentas" / "investigar_fontes.py")
inv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inv)


class TestInvestigador(unittest.TestCase):
    def test_json_ld_de_produto(self):
        ld = {"@context": "https://schema.org", "@type": "Product", "name": "Café 500g", "gtin13": "7891000053508",
              "brand": {"@type": "Brand", "name": "Marca"}, "offers": {"@type": "AggregateOffer", "lowPrice": 18.9,
              "priceCurrency": "BRL", "offers": [{"@type": "Offer", "price": 18.9, "priceCurrency": "BRL"}]}}
        html = f'<script type="application/ld+json">{json.dumps(ld)}</script>'
        d = inv.dados_embutidos(html)
        self.assertEqual(d["produtos_json_ld"][0]["gtin"], "7891000053508")
        self.assertEqual(d["produtos_json_ld"][0]["preco"], 18.9)
        self.assertEqual(d["produtos_json_ld"][0]["marca"], "Marca")
        self.assertIn("Product", d["json_ld_tipos"])

    def test_next_data(self):
        estado = {"props": {"pageProps": {"product": {"ean": "789", "price": {"value": 9.99}}}}}
        html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(estado)}</script>'
        d = inv.dados_embutidos(html)
        campos = d["estados_embutidos"]["__NEXT_DATA__"]["campos_de_preco_ou_gtin"]
        self.assertTrue(any(".ean = 789" in c for c in campos))
        self.assertTrue(any("price" in c for c in campos))

    def test_pistas_qlik(self):
        js = "var config={host:'qap.exemplo',prefix:'/paineis/'};var appID='f0176c31-3c3b-4d15-94b3-ca9f2e902854';" \
             "qlik.openApp(appID,config);app.getObject('Tabela-1','JDnEtp');fetch('/api/precos?x=1')"
        p = inv.pistas_do_script(js)
        self.assertEqual(p["qlik"]["app_ids"], ["f0176c31-3c3b-4d15-94b3-ca9f2e902854"])
        self.assertIn(("Tabela-1", "JDnEtp"), p["qlik"]["objetos"])
        self.assertIn("/api/precos?x=1", p["enderecos"])

    def test_scripts_so_do_proprio_site(self):
        html = '<script src="/assets/app.js"></script><script src="https://cdn.x.com/a.js"></script><script src="/vendor/jquery.js"></script>'
        self.assertEqual(inv.scripts_do_site(html, "https://loja.com.br/"), ["https://loja.com.br/assets/app.js"])


if __name__ == "__main__":
    unittest.main()


class TestExplorarTemas(unittest.TestCase):
    def test_sitemap_relativo_e_links_da_pagina(self):
        import tempfile
        from urllib.robotparser import RobotFileParser

        paginas = {
            "https://site.gov.br/sitemap.xml.gz": "<urlset><url><loc>/legislacao/convenios/2026</loc></url>"
                                                  "<url><loc>https://site.gov.br/noticias/festa</loc></url></urlset>",
            "https://site.gov.br/legislacao/convenios/2026": '<a href="/x/convenio-icms-10.pdf">Convênio</a>',
            "https://site.gov.br/precos/boletim": '<a href="/b/cotacao.xlsx">planilha</a>',
        }
        originais = (inv.baixar, inv.time.sleep)
        inv.baixar = lambda url, limite=0, contexto=None: (
            {"url": url, "status": 200, "ms": 1, "cabecalhos": {}, "texto": paginas[url]} if url in paginas
            else {"url": url, "status": 0, "erro": "x", "ms": 1})
        inv.time.sleep = lambda s: None
        try:
            rp = RobotFileParser()
            rp.parse([])
            with tempfile.TemporaryDirectory() as d:
                r = inv.explorar_temas("Sitemap: /sitemap.xml.gz", "https://site.gov.br", rp, Path(d),
                                       '<a href="/precos/boletim">Boletim de preços</a>', ["convenio", "preco"])
        finally:
            inv.baixar, inv.time.sleep = originais
        urls = [p["url"] for p in r["paginas"]]
        self.assertIn("https://site.gov.br/legislacao/convenios/2026", urls)
        self.assertIn("https://site.gov.br/precos/boletim", urls)
        self.assertNotIn("https://site.gov.br/noticias/festa", urls)
        boletim = next(p for p in r["paginas"] if p["url"].endswith("boletim"))
        self.assertEqual(boletim["arquivos_de_dados"], ["https://site.gov.br/b/cotacao.xlsx"])
