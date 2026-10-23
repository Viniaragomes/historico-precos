import os
import tempfile
import unittest
from datetime import date

from historico_precos.armazenamento import Banco
from historico_precos.exportar import dados_do_produto
from historico_precos.modelo import PontoDePreco, Produto
from historico_precos.qualidade import AVISO, BLOQUEIO, avaliar, limpar

EAN = "7896005800027"


def p(preco, data, loja="Loja A", descricao="Café 500g", preco_de=None):
    return PontoDePreco(ean=EAN, preco=preco, data_observada=data, fonte="vtex", loja=loja, url_origem="u",
                        url_evidencia=f"https://fonte/{loja}/{data}", metodo="m", descricao=descricao, preco_de=preco_de)


def tipos(alertas):
    return sorted((a.tipo, a.severidade, a.data) for a in alertas)


class TestQualidade(unittest.TestCase):
    def test_preco_absurdo_e_bloqueado(self):
        pontos = [p(24.9, "2026-01-10"), p(25.5, "2026-03-10"), p(249.0, "2026-05-10"), p(26.0, "2026-07-10")]
        limpos, alertas = limpar(pontos)
        self.assertIn(("preco_absurdo", BLOQUEIO, "2026-05-10"), tipos(alertas))
        self.assertNotIn(249.0, [x.preco for x in limpos])
        # o absurdo não pode gerar alertas falsos de salto nos vizinhos
        self.assertEqual([a.tipo for a in alertas], ["preco_absurdo"])

    def test_pico_que_volta_e_bloqueado(self):
        pontos = [p(20.0, "2026-01-01"), p(35.0, "2026-01-15"), p(20.5, "2026-02-01")]
        _, alertas = limpar(pontos)
        self.assertEqual(tipos(alertas), [("salto_suspeito", BLOQUEIO, "2026-01-15")])

    def test_salto_que_se_mantem_e_so_aviso(self):
        pontos = [p(20.0, "2026-01-01"), p(33.0, "2026-03-01"), p(33.5, "2026-05-01")]
        limpos, alertas = limpar(pontos)
        self.assertEqual(tipos(alertas), [("salto_suspeito", AVISO, "2026-03-01")])
        self.assertEqual(len(limpos), 3)

    def test_troca_de_embalagem_nao_e_erro(self):
        pontos = [p(15.0, "2026-01-01", descricao="Café 250g"), p(28.0, "2026-03-01", descricao="Café 500g")]
        self.assertEqual(avaliar(pontos), [])

    def test_produto_trocado_entre_lojas(self):
        pontos = [p(25.0, "2026-10-01", "Loja A", "Café 500g"), p(26.0, "2026-10-05", "Loja B", "Café 500g"),
                  p(14.0, "2026-10-03", "Loja C", "Café 250g")]
        alertas = [a for a in avaliar(pontos) if a.tipo == "produto_trocado"]
        self.assertEqual([(a.loja, a.severidade) for a in alertas], [("Loja C", AVISO)])

    def test_preco_de_irreal(self):
        self.assertEqual(tipos(avaliar([p(10.0, "2026-10-01", preco_de=99.0)])), [("preco_de_suspeito", AVISO, "2026-10-01")])

    def test_exportador_oculta_bloqueados(self):
        with tempfile.TemporaryDirectory() as d:
            banco = Banco(os.path.join(d, "t.db"))
            banco.salvar_produto(Produto(EAN, nome="Café"))
            banco.salvar_precos([p(24.9, "2026-10-01"), p(25.5, "2026-10-10"), p(249.0, "2026-10-15"), p(26.0, "2026-10-18")])
            dado = dados_do_produto(banco, EAN, None, hoje=date(2026, 10, 20))
            banco.con.close()
        self.assertEqual(dado["qualidade"], {"ocultos": 1, "avisos": 0})
        self.assertNotIn(249.0, [h["preco"] for h in dado["historico"]])
        self.assertEqual(dado["ofertas"][0]["preco"], 26.0)


if __name__ == "__main__":
    unittest.main()


class TestReferenciaECruzamento(unittest.TestCase):
    def test_muito_acima_do_custo_vira_aviso_sem_bloquear(self):
        limpos, alertas = limpar([p(33.99, "2026-10-21", descricao="Arroz Preto 500g")], custo=4.31)
        self.assertEqual(tipos(alertas), [("longe_do_custo", AVISO, "2026-10-21")])
        self.assertEqual(len(limpos), 1)

    def test_abaixo_do_custo_nao_alerta(self):
        # nas notas entre empresas a caixa costuma vir como "unidade": barra de cereal a R$ 13,49
        self.assertEqual(avaliar([p(1.69, "2026-10-21", descricao="Barra de Cereal 20g")], custo=13.49), [])

    def test_duas_lojas_com_diferenca_grande(self):
        alertas = avaliar([p(5.0, "2026-10-20", loja="A"), p(19.9, "2026-10-21", loja="B")])
        self.assertEqual(sorted(a.loja for a in alertas if a.tipo == "diferenca_entre_lojas"), ["A", "B"])
        self.assertTrue(all(a.severidade == AVISO for a in alertas))

