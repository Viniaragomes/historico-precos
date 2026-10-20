import os
import tempfile
import unittest
from pathlib import Path

from historico_precos.armazenamento import Banco
from historico_precos.viabilidade import (
    AgenteViabilidade, ResultadoProduto, calcular_metricas, para_markdown, salvar,
)

from test_agente import EAN, internet_padrao, nav_com

LOJAS = [{"nome": "Loja Exemplo", "dominio": "loja.exemplo.com.br", "tipo": "vtex"}]


class TestViabilidade(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.banco = Banco(os.path.join(self.dir.name, "t.db"))
        self.agente = AgenteViabilidade(nav_com(internet_padrao(), robots=False), self.banco, LOJAS)

    def tearDown(self):
        self.banco.con.close()
        self.dir.cleanup()

    def test_amostra_usa_codigos_reais_da_loja(self):
        self.assertEqual(self.agente.montar_amostra(1, ["leite"]), [(EAN, "Leite Condensado 395g")])

    def test_sondas_nao_quebram(self):
        sondas = self.agente.sondar()
        por_fonte = {s.fonte: s for s in sondas}
        self.assertTrue(por_fonte["Loja VTEX: Loja Exemplo"].ok)
        self.assertFalse(por_fonte["Banco Central (SGS)"].ok)  # não existe na internet simulada
        self.assertEqual(len(sondas), 1 + 8)

    def test_execucao_completa(self):
        arquivo = Path(self.dir.name) / "rel" / "amostra.tsv"
        rel = self.agente.executar(tamanho=1, max_capturas=10, produtos_com_causas=1, arquivo_amostra=arquivo)
        self.assertTrue(arquivo.read_text().startswith(EAN))
        p = rel.produtos[0]
        self.assertEqual(p.lojas_hoje, 1)  # só a loja simulada tem preço de hoje
        self.assertGreater(p.dias_historico, 180)  # o Wayback simulado vai até 2022
        self.assertEqual(p.mudancas, 2)
        self.assertEqual(rel.metricas["historico_6_meses"], 1.0)
        self.assertEqual(rel.veredito["preco_atual_2_lojas"], "ABAIXO DA META")
        md, js = salvar(rel, Path(self.dir.name) / "rel")
        self.assertIn("| Histórico de 6 meses ou mais | 100% | 40% | VIÁVEL |", md.read_text())
        self.assertTrue(js.exists())

    def test_metricas_sem_mudancas(self):
        produtos = [ResultadoProduto("1", "a", 0, 0, 0, None, 0), ResultadoProduto("2", "b", 3, 2, 200, 1, 0)]
        metricas, veredito = calcular_metricas(produtos, com_causas=2)
        self.assertEqual(metricas["preco_atual_2_lojas"], 0.5)
        self.assertEqual(veredito["mudancas_com_evidencia"], "sem dados")
        self.assertIn("sem dados", para_markdown(type("R", (), {
            "data": "x", "duracao_min": 0, "sondas": [], "produtos": produtos,
            "metricas": metricas, "veredito": veredito})()))


if __name__ == "__main__":
    unittest.main()
