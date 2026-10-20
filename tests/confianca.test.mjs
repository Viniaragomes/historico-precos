// node --test tests/confianca.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { confiancaPreco, nivelPorPontos, pesoDoVoto, precoSugerido, utilidade, chavePreco } from "../site/confianca.js";

const agora = new Date("2026-10-20T12:00:00Z").getTime();
const voto = (valor, diasAtras = 0, pontos_autor = 0, preco_informado = null) =>
  ({ valor, pontos_autor, preco_informado, criado_em: new Date(agora - diasAtras * 864e5).toISOString() });

test("sem votos, a confiança vem só da fonte e cai com a idade do preço", () => {
  const novo = confiancaPreco({ fonte: "wayback", data: "2026-10-20" }, [], agora);
  const velho = confiancaPreco({ fonte: "wayback", data: "2026-06-20" }, [], agora);
  assert.ok(novo.score > 0.65 && novo.score <= 0.7, String(novo.score));
  assert.ok(Math.abs(velho.score - 0.5) < 0.02, "preço antigo sem confirmação fica incerto");
  assert.equal(novo.rotulo, "Ainda sem confirmações");
});

test("confirmações sobem, contestações derrubam", () => {
  const ponto = { fonte: "vtex", data: "2026-10-19" };
  const confirmado = confiancaPreco(ponto, [voto(true), voto(true), voto(true), voto(true)], agora);
  const contestado = confiancaPreco(ponto, [voto(false), voto(false), voto(false), voto(false)], agora);
  assert.ok(confirmado.score > 0.8);
  assert.equal(confirmado.rotulo, "Muito confiável");
  assert.equal(confirmado.confirmacoes, 4);
  assert.ok(contestado.score < 0.4);
  assert.equal(contestado.rotulo, "Contestado");
});

test("reputação pesa e voto antigo vale menos", () => {
  assert.equal(pesoDoVoto(0), 1);
  assert.equal(pesoDoVoto(1000), 3);
  const ponto = { fonte: "vtex", data: "2026-10-19" };
  const guardiao = confiancaPreco(ponto, [voto(false, 0, 1000)], agora);
  const iniciante = confiancaPreco(ponto, [voto(false, 0, 0)], agora);
  assert.ok(guardiao.score < iniciante.score);
  const antigo = confiancaPreco(ponto, [voto(false, 21)], agora);
  assert.ok(antigo.score > iniciante.score);
});

test("estrelas de meia em meia", () => {
  const r = confiancaPreco({ fonte: "vtex", data: "2026-10-20" }, [voto(true)], agora);
  assert.equal(r.estrelas * 2, Math.round(r.estrelas * 2));
  assert.ok(r.estrelas >= 0 && r.estrelas <= 5);
});

test("níveis e progresso", () => {
  assert.equal(nivelPorPontos(0).nome, "Iniciante");
  assert.equal(nivelPorPontos(150).nome, "Fiscal de preços");
  assert.equal(nivelPorPontos(150).proximo.nome, "Especialista");
  assert.ok(Math.abs(nivelPorPontos(60).progresso - 0.5) < 1e-9);
  assert.equal(nivelPorPontos(5000).proximo, null);
});

test("preço sugerido pela mediana ignora valor absurdo", () => {
  const votos = [voto(false, 0, 0, 26.9), voto(false, 0, 0, 26.9), voto(false, 0, 0, 999), voto(true)];
  assert.deepEqual(precoSugerido(votos), { preco: 26.9, informantes: 3 });
  assert.equal(precoSugerido([voto(false, 0, 0, 10)]), null);
});

test("utilidade da explicação e chaves", () => {
  assert.deepEqual(utilidade([voto(true), voto(false), voto(true), voto(true)]), { uteis: 3, total: 4, percentual: 75 });
  assert.equal(chavePreco({ loja: "Loja B", data: "2026-10-20" }), "Loja B|2026-10-20");
});
