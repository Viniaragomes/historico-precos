"""Roda, a partir de uma conexão no Brasil, a investigação dos sites que recusam os servidores do GitHub.

Em 20/10/2026 o firewall do GDF (CEASA-DF, IPE-DF, dados.df.gov.br) respondeu "Página bloqueada" aos servidores
do GitHub (nos EUA), e a Conab respondeu "403 - Acesso proibido". Não é bloqueio de robô: é bloqueio de endereço
de fora do país. Do seu computador, no Brasil, o acesso é o mesmo de qualquer pessoa daqui.

As regras continuam: robots.txt respeitado, robô identificado, intervalo entre acessos. Se algum site recusar
também daqui, o relatório registra e paramos.

Uso, no seu computador (com Python 3.10+ e o repositório clonado):
    python ferramentas/coleta_brasil.py              # investiga e salva em relatorios/brasil
    python ferramentas/coleta_brasil.py --publicar   # e envia o relatório para o GitHub (git add/commit/push)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "ferramentas"))
import investigar_fontes  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publicar", action="store_true", help="faz commit e push do relatório")
    args = ap.parse_args()
    if args.publicar:
        email = subprocess.run(["git", "-C", str(RAIZ), "config", "user.email"], capture_output=True, text=True).stdout.strip()
        if not email:
            print('O Git ainda não sabe quem você é. Rode antes:\n  git config --global user.name "Seu Nome"\n'
                  '  git config --global user.email "seu-email"\n(ou o e-mail privado do GitHub, em Settings > Emails)')
            return 1
    pasta = RAIZ / "relatorios" / "brasil"
    r = investigar_fontes.investigar(pasta, so=investigar_fontes.SO_DO_BRASIL)
    for nome, item in r.items():
        print(f"\n== {nome}: robots {item['robots']['status']}")
        for p in item["paginas"]:
            print(f"   {p.get('status')} {p['url'][:90]} {p.get('titulo') or ''} {p.get('nota') or p.get('erro') or ''}")
            if p.get("arquivos_de_dados"):
                print(f"      arquivos de dados: {p['arquivos_de_dados'][:5]}")
    print(f"\nRelatório: {pasta / 'investigacao.json'}")
    if args.publicar:
        subprocess.run(["git", "-C", str(RAIZ), "add", "relatorios/brasil"], check=True)
        feito = subprocess.run(["git", "-C", str(RAIZ), "commit", "-m", "Investigação a partir do Brasil"], capture_output=True, text=True)
        if feito.returncode != 0 and "nothing to commit" not in feito.stdout + feito.stderr:
            print(feito.stdout + feito.stderr)
            return 1
        subprocess.run(["git", "-C", str(RAIZ), "pull", "--rebase", "origin", "main"], check=True)
        subprocess.run(["git", "-C", str(RAIZ), "push", "origin", "main"], check=True)
        print("Enviado ao GitHub.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
