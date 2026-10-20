import base64
import hashlib
import json
import socket
import struct
import threading
import unittest

from historico_precos.mapa_df import qlik


def _ler_frame(con):
    b1, b2 = con.recv(2)
    n = b2 & 0x7F
    if n == 126:
        n = struct.unpack(">H", con.recv(2))[0]
    elif n == 127:
        n = struct.unpack(">Q", con.recv(8))[0]
    mascara = con.recv(4)
    carga = b""
    while len(carga) < n:
        carga += con.recv(n - len(carga))
    return b1 & 0x0F, bytes(b ^ mascara[i % 4] for i, b in enumerate(carga))


def _frame(texto, fragmentar=False):
    dados = texto.encode()
    if fragmentar:  # dois pedaços: texto sem FIN + continuação com FIN
        a, b = dados[:5], dados[5:]
        return bytes([0x01, len(a)]) + a + bytes([0x80, 126]) + struct.pack(">H", len(b)) + b
    n = len(dados)
    topo = bytes([0x81, n]) if n < 126 else bytes([0x81, 126]) + struct.pack(">H", n)
    return topo + dados


def servidor_qlik_falso(respostas):
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    pedidos = []

    def atender():
        con, _ = srv.accept()
        cab = b""
        while b"\r\n\r\n" not in cab:
            cab += con.recv(4096)
        pedidos.append(cab.decode())
        chave = [l.split(": ")[1] for l in cab.decode().split("\r\n") if l.lower().startswith("sec-websocket-key")][0]
        aceite = base64.b64encode(hashlib.sha1((chave + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        con.sendall(f"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: {aceite}\r\n\r\n".encode()
                    + _frame(json.dumps({"jsonrpc": "2.0", "method": "OnConnected", "params": {"qSessionState": "SESSION_CREATED"}})))
        while True:
            try:
                op, carga = _ler_frame(con)
            except (ValueError, OSError):
                break
            if op == 0x8:
                break
            msg = json.loads(carga)
            pedidos.append(msg)
            resultado = respostas(msg)
            con.sendall(_frame(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": resultado}), fragmentar=msg["id"] % 2 == 0))
        con.close()
        srv.close()

    threading.Thread(target=atender, daemon=True).start()
    return f"ws://127.0.0.1:{srv.getsockname()[1]}/paineis/app/x", pedidos


def respostas(msg):
    m = msg["method"]
    if m == "OpenDoc":
        return {"qReturn": {"qHandle": 1}}
    if m == "GetObject":
        return {"qReturn": {"qHandle": 2}}
    if m == "GetLayout":
        return {"qLayout": {"qInfo": {"qType": "table"}, "title": "Preços por produto", "qHyperCube": {
            "qDimensionInfo": [{"qFallbackTitle": "Descrição"}, {"qFallbackTitle": "GTIN"}],
            "qMeasureInfo": [{"qFallbackTitle": "Preço médio"}], "qSize": {"qcx": 3, "qcy": 1200}}}}
    if m == "GetHyperCubeData":
        assert msg["params"]["qPages"][0]["qHeight"] == 2
        return {"qDataPages": [{"qMatrix": [[{"qText": "CAFE X 500G"}, {"qText": "7891"}, {"qText": "R$ 18,90", "qNum": 18.9}],
                                            [{"qText": "CAFE Y 500G"}, {"qText": "-"}, {"qNum": 21.5}]]}]}
    return {}


class TestQlik(unittest.TestCase):
    def test_conversa_com_o_motor(self):
        url, pedidos = servidor_qlik_falso(respostas)
        motor = qlik.Motor("app-1", url=url)
        doc = motor.abrir_app()
        t = qlik.ler_tabela(motor, doc, "Tabela-1", "JDnEtp", linhas=2)
        motor.fechar()
        self.assertEqual((t.titulo, t.dimensoes, t.medidas, t.linhas_total), ("Preços por produto", ["Descrição", "GTIN"], ["Preço médio"], 1200))
        self.assertEqual(t.amostra, [["CAFE X 500G", "7891", "R$ 18,90"], ["CAFE Y 500G", "-", "21.5"]])
        self.assertIn("HistoricoPrecosBot", pedidos[0])  # se identifica como robô
        self.assertNotIn("Origin:", pedidos[0])
        self.assertEqual(pedidos[1]["method"], "OpenDoc")
        self.assertEqual(motor.avisos[0]["method"], "OnConnected")

    def test_recusa_vira_erro_claro(self):
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)

        def recusar():
            con, _ = srv.accept()
            con.recv(4096)
            con.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
            con.close()

        threading.Thread(target=recusar, daemon=True).start()
        with self.assertRaisesRegex(qlik.ErroQlik, "HTTP 403"):
            qlik.WebSocket(f"ws://127.0.0.1:{srv.getsockname()[1]}/x")
        srv.close()


if __name__ == "__main__":
    unittest.main()


def respostas_precos(msg):
    m = msg["method"]
    if m == "OpenDoc":
        return {"qReturn": {"qHandle": 1}}
    if m in ("GetField", "CreateSessionObject"):
        if m == "CreateSessionObject":
            dims = [d["qDef"]["qFieldDefs"][0] for d in msg["params"][0]["qHyperCubeDef"]["qDimensions"]]
            assert not any("cpf" in d or "cnpj" in d for d in dims)  # nunca pede dado de pessoa
        return {"qReturn": {"qHandle": 3}}
    if m == "GetLayout":
        return {"qLayout": {"qHyperCube": {"qSize": {"qcx": 10, "qcy": 3}}}}
    if m == "GetHyperCubeData":
        def linha(ean, data, num, mediana, itens):
            return [{"qText": ean}, {"qText": data, "qNum": num}, {"qText": "UN"}, {"qNum": mediana}, {"qNum": mediana},
                    {"qNum": mediana - 1}, {"qNum": mediana + 1}, {"qNum": 100}, {"qNum": itens}, {"qText": "CAFE X 500G"}]
        return {"qDataPages": [{"qMatrix": [linha("7891", "15/10/2026", 46310, 18.5, 12),
                                            linha("7891", "-", None, 19.0, 3),  # sem data: ignorada
                                            linha("9999", "16/10/2026", 46311, 5.0, 2)]}]}  # GTIN não pedido
    return {}


class TestPrecosQlik(unittest.TestCase):
    def test_precos_por_gtin_e_serie(self):
        import sqlite3

        url, pedidos = servidor_qlik_falso(respostas_precos)
        motor = qlik.Motor("app", url=url)
        doc = motor.abrir_app()
        linhas = qlik.precos_por_gtin(motor, doc, ["7891", "abc"])
        motor.fechar()
        self.assertEqual(len(linhas), 1)
        self.assertEqual((linhas[0]["data"], linhas[0]["mediana"], linhas[0]["itens"]), ("2026-10-15", 18.5, 12))
        selecao = next(p for p in pedidos[1:] if p["method"] == "SelectValues")
        self.assertEqual([v["qText"] for v in selecao["params"]["qFieldValues"]], ["7891"])
        self.assertEqual(pedidos[-1]["method"], "ClearAll")  # deixa a sessão limpa

        con = sqlite3.connect(":memory:")
        qlik.salvar(con, linhas)
        qlik.salvar(con, [{**linhas[0], "mediana": 18.9}])  # recarga atualiza o mesmo dia
        s = qlik.serie(con, "7891")
        self.assertEqual(s["unidade"], "UN")
        self.assertEqual([p["mediana"] for p in s["pontos"]], [18.9])

    def test_data_em_numero_de_serie(self):
        self.assertEqual(qlik._data_iso({"qText": "", "qNum": 46310}), "2026-10-15")
        self.assertEqual(qlik._data_iso({"qText": "2026-10-15"}), "2026-10-15")

    def test_tendencia(self):
        from datetime import date, timedelta

        base = date(2026, 10, 1)
        pontos = [{"data": (base + timedelta(days=i)).isoformat(), "mediana": 10.0 if i < 7 else 11.0, "itens": 3}
                  for i in range(14)]
        t = qlik.tendencia(pontos)
        self.assertEqual(t["variacao_pct"], 10.0)
        self.assertIsNone(qlik.tendencia(pontos[-3:])["variacao_pct"])  # poucas notas
