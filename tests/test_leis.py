import json
import os
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path

from historico_precos.armazenamento import Banco
from historico_precos.causas import COMPROVADO
from historico_precos.causas import tributos
from historico_precos.causas.analise import AgenteCausas
from historico_precos.leis import fontes
from historico_precos.leis.extrator import extrair
from historico_precos.leis.monitor import MonitorLeis
from historico_precos.modelo import PontoDePreco, Produto

from test_agente import Fake, nav_com

RAIZ = Path(__file__).resolve().parents[1]
CATS = {"categorias": {"cafe": {"palavras": ["café"]}, "leite": {"palavras": ["leite longa vida"]}}}

TEXTO_DECRETO = (
    "DECRETO Nº 45.000, DE 20 DE DEZEMBRO DE 2023. Altera o Regulamento do ICMS. Art. 1º A alíquota do "
    "ICMS nas operações internas passa de 18% (dezoito por cento) para 20% (vinte por cento). "
    "Art. 2º Este Decreto produz efeitos a partir de 1º de janeiro de 2024."
)

DOU_ITENS = {"jsonArray": [
    {"pubName": "DO1", "urlTitle": "convenio-icms-n-10-de-2024-123", "title": "CONVÊNIO ICMS Nº 10, DE 5 DE ABRIL DE 2024",
     "pubDate": "08/04/2024", "hierarchyStr": "Ministério da Fazenda/Conselho Nacional de Política Fazendária",
     "content": "Autoriza a redução da <b>alíquota</b> do ICMS de 12% para 7% nas saídas de café torrado e moído."},
    {"pubName": "DO1", "urlTitle": "portaria-qualquer-1", "title": "PORTARIA Nº 1",
     "pubDate": "09/04/2024", "hierarchyStr": "Ministério da Saúde", "content": "Nomeia servidor."},
]}
PAGINA_DOU = (
    '<html><script type="application/json" id="_br_com_seatecnologia_in_buscadou_BuscaDouPortlet_params">'
    + json.dumps(DOU_ITENS) + "</script></html>"
)
QD = {"gazettes": [{"territory_id": "5300108", "territory_name": "Brasília", "date": "2023-12-21",
                    "url": "https://dodf.exemplo/2023-12-21.pdf", "excerpts": [TEXTO_DECRETO]}]}


def internet():
    return Fake([
        ("https://www.in.gov.br/consulta/-/buscar/dou", (200, PAGINA_DOU)),
        ("https://api.queridodiario.ok.org.br/gazettes", (200, json.dumps(QD))),
        ("https://receita.exemplo/legislacao", (200, '<a href="/decreto-45000.pdf">Decreto 45.000 - altera alíquota do ICMS</a>'
                                                     '<a href="/noticia">Feira de artesanato</a>')),
    ])


CONFIG = {
    "pontuacao_minima": 5,
    "fontes": {
        "dou": {"ativa": True, "termos": ["\"Convênio ICMS\""]},
        "querido_diario": {"ativa": True, "territorios": [{"id": "5300108", "uf": "DF"}], "termos": ["ICMS"]},
        "paginas": [{"nome": "Receita DF", "url": "https://receita.exemplo/legislacao", "uf": "DF", "palavras": ["icms"]}],
    },
}


class TestExtrator(unittest.TestCase):
    def test_decreto(self):
        ex = extrair(TEXTO_DECRETO, {"cafe": ["café"]})
        self.assertEqual(ex.tributos, ["ICMS"])
        self.assertEqual((ex.aliquota_anterior, ex.aliquota_nova), (18.0, 20.0))
        self.assertEqual(ex.vigencia, date(2024, 1, 1))
        self.assertGreaterEqual(ex.pontuacao, 8)
        self.assertIn("ICMS", ex.trecho)

    def test_vigencia_numerica_e_produto(self):
        ex = extrair("Reduz a alíquota do ICMS de 12% para 7% para café, com efeitos a partir de 01/03/2025.",
                     {"cafe": ["café"]})
        self.assertEqual(ex.vigencia, date(2025, 3, 1))
        self.assertEqual(ex.categorias, ["cafe"])

    def test_texto_irrelevante(self):
        self.assertLess(extrair("Nomeia servidor para cargo em comissão.").pontuacao, 3)

    def test_sigla_nao_casa_dentro_de_palavra(self):
        self.assertNotIn("IBS", extrair("Os ribs do churrasco").tributos)


class TestFontes(unittest.TestCase):
    def test_dou(self):
        pubs = fontes.buscar_dou(nav_com(internet(), robots=False), "icms", date(2024, 4, 1), date(2024, 4, 30))
        self.assertEqual(len(pubs), 2)
        self.assertEqual(pubs[0].uf, "CONFAZ")
        self.assertEqual(pubs[0].data, "2024-04-08")
        self.assertEqual(pubs[0].url, "https://www.in.gov.br/web/dou/-/convenio-icms-n-10-de-2024-123")
        self.assertNotIn("<b>", pubs[0].texto)

    def test_pagina(self):
        pubs = fontes.links_da_pagina(nav_com(internet(), robots=False), "https://receita.exemplo/legislacao",
                                      ["icms"], "DF", "Receita DF")
        self.assertEqual([p.url for p in pubs], ["https://receita.exemplo/decreto-45000.pdf"])


class TestMonitor(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.banco = Banco(os.path.join(self.dir.name, "t.db"))
        self.eventos = Path(self.dir.name) / "eventos.json"
        shutil.copy(RAIZ / "eventos_tributarios.json", self.eventos)
        self.monitor = MonitorLeis(nav_com(internet(), robots=False), self.banco, CONFIG, CATS)

    def tearDown(self):
        self.banco.con.close()
        self.dir.cleanup()

    def test_varredura(self):
        novos = self.monitor.monitorar(date(2023, 12, 1), date(2024, 4, 30))
        por_fonte = {c.fonte: c for c in novos}
        self.assertEqual(set(por_fonte), {"Querido Diário", "DOU"})  # a portaria e o link solto ficam de fora
        df = por_fonte["Querido Diário"]
        self.assertEqual((df.uf, df.aliquota_anterior, df.aliquota_nova, df.vigencia), ("DF", 18.0, 20.0, "2024-01-01"))
        self.assertEqual(por_fonte["DOU"].categorias, ["cafe"])
        # rodar de novo não traz os mesmos candidatos
        self.assertEqual(self.monitor.monitorar(date(2023, 12, 1), date(2024, 4, 30)), [])
        self.assertEqual(len(self.monitor.candidatos("pendente")), 2)

    def test_confaz_exige_uf(self):
        cand = next(c for c in self.monitor.monitorar(date(2024, 4, 1), date(2024, 4, 30)) if c.uf == "CONFAZ")
        with self.assertRaisesRegex(ValueError, "internalizado"):
            self.monitor.aprovar(cand.id, self.eventos)

    def test_aprovar_atualiza_evento_e_vira_comprovado(self):
        cand = next(c for c in self.monitor.monitorar(date(2023, 12, 1), date(2024, 4, 30)) if c.uf == "DF")
        evento = self.monitor.aprovar(cand.id, self.eventos, evento_id="df-icms-modal-2024", categorias=["*"])
        self.assertTrue(evento["verificado"])
        self.assertEqual(evento["fontes"][0], "https://dodf.exemplo/2023-12-21.pdf")
        self.assertEqual(evento["calculo"], "por_dentro")
        self.assertEqual(self.monitor.candidato(cand.id).status, "aprovado")
        carregados = tributos.carregar(self.eventos)
        self.assertEqual(len([e for e in carregados if e.id == "df-icms-modal-2024"]), 1)

        # o agente de causas agora mostra o imposto como COMPROVADO
        self.banco.salvar_produto(Produto("1", nome="Sabão em pó 1kg"))
        base = dict(ean="1", fonte="x", loja="L", url_origem="u", url_evidencia="e", metodo="m")
        self.banco.salvar_precos([PontoDePreco(preco=10.0, data_observada="2023-12-10", **base),
                                  PontoDePreco(preco=10.5, data_observada="2024-02-10", **base)])
        cfg = {"categorias": {}, "series_bcb_gerais": []}
        _, explicacoes = AgenteCausas(nav_com(Fake([]), robots=False), self.banco, cfg, carregados,
                                      usar_noticias=False).explicar("1", uf="DF")
        imposto = next(e for e in explicacoes[0].evidencias if e.tipo == "imposto")
        self.assertEqual(imposto.nivel, COMPROVADO)
        self.assertAlmostEqual(explicacoes[0].comprovado_pct, 2.5, places=4)

    def test_aprovar_sem_dados_pede_informacao(self):
        self.monitor.monitorar(date(2023, 12, 1), date(2024, 4, 30))
        self.banco.con.execute("UPDATE candidatos_leis SET vigencia = NULL WHERE uf = 'DF'")
        cand = next(c for c in self.monitor.candidatos() if c.uf == "DF")
        with self.assertRaisesRegex(ValueError, "--vigencia"):
            self.monitor.aprovar(cand.id, self.eventos, categorias=["*"])

    def test_descartar(self):
        cand = self.monitor.monitorar(date(2023, 12, 1), date(2024, 4, 30))[0]
        self.assertTrue(self.monitor.descartar(cand.id))
        self.assertNotIn(cand.id, [c.id for c in self.monitor.candidatos()])


if __name__ == "__main__":
    unittest.main()


class TestLexml(unittest.TestCase):
    def test_registros_no_periodo(self):
        xml = """<?xml version="1.0"?><srw:searchRetrieveResponse xmlns:srw="http://www.loc.gov/zing/srw/"
          xmlns:dc="http://purl.org/dc/elements/1.1/"><srw:records>
          <srw:record><srw:recordData><srw_dc xmlns="info:srw/schema/1/dc-schema">
            <urn>urn:lex:br;distrito.federal:distrital:lei:2023-12-20;7326</urn>
            <dc:title>Lei nº 7.326, de 20 de dezembro de 2023</dc:title>
            <dc:description>Altera a alíquota do ICMS de 18% para 20%.</dc:description>
            <dc:date>2023-12-20</dc:date></srw_dc></srw:recordData></srw:record>
          <srw:record><srw:recordData><srw_dc xmlns="info:srw/schema/1/dc-schema">
            <urn>urn:lex:br:federal:lei:2010-01-01;1</urn><dc:title>Antiga</dc:title><dc:date>2010-01-01</dc:date>
          </srw_dc></srw:recordData></srw:record></srw:records></srw:searchRetrieveResponse>"""
        nav = nav_com(Fake([("https://www.lexml.gov.br/busca/SRU", (200, xml))]), robots=False)
        pubs = fontes.buscar_lexml(nav, 'dc.description any "ICMS"', date(2023, 1, 1), date(2024, 12, 31))
        self.assertEqual(len(pubs), 1)
        self.assertEqual((pubs[0].uf, pubs[0].data, pubs[0].fonte), ("DF", "2023-12-20", "LexML"))
        self.assertIn("18% para 20%", pubs[0].texto)
        self.assertTrue(pubs[0].url.startswith("https://www.lexml.gov.br/urn/urn:lex:br;distrito.federal"))
