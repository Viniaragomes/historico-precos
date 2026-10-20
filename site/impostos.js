// Estimativa dos impostos na venda ao consumidor (DF), a partir da tabela legal em impostos.json.

export function normalizar(texto) {
  return ` ${(texto || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()} `;
}

// primeira categoria cuja palavra aparece no nome; a ordem da tabela resolve casos como "leite condensado" x "leite"
export function categoria(tabela, ...textos) {
  const alvo = normalizar(textos.filter(Boolean).join(" "));
  return tabela.categorias.find((c) => c.palavras.some((p) => alvo.includes(normalizar(p).trimEnd()))) || null;
}

export function calcular(tabela, cat, preco) {
  const icmsRegra = tabela.regras.icms[cat.icms];
  const pisRegra = tabela.regras.pis_cofins[cat.pis_cofins];
  const icms = preco * (icmsRegra.carga / 100);
  // o ICMS não entra na base do PIS/Cofins (STF, Tema 69)
  const pisCofins = (preco - icms) * (pisRegra.aliquota / 100);
  const total = icms + pisCofins;

  const ref = tabela.regras.reforma;
  const regime = ref.regimes[cat.reforma];
  const aliquota = ref.aliquota_referencia * (1 - regime.reducao / 100);
  // IBS e CBS são cobrados "por fora": no mesmo preço final, a parte de imposto é a/(1+a)
  const valorReforma = preco * (aliquota / 100) / (1 + aliquota / 100);

  return {
    preco,
    icms: { valor: icms, carga: icmsRegra.carga, regra: cat.icms, fonte: icmsRegra.fonte },
    pisCofins: { valor: pisCofins, aliquota: pisRegra.aliquota, regra: cat.pis_cofins, fonte: pisRegra.fonte },
    total,
    percentual: preco ? (total / preco) * 100 : 0,
    reforma: {
      ano: ref.ano_completo,
      aliquota,
      regime: cat.reforma,
      valor: valorReforma,
      percentual: preco ? (valorReforma / preco) * 100 : 0,
      fontes: [regime.fonte, ref.fonte_referencia],
    },
    fontes: [...new Set([icmsRegra.fonte, pisRegra.fonte, tabela.regras.pis_cofins.base_sem_icms.fonte, regime.fonte, ref.fonte_referencia])],
  };
}
