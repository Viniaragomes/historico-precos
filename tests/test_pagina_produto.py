import json
import os
import tempfile
import unittest
from datetime import date

from historico_precos.armazenamento import Banco
from historico_precos.fontes import pagina_produto

from test_agente import Fake, nav_com

INDICE = """<?xml version="1.0"?><sitemapindex><sitemap><loc>https://loja.com.br/sitemap/category-0.xml</loc></sitemap>
<sitemap><loc>https://loja.com.br/sitemap/product-0.xml</loc></sitemap></sitemapindex>"""
PRODUTOS = """<urlset><url><loc>https://loja.com.br/cafe-uniao-tradicional-500g-123/p</loc></url>
<url><loc>https://loja.com.br/cafe-sem-estoque-250g-9/p</loc></url>
<url><loc>https://loja.com.br/arroz-camil-5kg-456/p</loc></url>
<url><loc>https://loja.com.br/institucional/cafe</loc></url></urlset>"""


def pagina(gtin, preco, estoque="InStock"):
    ld = {"@context": "https://schema.org", "@type": "Product", "name": "Café União Tradicional 500g", "gtin13": gtin,
          "offers": {"@type": "AggregateOffer", "lowPrice": preco, "priceCurrency": "BRL",
                     "offers": [{"@type": "Offer", "price": preco, "availability": f"https://schema.org/{estoque}"}]}}
    return f'<html><script type="application/ld+json">{json.dumps(ld)}</script></html>'


def internet():
    return Fake([
        ("https://loja.com.br/robots.txt", (200, "User-agent: *\nDisallow: /checkout/\nSitemap: https://loja.com.br/sitemap.xml")),
        ("https://loja.com.br/sitemap.xml", (200, INDICE)),
        ("https://loja.com.br/sitemap/product-0.xml", (200, PRODUTOS)),
        ("https://loja.com.br/cafe-uniao-tradicional-500g-123/p", (200, pagina("7891910030378", 24.9))),
        ("https://loja.com.br/cafe-sem-estoque-250g-9/p", (200, pagina("7891910030347", 13.5, "OutOfStock"))),
    ])


LOJA = {"nome": "Loja (site)", "tipo": "sitemap", "sitemap": "https://loja.com.br/sitemap.xml", "padrao_produto": "/p$", "cidade": None}


class TestPaginaProduto(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.banco = Banco(os.path.join(self.dir.name, "t.db"))

    def tearDown(self):
        self.banco.con.close()
        self.dir.cleanup()

    def test_sitemap_filtra_por_termo_e_ignora_categorias(self):
        fake = internet()
        urls = pagina_produto.urls_do_sitemap(nav_com(fake), LOJA["sitemap"], termos=["café"])
        self.assertEqual(urls, ["https://loja.com.br/cafe-uniao-tradicional-500g-123/p", "https://loja.com.br/cafe-sem-estoque-250g-9/p"])
        self.assertNotIn("https://loja.com.br/sitemap/category-0.xml", fake.acessos)

    def test_ler_pagina(self):
        produto, ponto = pagina_produto.ler(nav_com(internet()), "https://loja.com.br/cafe-uniao-tradicional-500g-123/p",
                                            "Loja (site)", hoje=date(2026, 10, 20))
        self.assertEqual((produto.ean, ponto.preco, ponto.data_observada, ponto.metodo), ("7891910030378", 24.9, "2026-10-20", "json-ld"))
        self.assertEqual(ponto.url_evidencia, "https://loja.com.br/cafe-uniao-tradicional-500g-123/p")

    def test_catalogar_guarda_pagina_para_site_e_arquivo(self):
        r = pagina_produto.catalogar(nav_com(internet()), self.banco, LOJA, ["cafe"], lojas_arquivo=["Loja (arquivo)"])
        self.assertEqual((r["no_sitemap"], r["lidas"], r["com_gtin"], r["precos"]), (2, 2, 2, 1))  # sem estoque: sem preço
        self.assertEqual(sorted(l for l, _ in self.banco.paginas("7891910030378")), ["Loja (arquivo)", "Loja (site)"])
        # a segunda vez não relê páginas já catalogadas
        r2 = pagina_produto.catalogar(nav_com(internet()), self.banco, LOJA, ["cafe"])
        self.assertEqual(r2["lidas"], 0)

    def test_robots_proibe_pagina(self):
        fake = Fake([("https://loja.com.br/robots.txt", (200, "User-agent: *\nDisallow: /")),
                     ("https://loja.com.br/x/p", (200, pagina("7891910030378", 24.9)))])
        self.assertEqual(pagina_produto.ler(nav_com(fake), "https://loja.com.br/x/p", "L"), (None, None))
        self.assertNotIn("https://loja.com.br/x/p", fake.acessos)


if __name__ == "__main__":
    unittest.main()
