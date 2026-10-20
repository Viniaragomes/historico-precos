// Preço com Prova: leitor de código de barras + histórico, comparativo e causas, a partir de dados/*.json.

const conteudo = document.getElementById("conteudo");
const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const pct = (v) => `${v > 0 ? "+" : ""}${v.toFixed(1).replace(".", ",")}%`;
const LEITOR_ALTERNATIVO = "https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.8/html5-qrcode.min.js";
const NIVEIS = {
  "COMPROVADO": "comprovado",
  "A CONFIRMAR": "a-confirmar",
  "DECLARADO": "declarado",
  "ASSOCIADO": "associado",
  "REFERÊNCIA": "referencia",
};

// ---------- utilidades ----------

function el(tag, attrs = {}, ...filhos) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const f of filhos.flat()) {
    if (f == null || f === false) continue;
    n.append(f instanceof Node ? f : document.createTextNode(String(f)));
  }
  return n;
}

const svgNS = "http://www.w3.org/2000/svg";
function s(tag, attrs = {}, ...filhos) {
  const n = document.createElementNS(svgNS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null) n.setAttribute(k, v);
  for (const f of filhos) n.append(f instanceof Node ? f : document.createTextNode(String(f)));
  return n;
}

function dataBR(iso) {
  const [a, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}/${a}`;
}

function idade(iso) {
  const dias = Math.round((Date.now() - new Date(iso + "T12:00:00").getTime()) / 864e5);
  if (dias <= 0) return "hoje";
  if (dias === 1) return "ontem";
  return `há ${dias} dias`;
}

function host(url) {
  try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return url; }
}

// GTIN (EAN-8, UPC-A, EAN-13, GTIN-14): o último dígito confere os anteriores
function gtinValido(codigo) {
  if (!/^\d{8}$|^\d{12,14}$/.test(codigo)) return false;
  const d = codigo.split("").map(Number);
  const verificador = d.pop();
  const soma = d.reverse().reduce((t, n, i) => t + n * (i % 2 === 0 ? 3 : 1), 0);
  return (10 - (soma % 10)) % 10 === verificador;
}

async function carregarJSON(caminho) {
  const r = await fetch(caminho, { cache: "no-cache" });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

function carregarScript(src) {
  return new Promise((ok, erro) => {
    const t = document.createElement("script");
    t.src = src;
    t.onload = ok;
    t.onerror = () => erro(new Error("não carregou " + src));
    document.head.append(t);
  });
}

// ---------- câmera ----------

let pararCamera = null;

async function desligarCamera() {
  if (pararCamera) {
    const parar = pararCamera;
    pararCamera = null;
    try { await parar(); } catch { /* já parada */ }
  }
}

function aoLer(codigo, estado) {
  codigo = String(codigo).trim();
  if (!gtinValido(codigo)) {
    estado.textContent = `Li "${codigo}", mas não parece um código de produto. Tente de novo.`;
    return false;
  }
  if (navigator.vibrate) navigator.vibrate(60);
  desligarCamera();
  location.hash = `#/p/${codigo}`;
  return true;
}

async function abrirCamera(caixa, estado) {
  estado.textContent = "Abrindo a câmera…";
  const formatos = ["ean_13", "ean_8", "upc_a", "upc_e"];
  let nativo = false;
  if ("BarcodeDetector" in window) {
    try {
      const suportados = await BarcodeDetector.getSupportedFormats();
      nativo = formatos.some((f) => suportados.includes(f));
    } catch { nativo = false; }
  }
  try {
    if (nativo) await cameraNativa(caixa, estado, formatos);
    else await cameraAlternativa(caixa, estado);
    caixa.classList.add("ativa");
    estado.textContent = "Centralize o código na moldura.";
  } catch (e) {
    caixa.classList.remove("ativa");
    estado.textContent = e && e.name === "NotAllowedError"
      ? "Sem permissão para usar a câmera. Libere nas configurações do navegador ou digite o código."
      : "Não consegui abrir a câmera neste aparelho. Digite o código abaixo.";
  }
}

async function cameraNativa(caixa, estado, formatos) {
  const video = caixa.querySelector("video");
  const fluxo = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false });
  video.srcObject = fluxo;
  await video.play();
  const suportados = await BarcodeDetector.getSupportedFormats();
  const detector = new BarcodeDetector({ formats: formatos.filter((f) => suportados.includes(f)) });
  let ativo = true;
  pararCamera = async () => {
    ativo = false;
    fluxo.getTracks().forEach((t) => t.stop());
    video.srcObject = null;
  };
  const procurar = async () => {
    if (!ativo) return;
    try {
      const achados = await detector.detect(video);
      for (const a of achados) if (aoLer(a.rawValue, estado)) return;
    } catch { /* quadro ainda não pronto */ }
    setTimeout(procurar, 200);
  };
  procurar();
}

// iPhone e navegadores sem BarcodeDetector: biblioteca html5-qrcode, carregada só quando precisa
async function cameraAlternativa(caixa, estado) {
  if (!window.Html5Qrcode) await carregarScript(LEITOR_ALTERNATIVO);
  const F = window.Html5QrcodeSupportedFormats;
  const leitor = new window.Html5Qrcode("leitor-alternativo", {
    formatsToSupport: [F.EAN_13, F.EAN_8, F.UPC_A, F.UPC_E],
    verbose: false,
  });
  await leitor.start(
    { facingMode: "environment" },
    { fps: 10, qrbox: { width: 260, height: 120 } },
    (texto) => { aoLer(texto, estado); },
    () => {},
  );
  pararCamera = async () => { await leitor.stop(); leitor.clear(); };
}

// ---------- telas ----------

function telaLeitor() {
  const tela = document.getElementById("tpl-leitor").content.cloneNode(true);
  conteudo.replaceChildren(tela);
  const caixa = document.getElementById("camera");
  const estado = document.getElementById("estado-camera");
  document.getElementById("abrir-camera").addEventListener("click", () => abrirCamera(caixa, estado));
  document.getElementById("form-manual").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const codigo = document.getElementById("codigo").value.replace(/\D/g, "");
    if (!aoLer(codigo, estado)) document.getElementById("codigo").focus();
  });
  if (!navigator.mediaDevices || !window.isSecureContext) {
    estado.textContent = "A câmera precisa de conexão segura (https). Digite o código abaixo.";
  }
}

async function telaLista() {
  conteudo.replaceChildren(el("p", { class: "carregando" }, "Carregando produtos…"));
  let indice;
  try { indice = await carregarJSON("dados/indice.json"); } catch { indice = null; }
  const produtos = indice?.produtos ?? [];
  if (!produtos.length) {
    conteudo.replaceChildren(el("div", { class: "vazio" },
      el("p", {}, "Nenhum produto acompanhado ainda."),
      el("p", { class: "minusculo" }, "Os dados aparecem aqui depois da primeira coleta.")));
    return;
  }
  const lista = el("ul", { class: "lista-produtos" });
  const desenhar = (filtro = "") => {
    const f = filtro.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
    const itens = produtos.filter((p) =>
      !f || p.ean.includes(f) || (p.nome || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().includes(f));
    lista.replaceChildren(...itens.map((p) => el("li", {},
      el("a", { href: `#/p/${p.ean}` },
        el("span", {}, p.nome || p.ean),
        el("span", { class: "preco" }, p.menor_preco != null ? brl.format(p.menor_preco) : "—"),
        el("span", { class: "minusculo" }, p.ean),
        el("span", { class: "minusculo" }, p.loja ? `${p.loja}${p.lojas > 1 ? ` · ${p.lojas} lojas` : ""}` : "sem preço recente")))));
  };
  const busca = el("input", { type: "search", placeholder: "Buscar por nome ou código", "aria-label": "Buscar produto" });
  busca.addEventListener("input", () => desenhar(busca.value));
  conteudo.replaceChildren(el("section", { class: "cartao" },
    el("h1", {}, "Produtos acompanhados"),
    el("p", { class: "minusculo" }, `${produtos.length} produtos · atualizado em ${dataBR(indice.atualizado_em)}`),
    el("div", { class: "busca linha" }, busca),
    lista));
  desenhar();
}

async function telaProduto(ean) {
  conteudo.replaceChildren(el("p", { class: "carregando" }, "Buscando o produto…"));
  let p;
  try { p = await carregarJSON(`dados/${ean}.json`); } catch {
    conteudo.replaceChildren(el("div", { class: "vazio" }, "Sem conexão e sem cópia salva deste produto."));
    return;
  }
  if (!p) {
    conteudo.replaceChildren(el("section", { class: "cartao vazio" },
      el("h1", {}, "Ainda não acompanhamos este produto"),
      el("p", { class: "sutil" }, `Código ${ean}`),
      el("p", { class: "minusculo" }, "A lista de produtos cresce a cada coleta."),
      el("p", {}, el("a", { href: "#/", class: "botao" }, "Ler outro código"))));
    return;
  }
  document.title = `${p.nome || ean} · Preço com Prova`;
  conteudo.replaceChildren(
    cartaoResumo(p),
    cartaoHistorico(p),
    cartaoCausas(p),
    cartaoImpostos(),
    el("p", { class: "minusculo" }, p.aviso, ` Dados atualizados em ${dataBR(p.atualizado_em)}.`),
  );
}

function cartaoResumo(p) {
  const subtitulo = [p.marca, p.quantidade].filter(Boolean).join(" · ");
  const melhor = p.ofertas[0];
  const ofertas = el("ul", { class: "ofertas" }, p.ofertas.map((o, i) => el("li", {},
    el("span", { class: "loja" }, o.loja, " ",
      i === 0 && p.ofertas.length > 1 ? el("span", { class: "selo barato" }, "MAIS BARATO") : null, " ",
      o.em_promocao ? el("span", { class: "selo promo" }, "PROMOÇÃO") : null),
    el("span", { class: "preco" }, brl.format(o.preco)),
    el("span", { class: "meta" }, `${idade(o.data)} · `, el("a", { href: o.evidencia, target: "_blank", rel: "noopener" }, "fonte")),
    el("span", { class: "dif" }, i === 0 ? (o.em_promocao ? `era ${brl.format(o.preco_de)}` : "")
      : `+${brl.format(o.diferenca_rs)} (${pct(o.diferenca_pct)})`))));

  const economia = p.ofertas.length > 1 ? p.ofertas[p.ofertas.length - 1].preco - melhor.preco : 0;
  return el("section", { class: "cartao cabecalho-produto" },
    el("h1", {}, p.nome || "Produto sem nome cadastrado"),
    el("p", { class: "sutil" }, subtitulo, subtitulo ? " · " : "", el("span", { class: "ean" }, p.ean)),
    melhor
      ? el("div", { class: "destaque" },
          el("span", { class: "valor" }, brl.format(melhor.preco)),
          el("span", { class: "sutil" }, `em ${melhor.loja}`,
            economia > 0.004 ? ` · até ${brl.format(economia)} mais barato que a loja mais cara` : ""))
      : el("p", { class: "sutil" }, "Nenhum preço dos últimos 30 dias."),
    p.ofertas.length ? el("h2", { style: "margin-top:16px" }, "Onde está mais barato") : null,
    p.ofertas.length ? ofertas : null,
    p.ofertas_antigas.length
      ? el("p", { class: "minusculo" }, "Preços antigos, fora da comparação: ",
          p.ofertas_antigas.map((o) => `${o.loja} ${brl.format(o.preco)} em ${dataBR(o.data)}`).join("; "))
      : null);
}

// ---------- gráfico do histórico ----------

function cartaoHistorico(p) {
  const cartao = el("section", { class: "cartao" }, el("h2", {}, "Histórico do preço"));
  const pontos = p.historico.map((h) => ({ ...h, t: new Date(h.data + "T12:00:00").getTime() }));
  const datas = new Set(pontos.map((h) => h.data));
  if (datas.size < 2) {
    cartao.append(el("p", { class: "sutil" }, "Histórico ainda curto: só há preço de ",
      datas.size ? dataBR([...datas][0]) : "nenhuma data", ". Ele cresce a cada coleta."));
    return cartao;
  }

  // até 3 lojas no gráfico (as com mais observações); a cor segue a loja, em ordem alfabética
  const porLoja = new Map();
  for (const h of pontos) porLoja.set(h.loja, [...(porLoja.get(h.loja) || []), h]);
  const lojas = [...porLoja.keys()].sort((a, b) => porLoja.get(b).length - porLoja.get(a).length).slice(0, 3).sort();
  const cores = ["var(--serie-1)", "var(--serie-2)", "var(--serie-3)"];
  const series = lojas.map((loja, i) => ({
    loja, cor: cores[i], pts: porLoja.get(loja).sort((a, b) => a.t - b.t),
  }));
  const usados = series.flatMap((x) => x.pts);

  const caixa = el("div", { class: "grafico" });
  const dica = el("div", { class: "dica", hidden: true });
  const instantes = [...new Set(usados.map((h) => h.t))].sort((a, b) => a - b);
  const t0 = instantes[0], t1 = instantes[instantes.length - 1];
  let y0 = Math.min(...usados.map((h) => h.preco)), y1 = Math.max(...usados.map((h) => h.preco));
  const folga = (y1 - y0) * 0.12 || y1 * 0.1;
  y0 = Math.max(0, y0 - folga); y1 = y1 + folga;
  const mesAno = (t) => { const d = new Date(t); return `${String(d.getMonth() + 1).padStart(2, "0")}/${String(d.getFullYear()).slice(2)}`; };

  // desenha em pixels reais da tela, para o texto não encolher no celular
  const desenhar = (W) => {
    const L = 66, R = 10, T = 10, B = 26, H = 220;
    const x = (t) => L + ((t - t0) / (t1 - t0 || 1)) * (W - L - R);
    const y = (v) => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);
    const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: "img",
      "aria-label": `Histórico de preço em ${lojas.join(", ")}, de ${dataBR(usados[0].data)} a ${dataBR(new Date(t1).toISOString())}` });
    for (let i = 0; i <= 3; i++) {
      const v = y0 + ((y1 - y0) * i) / 3;
      svg.append(s("line", { class: "grade", x1: L, x2: W - R, y1: y(v), y2: y(v) }));
      svg.append(s("text", { class: "eixo", x: L - 8, y: y(v) + 4, "text-anchor": "end" }, brl.format(v)));
    }
    [[t0, "start"], [(t0 + t1) / 2, "middle"], [t1, "end"]].forEach(([t, ancora]) =>
      svg.append(s("text", { class: "eixo", x: x(t), y: H - 6, "text-anchor": ancora }, mesAno(t))));

    for (const serie of series) {
      // degraus: o preço vale até a próxima observação
      let d = `M${x(serie.pts[0].t)},${y(serie.pts[0].preco)}`;
      for (const h of serie.pts.slice(1)) d += ` H${x(h.t)} V${y(h.preco)}`;
      svg.append(s("path", { d, fill: "none", stroke: serie.cor, "stroke-width": 2, "stroke-linejoin": "round" }));
      for (const h of serie.pts) {
        svg.append(s("circle", { cx: x(h.t), cy: y(h.preco), r: 4, fill: serie.cor, stroke: "var(--superficie)", "stroke-width": 2 }));
      }
    }

    const mira = s("line", { class: "mira-x", y1: T, y2: H - B, visibility: "hidden" });
    const area = s("rect", { x: L, y: 0, width: W - L - R, height: H, fill: "transparent" });
    svg.append(mira, area);

    const mostrar = (ev) => {
      const px = ev.clientX - svg.getBoundingClientRect().left;
      const t = instantes.reduce((m, c) => (Math.abs(x(c) - px) < Math.abs(x(m) - px) ? c : m), instantes[0]);
      mira.setAttribute("x1", x(t)); mira.setAttribute("x2", x(t)); mira.setAttribute("visibility", "visible");
      const linhas = series.map((serie) => {
        const vigente = serie.pts.filter((h) => h.t <= t).pop();
        return vigente ? el("div", { class: "item" }, el("span", { class: "amostra", style: `background:${serie.cor}` }),
          el("strong", {}, brl.format(vigente.preco)), ` ${serie.loja}`) : null;
      }).filter(Boolean);
      dica.replaceChildren(el("div", { class: "data" }, dataBR(new Date(t).toISOString())), ...linhas);
      dica.hidden = false;
      dica.style.left = `${Math.min(Math.max(x(t) - 75, 0), W - 160)}px`;
      dica.style.top = "4px";
    };
    area.addEventListener("pointermove", mostrar);
    area.addEventListener("pointerdown", mostrar);
    area.addEventListener("pointerleave", () => { dica.hidden = true; mira.setAttribute("visibility", "hidden"); });
    caixa.replaceChildren(svg, dica);
  };
  let larguraAtual = 0;
  new ResizeObserver(([e]) => {
    const largura = Math.floor(e.contentRect.width);
    if (largura > 0 && largura !== larguraAtual) { larguraAtual = largura; desenhar(largura); }
  }).observe(caixa);

  if (series.length > 1) {
    cartao.append(el("ul", { class: "legenda" }, series.map((serie) =>
      el("li", {}, el("span", { class: "amostra", style: `background:${serie.cor}` }), serie.loja))));
  } else {
    cartao.append(el("p", { class: "minusculo" }, series[0].loja));
  }
  cartao.append(caixa);
  if (porLoja.size > series.length) {
    cartao.append(el("p", { class: "minusculo" }, `Mais ${porLoja.size - series.length} loja(s) na tabela abaixo.`));
  }

  const linhas = [...p.historico].reverse().map((h) => el("tr", {},
    el("td", {}, dataBR(h.data)), el("td", {}, h.loja), el("td", { class: "num" }, brl.format(h.preco)),
    el("td", {}, el("a", { href: h.evidencia, target: "_blank", rel: "noopener" }, host(h.evidencia)))));
  cartao.append(el("details", { class: "tabela" }, el("summary", {}, `Ver todos os ${p.historico.length} preços e fontes`),
    el("table", {}, el("thead", {}, el("tr", {}, el("th", {}, "Data"), el("th", {}, "Loja"), el("th", { class: "num" }, "Preço"), el("th", {}, "Fonte"))),
      el("tbody", {}, linhas))));
  return cartao;
}

// ---------- causas ----------

function cartaoCausas(p) {
  const cartao = el("section", { class: "cartao" }, el("h2", {}, "Por que o preço mudou"));
  if (!p.mudancas.length) {
    cartao.append(el("p", { class: "sutil" }, "Nenhuma mudança de preço registrada ainda."));
    return cartao;
  }
  cartao.append(el("p", { class: "niveis-explicados" },
    el("span", { class: "nivel comprovado" }, "COMPROVADO"), "fato documentado com efeito calculável. ",
    "Os outros níveis mostram o contexto, mas não provam a causa."));
  for (const m of p.mudancas.slice(0, 6)) {
    const evid = m.evidencias.map((e) => {
      const fontes = e.fontes.slice(0, 2);
      const mesmoSite = fontes.length === 2 && host(fontes[0]) === host(fontes[1]);
      return el("li", {},
        el("span", { class: `nivel ${NIVEIS[e.nivel] || "associado"}` }, e.nivel), e.descricao,
        ...fontes.map((f, i) => [" ", el("a", { href: f.startsWith("http") ? f : null, target: "_blank", rel: "noopener" },
          mesmoSite ? ["fonte (antes)", "fonte (depois)"][i] : host(f))]));
    });
    cartao.append(el("div", { class: "mudanca" },
      el("div", { class: "titulo" },
        el("span", {}, `${m.loja}: ${brl.format(m.preco_anterior)} → ${brl.format(m.preco_novo)}`),
        el("span", { class: `var ${m.variacao_pct > 0 ? "sobe" : "desce"}` }, pct(m.variacao_pct))),
      el("div", { class: "minusculo" }, `${dataBR(m.data_anterior)} a ${dataBR(m.data_nova)}`),
      evid.length ? el("ul", { class: "evidencias" }, evid)
        : el("p", { class: "minusculo" }, "Nenhuma evidência encontrada para este período."),
      m.comprovado_pct
        ? el("p", { class: "resumo-prova" }, `Imposto comprovado explica ${pct(m.comprovado_pct)}. `,
            `Sem causa comprovada: ${pct(m.nao_explicado_pct)}.`)
        : null));
  }
  if (p.mudancas.length > 6) cartao.append(el("p", { class: "minusculo" }, `E mais ${p.mudancas.length - 6} mudança(s) anteriores.`));
  return cartao;
}

function cartaoImpostos() {
  return el("section", { class: "cartao" }, el("h2", {}, "Impostos no preço"),
    el("p", { class: "sutil" }, "Em construção: o cálculo do imposto embutido, a partir da lei, ainda não está disponível."));
}

// ---------- rotas ----------

async function rotear() {
  await desligarCamera();
  const hash = location.hash || "#/";
  const produto = hash.match(/^#\/p\/(\d{8,14})$/);
  document.querySelectorAll(".topo nav a").forEach((a) =>
    a.classList.toggle("ativo", (a.dataset.rota === "lista" && hash === "#/lista") || (a.dataset.rota === "leitor" && hash === "#/")));
  document.title = "Preço com Prova";
  if (produto) await telaProduto(produto[1]);
  else if (hash === "#/lista") await telaLista();
  else telaLeitor();
  conteudo.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}

window.addEventListener("hashchange", rotear);
rotear();

if ("serviceWorker" in navigator && location.protocol !== "file:") {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}
