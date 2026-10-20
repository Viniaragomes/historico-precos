import json
import os
import tempfile
import unittest
from datetime import date
from urllib.parse import parse_qs

from historico_precos.armazenamento import Banco
from historico_precos.mapa_df import html as leitor
from historico_precos.mapa_df.agente import (
    AgenteMapaDF, adivinhar_campos, escolher_opcao, mapear_colunas, ultimos_meses,
)

from test_agente import Fake, nav_com

URL = "https://painel.exemplo/mapadeprecos/index.php"
MESES = "".join(f'<option value="{i}">{n}</option>' for i, n in enumerate(
    ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
     "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"], start=1))

PAINEL = f"""<html><body>
<form action="consulta.php" method="post">
  <input type="hidden" name="token" value="abc123">
  <select name="cboAno"><option value="2025">2025</option><option value="2026" selected>2026</option></select>
  <select name="cboMes">{MESES}</select>
  <select name="cboUF"><option value="">Todas</option><option value="DF">DF</option></select>
  <input type="text" name="txtProduto">
  <input type="submit" value="Pesquisar">
</form>
<script>$.post("ajax/detalhe.php", {{id: 1}});</script>
</body></html>"""

TABELA = """<table><tr><th>Descrição do Produto</th><th>Unidade</th><th>UF Origem</th><th>Qtd. Notas</th>
<th>Valor Mínimo</th><th>Valor Médio</th><th>Valor Máximo</th></tr>
<tr><td>CAFE TORRADO MOIDO 500G</td><td>PC</td><td>DF</td><td>12</td><td>R$ 14,10</td><td>R$ 16,25</td><td>R$ 19,90</td></tr>
<tr><td>CAFE TORRADO MOIDO 250G</td><td>PC</td><td>GO</td><td>4</td><td>8,10</td><td>8,90</td><td>9,50</td></tr>
<tr><td>Total</td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
</table>"""


def resposta_consulta(url, dados):
    campos = parse_qs(dados.decode())
    assert campos["token"] == ["abc123"], "token oculto deve ir junto"
    precos = {"8": TABELA, "9": TABELA.replace("16,25", "17,00").replace("8,90", "9,10")}
    return 200, precos.get(campos["cboMes"][0], "<p>Nenhum resultado</p>")


def internet():
    return Fake([(URL, (200, PAINEL)), ("https://painel.exemplo/mapadeprecos/consulta.php", resposta_consulta)])


class TestLeitorHTML(unittest.TestCase):
    def test_descoberta(self):
        d = leitor.descobrir(URL, PAINEL)
        self.assertEqual(len(d.formularios), 1)
        f = d.formularios[0]
        self.assertEqual((f.metodo, f.acao), ("post", "https://painel.exemplo/mapadeprecos/consulta.php"))
        self.assertEqual([c.nome for c in f.campos], ["token", "cboAno", "cboMes", "cboUF", "txtProduto"])
        self.assertEqual(f.campo("cboAno").valor, "2026")  # respeita a opção marcada
        self.assertIn("https://painel.exemplo/mapadeprecos/ajax/detalhe.php", d.endpoints)
        self.assertEqual(adivinhar_campos(f), {"produto": "txtProduto", "mes": "cboMes", "ano": "cboAno"})

    def test_painel_embutido(self):
        d = leitor.descobrir(URL, '<iframe src="https://app.powerbi.com/view?r=xyz"></iframe>')
        self.assertEqual(d.paineis_embutidos, ["https://app.powerbi.com/view?r=xyz"])

    def test_escolher_opcao(self):
        campo = leitor.descobrir(URL, PAINEL).formularios[0].campo("cboMes")
        self.assertEqual(escolher_opcao(campo, 3, "marco"), "3")
        sem_value = leitor.Campo("m", "select", opcoes=[("Jan", "Jan"), ("Mar", "Mar")])
        self.assertEqual(escolher_opcao(sem_value, 3, "marco"), "Mar")

    def test_colunas(self):
        mapa = mapear_colunas(["Descrição do Produto", "Unidade", "UF Origem", "Qtd. Notas",
                               "Valor Mínimo", "Valor Médio", "Valor Máximo"])
        self.assertEqual(mapa["descricao"], "Descrição do Produto")
        self.assertEqual(mapa["valor_medio"], "Valor Médio")
        self.assertEqual(mapa["valor_min"], "Valor Mínimo")
        self.assertEqual(mapa["quantidade"], "Qtd. Notas")
        self.assertEqual(mapa["uf_origem"], "UF Origem")

    def test_json_datatables(self):
        self.assertEqual(leitor.linhas_json('{"data": [{"produto": "ARROZ", "valor": "5,10"}]}'),
                         [{"produto": "ARROZ", "valor": "5,10"}])
        self.assertIsNone(leitor.linhas_json("<html>"))

    def test_ultimos_meses(self):
        self.assertEqual(ultimos_meses(3, date(2026, 2, 10)), [(2026, 2), (2026, 1), (2025, 12)])


class TestAgenteMapaDF(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.banco = Banco(os.path.join(self.dir.name, "t.db"))
        self.cfg = {"url": URL, "campos": {}, "fixos": {}, "colunas": {}}

    def tearDown(self):
        self.banco.con.close()
        self.dir.cleanup()

    def test_coleta_e_serie_mensal(self):
        fake = internet()
        agente = AgenteMapaDF(nav_com(fake, robots=False), self.banco, self.cfg)
        novos = agente.coletar(["CAFE"], [(2026, 8), (2026, 9), (2026, 10)])
        self.assertEqual(novos, 4)  # 2 itens x 2 meses com dados; "Total" e mês vazio são ignorados
        enviado = parse_qs(fake.envios[-1].decode())
        self.assertEqual(enviado["txtProduto"], ["CAFE"])
        self.assertEqual(enviado["cboAno"], ["2026"])

        r = agente.registros("cafe")[0]
        self.assertEqual((r.descricao, r.unidade, r.uf_origem, r.quantidade), ("CAFE TORRADO MOIDO 250G", "PC", "GO", 4.0))

        serie = agente.serie_mensal("CAFE", filtro_descricao="500g")
        self.assertEqual([(s["mes"], s["mediana"]) for s in serie], [(8, 16.25), (9, 17.0)])

        # coletar de novo não duplica
        self.assertEqual(agente.coletar(["CAFE"], [(2026, 8)]), 0)

    def test_salva_resposta_bruta(self):
        agente = AgenteMapaDF(nav_com(internet(), robots=False), self.banco, self.cfg)
        pasta = __import__("pathlib").Path(self.dir.name) / "bruto"
        agente.coletar(["OLEO DE SOJA"], [(2026, 10)], pasta)
        self.assertTrue((pasta / "resposta_oleo_de_soja_202610.html").exists())

    def test_endpoint_json_configurado(self):
        fake = Fake([(URL, (200, PAINEL)), ("https://painel.exemplo/api/precos",
                     (200, json.dumps({"data": [{"descricao": "ARROZ 5KG", "valorMedio": "24,90"}]})))])
        cfg = {**self.cfg, "endpoint": "https://painel.exemplo/api/precos",
               "colunas": {"valor_medio": "valorMedio"}}
        agente = AgenteMapaDF(nav_com(fake, robots=False), self.banco, cfg)
        self.assertEqual(agente.coletar(["ARROZ"], [(2026, 10)]), 1)
        self.assertEqual(agente.registros("ARROZ")[0].valor_medio, 24.9)

    def test_painel_fora_do_ar(self):
        agente = AgenteMapaDF(nav_com(Fake([]), robots=False), self.banco, self.cfg)
        self.assertIsNone(agente.descobrir())
        self.assertEqual(agente.coletar(["CAFE"], [(2026, 10)]), 0)


if __name__ == "__main__":
    unittest.main()
