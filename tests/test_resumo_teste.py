import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("resumo_teste", Path(__file__).resolve().parents[1] / "ferramentas" / "resumo_teste.py")
resumo_teste = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resumo_teste)


class TestResumoTeste(unittest.TestCase):
    def test_sus(self):
        self.assertEqual(resumo_teste.nota_sus([5, 1] * 5), 100.0)
        self.assertEqual(resumo_teste.nota_sus([1, 5] * 5), 0.0)
        self.assertEqual(resumo_teste.nota_sus([3] * 10), 50.0)
        with self.assertRaises(ValueError):
            resumo_teste.nota_sus([3] * 9)

    def test_tarefas(self):
        linhas = [
            {"tarefa": "T1", "resultado": "sucesso", "tempo_seg": "30", "facilidade_1a7": "6", "onde_travou": ""},
            {"tarefa": "T1", "resultado": "parcial", "tempo_seg": "90", "facilidade_1a7": "4", "onde_travou": "não achou o botão"},
            {"tarefa": "T2", "resultado": "", "tempo_seg": "", "facilidade_1a7": "", "onde_travou": ""},
        ]
        r = resumo_teste.resumir_tarefas(linhas)
        self.assertEqual(len(r), 1)
        self.assertEqual((r[0]["sucesso"], r[0]["facilidade"], r[0]["tempo_mediano"]), (0.75, 5, 60))
        self.assertEqual(r[0]["travou"], ["não achou o botão"])


if __name__ == "__main__":
    unittest.main()
