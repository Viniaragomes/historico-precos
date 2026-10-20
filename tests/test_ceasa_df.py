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


BOLETIM = """COTAÇÕES DE PREÇOS NO ATACADO - DATA – 15.10.2026
PRODUTOS/VARIEDADES UNIDADE DE CO-
HORTALIÇAS FRUTO
Tomate extra Cx-   19  a  21 kg. 230,00 240,00 250,00
Tomate primeira Cx-   19  a  21 kg.
Cebola Sc- 20 kg. 130,00 140,00 160,00
Alho importado (TP 5 a 6) Cx/Sc 10 kg. 0,00 0,00 0,00
Milho verde Pcte -  5 unidades 4,50 5,00 5,50
Abóbora seca ou madura 1 kg. 4,50 5,00 5,50
Amendoim com casca Sc- 25 kg. 1.480,00 1.500,00 1.540,00
"""


class TestBoletim(unittest.TestCase):
    def test_ler_boletim(self):
        data, linhas = ceasa_df.ler_boletim(BOLETIM)
        self.assertEqual(data, "2026-10-15")
        por_nome = {l.produto: l for l in linhas}
        self.assertEqual(set(por_nome), {"Tomate extra", "Cebola", "Milho verde", "Abóbora seca ou madura", "Amendoim com casca"})
        self.assertEqual((por_nome["Tomate extra"].comum, por_nome["Tomate extra"].kg_por_unidade, por_nome["Tomate extra"].comum_kg), (240.0, 20.0, 12.0))
        self.assertEqual(por_nome["Cebola"].comum_kg, 7.0)
        self.assertIsNone(por_nome["Milho verde"].comum_kg)  # vendido por unidade, sem peso
        self.assertEqual(por_nome["Abóbora seca ou madura"].comum_kg, 5.0)
        self.assertEqual(por_nome["Amendoim com casca"].comum, 1500.0)

    def test_coletar_boletim_uma_vez(self):
        url = "https://www.portal.ceasadf.com.br/storage/files/2026/10/atacado-1792062554.pdf"
        fake = Fake([("https://www.portal.ceasadf.com.br/robots.txt", (200, "<html></html>")),
                     ("https://www.portal.ceasadf.com.br/informacao-mercado", (200, f'<a href="{url}">Preço no Atacado</a>'
                       '<a href="https://www.portal.ceasadf.com.br/storage/files/2026/10/sima-1.pdf">SIMA</a>'))])
        baixados = []
        nav = nav_com(fake)
        nav._abrir_bytes = lambda u: baixados.append(u) or b"%PDF"
        con = sqlite3.connect(":memory:")
        r = ceasa_df.coletar_boletim(nav, con, lambda dados: BOLETIM)
        self.assertEqual((r["data"], r["linhas"]), ("2026-10-15", 5))
        self.assertEqual(baixados, [url])
        self.assertEqual(ceasa_df.coletar_boletim(nav, con, lambda dados: BOLETIM)["nota"], "boletim já coletado")
        con.execute("UPDATE ceasa_df_boletim SET data = date('now')")  # para cair na janela de dias de series_boletim
        s = {x["produto"]: x for x in ceasa_df.series_boletim(con)}
        self.assertEqual(s["Cebola"]["ultimo"]["preco_kg"], 7.0)
        self.assertEqual(s["Cebola"]["ultimo"]["evidencia"], url)
