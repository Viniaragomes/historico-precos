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
