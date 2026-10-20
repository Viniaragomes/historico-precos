# Conferência das leis de impostos (DF)

_Gerado a partir de `site/impostos.json` (revisado em 2026-10-20). Não edite este arquivo: rode `python -m historico_precos conferencia-impostos` de novo depois de mudar a tabela._

## Como conferir

1. Para cada categoria abaixo, abra o **texto oficial** (Planalto, SINJ-DF ou Diário Oficial), nunca um resumo de blog.
2. Responda às três perguntas e anote o **link do artigo** que comprova cada resposta.
3. Se a resposta for diferente da tabela, corrija `icms`, `pis_cofins` ou `reforma` da categoria em `site/impostos.json`.
4. Preencha na categoria:

```json
"conferencia": {"conferido_em": "AAAA-MM-DD", "por": "Nome de quem conferiu",
                "links": ["link do artigo do ICMS", "link do PIS/Cofins", "link da Reforma"]}
```

5. Apague o campo `"pendente"` (ou deixe `null`). O app passa a mostrar **LEI CONFERIDA** com a data.
6. Rode `node --test tests/impostos.test.mjs`: o teste recusa categoria conferida sem os três links.

## Regras gerais (valem para todas as categorias)

- [ ] Alíquota geral do ICMS no DF é 20% desde 22/01/2024 (Lei 7.326/2023). Confirmar a data no DODF.
- [ ] PIS/Cofins não cumulativo: 1,65% + 7,6% (Leis 10.637/2002 e 10.833/2003).
- [ ] O ICMS não entra na base do PIS/Cofins (STF, RE 574.706, Tema 69): conferir a modulação de efeitos.
- [ ] Alíquota de referência da Reforma: trocar 26,5% pelo valor oficial quando o Senado publicar a resolução.

## Onde conferir

**ICMS (DF)**
- [Lei distrital 5.745/2016 (cesta básica com carga de 7%)](https://www.sinj.df.gov.br/sinj/)
- [RICMS-DF, Decreto 18.955/1997, Anexo I, Caderno II, item 11 (redução de base de cálculo)](https://www.sinj.df.gov.br/sinj/)
- [Lei distrital 7.326/2023 (alíquota geral de 20%)](https://www.sinj.df.gov.br/sinj/)

**PIS/Cofins**
- [Lei 10.925/2004, art. 1º (incisos de alíquota zero)](https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2004/lei/l10.925.htm)
- [Lei 12.839/2013 (cesta básica: carnes, café, açúcar, óleos, higiene)](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2013/lei/l12839.htm)
- [Tabela TIPI, para achar o NCM do produto](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/legislacao/documentos-e-arquivos/tipi.pdf)

**Reforma Tributária**
- [LC 214/2025, Anexo I (cesta básica nacional, alíquota zero)](https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp214.htm)
- [LC 214/2025, Anexos com redução de 60% (alimentos e higiene)](https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp214.htm)

## Categorias

### Leite condensado (⬜ não conferida)

Palavras que identificam: leite condensado

- [ ] **ICMS**, hoje `modal`: O produto NÃO tem redução no RICMS-DF e paga a alíquota geral de 20%? (procure o NCM no Caderno II do Anexo I)
- [ ] **PIS/Cofins**, hoje `geral`: O produto NÃO tem alíquota zero de PIS/Cofins e paga 1,65% + 7,6% no regime não cumulativo?
- [ ] **Reforma**, hoje `cheia`: O produto não aparece em nenhum anexo com redução da LC 214/2025?
- ⚠️ Pendência registrada: ICMS, PIS/Cofins e enquadramento na Reforma não confirmados para este item.

### Arroz (⬜ não conferida)

Palavras que identificam: arroz

- [ ] **ICMS**, hoje `cesta`: O produto está na lista da Lei 5.745/2016 / RICMS-DF com carga efetiva de 7%? Qual o percentual de redução da base hoje?
- [ ] **PIS/Cofins**, hoje `zero_10925`: Qual inciso do art. 1º da Lei 10.925/2004 zera PIS/Cofins para este produto? Com qual NCM?
- [ ] **Reforma**, hoje `zero`: O produto (pelo NCM) está no Anexo I da LC 214/2025, com alíquota zero de IBS e CBS?
- ⚠️ Pendência registrada: PIS/Cofins zero para arroz não confirmado no texto da Lei 10.925/2004.

### Feijão (⬜ não conferida)

Palavras que identificam: feijao

- [ ] **ICMS**, hoje `cesta`: O produto está na lista da Lei 5.745/2016 / RICMS-DF com carga efetiva de 7%? Qual o percentual de redução da base hoje?
- [ ] **PIS/Cofins**, hoje `zero_10925`: Qual inciso do art. 1º da Lei 10.925/2004 zera PIS/Cofins para este produto? Com qual NCM?
- [ ] **Reforma**, hoje `zero`: O produto (pelo NCM) está no Anexo I da LC 214/2025, com alíquota zero de IBS e CBS?
- ⚠️ Pendência registrada: Inciso da Lei 10.925/2004 para feijão não confirmado.

### Macarrão (⬜ não conferida)

Palavras que identificam: macarrao, espaguete, massa de semola, massa com ovos

- [ ] **ICMS**, hoje `cesta`: O produto está na lista da Lei 5.745/2016 / RICMS-DF com carga efetiva de 7%? Qual o percentual de redução da base hoje?
- [ ] **PIS/Cofins**, hoje `geral`: O produto NÃO tem alíquota zero de PIS/Cofins e paga 1,65% + 7,6% no regime não cumulativo?
- [ ] **Reforma**, hoje `zero`: O produto (pelo NCM) está no Anexo I da LC 214/2025, com alíquota zero de IBS e CBS?
- ⚠️ Pendência registrada: A redução do ICMS cita o 'macarrão espaguete comum'; outros formatos podem ter carga diferente.

### Óleo de soja (⬜ não conferida)

Palavras que identificam: oleo de soja

- [ ] **ICMS**, hoje `cesta`: O produto está na lista da Lei 5.745/2016 / RICMS-DF com carga efetiva de 7%? Qual o percentual de redução da base hoje?
- [ ] **PIS/Cofins**, hoje `zero_12839`: A Lei 12.839/2013 zera PIS/Cofins para este produto? Com qual NCM?
- [ ] **Reforma**, hoje `reduzida_60`: Em qual anexo da LC 214/2025 está a redução de 60% para este produto? Ele não está no Anexo I?
- ⚠️ Pendência registrada: Enquadramento na Reforma (redução de 60%) vem de fonte secundária.

### Farinha de trigo (⬜ não conferida)

Palavras que identificam: farinha de trigo

- [ ] **ICMS**, hoje `cesta`: O produto está na lista da Lei 5.745/2016 / RICMS-DF com carga efetiva de 7%? Qual o percentual de redução da base hoje?
- [ ] **PIS/Cofins**, hoje `zero_10925`: Qual inciso do art. 1º da Lei 10.925/2004 zera PIS/Cofins para este produto? Com qual NCM?
- [ ] **Reforma**, hoje `zero`: O produto (pelo NCM) está no Anexo I da LC 214/2025, com alíquota zero de IBS e CBS?

### Farinha de mandioca (⬜ não conferida)

Palavras que identificam: farinha de mandioca

- [ ] **ICMS**, hoje `cesta`: O produto está na lista da Lei 5.745/2016 / RICMS-DF com carga efetiva de 7%? Qual o percentual de redução da base hoje?
- [ ] **PIS/Cofins**, hoje `zero_10925`: Qual inciso do art. 1º da Lei 10.925/2004 zera PIS/Cofins para este produto? Com qual NCM?
- [ ] **Reforma**, hoje `zero`: O produto (pelo NCM) está no Anexo I da LC 214/2025, com alíquota zero de IBS e CBS?
- ⚠️ Pendência registrada: PIS/Cofins zero para farinha de mandioca não confirmado.

### Açúcar (⬜ não conferida)

Palavras que identificam: acucar

- [ ] **ICMS**, hoje `cesta`: O produto está na lista da Lei 5.745/2016 / RICMS-DF com carga efetiva de 7%? Qual o percentual de redução da base hoje?
- [ ] **PIS/Cofins**, hoje `zero_12839`: A Lei 12.839/2013 zera PIS/Cofins para este produto? Com qual NCM?
- [ ] **Reforma**, hoje `zero`: O produto (pelo NCM) está no Anexo I da LC 214/2025, com alíquota zero de IBS e CBS?

### Café (⬜ não conferida)

Palavras que identificam: cafe torrado, cafe moido, cafe em po, cafe soluvel, cafe em graos, cafe 

- [ ] **ICMS**, hoje `modal`: O produto NÃO tem redução no RICMS-DF e paga a alíquota geral de 20%? (procure o NCM no Caderno II do Anexo I)
- [ ] **PIS/Cofins**, hoje `zero_12839`: A Lei 12.839/2013 zera PIS/Cofins para este produto? Com qual NCM?
- [ ] **Reforma**, hoje `zero`: O produto (pelo NCM) está no Anexo I da LC 214/2025, com alíquota zero de IBS e CBS?
- ⚠️ Pendência registrada: Não confirmado se o café está na lista da cesta básica com ICMS reduzido no DF; usada a alíquota geral.

### Leite (⬜ não conferida)

Palavras que identificam: leite longa vida, leite integral, leite desnatado, leite semidesnatado, leite uht, leite em po

- [ ] **ICMS**, hoje `modal`: O produto NÃO tem redução no RICMS-DF e paga a alíquota geral de 20%? (procure o NCM no Caderno II do Anexo I)
- [ ] **PIS/Cofins**, hoje `zero_10925`: Qual inciso do art. 1º da Lei 10.925/2004 zera PIS/Cofins para este produto? Com qual NCM?
- [ ] **Reforma**, hoje `zero`: O produto (pelo NCM) está no Anexo I da LC 214/2025, com alíquota zero de IBS e CBS?
- ⚠️ Pendência registrada: ICMS do leite no DF não confirmado; usada a alíquota geral.

### Manteiga (⬜ não conferida)

Palavras que identificam: manteiga

- [ ] **ICMS**, hoje `modal`: O produto NÃO tem redução no RICMS-DF e paga a alíquota geral de 20%? (procure o NCM no Caderno II do Anexo I)
- [ ] **PIS/Cofins**, hoje `zero_12839`: A Lei 12.839/2013 zera PIS/Cofins para este produto? Com qual NCM?
- [ ] **Reforma**, hoje `zero`: O produto (pelo NCM) está no Anexo I da LC 214/2025, com alíquota zero de IBS e CBS?
- ⚠️ Pendência registrada: ICMS da manteiga no DF não confirmado; usada a alíquota geral.

### Margarina (⬜ não conferida)

Palavras que identificam: margarina

- [ ] **ICMS**, hoje `modal`: O produto NÃO tem redução no RICMS-DF e paga a alíquota geral de 20%? (procure o NCM no Caderno II do Anexo I)
- [ ] **PIS/Cofins**, hoje `zero_12839`: A Lei 12.839/2013 zera PIS/Cofins para este produto? Com qual NCM?
- [ ] **Reforma**, hoje `zero`: O produto (pelo NCM) está no Anexo I da LC 214/2025, com alíquota zero de IBS e CBS?
- ⚠️ Pendência registrada: ICMS e enquadramento na Reforma não confirmados.

### Carnes (⬜ não conferida)

Palavras que identificam: carne bovina, contrafile, alcatra, patinho, acem, frango, peito de frango, coxa de frango, carne suina, linguica

- [ ] **ICMS**, hoje `modal`: O produto NÃO tem redução no RICMS-DF e paga a alíquota geral de 20%? (procure o NCM no Caderno II do Anexo I)
- [ ] **PIS/Cofins**, hoje `zero_12839`: A Lei 12.839/2013 zera PIS/Cofins para este produto? Com qual NCM?
- [ ] **Reforma**, hoje `zero`: O produto (pelo NCM) está no Anexo I da LC 214/2025, com alíquota zero de IBS e CBS?
- ⚠️ Pendência registrada: ICMS das carnes no DF e enquadramento na Reforma (zero ou 60%) não confirmados.

### Papel higiênico (⬜ não conferida)

Palavras que identificam: papel higienico

- [ ] **ICMS**, hoje `modal`: O produto NÃO tem redução no RICMS-DF e paga a alíquota geral de 20%? (procure o NCM no Caderno II do Anexo I)
- [ ] **PIS/Cofins**, hoje `zero_12839`: A Lei 12.839/2013 zera PIS/Cofins para este produto? Com qual NCM?
- [ ] **Reforma**, hoje `reduzida_60`: Em qual anexo da LC 214/2025 está a redução de 60% para este produto? Ele não está no Anexo I?
- ⚠️ Pendência registrada: Enquadramento na Reforma (higiene pessoal com redução de 60%) não confirmado.

### Creme dental (⬜ não conferida)

Palavras que identificam: creme dental, pasta de dente, gel dental

- [ ] **ICMS**, hoje `modal`: O produto NÃO tem redução no RICMS-DF e paga a alíquota geral de 20%? (procure o NCM no Caderno II do Anexo I)
- [ ] **PIS/Cofins**, hoje `zero_12839`: A Lei 12.839/2013 zera PIS/Cofins para este produto? Com qual NCM?
- [ ] **Reforma**, hoje `reduzida_60`: Em qual anexo da LC 214/2025 está a redução de 60% para este produto? Ele não está no Anexo I?
- ⚠️ Pendência registrada: Enquadramento na Reforma (higiene pessoal com redução de 60%) não confirmado.

### Sabonete (⬜ não conferida)

Palavras que identificam: sabonete

- [ ] **ICMS**, hoje `modal`: O produto NÃO tem redução no RICMS-DF e paga a alíquota geral de 20%? (procure o NCM no Caderno II do Anexo I)
- [ ] **PIS/Cofins**, hoje `zero_12839`: A Lei 12.839/2013 zera PIS/Cofins para este produto? Com qual NCM?
- [ ] **Reforma**, hoje `reduzida_60`: Em qual anexo da LC 214/2025 está a redução de 60% para este produto? Ele não está no Anexo I?
- ⚠️ Pendência registrada: Enquadramento na Reforma (higiene pessoal com redução de 60%) não confirmado.
