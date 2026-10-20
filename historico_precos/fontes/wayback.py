"""Histórico de preços a partir de cópias antigas de páginas no Wayback Machine (Internet Archive).

A API CDX é pública e devolve JSON. Cada cópia vira um ponto de preço com o link da cópia
como evidência, que qualquer pessoa pode abrir para conferir.
"""

from __future__ import annotations

from urllib.parse import urlencode

from ..extratores import extrair_preco
from ..modelo import PontoDePreco
from ..rede import Navegador

CDX = "https://web.archive.org/cdx/search/cdx"


def listar_capturas(nav: Navegador, url: str, desde: str | None = None, limite: int = 500) -> list[tuple[str, str]]:
    """Devolve [(timestamp AAAAMMDDhhmmss, url_original)] de cópias com HTTP 200 e conteúdo diferente."""
    params = {
        "url": url,
        "output": "json",
        "fl": "timestamp,original,statuscode",
        "filter": "statuscode:200",
        "collapse": "digest",  # pula cópias idênticas à anterior
        "limit": str(limite),
    }
    if desde:
        params["from"] = desde
    linhas = nav.get_json(f"{CDX}?{urlencode(params)}")
    if not isinstance(linhas, list) or len(linhas) < 2:
        return []
    cabecalho = linhas[0]
    i_ts, i_orig = cabecalho.index("timestamp"), cabecalho.index("original")
    return [(linha[i_ts], linha[i_orig]) for linha in linhas[1:]]


def amostrar(capturas: list, maximo: int) -> list:
    """Escolhe até `maximo` capturas espalhadas no tempo, sempre com a primeira e a última."""
    if maximo <= 0 or len(capturas) <= maximo:
        return capturas
    if maximo == 1:
        return [capturas[-1]]
    passo = (len(capturas) - 1) / (maximo - 1)
    indices = sorted({round(i * passo) for i in range(maximo)})
    return [capturas[i] for i in indices]


def _data(ts: str) -> str:
    return f"{ts[0:4]}-{ts[4:6]}-{ts[6:8]}"


def historico(
    nav: Navegador,
    url_produto: str,
    ean: str,
    loja: str,
    max_capturas: int = 40,
    desde: str | None = None,
) -> list[PontoDePreco]:
    pontos = []
    for ts, original in amostrar(listar_capturas(nav, url_produto, desde), max_capturas):
        # "id_" devolve o HTML original, sem a barra de navegação do arquivo
        html = nav.get_texto(f"https://web.archive.org/web/{ts}id_/{original}")
        if not html:
            continue
        achado = extrair_preco(html, ean)
        if achado is None:
            continue
        pontos.append(
            PontoDePreco(
                ean=ean,
                preco=achado.preco,
                preco_de=achado.preco_de,
                data_observada=_data(ts),
                fonte="wayback",
                loja=loja,
                url_origem=original,
                url_evidencia=f"https://web.archive.org/web/{ts}/{original}",
                metodo=f"wayback+{achado.metodo}",
                descricao=achado.nome,
            )
        )
    return pontos
