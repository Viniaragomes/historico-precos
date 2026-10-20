from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone


def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Produto:
    ean: str
    nome: str | None = None
    marca: str | None = None
    quantidade: str | None = None
    fonte: str | None = None


@dataclass
class PontoDePreco:
    """Um preço observado, sempre acompanhado da evidência de onde foi tirado."""

    ean: str
    preco: float
    data_observada: str  # AAAA-MM-DD: dia em que o preço valia
    fonte: str  # vtex | wayback | open_prices
    loja: str
    url_origem: str  # página original onde o preço aparecia
    url_evidencia: str  # link para conferir (cópia arquivada, resposta da API)
    metodo: str  # como o preço foi extraído (json-ld, vtex-api, sku-json...)
    preco_de: float | None = None  # preço "de" riscado, quando houver
    cidade: str | None = None
    descricao: str | None = None  # nome do produto como a fonte mostrava (revela troca de embalagem)
    coletado_em: str = field(default_factory=agora_iso)

    def chave(self) -> tuple:
        return (self.ean, self.loja, self.data_observada, round(self.preco, 2), self.fonte)

    def para_dict(self) -> dict:
        return asdict(self)
