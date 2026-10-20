// Comunidade: confirmações de preço, avaliação de causas, evidências sugeridas, pontos e ranking.
// Modo "teste": tudo fica neste aparelho. Modo "online": Supabase com login anônimo (ver supabase/schema.sql).

import { PONTOS, LIMITE_VOTOS_POR_HORA } from "./confianca.js";

export const VERSAO_TERMOS = "2026-10-20";
const SUPABASE_JS = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.js";

const hoje = () => new Date().toISOString().slice(0, 10);

function armazenamento() {
  try { return window.localStorage; } catch { return null; }
}

// ---------- consentimento (pedido no primeiro voto, nunca ao abrir o app) ----------

export const consentimento = {
  ler() {
    try { return JSON.parse(armazenamento()?.getItem("consentimento_comunidade") || "null"); } catch { return null; }
  },
  valido() { return this.ler()?.versao === VERSAO_TERMOS; },
  dar() {
    try { armazenamento()?.setItem("consentimento_comunidade", JSON.stringify({ versao: VERSAO_TERMOS, em: new Date().toISOString() })); } catch { /* sem armazenamento */ }
  },
  retirar() {
    try { armazenamento()?.removeItem("consentimento_comunidade"); } catch { /* nada */ }
  },
};

export class ErroComunidade extends Error {}

// ---------- modo teste: só neste aparelho ----------

export class ComunidadeLocal {
  constructor(store = armazenamento()) {
    this.modo = "teste";
    this.store = store;
  }
  _ler() {
    const vazio = { perfil: { apelido: null, pontos: 0 }, votos: [], evidencias: [], reportes: [], proximoId: 1 };
    try { return { ...vazio, ...(JSON.parse(this.store?.getItem("comunidade_teste") || "null") || {}) }; }
    catch { return vazio; }
  }
  _gravar(d) { try { this.store?.setItem("comunidade_teste", JSON.stringify(d)); } catch { /* sem armazenamento */ } }

  async perfil() { return this._ler().perfil; }
  async definirApelido(apelido) {
    const d = this._ler();
    d.perfil.apelido = validarApelido(apelido);
    this._gravar(d);
    return d.perfil;
  }
  async votos(ean) {
    return this._ler().votos.filter((v) => v.ean === ean).map((v) => ({ ...v, pontos_autor: this._ler().perfil.pontos }));
  }
  async meuVoto(ean, alvo, chave) {
    return this._ler().votos.find((v) => v.ean === ean && v.alvo === alvo && v.chave === chave && v.dia === hoje()) || null;
  }
  async votar({ ean, alvo, chave, valor, preco_informado = null }) {
    const d = this._ler();
    const umaHora = Date.now() - 3600e3;
    if (d.votos.filter((v) => new Date(v.criado_em).getTime() > umaHora).length >= LIMITE_VOTOS_POR_HORA) {
      throw new ErroComunidade("Muitas contribuições em pouco tempo. Tente de novo mais tarde.");
    }
    if (d.votos.some((v) => v.ean === ean && v.alvo === alvo && v.chave === chave && v.dia === hoje())) {
      throw new ErroComunidade("Você já contribuiu com este item hoje. Obrigado!");
    }
    const voto = { ean, alvo, chave, valor, preco_informado: validarPreco(preco_informado), criado_em: new Date().toISOString(), dia: hoje() };
    d.votos.push(voto);
    const ganho = pontosDoVoto(voto);
    d.perfil.pontos += ganho;
    this._gravar(d);
    return { ganho };
  }
  async sugerirEvidencia({ ean, chave, url, descricao }) {
    const d = this._ler();
    d.evidencias.push({ id: d.proximoId++, ean, chave, url: validarUrl(url), descricao: (descricao || "").slice(0, 500), status: "pendente", nivel: null, criado_em: new Date().toISOString() });
    this._gravar(d);
    return { ganho: 0 }; // pontos só depois que a evidência for conferida
  }
  async reportar(reporte) {
    const d = this._ler();
    d.reportes.push({ id: d.proximoId++, ...validarReporte(reporte), status: "aberto", resposta: null, criado_em: new Date().toISOString() });
    this._gravar(d);
    return { ganho: 0 };
  }
  async evidenciasPublicas(ean) {
    return this._ler().evidencias.filter((e) => e.ean === ean && e.status === "aceita");
  }
  // no modo de teste, o próprio aparelho faz o papel de moderação, para experimentar o fluxo
  async souModerador() { return true; }
  async meuId() { return "modo-de-teste"; }
  async filaModeracao() {
    const d = this._ler();
    return { evidencias: d.evidencias.filter((e) => e.status === "pendente"), reportes: d.reportes.filter((r) => r.status === "aberto") };
  }
  async moderarEvidencia(id, { status, nivel = null, motivo = null }) {
    const d = this._ler();
    const e = d.evidencias.find((x) => x.id === id);
    if (!e) throw new ErroComunidade("Evidência não encontrada.");
    Object.assign(e, validarDecisao({ status, nivel, motivo }), { moderado_em: new Date().toISOString() });
    if (e.status === "aceita") d.perfil.pontos += PONTOS.evidencia;
    this._gravar(d);
  }
  async responderReporte(id, { status, resposta = null }) {
    const d = this._ler();
    const r = d.reportes.find((x) => x.id === id);
    if (!r) throw new ErroComunidade("Reporte não encontrado.");
    Object.assign(r, { status, resposta: (resposta || "").slice(0, 1000) || null });
    this._gravar(d);
  }
  async ranking() { return null; } // ranking só existe com a comunidade online
  async apagarTudo() { try { this.store?.removeItem("comunidade_teste"); } catch { /* nada */ } consentimento.retirar(); }
}

// ---------- modo online: Supabase ----------

export class ComunidadeSupabase {
  constructor({ url, chave_publica }) {
    this.modo = "online";
    this.url = url;
    this.chave = chave_publica;
    this.cliente = null;
  }
  async _cliente() {
    if (this.cliente) return this.cliente;
    if (!window.supabase) {
      await new Promise((ok, erro) => {
        const s = document.createElement("script");
        s.src = SUPABASE_JS;
        s.onload = ok;
        s.onerror = () => erro(new ErroComunidade("Não foi possível conectar à comunidade agora."));
        document.head.append(s);
      });
    }
    this.cliente = window.supabase.createClient(this.url, this.chave);
    return this.cliente;
  }
  // login anônimo: sem e-mail, sem telefone; só depois do consentimento
  async _usuario() {
    const c = await this._cliente();
    let { data: { session } } = await c.auth.getSession();
    if (!session) {
      if (!consentimento.valido()) throw new ErroComunidade("É preciso aceitar os termos para colaborar.");
      const { data, error } = await c.auth.signInAnonymously();
      if (error) throw new ErroComunidade("Não foi possível entrar na comunidade agora.");
      session = data.session;
      await c.from("perfis").insert({ id: session.user.id, versao_termos: VERSAO_TERMOS });
    }
    return session.user;
  }
  async perfil() {
    const c = await this._cliente();
    const { data: { session } } = await c.auth.getSession();
    if (!session) return { apelido: null, pontos: 0 };
    const { data } = await c.from("perfis").select("apelido, pontos").eq("id", session.user.id).maybeSingle();
    return data || { apelido: null, pontos: 0 };
  }
  async definirApelido(apelido) {
    const usuario = await this._usuario();
    const c = await this._cliente();
    const { error } = await c.from("perfis").update({ apelido: validarApelido(apelido) }).eq("id", usuario.id);
    if (error) throw new ErroComunidade("Esse apelido não pode ser usado.");
    return this.perfil();
  }
  async votos(ean) {
    const c = await this._cliente();
    const { data, error } = await c.from("resumo_votos").select("alvo, chave, valor, preco_informado, criado_em, pontos_autor").eq("ean", ean);
    if (error) return [];
    return data;
  }
  async meuVoto(ean, alvo, chave) {
    const c = await this._cliente();
    const { data: { session } } = await c.auth.getSession();
    if (!session) return null;
    const { data } = await c.from("meus_votos").select("valor, preco_informado, dia").eq("ean", ean).eq("alvo", alvo).eq("chave", chave).eq("dia", hoje()).maybeSingle();
    return data || null;
  }
  async votar({ ean, alvo, chave, valor, preco_informado = null }) {
    await this._usuario();
    const c = await this._cliente();
    const { error } = await c.from("votos").insert({ ean, alvo, chave, valor, preco_informado: validarPreco(preco_informado) });
    if (error?.code === "23505") throw new ErroComunidade("Você já contribuiu com este item hoje. Obrigado!");
    if (error?.message?.includes("limite")) throw new ErroComunidade("Muitas contribuições em pouco tempo. Tente de novo mais tarde.");
    if (error) throw new ErroComunidade("Não foi possível registrar agora.");
    return { ganho: pontosDoVoto({ alvo, valor, preco_informado }) };
  }
  async sugerirEvidencia({ ean, chave, url, descricao }) {
    await this._usuario();
    const c = await this._cliente();
    const { error } = await c.from("evidencias_sugeridas").insert({ ean, chave, url: validarUrl(url), descricao: (descricao || "").slice(0, 500) });
    if (error) throw new ErroComunidade("Não foi possível enviar agora.");
    return { ganho: 0 };
  }
  async ranking() {
    const c = await this._cliente();
    const { data } = await c.from("ranking").select("apelido, pontos");
    return data || [];
  }
  // reportar não exige conta: vale também para lojas e fabricantes
  async reportar(reporte) {
    const c = await this._cliente();
    const { error } = await c.from("reportes").insert(validarReporte(reporte));
    if (error) throw new ErroComunidade("Não foi possível enviar agora. Tente mais tarde.");
    return { ganho: 0 };
  }
  async evidenciasPublicas(ean) {
    const c = await this._cliente();
    const { data } = await c.from("evidencias_publicas").select("chave, url, descricao, nivel, moderado_em").eq("ean", ean);
    return data || [];
  }
  async meuId() {
    const c = await this._cliente();
    const { data: { session } } = await c.auth.getSession();
    return session?.user.id || null;
  }
  async souModerador() {
    const c = await this._cliente();
    if (!(await this.meuId())) return false;
    const { data } = await c.rpc("eh_moderador");
    return data === true;
  }
  async filaModeracao() {
    const c = await this._cliente();
    const [ev, rep] = await Promise.all([
      c.from("evidencias_sugeridas").select("id, ean, chave, url, descricao, criado_em").eq("status", "pendente").order("criado_em"),
      c.from("reportes").select("id, ean, tipo, descricao, link, contato, criado_em").eq("status", "aberto").order("criado_em"),
    ]);
    return { evidencias: ev.data || [], reportes: rep.data || [] };
  }
  async moderarEvidencia(id, decisao) {
    const c = await this._cliente();
    const { error } = await c.from("evidencias_sugeridas")
      .update({ ...validarDecisao(decisao), moderado_em: new Date().toISOString() }).eq("id", id);
    if (error) throw new ErroComunidade("Não foi possível salvar a decisão.");
  }
  async responderReporte(id, { status, resposta = null }) {
    const c = await this._cliente();
    const { error } = await c.from("reportes").update({ status, resposta: (resposta || "").slice(0, 1000) || null }).eq("id", id);
    if (error) throw new ErroComunidade("Não foi possível salvar a resposta.");
  }
  // apaga perfil, votos e evidências (em cascata no banco) e encerra a sessão
  async apagarTudo() {
    const c = await this._cliente();
    const { data: { session } } = await c.auth.getSession();
    if (session) {
      await c.rpc("apagar_minha_conta");
      await c.auth.signOut();
    }
    consentimento.retirar();
  }
}

// ---------- regras comuns ----------

export function pontosDoVoto({ alvo, valor, preco_informado }) {
  if (alvo === "causa") return PONTOS.avaliar_causa;
  return !valor && preco_informado ? PONTOS.corrigir : PONTOS.confirmar;
}

export function validarApelido(apelido) {
  const limpo = (apelido || "").trim().replace(/\s+/g, " ");
  if (!limpo) return null;
  if (limpo.length < 2 || limpo.length > 24 || !/^[\p{L}\p{N} ._-]+$/u.test(limpo)) {
    throw new ErroComunidade("Use de 2 a 24 letras, números, espaço, ponto, traço ou sublinhado.");
  }
  return limpo;
}

export function validarPreco(preco) {
  if (preco == null || preco === "") return null;
  const n = Number(preco);
  if (!(n > 0 && n < 100000)) throw new ErroComunidade("Informe um preço válido.");
  return Math.round(n * 100) / 100;
}

export function validarUrl(url) {
  try {
    const u = new URL(url);
    if (u.protocol === "https:" || u.protocol === "http:") return u.toString();
  } catch { /* inválida */ }
  throw new ErroComunidade("Informe um link completo, começando com https://");
}

export const TIPOS_REPORTE = {
  preco: "O preço está errado",
  produto: "O produto não é este",
  foto: "A foto ou o nome estão errados",
  causa: "Uma explicação de causa está errada",
  imposto: "O cálculo de imposto está errado",
  contestacao_loja: "Sou da loja ou do fabricante e quero contestar",
  outro: "Outro problema",
};

export function validarReporte({ ean = null, tipo, descricao, link = null, contato = null }) {
  if (!TIPOS_REPORTE[tipo]) throw new ErroComunidade("Escolha o tipo de problema.");
  const texto = (descricao || "").trim();
  if (texto.length < 5) throw new ErroComunidade("Conte em poucas palavras o que está errado.");
  return {
    ean: ean && /^\d{8,14}$/.test(ean) ? ean : null,
    tipo,
    descricao: texto.slice(0, 1000),
    link: link ? validarUrl(link) : null,
    contato: (contato || "").trim().slice(0, 200) || null,
  };
}

export function validarDecisao({ status, nivel = null, motivo = null }) {
  if (!["aceita", "recusada"].includes(status)) throw new ErroComunidade("Decisão inválida.");
  // a comunidade nunca gera COMPROVADO: isso exige fato documentado com efeito calculável
  if (status === "aceita" && !["DECLARADO", "ASSOCIADO"].includes(nivel)) throw new ErroComunidade("Escolha o nível: declarado ou associado.");
  return { status, nivel: status === "aceita" ? nivel : null, motivo: (motivo || "").slice(0, 300) || null };
}

export function criarComunidade(config) {
  const c = config?.comunidade;
  if (c?.provedor === "supabase" && c.url && c.chave_publica) return new ComunidadeSupabase(c);
  return new ComunidadeLocal();
}
