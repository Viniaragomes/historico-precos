// node --test tests/comunidade.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { ComunidadeLocal, ErroComunidade, criarComunidade, validarApelido, validarPreco, validarUrl, pontosDoVoto } from "../site/comunidade.js";

function memoria() {
  const m = new Map();
  return { getItem: (k) => (m.has(k) ? m.get(k) : null), setItem: (k, v) => m.set(k, String(v)), removeItem: (k) => m.delete(k) };
}

test("sem configuração, usa o modo de teste", () => {
  assert.equal(criarComunidade({}).modo, "teste");
  assert.equal(criarComunidade({ comunidade: { provedor: "supabase", url: null } }).modo, "teste");
  assert.equal(criarComunidade({ comunidade: { provedor: "supabase", url: "https://x.supabase.co", chave_publica: "abc" } }).modo, "online");
});

test("votar dá pontos e permite um voto por item por dia", async () => {
  const c = new ComunidadeLocal(memoria());
  const base = { ean: "7896005800027", alvo: "preco", chave: "Loja B|2026-10-20" };
  assert.deepEqual(await c.votar({ ...base, valor: true }), { ganho: 1 });
  await assert.rejects(c.votar({ ...base, valor: false }), ErroComunidade);
  assert.deepEqual(await c.votar({ ...base, chave: "Loja A|2026-10-18", valor: false, preco_informado: "26.9" }), { ganho: 3 });
  assert.equal((await c.perfil()).pontos, 4);
  const votos = await c.votos("7896005800027");
  assert.equal(votos.length, 2);
  assert.equal(votos[1].preco_informado, 26.9);
});

test("evidência não dá ponto antes da conferência", async () => {
  const c = new ComunidadeLocal(memoria());
  assert.deepEqual(await c.sugerirEvidencia({ ean: "7896005800027", chave: "k", url: "https://g1.globo.com/x" }), { ganho: 0 });
  await assert.rejects(c.sugerirEvidencia({ ean: "1", chave: "k", url: "javascript:alert(1)" }), ErroComunidade);
});

test("apagar tudo zera perfil e votos", async () => {
  const c = new ComunidadeLocal(memoria());
  await c.votar({ ean: "1", alvo: "causa", chave: "k", valor: true });
  await c.apagarTudo();
  assert.equal((await c.perfil()).pontos, 0);
  assert.equal((await c.votos("1")).length, 0);
});

test("validações", () => {
  assert.equal(validarApelido("  Maria  do Guará "), "Maria do Guará");
  assert.equal(validarApelido(""), null);
  assert.throws(() => validarApelido("<script>"), ErroComunidade);
  assert.throws(() => validarApelido("x"), ErroComunidade);
  assert.equal(validarPreco("24.999"), 25);
  assert.throws(() => validarPreco(-1), ErroComunidade);
  assert.equal(validarUrl("https://exemplo.com/a"), "https://exemplo.com/a");
  assert.equal(pontosDoVoto({ alvo: "preco", valor: true }), 1);
  assert.equal(pontosDoVoto({ alvo: "causa", valor: false }), 1);
});

test("reportar não exige conta e valida o conteúdo", async () => {
  const { validarReporte } = await import("../site/comunidade.js");
  const c = new ComunidadeLocal(memoria());
  await c.reportar({ ean: "7896005800027", tipo: "preco", descricao: "Na loja está R$ 23,90" });
  await assert.rejects(c.reportar({ tipo: "preco", descricao: "x" }), ErroComunidade);
  await assert.rejects(c.reportar({ tipo: "inexistente", descricao: "texto qualquer" }), ErroComunidade);
  assert.equal(validarReporte({ ean: "abc", tipo: "outro", descricao: "texto ok" }).ean, null);
  const fila = await c.filaModeracao();
  assert.equal(fila.reportes.length, 1);
  await c.responderReporte(fila.reportes[0].id, { status: "resolvido", resposta: "Corrigido" });
  assert.equal((await c.filaModeracao()).reportes.length, 0);
});

test("moderação: evidência aceita vira pública com nível dado, nunca COMPROVADO", async () => {
  const c = new ComunidadeLocal(memoria());
  await c.sugerirEvidencia({ ean: "1", chave: "Loja|a|b", url: "https://noticia.exemplo/x", descricao: "Seca elevou o preço" });
  await c.sugerirEvidencia({ ean: "1", chave: "Loja|a|b", url: "https://spam.exemplo" });
  const [boa, ruim] = (await c.filaModeracao()).evidencias;
  await assert.rejects(c.moderarEvidencia(boa.id, { status: "aceita", nivel: "COMPROVADO" }), ErroComunidade);
  await c.moderarEvidencia(boa.id, { status: "aceita", nivel: "DECLARADO" });
  await c.moderarEvidencia(ruim.id, { status: "recusada", motivo: "spam" });
  const publicas = await c.evidenciasPublicas("1");
  assert.equal(publicas.length, 1);
  assert.equal(publicas[0].nivel, "DECLARADO");
  assert.equal((await c.perfil()).pontos, 5); // evidência aceita vale 5
});

test("preço informado: mediana por mercado, nome sem diferença de maiúsculas, um por dia", async () => {
  const { ComunidadeLocal, resumirPrecos } = await import("../site/comunidade.js");
  const memoria = new Map();
  const store = { getItem: (k) => memoria.get(k) ?? null, setItem: (k, v) => memoria.set(k, v), removeItem: (k) => memoria.delete(k) };
  const c = new ComunidadeLocal(store);
  const r = await c.informarPreco({ ean: "7891000100103", mercado: "  Big   Box ", preco: "6.49" });
  assert.equal(r.ganho, 3);
  await assert.rejects(c.informarPreco({ ean: "7891000100103", mercado: "big box", preco: 6.5 }), /já informou/);
  await assert.rejects(c.informarPreco({ ean: "7891000100103", mercado: "x", preco: 6.5 }), /mercado/);
  await assert.rejects(c.informarPreco({ ean: "7891000100103", mercado: "Dona", preco: -1 }), /preço válido/);
  const lista = await c.precosInformados("7891000100103");
  assert.deepEqual(lista.map((x) => [x.mercado, x.preco_mediano, x.pessoas]), [["Big Box", 6.49, 1]]);

  const resumo = resumirPrecos([
    { mercado: "Dona", preco: 7, dia: "2026-10-20" }, { mercado: "dona", preco: 9, dia: "2026-10-21" },
    { mercado: "Dona", preco: 8, dia: "2026-10-21" }, { mercado: "Tatico", preco: 6, dia: "2026-10-21" },
    { mercado: "Velho", preco: 1, dia: "2026-09-01" },
  ], "2026-10-21");
  assert.deepEqual(resumo.map((x) => [x.mercado, x.preco_mediano, x.pessoas, x.ultimo_dia]),
    [["Tatico", 6, 1, "2026-10-21"], ["Dona", 8, 3, "2026-10-21"]]);
});

test("pedido de código no modo de teste não finge que registrou", async () => {
  const { ComunidadeLocal } = await import("../site/comunidade.js");
  assert.deepEqual(await new ComunidadeLocal(memoria()).pedirCodigo("7898955519028"), { registrado: false });
});
