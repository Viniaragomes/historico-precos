// node --test tests/impostos.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { calcular, categoria } from "../site/impostos.js";

const tabela = JSON.parse(readFileSync(new URL("../site/impostos.json", import.meta.url)));
const perto = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} != ${b}`);

test("toda regra e toda fonte citada existem", () => {
  for (const c of tabela.categorias) {
    assert.ok(tabela.regras.icms[c.icms], `${c.id}: icms ${c.icms}`);
    assert.ok(tabela.regras.pis_cofins[c.pis_cofins], `${c.id}: pis ${c.pis_cofins}`);
    assert.ok(tabela.regras.reforma.regimes[c.reforma], `${c.id}: reforma ${c.reforma}`);
    assert.ok(c.palavras.length, `${c.id}: sem palavras`);
  }
  const usadas = JSON.stringify(tabela.regras).match(/"fonte(?:_referencia)?":"([^"]+)"/g)
    .map((m) => m.split(":")[1].replaceAll('"', ""));
  for (const f of usadas) assert.ok(tabela.fontes[f], `fonte ${f} não cadastrada`);
});

test("categoria pelo nome, com acento e ordem de prioridade", () => {
  assert.equal(categoria(tabela, "ARROZ TIPO 1 5KG").id, "arroz");
  assert.equal(categoria(tabela, "Feijão Carioca 1kg").id, "feijao");
  assert.equal(categoria(tabela, "Leite Condensado 395g").id, "leite_condensado");
  assert.equal(categoria(tabela, "Leite Integral UHT 1L").id, "leite");
  assert.equal(categoria(tabela, "Café Torrado e Moído 500g").id, "cafe");
  assert.equal(categoria(tabela, "Sabão em pó 1kg"), null);
});

test("cesta básica no DF: ICMS 7% e PIS/Cofins zero", () => {
  const r = calcular(tabela, categoria(tabela, "Açúcar refinado 1kg"), 5);
  perto(r.icms.valor, 0.35);
  perto(r.pisCofins.valor, 0);
  perto(r.percentual, 7);
  perto(r.reforma.valor, 0); // cesta básica nacional: alíquota zero
});

test("PIS/Cofins geral sem ICMS na base", () => {
  const r = calcular(tabela, categoria(tabela, "Leite condensado"), 10);
  perto(r.icms.valor, 2);
  perto(r.pisCofins.valor, (10 - 2) * 0.0925);
  perto(r.total, 2 + 0.74);
});

test("Reforma: redução de 60% e imposto por fora", () => {
  const r = calcular(tabela, categoria(tabela, "Óleo de soja 900ml"), 10);
  const a = 26.5 * 0.4;
  perto(r.reforma.aliquota, a);
  perto(r.reforma.valor, 10 * (a / 100) / (1 + a / 100));
});
