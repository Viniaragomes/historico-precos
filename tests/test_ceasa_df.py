import json
import sqlite3
import unittest
from urllib.parse import parse_qs

from historico_precos.fontes import ceasa_df

from test_agente import Fake, nav_com

PAGINA = '''<select name="product" id="productChart" class="select" required="required"/>
<option value="">Selecione um Produto</option><option value="1">
  TOMATE</option><option value="50">
  BANANA PRATA</option><option value="81">CEBOLA</option></select>'''


class FakePost(Fake):
    """Responde conforme o corpo do POST, como o portal."""

    def __call__(self, url, dados=None):
        self.acessos.append(url)
        self.envios.append(dados)
        if url.endswith("/robots.txt"):
            return 200, "<html>sem robots</html>"
        if url.endswith("/classification"):
            return 200, json.dumps([{"id": 7, "classification": "AA"}, {"id": 8, "classification": "A"}])
        if url.endswith("/precos") and dados:
            q = parse_qs(dados.decode())
            if q["classification"] == ["7"]:
                return 200, json.dumps({"priceMonth": [{"dia": "01", "price": "4.5"}, {"dia": "02", "price": "5.00"},
                                                       {"dia": "31", "price": "9"}], "priceYear": []})
            return 200, json.dumps({"message": "Nenhum preço"})
        if url.endswith("/precos"):
            return 200, PAGINA
        return 404, ""


class TestCeasaDF(unittest.TestCase):
    def test_coleta(self):
        fake = FakePost([])
        nav = nav_com(fake)
        con = sqlite3.connect(":memory:")
        r = ceasa_df.coletar(nav, con, ["tomate", "Pera"], [(2026, 10)])
        self.assertEqual((r["no_portal"], r["produtos"], r["series"], r["cotacoes"]), (3, 1, 2, 3))  # 01, 02 e 31/10
        self.assertEqual(r["nao_achados"], ["PERA"])
        linhas = con.execute("SELECT produto, classificacao, data, preco_kg FROM ceasa_df ORDER BY data").fetchall()
        self.assertEqual(linhas[0], ("TOMATE", "AA", "2026-10-01", 4.5))
        corpo = parse_qs(next(d for u, d in zip(fake.acessos, fake.envios) if u.endswith("/precos") and d).decode())
        self.assertEqual((corpo["month"], corpo["year"], corpo["product"]), (["10"], ["2026"], ["1"]))

    def test_dia_invalido_ignorado(self):
        class Fev(FakePost):
            pass
        con = sqlite3.connect(":memory:")
        r = ceasa_df.coletar(nav_com(Fev([])), con, ["TOMATE"], [(2026, 2)])  # 31/02 não existe
        self.assertEqual(r["cotacoes"], 2)
