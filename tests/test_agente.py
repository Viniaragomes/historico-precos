import json
import os
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from historico_precos.agente import AgenteHistorico, detectar_mudancas
from historico_precos.armazenamento import Banco
from historico_precos.extratores import extrair_preco, para_float
from historico_precos.fontes import openprices, vtex, wayback
from historico_precos.modelo import PontoDePreco
from historico_precos.rede import Navegador

EAN = "7891000100103"
LINK = "https://loja.exemplo.com.br/leite-condensado-395g/p"


def pagina_json_ld(preco, gtin=EAN):
    dado = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Leite Condensado 395g",
        "gtin13": gtin,
        "offers": {"@type": "Offer", "price": preco, "priceCurrency": "BRL"},
    }
    return f'<html><head><script type="application/ld+json">{json.dumps(dado)}</script></head></html>'


PAGINA_SKU_JSON = """<script>var skuJson_0 = {"productId":1,"skus":[{"sku":9,"available":true,
"listPrice":899,"bestPrice":749}]};CATALOG_SDK.setProductWithVariationsCache(1, skuJson_0);</script>"""

RESPOSTA_VTEX = [
    {
        "productName": "Leite Condensado 395g",
        "link": LINK,
        "items": [
            {
                "ean": EAN,
                "sellers": [{"commertialOffer": {"Price": 8.49, "ListPrice": 9.99, "IsAvailable": True}}],
            }
        ],
    }
]

CDX = [
    ["timestamp", "original", "statuscode"],
    ["20220110120000", LINK, "200"],
    ["20230315080000", LINK, "200"],
    ["20240601093000", LINK, "200"],
]


class Fake:
    """Simula a internet: mapeia (prefixo de URL) -> (status, corpo)."""

    def __init__(self, rotas):
        self.rotas = rotas
        self.acessos = []
        self.envios = []

    def __call__(self, url, dados=None):
        self.acessos.append(url)
        self.envios.append(dados)
        for prefixo, resposta in self.rotas:
            if url.startswith(prefixo):
                if callable(resposta):
                    return resposta(url) if dados is None else resposta(url, dados)
                return resposta
        return 404, ""


def snapshot(url):
    ts = url.split("/web/")[1][:14]
    return 200, {"20220110120000": pagina_json_ld("5.99"), "20230315080000": PAGINA_SKU_JSON,
                 "20240601093000": pagina_json_ld("8,49")}[ts]


def internet_padrao():
    return Fake(
        [
            ("https://world.openfoodfacts.org/api", (200, json.dumps(
                {"status": 1, "product": {"product_name": "Leite Condensado", "brands": "Marca", "quantity": "395 g"}}))),
            ("https://loja.exemplo.com.br/api/catalog_system", (200, json.dumps(RESPOSTA_VTEX))),
            ("https://web.archive.org/cdx", (200, json.dumps(CDX))),
            ("https://web.archive.org/web/", snapshot),
            ("https://prices.openfoodfacts.org/api", (200, json.dumps({"items": [
                {"id": 42, "price": 7.9, "currency": "BRL", "date": "2025-02-01",
                 "location": {"osm_name": "Mercado do Bairro", "osm_address_city": "Brasília"}},
                {"id": 43, "price": 2.0, "currency": "EUR", "date": "2025-02-01"},
            ]}))),
        ]
    )


def nav_com(fake, robots=True):
    return Navegador(intervalo=0, abrir=fake, dormir=lambda s: None, respeitar_robots=robots)


class TestExtratores(unittest.TestCase):
    def test_para_float(self):
        self.assertEqual(para_float("12,99"), 12.99)
        self.assertEqual(para_float("R$ 1.234,56"), 1234.56)
        self.assertEqual(para_float("1,234.56"), 1234.56)
        self.assertEqual(para_float(7), 7.0)
        self.assertIsNone(para_float("grátis"))
        self.assertIsNone(para_float(0))

    def test_json_ld(self):
        achado = extrair_preco(pagina_json_ld("12.99"), EAN)
        self.assertEqual((achado.preco, achado.metodo), (12.99, "json-ld"))

    def test_json_ld_graph_e_aggregate_offer(self):
        dado = {"@graph": [{"@type": "WebPage"}, {"@type": "Product", "offers": {"@type": "AggregateOffer", "lowPrice": "3,49"}}]}
        html = f'<script type="application/ld+json">{json.dumps(dado)}</script>'
        self.assertEqual(extrair_preco(html).preco, 3.49)

    def test_json_ld_de_outro_produto_e_ignorado(self):
        self.assertIsNone(extrair_preco(pagina_json_ld("9.99", gtin="7890000000000"), EAN))

    def test_sku_json_vtex_antigo(self):
        achado = extrair_preco(PAGINA_SKU_JSON)
        self.assertEqual((achado.preco, achado.preco_de, achado.metodo), (7.49, 8.99, "sku-json"))

    def test_meta(self):
        html = '<span itemprop="price" content="4.59"></span>'
        self.assertEqual(extrair_preco(html).preco, 4.59)


class TestFontes(unittest.TestCase):
    def test_vtex(self):
        loja = {"nome": "Loja Exemplo", "dominio": "loja.exemplo.com.br", "cidade": "Brasília", "sc": "2"}
        fake = internet_padrao()
        pontos, links = vtex.buscar_por_ean(nav_com(fake, robots=False), loja, EAN)
        self.assertEqual(links, [LINK])
        self.assertEqual((pontos[0].preco, pontos[0].preco_de, pontos[0].cidade), (8.49, 9.99, "Brasília"))
        self.assertIn("fq=alternateIds_Ean:" + EAN, fake.acessos[0])
        self.assertIn("&sc=2", fake.acessos[0])

    def test_wayback(self):
        fake = internet_padrao()
        pontos = wayback.historico(nav_com(fake, robots=False), LINK, EAN, "Loja Exemplo")
        self.assertEqual([(p.data_observada, p.preco) for p in pontos],
                         [("2022-01-10", 5.99), ("2023-03-15", 7.49), ("2024-06-01", 8.49)])
        self.assertEqual(pontos[0].url_evidencia, f"https://web.archive.org/web/20220110120000/{LINK}")
        consulta = parse_qs(urlsplit(fake.acessos[0]).query)
        self.assertEqual(consulta["filter"], ["statuscode:200"])
        self.assertEqual(consulta["collapse"], ["digest"])

    def test_amostrar_mantem_primeira_e_ultima(self):
        amostra = wayback.amostrar(list(range(100)), 5)
        self.assertEqual(len(amostra), 5)
        self.assertEqual((amostra[0], amostra[-1]), (0, 99))
        self.assertEqual(wayback.amostrar([1, 2], 5), [1, 2])

    def test_open_prices_so_reais(self):
        pontos = openprices.buscar(nav_com(internet_padrao(), robots=False), EAN)
        self.assertEqual(len(pontos), 1)
        self.assertEqual((pontos[0].preco, pontos[0].loja, pontos[0].cidade), (7.9, "Mercado do Bairro", "Brasília"))


class TestRobots(unittest.TestCase):
    def test_respeita_robots(self):
        fake = Fake([("https://site.com.br/robots.txt", (200, "User-agent: *\nDisallow: /privado/"))])
        nav = nav_com(fake)
        self.assertIsNone(nav.get_texto("https://site.com.br/privado/pagina"))
        self.assertNotIn("https://site.com.br/privado/pagina", fake.acessos)

    def test_robots_403_bloqueia_tudo(self):
        fake = Fake([("https://site.com.br/robots.txt", (403, ""))])
        self.assertIsNone(nav_com(fake).get_texto("https://site.com.br/qualquer"))

    def test_sem_robots_libera(self):
        fake = Fake([("https://site.com.br/ok", (200, "oi"))])
        self.assertEqual(nav_com(fake).get_texto("https://site.com.br/ok"), "oi")


class TestAgente(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.banco = Banco(os.path.join(self.dir.name, "t.db"))
        self.lojas = [{"nome": "Loja Exemplo", "dominio": "loja.exemplo.com.br", "tipo": "vtex"}]

    def tearDown(self):
        self.banco.con.close()
        self.dir.cleanup()

    def test_ponta_a_ponta(self):
        agente = AgenteHistorico(nav_com(internet_padrao()), self.banco, self.lojas)
        rel = agente.executar(EAN)
        self.assertEqual(rel.produto.nome, "Leite Condensado")
        # 3 cópias do Wayback + 1 preço atual VTEX + 1 do Open Prices
        self.assertEqual(rel.novos, 5)
        variacoes = [(m.preco_anterior, m.preco_novo) for m in rel.mudancas if m.loja == "Loja Exemplo"]
        self.assertEqual(variacoes[:2], [(5.99, 7.49), (7.49, 8.49)])
        self.assertTrue(all(p.url_evidencia.startswith("http") for p in rel.pontos))

        # segunda execução no mesmo dia não duplica nada
        self.assertEqual(agente.executar(EAN).novos, 0)

    def test_detectar_mudancas_ignora_oscilacao_minima(self):
        base = dict(ean=EAN, fonte="x", loja="L", url_origem="u", url_evidencia="e", metodo="m")
        pontos = [PontoDePreco(preco=10.0, data_observada="2024-01-01", **base),
                  PontoDePreco(preco=10.02, data_observada="2024-02-01", **base),
                  PontoDePreco(preco=11.0, data_observada="2024-03-01", **base)]
        mudancas = detectar_mudancas(pontos)
        self.assertEqual(len(mudancas), 1)
        self.assertAlmostEqual(mudancas[0].variacao_pct, 9.78, places=2)


if __name__ == "__main__":
    unittest.main()


class TestRegiaoERede(unittest.TestCase):
    def setUp(self):
        vtex._regioes.clear()

    def test_regiao_confirmada_pelo_cep(self):
        fake = internet_padrao()
        fake.rotas.insert(0, ("https://loja.exemplo.com.br/api/checkout/pub/regions", (200, json.dumps([{"id": "v2.ABC"}]))))
        loja = {"nome": "Loja Exemplo", "dominio": "loja.exemplo.com.br", "cidade": "Brasília", "cep": "70040-010"}
        pontos, _ = vtex.buscar_por_ean(nav_com(fake, robots=False), loja, EAN)
        self.assertIn("regionId=v2.ABC", fake.acessos[-1])
        self.assertIn("postalCode=70040010", fake.acessos[0])
        self.assertEqual(pontos[0].cidade, "Brasília")

    def test_sem_regiao_nao_afirma_cidade(self):
        loja = {"nome": "Loja Exemplo", "dominio": "loja.exemplo.com.br", "cidade": "Brasília", "cep": "70040010"}
        pontos, _ = vtex.buscar_por_ean(nav_com(internet_padrao(), robots=False), loja, EAN)
        self.assertIsNone(pontos[0].cidade)

    def test_206_e_gzip(self):
        import gzip
        fake = Fake([("https://site.com.br/a", (206, "[1]"))])
        self.assertEqual(nav_com(fake, robots=False).get_json("https://site.com.br/a"), [1])
        self.assertEqual(Navegador._descomprimir(gzip.compress(b'{"ok":1}'), None), b'{"ok":1}')
        self.assertEqual(Navegador._descomprimir(b"texto", None), b"texto")
