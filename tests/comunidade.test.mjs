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
