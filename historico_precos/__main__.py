"""Linha de comando.

  python -m historico_precos buscar 7891000100103
  python -m historico_precos buscar 7891000100103 --url "Loja X=https://loja.com.br/produto/p"
  python -m historico_precos historico 7891000100103 --json saida.json
  python -m historico_precos detectar-lojas
  python -m historico_precos causas 7891000100103 --uf DF
  python -m historico_precos comparar 7891000100103 --atualizar
  python -m historico_precos leis monitorar --desde 2023-01-01
  python -m historico_precos leis aprovar <id> --li-a-norma
  python -m historico_precos mapa-df descobrir
  python -m historico_precos mapa-df coletar --termos CAFE,ARROZ
  python -m historico_precos mapa-df consultar CAFE --filtro 500G
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .agente import AgenteHistorico, Relatorio, detectar_mudancas
from .armazenamento import Banco
from .causas.analise import AgenteCausas, carregar_categorias
from .comparativo import comparar
from .fontes import vtex
from .causas.series import normalizar
from .leis.monitor import MonitorLeis
from .mapa_df.agente import AgenteMapaDF, adivinhar_campos, ultimos_meses
from .viabilidade import AgenteViabilidade, para_markdown, salvar
from .modelo import Produto
from .rede import Navegador

LOJAS_PADRAO = Path(__file__).resolve().parent.parent / "lojas.json"


def carregar_lojas(caminho: str) -> list[dict]:
    return [l for l in json.loads(Path(caminho).read_text(encoding="utf-8"))["lojas"] if l.get("ativa", True)]


def _url_extra(texto: str) -> tuple[str, str]:
    if "=" in texto and not texto.startswith("http"):
        nome, url = texto.split("=", 1)
        return nome.strip(), url.strip()
    return "página informada", texto


def imprimir(rel: Relatorio) -> None:
    p = rel.produto
    print(f"\nProduto: {p.nome or '(nome não encontrado)'} | {p.marca or ''} {p.quantidade or ''} | EAN {p.ean}")
    print(f"Pontos de preço: {len(rel.pontos)} (novos nesta execução: {rel.novos})\n")
    for pt in rel.pontos:
        de = f" (de R$ {pt.preco_de:.2f})" if pt.preco_de else ""
        print(f"  {pt.data_observada}  R$ {pt.preco:>8.2f}{de}  {pt.loja:<22} [{pt.fonte}]  {pt.url_evidencia}")
    if rel.mudancas:
        print("\nMudanças de preço:")
        for m in rel.mudancas:
            print(
                f"  {m.loja}: {m.data_anterior} R$ {m.preco_anterior:.2f} -> {m.data_nova} R$ {m.preco_novo:.2f}"
                f"  ({m.variacao_pct:+.1f}%)"
            )
    for aviso in rel.avisos:
        print(f"  ! {aviso}")


def exportar(rel: Relatorio, caminho: str) -> None:
    dado = {
        "produto": asdict(rel.produto),
        "precos": [pt.para_dict() for pt in rel.pontos],
        "mudancas": [{**asdict(m), "variacao_pct": round(m.variacao_pct, 2)} for m in rel.mudancas],
        "avisos": rel.avisos,
    }
    Path(caminho).write_text(json.dumps(dado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nExportado para {caminho}")


def _causas(args, nav: Navegador, banco: Banco) -> int:
    agente = AgenteCausas(nav, banco, usar_noticias=not args.sem_noticias)
    categoria, explicacoes = agente.explicar(args.ean, uf=args.uf, categoria=args.categoria)
    produto = banco.produto(args.ean)
    print(f"\nProduto: {(produto and produto.nome) or args.ean} | categoria: {categoria or 'não identificada'} | UF {args.uf}")
    if not explicacoes:
        print("Nenhuma mudança de preço no banco. Rode antes: python -m historico_precos buscar", args.ean)
        return 0
    for ex in explicacoes:
        m = ex.mudanca
        print(f"\n{m.loja}: {m.data_anterior} R$ {m.preco_anterior:.2f} -> {m.data_nova} R$ {m.preco_novo:.2f}"
              f"  ({m.variacao_pct:+.1f}%)")
        for e in ex.evidencias:
            print(f"  [{e.nivel}] {e.descricao}")
            for f in e.fontes:
                print(f"      fonte: {f}")
        print(f"  => Comprovado: {ex.comprovado_pct:+.1f}%  |  Sem causa comprovada: {ex.nao_explicado_pct:+.1f}%")
    print("\nComprovado = fato documentado com efeito calculável. Os demais níveis NÃO provam causa.")
    if args.json:
        dado = {"ean": args.ean, "categoria": categoria, "explicacoes": [
            {"mudanca": {**asdict(ex.mudanca), "variacao_pct": round(ex.mudanca.variacao_pct, 2)},
             "evidencias": [asdict(e) for e in ex.evidencias],
             "comprovado_pct": round(ex.comprovado_pct, 2), "nao_explicado_pct": round(ex.nao_explicado_pct, 2)}
            for ex in explicacoes]}
        Path(args.json).write_text(json.dumps(dado, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Exportado para {args.json}")
    return 0


def _comparar(args, banco: Banco) -> int:
    comp = comparar(banco.precos(args.ean), max_dias=args.max_dias, cidade=args.cidade)
    produto = banco.produto(args.ean)
    print(f"\nOnde está mais barato: {(produto and produto.nome) or args.ean}\n")
    if not comp.ofertas:
        print(f"Nenhum preço dos últimos {args.max_dias} dias. Rode com --atualizar ou use: buscar {args.ean}")
    for i, o in enumerate(comp.ofertas, 1):
        selo = "MAIS BARATO" if i == 1 else f"+R$ {o.diferenca_rs:.2f} ({o.diferenca_pct:+.1f}%)"
        promo = f" promoção, era R$ {o.preco_de:.2f}" if o.em_promocao else ""
        idade = "hoje" if o.dias == 0 else f"há {o.dias} dia(s)" + (" ⚠ pode estar desatualizado" if o.desatualizado else "")
        print(f"  {i}. {o.loja:<24} R$ {o.preco:>7.2f}  {selo:<20} {idade}{promo}  [{o.fonte}]")
    if len(comp.ofertas) > 1:
        print(f"\n  Média: R$ {comp.media:.2f} | Economia comprando no mais barato: até R$ {comp.economia_maxima:.2f}")
    if comp.ignoradas:
        print(f"\n  Fora da comparação (preço com mais de {args.max_dias} dias): "
              + ", ".join(f"{o.loja} R$ {o.preco:.2f} em {o.data}" for o in comp.ignoradas))
    print("\n  Preços online podem diferir da loja física.")
    if args.json:
        dado = {"ean": args.ean, "ofertas": [asdict(o) for o in comp.ofertas],
                "ignoradas": [asdict(o) for o in comp.ignoradas]}
        Path(args.json).write_text(json.dumps(dado, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Exportado para {args.json}")
    return 0


def _mostrar_candidato(c, detalhe: bool = False) -> None:
    aliq = f"{c.aliquota_anterior:g}% -> {c.aliquota_nova:g}%" if c.aliquota_anterior is not None else "alíquotas: ?"
    print(f"\n[{c.id}] {c.data_publicacao or 's/ data'} {c.fonte} ({c.uf}) pontuação {c.pontuacao}")
    print(f"  {c.titulo}")
    print(f"  {', '.join(c.tributos) or 'tributo: ?'} | {aliq} | vigência: {c.vigencia or '?'} | "
          f"produtos: {', '.join(c.categorias) or '?'}")
    print(f"  {c.url}")
    if detalhe:
        print(f"  Por que apareceu: {'; '.join(c.motivos)}")
        print(f"  Percentuais citados: {', '.join(f'{p:g}%' for p in c.percentuais) or 'nenhum'}")
        print(f"  Trecho: {c.trecho}")


def _leis(args, nav: Navegador, banco: Banco) -> int:
    monitor = MonitorLeis(nav, banco, categorias=carregar_categorias())
    if args.acao == "monitorar":
        ate = date.fromisoformat(args.ate) if args.ate else None
        novos = monitor.monitorar(date.fromisoformat(args.desde), ate)
        print(f"\n{len(novos)} candidato(s) novo(s) para conferir.")
        for c in novos:
            _mostrar_candidato(c)
    elif args.acao == "pendentes":
        pendentes = monitor.candidatos("pendente")
        print(f"\n{len(pendentes)} candidato(s) pendente(s).")
        for c in pendentes:
            _mostrar_candidato(c)
    elif args.acao == "ver":
        c = monitor.candidato(args.id)
        if not c:
            print("Candidato não encontrado.")
            return 1
        _mostrar_candidato(c, detalhe=True)
    elif args.acao == "descartar":
        print("Descartado." if monitor.descartar(args.id) else "Candidato não encontrado.")
    else:
        categorias = [x.strip() for x in args.categorias.split(",")] if args.categorias else None
        try:
            evento = monitor.aprovar(
                args.id, evento_id=args.evento_id, uf=args.uf, tributo=args.tributo,
                aliquota_anterior=args.anterior, aliquota_nova=args.nova, vigencia=args.vigencia,
                categorias=categorias, calculo=args.calculo, abrangencia=args.abrangencia,
            )
        except ValueError as e:
            print(f"Não aprovado: {e}")
            return 1
        print(f"Evento '{evento['id']}' gravado como COMPROVADO em eventos_tributarios.json")
        print(f"  {evento['tributo']} ({evento['uf']}): {evento['aliquota_anterior']:g}% -> "
              f"{evento['aliquota_nova']:g}% a partir de {evento['vigencia']} | fonte: {evento['fontes'][0]}")
    return 0


def _mapa_df(args, nav: Navegador, banco: Banco) -> int:
    agente = AgenteMapaDF(nav, banco)
    if args.acao == "descobrir":
        desc = agente.descobrir(Path(args.bruto))
        if desc is None:
            print("Não consegui abrir o painel (fora do ar, bloqueado ou robots.txt não permite).")
            return 1
        print(f"\nPainel: {desc.url}\nHTML salvo em {args.bruto}/painel.html\n")
        if desc.paineis_embutidos:
            print("⚠ O painel é um dashboard embutido (Power BI/Qlik/Tableau). A coleta por formulário não vai funcionar:")
            for p in desc.paineis_embutidos:
                print(f"   {p}")
        for i, f in enumerate(desc.formularios):
            papeis = adivinhar_campos(f)
            print(f"Formulário {i}: {f.metodo.upper()} {f.acao}")
            for c in f.campos:
                papel = next((p for p, n in papeis.items() if n == c.nome), "")
                opcoes = f"  opções: {', '.join(t for _, t in c.opcoes[:8])}{'...' if len(c.opcoes) > 8 else ''}" if c.opcoes else ""
                print(f"   - {c.nome} ({c.tipo}){' <- ' + papel if papel else ''}{opcoes}")
        if not desc.formularios:
            print("Nenhum formulário encontrado.")
        if desc.endpoints:
            print("\nEndereços de consulta achados no JavaScript:")
            for e in desc.endpoints[:15]:
                print(f"   {e}")
        print(f"\nTabelas na página inicial: {desc.tabelas}")
        print("\nPróximo passo: python -m historico_precos mapa-df coletar --termos CAFE --bruto mapa_df_bruto")
        return 0

    if args.acao == "coletar":
        termos = [t.strip() for t in args.termos.split(",")] if args.termos else agente.cfg["termos_padrao"]
        if args.meses:
            meses = [(int(m[:4]), int(m[5:7])) for m in args.meses.split(",")]
        else:
            meses = ultimos_meses(agente.cfg.get("meses_por_coleta", 4))
        novos = agente.coletar(termos, meses, Path(args.bruto) if args.bruto else None)
        print(f"{novos} registro(s) novo(s) guardado(s) de {len(termos)} termo(s) x {len(meses)} mês(es).")
        if novos == 0:
            print("Nada guardado. Rode 'mapa-df descobrir' e 'coletar --bruto pasta' e me mande os arquivos da pasta.")
        return 0

    serie = agente.serie_mensal(args.termo, args.filtro)
    print(f"\nMapa de Preços do DF (NF-e, não é preço de prateleira): {args.termo}"
          f"{' / ' + args.filtro if args.filtro else ''}\n")
    if not serie:
        print("Nada guardado para este termo.")
        return 0
    anterior = None
    for s in serie:
        var = f"  ({(s['mediana'] / anterior - 1) * 100:+.1f}%)" if anterior else ""
        print(f"  {s['mes']:02d}/{s['ano']}  mediana R$ {s['mediana']:>9.2f}  (mín {s['minimo']:.2f}, "
              f"máx {s['maximo']:.2f}, {s['itens']} itens){var}")
        anterior = s["mediana"]
    if args.detalhe:
        print()
        for r in agente.registros(args.termo):
            if args.filtro and normalizar(args.filtro) not in normalizar(r.descricao):
                continue
            print(f"  {r.mes:02d}/{r.ano}  R$ {r.valor_medio:>9.2f}  {r.unidade or '':<6} {r.descricao}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="historico_precos", description="Varre fontes públicas de preço por EAN.")
    ap.add_argument("--banco", default="precos.db")
    ap.add_argument("--lojas", default=str(LOJAS_PADRAO))
    ap.add_argument("--intervalo", type=float, default=2.0, help="segundos entre acessos ao mesmo site")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="comando", required=True)

    b = sub.add_parser("buscar", help="varre as fontes e mostra o histórico")
    b.add_argument("ean")
    b.add_argument("--sem-wayback", action="store_true")
    b.add_argument("--max-capturas", type=int, default=40, help="cópias antigas por página")
    b.add_argument("--url", action="append", default=[], help='página extra: "Nome da loja=https://..."')
    b.add_argument("--json", help="exporta o resultado para um arquivo JSON")

    h = sub.add_parser("historico", help="mostra o que já está no banco, sem acessar a internet")
    h.add_argument("ean")
    h.add_argument("--json")

    sub.add_parser("detectar-lojas", help="testa quais lojas do lojas.json respondem como VTEX")

    c = sub.add_parser("causas", help="explica cada mudança de preço, separando o que é comprovado do que não é")
    c.add_argument("ean")
    c.add_argument("--uf", default="DF")
    c.add_argument("--categoria", help="força a categoria (ver categorias.json)")
    c.add_argument("--sem-noticias", action="store_true")
    c.add_argument("--json")

    m = sub.add_parser("comparar", help="mostra em qual loja o produto está mais barato agora")
    m.add_argument("ean")
    m.add_argument("--atualizar", action="store_true", help="consulta as lojas antes de comparar")
    m.add_argument("--max-dias", type=int, default=30, help="ignora preços mais antigos que isso")
    m.add_argument("--cidade")
    m.add_argument("--json")

    lei = sub.add_parser("leis", help="monitor de leis que mudam impostos (com aprovação humana)")
    lsub = lei.add_subparsers(dest="acao", required=True)
    lm = lsub.add_parser("monitorar", help="varre Diário Oficial e outras fontes")
    lm.add_argument("--desde", required=True, help="AAAA-MM-DD")
    lm.add_argument("--ate", help="AAAA-MM-DD (padrão: hoje)")
    lsub.add_parser("pendentes", help="lista candidatos esperando conferência")
    lv = lsub.add_parser("ver", help="mostra um candidato em detalhe")
    lv.add_argument("id")
    ld = lsub.add_parser("descartar", help="marca um candidato como irrelevante")
    ld.add_argument("id")
    la = lsub.add_parser("aprovar", help="depois de ler a norma oficial, grava o evento como COMPROVADO")
    la.add_argument("id")
    la.add_argument("--li-a-norma", action="store_true", required=True,
                    help="obrigatório: confirma que você abriu e conferiu a norma oficial")
    la.add_argument("--evento-id", help="atualiza um evento existente (ex.: df-icms-modal-2024)")
    la.add_argument("--uf")
    la.add_argument("--tributo")
    la.add_argument("--anterior", type=float, help="alíquota anterior em %%")
    la.add_argument("--nova", type=float, help="alíquota nova em %%")
    la.add_argument("--vigencia", help="AAAA-MM-DD")
    la.add_argument("--categorias", help='separadas por vírgula, ou "*" para alíquota geral')
    la.add_argument("--calculo", choices=["por_dentro", "por_fora", "sem_efeito"])
    la.add_argument("--abrangencia")

    md = sub.add_parser("mapa-df", help="Mapa de Preços do DF (NF-e, painel da Secretaria de Economia)")
    msub = md.add_subparsers(dest="acao", required=True)
    mds = msub.add_parser("descobrir", help="mapeia formulários e campos do painel e salva o HTML para análise")
    mds.add_argument("--bruto", default="mapa_df_bruto", help="pasta onde salvar o HTML")
    mdc = msub.add_parser("coletar", help="consulta o painel por produto e mês e guarda")
    mdc.add_argument("--termos", help="separados por vírgula (padrão: termos_padrao do mapa_df.json)")
    mdc.add_argument("--meses", help="AAAA-MM separados por vírgula (padrão: últimos meses)")
    mdc.add_argument("--bruto", help="salva as respostas nesta pasta (útil para ajustar o agente)")
    mdq = msub.add_parser("consultar", help="mostra o histórico mensal guardado de um termo")
    mdq.add_argument("termo")
    mdq.add_argument("--filtro", help="só descrições que contenham este texto (ex.: '500G')")
    mdq.add_argument("--detalhe", action="store_true", help="lista cada item, não só a mediana")

    v = sub.add_parser("viabilidade", help="testa as fontes, roda os agentes numa amostra real e gera relatório")
    v.add_argument("--amostra", type=int, default=60, help="quantidade de produtos")
    v.add_argument("--max-capturas", type=int, default=10, help="cópias do Wayback por página")
    v.add_argument("--com-causas", type=int, default=15, help="quantos produtos passam pelo agente de causas")
    v.add_argument("--saida", default="relatorios")
    v.add_argument("--so-fontes", action="store_true", help="só testa se as fontes respondem (rápido)")

    bl = sub.add_parser("buscar-lista", help="roda 'buscar' para cada EAN de um arquivo (um por linha)")
    bl.add_argument("arquivo")
    bl.add_argument("--sem-wayback", action="store_true")
    bl.add_argument("--max-capturas", type=int, default=10)

    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(message)s")
    banco = Banco(args.banco)
    nav = Navegador(intervalo=args.intervalo)

    if args.comando == "viabilidade":
        agente = AgenteViabilidade(nav, banco, carregar_lojas(args.lojas))
        if args.so_fontes:
            for s in agente.sondar():
                print(f"{'OK ' if s.ok else 'NÃO'}  {s.fonte:<35} {s.detalhe}")
            return 0
        rel = agente.executar(args.amostra, args.max_capturas, args.com_causas, Path(args.saida) / "amostra.tsv")
        md, _ = salvar(rel, Path(args.saida))
        print(para_markdown(rel))
        print(f"Relatório salvo em {md}")
        return 0
    if args.comando == "buscar-lista":
        agente = AgenteHistorico(nav, banco, carregar_lojas(args.lojas))
        eans = [l.split("\t")[0].strip() for l in Path(args.arquivo).read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")]
        total = 0
        for i, ean in enumerate(eans, 1):
            rel = agente.executar(ean, usar_wayback=not args.sem_wayback, max_capturas=args.max_capturas)
            total += rel.novos
            print(f"({i}/{len(eans)}) {ean}: {rel.novos} preço(s) novo(s)")
        print(f"Total: {total} preço(s) novo(s).")
        return 0
    if args.comando == "mapa-df":
        return _mapa_df(args, nav, banco)
    if args.comando == "leis":
        return _leis(args, nav, banco)
    if args.comando == "causas":
        return _causas(args, nav, banco)
    if args.comando == "comparar":
        if args.atualizar:
            AgenteHistorico(nav, banco, carregar_lojas(args.lojas)).executar(args.ean, usar_wayback=False)
        return _comparar(args, banco)

    if args.comando == "buscar":
        agente = AgenteHistorico(nav, banco, carregar_lojas(args.lojas))
        rel = agente.executar(
            args.ean,
            usar_wayback=not args.sem_wayback,
            max_capturas=args.max_capturas,
            urls_extras=[_url_extra(u) for u in args.url],
        )
    elif args.comando == "historico":
        pontos = banco.precos(args.ean)
        produto = banco.produto(args.ean)
        rel = Relatorio(produto or Produto(args.ean), pontos, 0, detectar_mudancas(pontos))
    else:
        for loja in json.loads(Path(args.lojas).read_text(encoding="utf-8"))["lojas"]:
            ok = vtex.eh_vtex(nav, loja["dominio"])
            print(f"{'VTEX ok ' if ok else 'não     '} {loja['nome']:<25} {loja['dominio']}")
        return 0

    imprimir(rel)
    if args.json:
        exportar(rel, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
