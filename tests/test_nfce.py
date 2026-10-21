import unittest

from historico_precos.fontes import nfce_df
from historico_precos.vinculo import Catalogo

CUPOM = """<html><body><div id="conteudo">
<div class="txtCenter"><div id="u20" class="txtTopo">SUPERMERCADO EXEMPLO LTDA</div>
<div class="text">CNPJ: 12.345.678/0001-90</div>
<div class="text">SQS 102 BLOCO A, ASA SUL, BRASILIA, DF</div></div>
<table id="tabResult">
<tr id="Item + 1"><td valign="top"><span class="txtTit">ARROZ CAMIL TIPO 1 5KG</span><span class="RCod">(Código: 7896006711155 )</span><br/>
<span class="Rqtd"><strong>Qtde.:</strong>1</span><span class="RUN"><strong>UN: </strong>UN</span>
<span class="RvlUnit"><strong>Vl. Unit.:</strong>&nbsp;24,99</span></td><td class="txtTit noWrap"><span class="valor">24,99</span></td></tr>
<tr id="Item + 2"><td valign="top"><span class="txtTit2">AGUA MINERAL PLATINA S/GAS 310ML</span><span class="RCod">(Código: 10234 )</span><br/>
<span class="Rqtd"><strong>Qtde.:</strong>2</span><span class="RUN"><strong>UN: </strong>UN</span>
<span class="RvlUnit"><strong>Vl. Unit.:</strong>&nbsp;2,49</span></td><td class="txtTit noWrap"><span class="valor">4,98</span></td></tr>
<tr id="Item + 3"><td valign="top"><span class="txtTit">BANANA PRATA KG</span><span class="RCod">(Código: 55 )</span><br/>
<span class="Rqtd"><strong>Qtde.:</strong>1,235</span><span class="RUN"><strong>UN: </strong>KG</span>
<span class="RvlUnit"><strong>Vl. Unit.:</strong>&nbsp;6,99</span></td><td class="txtTit noWrap"><span class="valor">8,63</span></td></tr>
</table>
<ul><li><strong>Número: </strong>1234 <strong>Série: </strong>1 <strong>Emissão: </strong>21/10/2026 10:21:33-03:00</li></ul>
<div id="infos"><h4>Consumidor</h4><ul><li><strong>CPF: </strong>123.456.789-00</li><li><strong>Nome: </strong>FULANO</li></ul></div>
</div></body></html>"""


class TestCupom(unittest.TestCase):
    def test_ler(self):
        c = nfce_df.ler_cupom(CUPOM)
        self.assertEqual((c.mercado, c.cnpj, c.emissao), ("SUPERMERCADO EXEMPLO LTDA", "12345678000190", "2026-10-21"))
        self.assertIn("ASA SUL", c.endereco)
        self.assertEqual([(i.descricao, i.codigo, i.quantidade, i.unidade, i.valor_unitario) for i in c.itens], [
            ("ARROZ CAMIL TIPO 1 5KG", "7896006711155", 1.0, "UN", 24.99),
            ("AGUA MINERAL PLATINA S/GAS 310ML", "10234", 2.0, "UN", 2.49),
            ("BANANA PRATA KG", "55", 1.235, "KG", 6.99)])

    def test_cpf_nunca_aparece(self):
        c = nfce_df.ler_cupom(CUPOM)
        self.assertNotIn("123.456.789-00", repr(c))
        self.assertNotIn("FULANO", repr(c))

    def test_pontos_codigo_valido_e_vinculo(self):
        cat = Catalogo([("7898955519028", "Água Mineral Platina sem Gás 310ml", "Platina")])
        pontos = nfce_df.pontos_do_cupom(nfce_df.ler_cupom(CUPOM), cat, "abcdef1234567890")
        self.assertEqual([(p.ean, p.preco, p.metodo, p.loja) for p in pontos], [
            ("7896006711155", 24.99, "nfce-codigo", "SUPERMERCADO EXEMPLO LTDA"),
            ("7898955519028", 2.49, "nfce-vinculo-nome", "SUPERMERCADO EXEMPLO LTDA")])  # código interno: vínculo pelo nome
        # banana a granel (código 55, sem tamanho no nome) fica de fora: sem vínculo seguro


if __name__ == "__main__":
    unittest.main()
