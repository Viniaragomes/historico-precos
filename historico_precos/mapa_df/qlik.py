"""Leitor do Mapa de Preços do DF pelo mesmo caminho que a página pública usa.

O painel (paineis.fazenda.df.gov.br/mapadeprecos) é um "mashup" do Qlik Sense: o navegador de qualquer
visitante abre, sem login, uma conexão websocket com o servidor qap.fazenda.df.gov.br e pede ao motor do Qlik
as tabelas do aplicativo (identificadores no script público assets/js/app.js). Aqui fazemos o mesmo, só leitura,
com identificação honesta (User-Agent do projeto) e poucas requisições.

Só biblioteca padrão: um cliente websocket mínimo (RFC 6455) e as chamadas JSON-RPC do motor do Qlik.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import ssl
import struct
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from ..rede import USER_AGENT

HOST = "qap.fazenda.df.gov.br"
PREFIXO = "/paineis/"
APP_ID = "f0176c31-3c3b-4d15-94b3-ca9f2e902854"  # do assets/js/app.js do painel ("Funcionando SRV815")
APP_ID_ANTIGO = "26a0f2da-28fd-4249-9b72-055528829f0f"  # comentado no mesmo script ("SRV824")

# objetos que a página desenha (id do elemento HTML -> id do objeto Qlik), tirados do app.js
TABELAS = {"Tabela-1": "JDnEtp", "Tabela-2": "fXMujgw", "Tabela-3": "VpyShME", "Tabela-4": "VeewZ",
           "Tabela-5": "SmEzj", "Tabela-6": "GKjkaU", "Tabela-7": "MXWS", "Tabela-8": "kqYr",
           "Tabela-9": "vBfzHk", "Tabela-10": "phprpS"}
FILTROS = {"QVFILTROS-01": "QDPVpqr", "QVFILTROS-02": "gyEJEAH", "QVFILTROS-03": "jGFCY", "QVFILTROS-04": "kqYr",
           "QVFILTROS-05": "RjhVp", "QVFILTROS-07": "UJPWbUH"}
INDICADORES = {"KPI01": "JwTxe", "KPI02": "UJnFZ", "KPI03": "ufkBM", "KPI04": "EKeCnR", "DASHBOARD-04": "CWpswn"}


class ErroQlik(Exception):
    pass


# ---------------- websocket mínimo ----------------

class WebSocket:
    def __init__(self, url: str, origem: str | None = None, timeout: float = 60.0):
        partes = urlsplit(url)
        self.host = partes.hostname
        porta = partes.port or (443 if partes.scheme == "wss" else 80)
        bruto = socket.create_connection((self.host, porta), timeout=timeout)
        self.sock = ssl.create_default_context().wrap_socket(bruto, server_hostname=self.host) if partes.scheme == "wss" else bruto
        chave = base64.b64encode(os.urandom(16)).decode()
        caminho = partes.path + (f"?{partes.query}" if partes.query else "")
        linhas = [f"GET {caminho} HTTP/1.1", f"Host: {self.host}", "Upgrade: websocket", "Connection: Upgrade",
                  f"Sec-WebSocket-Key: {chave}", "Sec-WebSocket-Version: 13", f"User-Agent: {USER_AGENT}"]
        if origem:
            linhas.append(f"Origin: {origem}")
        self.sock.sendall(("\r\n".join(linhas) + "\r\n\r\n").encode())
        cabecalho = b""
        while b"\r\n\r\n" not in cabecalho:
            pedaco = self.sock.recv(4096)
            if not pedaco:
                break
            cabecalho += pedaco
        topo, _, self._sobra = cabecalho.partition(b"\r\n\r\n")
        self.resposta = topo.decode("latin-1")
        status = self.resposta.split(" ", 2)[1] if " " in self.resposta else "0"
        if status != "101":
            self.sock.close()
            raise ErroQlik(f"o servidor não abriu o websocket (HTTP {status}): {self.resposta[:300]}")

    def _ler(self, n: int) -> bytes:
        dados = self._sobra[:n]
        self._sobra = self._sobra[n:]
        while len(dados) < n:
            pedaco = self.sock.recv(max(65536, n - len(dados)))
            if not pedaco:
                raise ErroQlik("conexão fechada pelo servidor")
            dados += pedaco
        if len(dados) > n:
            self._sobra = dados[n:] + self._sobra
            dados = dados[:n]
        return dados

    def enviar(self, texto: str, opcode: int = 0x1) -> None:
        carga = texto.encode() if isinstance(texto, str) else texto
        mascara = os.urandom(4)
        n = len(carga)
        topo = bytes([0x80 | opcode])
        if n < 126:
            topo += bytes([0x80 | n])
        elif n < 65536:
            topo += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            topo += bytes([0x80 | 127]) + struct.pack(">Q", n)
        self.sock.sendall(topo + mascara + bytes(b ^ mascara[i % 4] for i, b in enumerate(carga)))

    def receber(self) -> str:
        partes = []
        while True:
            b1, b2 = self._ler(2)
            fim, opcode, n = b1 & 0x80, b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._ler(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._ler(8))[0]
            mascara = self._ler(4) if b2 & 0x80 else None
            carga = self._ler(n)
            if mascara:
                carga = bytes(b ^ mascara[i % 4] for i, b in enumerate(carga))
            if opcode == 0x8:
                raise ErroQlik(f"servidor fechou a conexão: {carga[2:].decode('utf-8', 'replace')}")
            if opcode == 0x9:
                self.enviar(carga, opcode=0xA)
                continue
            if opcode in (0x1, 0x2, 0x0):
                partes.append(carga)
                if fim:
                    return b"".join(partes).decode("utf-8", "replace")

    def fechar(self) -> None:
        try:
            self.enviar(b"\x03\xe8", opcode=0x8)
        except OSError:
            pass
        self.sock.close()


# ---------------- motor do Qlik (JSON-RPC) ----------------

class Motor:
    def __init__(self, app_id: str = APP_ID, host: str = HOST, prefixo: str = PREFIXO, origem: str | None = None,
                 url: str | None = None):
        self.ws = WebSocket(url or f"wss://{host}{prefixo}app/{app_id}", origem=origem)
        self._id = 0
        self.avisos: list[dict] = []
        self.app_id = app_id

    def chamar(self, handle: int, metodo: str, params=None) -> dict:
        self._id += 1
        self.ws.enviar(json.dumps({"jsonrpc": "2.0", "id": self._id, "handle": handle, "method": metodo,
                                   "params": params if params is not None else {}}))
        while True:
            msg = json.loads(self.ws.receber())
            if msg.get("id") == self._id:
                if "error" in msg:
                    raise ErroQlik(f"{metodo}: {msg['error']}")
                return msg.get("result", {})
            self.avisos.append(msg)  # notificações (OnConnected, OnAuthenticationInformation…)

    def abrir_app(self) -> int:
        return self.chamar(-1, "OpenDoc", [self.app_id])["qReturn"]["qHandle"]

    def fechar(self) -> None:
        self.ws.fechar()


@dataclass
class Tabela:
    elemento: str
    objeto: str
    tipo: str | None = None
    titulo: str | None = None
    dimensoes: list[str] = field(default_factory=list)
    medidas: list[str] = field(default_factory=list)
    linhas_total: int | None = None
    amostra: list[list[str]] = field(default_factory=list)
    erro: str | None = None


def _texto_celula(c: dict) -> str:
    return c.get("qText") if c.get("qText") is not None else str(c.get("qNum"))


def ler_tabela(motor: Motor, doc: int, elemento: str, objeto: str, linhas: int = 20) -> Tabela:
    t = Tabela(elemento, objeto)
    try:
        h = motor.chamar(doc, "GetObject", {"qId": objeto})["qReturn"]["qHandle"]
        lay = motor.chamar(h, "GetLayout")["qLayout"]
        t.tipo = (lay.get("qInfo") or {}).get("qType")
        t.titulo = lay.get("title") or (lay.get("qMeta") or {}).get("title")
        cubo = lay.get("qHyperCube")
        if not cubo:
            return t
        t.dimensoes = [d.get("qFallbackTitle") for d in cubo.get("qDimensionInfo", [])]
        t.medidas = [m.get("qFallbackTitle") for m in cubo.get("qMeasureInfo", [])]
        t.linhas_total = (cubo.get("qSize") or {}).get("qcy")
        largura = max(1, (cubo.get("qSize") or {}).get("qcx") or len(t.dimensoes) + len(t.medidas))
        if linhas and t.linhas_total:
            pag = motor.chamar(h, "GetHyperCubeData", {"qPath": "/qHyperCubeDef", "qPages": [
                {"qLeft": 0, "qTop": 0, "qWidth": largura, "qHeight": min(linhas, t.linhas_total)}]})
            for p in pag.get("qDataPages", []):
                t.amostra += [[_texto_celula(c) for c in linha] for linha in p.get("qMatrix", [])]
    except ErroQlik as e:
        t.erro = str(e)[:300]
    return t


def campos_do_app(motor: Motor, doc: int) -> list[str]:
    h = motor.chamar(doc, "CreateSessionObject", [{"qInfo": {"qType": "FieldList"},
                                                   "qFieldListDef": {"qShowSystem": False, "qShowHidden": False}}])["qReturn"]["qHandle"]
    return [i.get("qName") for i in motor.chamar(h, "GetLayout")["qLayout"]["qFieldList"]["qItems"]]


def explorar(app_id: str = APP_ID, linhas: int = 20) -> dict:
    """Abre o app como a página pública faz e descreve o que há: campos, tabelas, colunas e uma amostra."""
    tentativas, motor, origem_usada = [], None, None
    # 1º sem cabeçalho Origin; 2º com a origem do próprio servidor Qlik (sempre aceita pela configuração padrão)
    for origem in (None, f"https://{HOST}"):
        try:
            motor = Motor(app_id, origem=origem)
            origem_usada = origem
            break
        except (ErroQlik, OSError) as e:
            tentativas.append({"origin": origem, "erro": str(e)[:400]})
    if motor is None:
        return {"ok": False, "app_id": app_id, "tentativas": tentativas}
    try:
        doc = motor.abrir_app()
        layout = motor.chamar(doc, "GetAppLayout")["qLayout"]
        resultado = {
            "ok": True, "app_id": app_id, "origin_usado": origem_usada, "tentativas": tentativas,
            "titulo": layout.get("qTitle"), "ultima_carga": layout.get("qLastReloadTime"),
            "campos": campos_do_app(motor, doc),
            "tabelas": [ler_tabela(motor, doc, el, ob, linhas).__dict__ for el, ob in TABELAS.items()],
            "filtros": [ler_tabela(motor, doc, el, ob, 0).__dict__ for el, ob in FILTROS.items()],
            "indicadores": [ler_tabela(motor, doc, el, ob, 5).__dict__ for el, ob in INDICADORES.items()],
            "avisos_do_servidor": motor.avisos[:5],
        }
    except (ErroQlik, OSError) as e:
        resultado = {"ok": False, "app_id": app_id, "origin_usado": origem_usada, "erro": str(e)[:400],
                     "avisos_do_servidor": motor.avisos[:5]}
    finally:
        motor.fechar()
    return resultado
