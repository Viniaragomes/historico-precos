import json
import os
import tempfile
import unittest
from datetime import date

from historico_precos.armazenamento import Banco
from historico_precos.causas import A_CONFIRMAR, ASSOCIADO, COMPROVADO, DECLARADO, REFERENCIA, embalagem, noticias, series
from historico_precos.causas.analise import AgenteCausas, detectar_categoria
from historico_precos.causas.tributos import EventoTributario
from historico_precos.comparativo import comparar
from historico_precos.modelo import PontoDePreco, Produto

from test_agente import Fake, nav_com

EAN = "7896005800027"


def ponto(preco, data, loja="Loja A", descricao="Café Torrado e Moído 500g", **extra):
    return PontoDePreco(ean=EAN, preco=preco, data_observada=data, fonte="wayback", loja=loja,
                        url_origem="https://loja/p", url_evidencia=f"https://arquivo/{loja}/{data}",
                        metodo="json-ld", descricao=descricao, **extra)


def evento(verificado, categorias=("*",), vigencia=date(2024, 1, 1), uf="DF"):
    return EventoTributario(id="t", tributo="ICMS", uf=uf, vigencia=vigencia, aliquota_anterior=18,
                            aliquota_nova=20, calculo="por_dentro", abrangencia="alíquota modal",
                            categorias=list(categorias), verificado=verificado, fontes=["https://dodf/lei"])


CATEGORIAS = {
    "localidades_ipca": {"DF": "N6[5300108]"},
    "series_bcb_gerais": [{"codigo": 1, "nome": "Dólar", "defasagem_meses": 0}],
    "categorias": {
        "cafe": {"palavras": ["café"], "ipca_subitem": "Café moído",
                 "series_bcb": [], "termos_noticia": ["café"]},
    },
}

META_IBGE = {"classificacoes": [{"id": 315, "categorias": [
    {"id": 7187, "nome": "1101002.Arroz"}, {"id": 7234, "nome": "1110044.Café moído"}]}]}

IPCA = [{"resultados": [{"series": [{"serie": {"202312": "9.9", "202401": "2.0", "202402": "3.0", "202403": "-"}}]}]}]

BCB = [{"data": "02/10/2023", "valor": "5.00"}, {"data": "01/02/2024", "valor": "5.50"}]

GDELT = {"articles": [
    {"title": "Seca no cerrado faz preço do café disparar", "url": "https://jornal/1", "seendate": "20240210T120000Z", "domain": "jornal.com.br"},
    {"title": "Receita de bolo de café", "url": "https://jornal/2", "seendate": "20240211T120000Z", "domain": "jornal.com.br"},
]}


def internet():
    return Fake([
        ("https://servicodados.ibge.gov.br/api/v3/agregados/7060/metadados", (200, json.dumps(META_IBGE))),
        ("https://servicodados.ibge.gov.br/api/v3/agregados/7060/periodos", (200, json.dumps(IPCA))),
        ("https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/", (200, json.dumps(BCB))),
        ("https://api.gdeltproject.org/", (200, json.dumps(GDELT))),
    ])


class TestPecas(unittest.TestCase):
    def test_icms_por_dentro(self):
        # 18% -> 20% embutido no preço: (0,82 / 0,80) - 1 = 2,5%
        self.assertAlmostEqual(evento(True).efeito_pct(), 2.5, places=4)

    def test_quantidade(self):
        self.assertEqual(embalagem.quantidade("Café 500g"), (500.0, "g"))
        self.assertEqual(embalagem.quantidade("Óleo de Soja 0,9L"), (900.0, "ml"))
        self.assertEqual(embalagem.quantidade("Arroz 5 kg"), (5000.0, "g"))
        self.assertIsNone(embalagem.quantidade("Sabonete"))

    def test_reduflacao(self):
        qa, qd, un, var = embalagem.comparar("Café 500g", "Café 450g", 20.0, 20.0)
        self.assertEqual((qa, qd, un), (500.0, 450.0, "g"))
        self.assertAlmostEqual(var, 11.11, places=2)
        self.assertIsNone(embalagem.comparar("Café 500g", "Café 500g", 20.0, 22.0))

    def test_acumular_mensal(self):
        var = series.acumular_mensal({"202312": 9.9, "202401": 2.0, "202402": 3.0}, date(2023, 12, 20), date(2024, 2, 5))
        self.assertAlmostEqual(var, (1.02 * 1.03 - 1) * 100, places=6)

    def test_noticia_sem_motivo_e_descartada(self):
        self.assertEqual(noticias.classificar("Seca faz preço do café disparar"), ["clima"])
        self.assertEqual(noticias.classificar("Receita de bolo de café"), [])

    def test_categoria(self):
        self.assertEqual(detectar_categoria(CATEGORIAS, "CAFÉ PILÃO 500G"), "cafe")
        self.assertIsNone(detectar_categoria(CATEGORIAS, "Sabão em pó"))


class TestAgenteCausas(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.banco = Banco(os.path.join(self.dir.name, "t.db"))
        self.banco.salvar_produto(Produto(EAN, nome="Café Torrado e Moído"))
        self.banco.salvar_precos([ponto(20.0, "2023-12-20"), ponto(24.0, "2024-02-05", descricao="Café Torrado e Moído 450g")])

    def tearDown(self):
        self.banco.con.close()
        self.dir.cleanup()

    def explicar(self, eventos):
        agente = AgenteCausas(nav_com(internet(), robots=False), self.banco, CATEGORIAS, eventos)
        categoria, explicacoes = agente.explicar(EAN, uf="DF")
        self.assertEqual(categoria, "cafe")
        self.assertEqual(len(explicacoes), 1)
        return explicacoes[0]

    def test_niveis_de_prova(self):
        ex = self.explicar([evento(True)])
        por_tipo = {e.tipo: e for e in ex.evidencias}
        self.assertEqual(por_tipo["imposto"].nivel, COMPROVADO)
        self.assertEqual(por_tipo["embalagem"].nivel, COMPROVADO)
        self.assertEqual(por_tipo["categoria"].nivel, REFERENCIA)
        self.assertAlmostEqual(por_tipo["categoria"].efeito_pct, (1.02 * 1.03 - 1) * 100, places=4)
        self.assertEqual(por_tipo["indicador"].nivel, ASSOCIADO)
        self.assertIn("+10.0%", por_tipo["indicador"].descricao)
        noticias_ok = [e for e in ex.evidencias if e.tipo == "noticia"]
        self.assertEqual(len(noticias_ok), 1)
        self.assertEqual(noticias_ok[0].nivel, DECLARADO)

        # +20% total; 2,5% comprovado pelo imposto; o resto fica sem causa comprovada
        self.assertAlmostEqual(ex.comprovado_pct, 2.5, places=4)
        self.assertAlmostEqual(ex.nao_explicado_pct, (1.20 / 1.025 - 1) * 100, places=4)

    def test_evento_nao_verificado_nao_conta_como_comprovado(self):
        ex = self.explicar([evento(False)])
        imposto = next(e for e in ex.evidencias if e.tipo == "imposto")
        self.assertEqual(imposto.nivel, A_CONFIRMAR)
        self.assertEqual(ex.comprovado_pct, 0.0)

    def test_evento_fora_do_periodo_ou_de_outra_uf(self):
        ex = self.explicar([evento(True, vigencia=date(2025, 1, 1)), evento(True, uf="SP")])
        self.assertFalse([e for e in ex.evidencias if e.tipo == "imposto"])


class TestComparativo(unittest.TestCase):
    def test_ranking(self):
        pontos = [
            ponto(22.0, "2026-10-01", loja="Loja A"),
            ponto(19.0, "2026-10-19", loja="Loja A"),  # mais recente vale
            ponto(21.5, "2026-10-20", loja="Loja B", preco_de=25.0),
            ponto(15.0, "2026-06-01", loja="Loja C"),  # velho demais
        ]
        comp = comparar(pontos, hoje=date(2026, 10, 20), max_dias=30)
        self.assertEqual([(o.loja, o.preco) for o in comp.ofertas], [("Loja A", 19.0), ("Loja B", 21.5)])
        self.assertAlmostEqual(comp.ofertas[1].diferenca_rs, 2.5)
        self.assertTrue(comp.ofertas[1].em_promocao)
        self.assertEqual(comp.ofertas[0].dias, 1)
        self.assertAlmostEqual(comp.economia_maxima, 2.5)
        self.assertEqual([o.loja for o in comp.ignoradas], ["Loja C"])

    def test_vazio(self):
        comp = comparar([])
        self.assertIsNone(comp.mais_barata)
        self.assertEqual(comp.economia_maxima, 0.0)


if __name__ == "__main__":
    unittest.main()
