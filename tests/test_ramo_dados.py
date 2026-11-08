import os
import sqlite3
import tempfile
import unittest

from historico_precos import ramo_dados
from historico_precos.armazenamento import Banco
from historico_precos.fontes import pagina_produto
from historico_precos.modelo import PontoDePreco


def ponto(ean, loja, preco, data="2026-11-08", fonte="pagina-produto", url="https://l/p/1"):
    return PontoDePreco(ean=ean, preco=preco, data_observada=data, fonte=fonte, loja=loja, url_origem=url,
                        url_evidencia=url, metodo="vinculo-nome", descricao="x")


class TestJuntar(unittest.TestCase):
    def test_parte_paralela_substitui_so_as_suas_lojas(self):
        tmp = tempfile.mkdtemp()
        base, parte = os.path.join(tmp, "base.db"), os.path.join(tmp, "parte.db")
        b = Banco(base)
        b.con.executescript(pagina_produto._ESQUEMA_LOJA)
        b.salvar_precos([ponto("1", "Big Box", 10.0, data="2026-11-07"), ponto("2", "Big Box", 5.0, data="2026-11-07", url="https://l/p/2"),
                         ponto("3", "Fort", 7.0), ponto("9", "Atacadão", 3.0, fonte="vtex")])
        b.con.execute("INSERT INTO produtos_loja (loja, url, nome, ean) VALUES ('Big Box', 'https://l/p/1', 'a', '1')")
        b.con.execute("INSERT INTO produtos_loja (loja, url, nome, ean) VALUES ('Fort', 'https://f/p/1', 'c', '3')")
        b.con.commit()
        b.con.close()
        # a parte paralela partiu da mesma cópia, leu o Big Box de novo e desfez o vínculo do produto 2
        import shutil

        shutil.copy(base, parte)
        p = sqlite3.connect(parte)
        p.execute("DELETE FROM precos WHERE ean = '2'")
        p.execute("INSERT INTO precos SELECT ean, 11.0, '2026-11-08', fonte, loja, url_origem, url_evidencia, metodo, preco_de, cidade, descricao, coletado_em FROM precos WHERE ean = '1'")
        p.execute("UPDATE produtos_loja SET preco = 11.0, data = '2026-11-08' WHERE loja = 'Big Box'")
        p.commit()
        p.close()
        # enquanto isso, a parte base gravou um preço novo do Atacadão
        b = sqlite3.connect(base)
        b.execute("INSERT INTO precos SELECT '8', 4.0, data_observada, fonte, loja, url_origem, url_evidencia, metodo, preco_de, cidade, descricao, coletado_em FROM precos WHERE ean = '9'")
        b.commit()
        b.close()

        r = ramo_dados.juntar(base, parte, ["Big Box"])
        c = sqlite3.connect(base)
        bigbox = sorted(c.execute("SELECT ean, preco FROM precos WHERE loja = 'Big Box'").fetchall())
        self.assertEqual(bigbox, [("1", 10.0), ("1", 11.0)])  # o vínculo desfeito (produto 2) sumiu
        self.assertEqual(c.execute("SELECT preco FROM produtos_loja WHERE loja = 'Big Box'").fetchone(), (11.0,))
        self.assertEqual(c.execute("SELECT COUNT(*) FROM precos WHERE loja IN ('Fort', 'Atacadão')").fetchone(), (3,))
        self.assertEqual(c.execute("SELECT COUNT(*) FROM produtos_loja WHERE loja = 'Fort'").fetchone(), (1,))
        self.assertEqual(r["paginas"], 1)

    def test_grupos_dividem_as_lojas(self):
        lojas = [{"nome": str(i)} for i in range(8)]
        partes = [[l["nome"] for l in ramo_dados.lojas_do_grupo(lojas, g, 4)] for g in range(4)]
        self.assertEqual(sorted(sum(partes, [])), [str(i) for i in range(8)])
        self.assertEqual(partes[0], ["0", "4"])


if __name__ == "__main__":
    unittest.main()
