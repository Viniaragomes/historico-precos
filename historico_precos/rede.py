"""Acesso à web de forma educada: respeita robots.txt, limita a velocidade por site e se identifica."""

from __future__ import annotations

import gzip
import http.cookiejar
import zlib
import json
import logging
import time
import urllib.error
import urllib.request
from typing import Callable
from urllib.parse import urlencode, urlsplit
from urllib.robotparser import RobotFileParser

log = logging.getLogger(__name__)

USER_AGENT = "HistoricoPrecosBot/0.1 (pesquisa de precos ao consumidor; respeita robots.txt)"

# (url[, dados_post]) -> (status_http, texto). Status 0 significa falha de rede.
Abridor = Callable[..., tuple[int, str]]


class Navegador:
    def __init__(
        self,
        user_agent: str = USER_AGENT,
        intervalo: float = 2.0,
        timeout: float = 30.0,
        respeitar_robots: bool = True,
        abrir: Abridor | None = None,
        dormir: Callable[[float], None] = time.sleep,
        abrir_bytes: Callable[[str], bytes | None] | None = None,
    ):
        self.user_agent = user_agent
        self.intervalo = intervalo
        self.timeout = timeout
        self.respeitar_robots = respeitar_robots
        self._abrir = abrir or self._abrir_urllib
        self._dormir = dormir
        self._abrir_bytes = abrir_bytes
        # registro de cada requisição, para diagnosticar fontes que falham
        self.registro: list[dict] = []
        self._ultimo_acesso: dict[str, float] = {}
        self._robots: dict[str, RobotFileParser | None] = {}
        # guarda cookies de sessão entre requisições (painéis em PHP costumam exigir)
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    @staticmethod
    def _descomprimir(dados: bytes, codificacao: str | None) -> bytes:
        """Alguns servidores mandam gzip mesmo sem o pedido aceitar; o urllib não descomprime sozinho."""
        if (codificacao or "").lower() in ("gzip", "x-gzip") or dados[:2] == b"\x1f\x8b":
            try:
                return gzip.decompress(dados)
            except (OSError, EOFError):
                return dados
        if (codificacao or "").lower() == "deflate":
            try:
                return zlib.decompress(dados)
            except zlib.error:
                return zlib.decompress(dados, -zlib.MAX_WBITS)
        return dados

    @staticmethod
    def _decodificar(dados: bytes, charset: str | None) -> str:
        if charset:
            return dados.decode(charset, errors="replace")
        try:
            return dados.decode("utf-8")
        except UnicodeDecodeError:
            return dados.decode("latin-1")  # comum em sites antigos do governo

    def _abrir_urllib(self, url: str, dados: bytes | None = None) -> tuple[int, str]:
        cabecalhos = {"User-Agent": self.user_agent, "Accept": "*/*"}
        if dados is not None:
            cabecalhos["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(url, data=dados, headers=cabecalhos)
        try:
            with self._opener.open(req, timeout=self._tempo_limite(url)) as resp:
                corpo = self._descomprimir(resp.read(), resp.headers.get("Content-Encoding"))
                return resp.status, self._decodificar(corpo, resp.headers.get_content_charset())
        except urllib.error.HTTPError as e:
            try:
                corpo = self._decodificar(e.read()[:2000], None)
            except Exception:
                corpo = ""
            self._anotar(url, e.code, f"HTTP {e.code} {e.reason}", corpo)
            return e.code, ""
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            log.warning("falha de rede em %s: %s", url, e)
            self._anotar(url, 0, f"falha de rede: {e}", "")
            return 0, ""

    def _anotar(self, url: str, status: int, motivo: str, trecho: str) -> None:
        self.registro.append({"url": url[:300], "status": status, "motivo": motivo[:200],
                              "trecho": " ".join(trecho.split())[:300]})

    # sites que pedem mais espaço entre consultas do que o padrão
    INTERVALO_MINIMO = {"api.gdeltproject.org": 6.0}

    def _intervalo_do(self, host: str) -> float:
        """O maior entre: o padrão, o mínimo conhecido do site e o Crawl-delay que o robots.txt pede."""
        atraso = 0.0
        for base, rp in self._robots.items():
            if rp is not None and urlsplit(base).netloc == host:
                try:
                    atraso = float(rp.crawl_delay(self.user_agent) or 0)
                except (TypeError, ValueError):
                    atraso = 0.0
        return max(self.intervalo, self.INTERVALO_MINIMO.get(host, 0.0), atraso)

    def _esperar_vez(self, host: str) -> None:
        ultimo = self._ultimo_acesso.get(host)
        if ultimo is not None:
            falta = self._intervalo_do(host) - (time.monotonic() - ultimo)
            if falta > 0:
                self._dormir(falta)
        self._ultimo_acesso[host] = time.monotonic()

    def permitido(self, url: str) -> bool:
        if not self.respeitar_robots:
            return True
        partes = urlsplit(url)
        base = f"{partes.scheme}://{partes.netloc}"
        if base not in self._robots:
            self._esperar_vez(partes.netloc)
            status, texto = self._abrir(base + "/robots.txt")
            if status in (401, 403):
                # mesma convenção do urllib.robotparser: acesso negado ao robots = não coletar
                self._robots[base] = None
            else:
                rp = RobotFileParser()
                rp.parse(texto.splitlines() if status == 200 else [])
                self._robots[base] = rp
        rp = self._robots[base]
        return rp is not None and rp.can_fetch(self.user_agent, url)

    def get_bytes(self, url: str) -> bytes | None:
        """Baixa um arquivo (imagem, PDF) respeitando robots.txt e o intervalo entre acessos."""
        if not self.permitido(url):
            log.info("robots.txt não permite: %s", url)
            return None
        self._esperar_vez(urlsplit(url).netloc)
        if self._abrir_bytes:
            return self._abrir_bytes(url)
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent, "Accept": "*/*"})
        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
                return self._descomprimir(resp.read(), resp.headers.get("Content-Encoding")) if 200 <= resp.status < 300 else None
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            log.warning("falha ao baixar %s: %s", url, e)
            return None

    # sites lentos ganham mais tentativas e mais tempo para responder
    TENTATIVAS_EXTRA = {"web.archive.org": 2, "www.confaz.fazenda.gov.br": 2}
    TEMPO_LIMITE = {"www.confaz.fazenda.gov.br": 90.0}

    def _tempo_limite(self, url: str) -> float:
        return max(self.timeout, self.TEMPO_LIMITE.get(urlsplit(url).netloc, 0.0))

    def get_texto(self, url: str, tentativas: int = 2) -> str | None:
        return self._requisitar(url, None, tentativas + self.TENTATIVAS_EXTRA.get(urlsplit(url).netloc, 0))

    def post_texto(self, url: str, campos: dict, tentativas: int = 2) -> str | None:
        return self._requisitar(url, urlencode(campos, doseq=True).encode(), tentativas)

    def _requisitar(self, url: str, dados: bytes | None, tentativas: int) -> str | None:
        if not self.permitido(url):
            log.info("robots.txt não permite: %s", url)
            self._anotar(url, -1, "robots.txt não permite", "")
            return None
        host = urlsplit(url).netloc
        for tentativa in range(tentativas):
            self._esperar_vez(host)
            status, texto = self._abrir(url) if dados is None else self._abrir(url, dados)
            if 200 <= status < 300:  # a VTEX responde 206 (conteúdo parcial) em buscas paginadas
                return texto
            # 0 = falha de rede (tempo esgotado, TLS): o Internet Archive costuma oscilar; vale tentar de novo
            if status in (0, 429, 502, 503, 504) and tentativa + 1 < tentativas:
                self._dormir(max(self.intervalo * 5, self._intervalo_do(host) * 2))
                continue
            log.info("HTTP %s em %s", status, url)
            if not self.registro or self.registro[-1]["url"] != url[:300]:
                self._anotar(url, status, f"HTTP {status}", texto[:300])
            return None
        return None

    def get_json(self, url: str):
        texto = self.get_texto(url)
        if texto is None:
            return None
        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            log.info("resposta não é JSON: %s", url)
            self._anotar(url, 200, "resposta não é JSON", texto)
            return None
