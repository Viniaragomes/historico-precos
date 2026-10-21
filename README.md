# Agente de histórico de preços

Recebe um código de barras (EAN), varre fontes públicas da internet e monta o histórico de preço do produto. **Cada preço é guardado com o link de onde veio**, para qualquer pessoa conferir.

Não precisa de chave de API nem de instalar nada além do Python 3.10 ou mais novo.

## Fontes

| Fonte | O que traz | Prova guardada |
|---|---|---|
| **Wayback Machine** (Internet Archive) | Preços **antigos**, a partir de cópias arquivadas das páginas do produto | Link da cópia, ex.: `web.archive.org/web/20230315.../...` |
| **Lojas VTEX** (catálogo público em JSON) | Preço **de hoje**, preço "de" riscado e o link da página do produto | URL da consulta |
| **Open Prices** (Open Food Facts) | Preços enviados por pessoas, com data e local | Link do registro |
| **Open Food Facts** | Nome, marca e tamanho do produto | — |

O agente também pode receber **páginas que você já conhece** (`--url`), de qualquer loja ou site de ofertas. Ele procura as cópias antigas delas no Wayback e lê o preço.

## Como usar

```bash
cd historico-precos

# 1. Ver quais lojas do lojas.json respondem (rode uma vez)
python -m historico_precos detectar-lojas

# 2. Buscar o histórico de um produto
python -m historico_precos buscar 7891000100103

# Com páginas extras e exportando para JSON
python -m historico_precos buscar 7891000100103 \
  --url "Loja X=https://www.lojax.com.br/produto-tal/p" \
  --json historico.json

# 3. Ver o que já foi coletado, sem acessar a internet
python -m historico_precos historico 7891000100103

# 4. Onde está mais barato agora (--atualizar consulta as lojas antes)
python -m historico_precos comparar 7891000100103 --atualizar

# 5. Por que o preço mudou, separando o que é comprovado do que não é
python -m historico_precos causas 7891000100103 --uf DF
```

## Causas: níveis de prova

| Nível | Significa | Fonte |
|---|---|---|
| **COMPROVADO** | Fato documentado com efeito calculável | Lei de imposto conferida (`eventos_tributarios.json` com `"verificado": true`); embalagem que encolheu, vista no nome do produto nas duas datas |
| **A CONFIRMAR** | Mudança de imposto cuja lei ainda não foi conferida | `eventos_tributarios.json` com `"verificado": false` |
| **DECLARADO** | A imprensa atribuiu a alta a um motivo | GDELT (notícias em português, JSON público) |
| **ASSOCIADO** | Indicador que se moveu junto, sem prova de causa | Banco Central (dólar, commodities) |
| **REFERÊNCIA** | O que a categoria inteira fez na cidade | IPCA do IBGE por subitem (Brasília) |

No fim de cada mudança, o agente mostra quanto é **comprovado** e quanto ficou **sem causa comprovada**. Ele nunca chama de causa o que não está provado.

**Para um imposto virar COMPROVADO:** use o monitor de leis abaixo, ou confira a lei você mesmo e edite `eventos_tributarios.json`.

## Monitor de leis tributárias

Varre o **Diário Oficial da União** (leis federais, Reforma Tributária, convênios do Confaz), o **Querido Diário** (diários oficiais abertos) e páginas de legislação configuradas em `monitor_leis.json`. Ele extrai tributo, alíquota antiga e nova, vigência e produtos citados, e cria **candidatos** com o link oficial.

```bash
# 1. Procurar normas publicadas no período
python -m historico_precos leis monitorar --desde 2023-01-01

# 2. Ver os candidatos e os detalhes de um deles (trecho, motivos, percentuais)
python -m historico_precos leis pendentes
python -m historico_precos leis ver <id>

# 3. Depois de ABRIR e LER a norma oficial, aprovar (ou descartar)
python -m historico_precos leis aprovar <id> --li-a-norma --categorias "*"
python -m historico_precos leis aprovar <id> --li-a-norma --evento-id df-icms-modal-2024
python -m historico_precos leis descartar <id>
```

- **O agente nunca aprova sozinho.** O `--li-a-norma` é obrigatório, e só depois da aprovação o evento vira COMPROVADO no agente de causas.
- O que o extrator não conseguiu ler (alíquota, data, produtos) precisa ser informado em `--anterior`, `--nova`, `--vigencia` e `--categorias`.
- **Convênio do Confaz não vale sozinho no DF.** Ele só autoriza os estados. Para aprovar, informe `--uf DF` e use como fonte o decreto distrital que aplicou o convênio.
- Rodar todo dia, ou toda semana, mantém a base atualizada. Candidatos já vistos não se repetem.

Os dados ficam em `precos.db` (SQLite). Rodar de novo **acumula** dados sem duplicar, então agendar uma execução diária faz o histórico crescer.

## Mapa de Preços do DF

Painel público da Secretaria de Economia do DF com preços de **NF-e** (notas entre empresas, em geral) dos últimos meses. **Não é preço de prateleira**, por isso fica numa tabela separada e não entra no comparativo. Serve como referência de preço no atacado e de tendência no DF.

```bash
# 1. Descobrir como o painel funciona (salva o HTML em mapa_df_bruto/)
python -m historico_precos mapa-df descobrir

# 2. Coletar (padrão: termos_padrao do mapa_df.json e os últimos 4 meses)
python -m historico_precos mapa-df coletar --termos CAFE,ARROZ --bruto mapa_df_bruto

# 3. Ver a série mensal (mediana) e os itens
python -m historico_precos mapa-df consultar CAFE --filtro 500G --detalhe
```

- O painel mostra só os últimos meses. **Rodar uma vez por mês** faz o histórico guardado passar dessa janela.
- O agente tenta reconhecer sozinho os campos do formulário e as colunas da tabela. Se errar, preencha `campos` e `colunas` em `mapa_df.json` com os nomes que o `descobrir` mostrar.
- Se o painel for um dashboard embutido (Power BI, Qlik), o `descobrir` avisa, e a coleta por formulário não funciona.
- As descrições são digitadas por cada empresa, então use `--filtro` para separar tamanhos e marcas.

## Encartes e tabloides (preço de loja física)

O agente de encartes lê o tabloide de ofertas (imagem ou PDF) com IA de visão (`claude-opus-5-5`, saída em JSON validado por esquema) e extrai produto, preço, preço "de", condição e validade.

```bash
pip install -r requirements-encartes.txt      # precisa de ANTHROPIC_API_KEY ou `ant auth login`
python -m historico_precos encarte ler encarte.pdf --loja "Mercado X" --fonte "https://mercadox.com.br/ofertas"
python -m historico_precos encarte pendentes
python -m historico_precos encarte vincular <id> <EAN>
```

- A IA é instruída a **não incluir preço ilegível** e a **nunca inventar** código de barras.
- Preço com condição (leve 3 pague 2, cartão ou clube da loja) é guardado, mas **fica fora do comparativo**.
- Um item só vira preço de um produto quando o nome e o **tamanho** batem com segurança. O resto fica pendente para uma pessoa vincular.
- Preços de encarte entram com confiança inicial menor nas estrelas (0,55), porque a leitura por IA pode errar, e passam pelo agente de qualidade como qualquer outro preço.
- Cada leitura custa uma chamada à API. O fallback automático (`fallbacks: "default"`) está ligado: se o pedido for recusado por um classificador, a API tenta outro modelo recomendado.

## Qualidade dos dados

Antes de exportar, o agente de qualidade (`historico_precos/qualidade.py`) analisa cada produto:

| Alerta | Quando | Efeito |
|---|---|---|
| Preço absurdo | Mais de 3x acima ou abaixo da mediana do produto | **Bloqueado**, não vai para o app |
| Pico isolado | Variação de 60% ou mais que volta ao patamar anterior em até 45 dias | **Bloqueado** |
| Salto mantido | Variação de 60% ou mais que se mantém | Aviso |
| Produto trocado | Uma loja mostra tamanho diferente da maioria no mesmo período | Aviso |
| Preço "de" irreal | Preço riscado mais de 3x o preço de venda | Aviso |

Troca de embalagem nunca é tratada como erro. Para ver os alertas: `python -m historico_precos qualidade [EAN]`.

## O app (Prova Preço)

App web instalável (PWA) na pasta `site/`: o usuário aponta a câmera para o código de barras e vê onde o produto está mais barato, o gráfico do histórico e as causas de cada mudança de preço por nível de prova, com o link de cada fonte. Não precisa de servidor: o app lê os arquivos que o comando `exportar` gera.

```bash
python -m historico_precos exportar          # gera site/dados/*.json a partir do banco
python -m historico_precos servir            # abre em http://localhost:8000
```

- **Câmera:** usa o leitor nativo do navegador (Android/Chrome). No iPhone, carrega a biblioteca `html5-qrcode` só quando precisa. A câmera roda só no aparelho; nenhuma imagem é enviada.
- **Instalar no celular:** abra o endereço do app e use "Adicionar à tela inicial".
- **Publicação:** a coleta diária gera os dados e publica o app no GitHub Pages (ative em *Settings > Pages > Source: GitHub Actions*). O Pages é gratuito em repositório público.
- **Impostos no preço:** estimativa do ICMS do DF e do PIS/Cofins na venda, e de como fica com a Reforma (IBS + CBS), a partir de `site/impostos.json`. Cada regra cita a lei e cada categoria diz o que ainda falta conferir. Testes: `node --test tests/impostos.test.mjs`.
- **Produto não acompanhado:** mostra nome e foto pela base aberta Open Food Facts e calcula os impostos sobre o preço que a pessoa digitar.
- **Seus produtos:** a pessoa marca um produto e a tela inicial avisa se o preço baixou ou subiu desde a última visita (guardado só no aparelho).
- **Sobre e privacidade** (`#/sobre`): de onde vêm os dados, como lemos as causas, o que fica no aparelho e um botão para apagar tudo.
- **Ainda não tem (precisa de servidor):** consulta ao vivo de produto não acompanhado, alertas no celular e "reportar preço errado".

## Comunidade (confirmação de preços, no estilo do Waze)

Quem está na loja confirma ou corrige o preço, diz se uma explicação de causa ajudou e envia evidências. Cada preço ganha uma **confiança da comunidade** de 0 a 5 estrelas (`site/confianca.js`). Ela parte da qualidade da fonte, sobe com confirmações e cai com contestações. O voto de quem tem mais reputação pesa mais, e votos antigos perdem força. Quem colabora ganha pontos e sobe de nível, de *Iniciante* a *Guardião do preço*.

**Regras que separam opinião de prova:** votos nunca mudam o nível de prova de uma causa, e evidências enviadas são conferidas antes de aparecer.

**Compliance (LGPD):** login anônimo, sem e-mail, CPF ou localização; consentimento pedido só na primeira contribuição; o público vê só totais; botão para apagar tudo; votos apagados em 12 meses; limite de 60 contribuições por hora e um voto por item por dia; pontos sem valor econômico. A minuta dos termos e da política está em `site/legal/` e **precisa de revisão jurídica e dos campos entre colchetes preenchidos** antes de ligar para o público.

**Modos:**
- **Teste (padrão):** sem configuração, tudo fica só no aparelho, para experimentar.
- **Online (Supabase, plano gratuito):**
  1. Crie um projeto em supabase.com (região São Paulo).
  2. No *SQL Editor*, rode `supabase/schema.sql`.
  3. Em *Authentication > Sign In / Providers*, ative *Allow anonymous sign-ins*.
  4. (Opcional) Ative a extensão `pg_cron` e agende `select public.limpar_dados_antigos()` todo mês.
  5. Preencha `url` e `chave_publica` (a chave *anon*, que é pública) em `site/config.json`.

**Reportar e moderar:** qualquer pessoa, inclusive lojas e fabricantes, pode reportar um erro ou contestar uma informação sem ter conta (botão no fim de cada produto e na página Sobre). Evidências enviadas e reportes entram numa fila em `#/moderar`. Quem modera aceita uma evidência como **DECLARADO** ou **ASSOCIADO** (nunca COMPROVADO) ou a recusa, e responde os reportes. Para liberar alguém como moderador, rode no Supabase `insert into public.moderadores (id) values ('<id mostrado em #/moderar>');`. No modo de teste, o próprio aparelho modera, para experimentar o fluxo.

Testes: `node --test tests/*.test.mjs`.

## Acessibilidade e desempenho

- Auditoria automática (WCAG 2.1 AA, axe-core) de 11 telas nos temas claro e escuro: **nenhuma violação** em 20/10/2026. Para repetir: `node ferramentas/acessibilidade.mjs` (instruções no arquivo).
- Cores com contraste mínimo de 4,5:1; no tema escuro, o verde de texto (`--marca-texto`) é separado do verde de fundo.
- Títulos em ordem, nomes acessíveis em botões e barras, animações reduzidas para quem pede isso no sistema.
- Peso do app: cerca de 126 KB (sem contar os dados), sem frameworks.

## Rodando no GitHub (recomendado)

O GitHub Actions roda os agentes com internet liberada e de graça, dentro dos limites do plano.

1. **Viabilidade** (aba *Actions* > *Viabilidade* > *Run workflow*): testa se cada fonte responde, monta uma amostra de produtos **reais** (buscados por nome nas lojas e no Open Food Facts), roda todos os agentes e gera `relatorios/viabilidade-AAAA-MM-DD.md` com as métricas e uma decisão por métrica. O resumo também aparece na página da execução.
2. **Coleta diária** (automática, às 06:17 de Brasília): atualiza os preços dos produtos de `produtos.txt` (ou da amostra da viabilidade). Aos domingos também busca o Wayback; às segundas roda o monitor de leis; no dia 5 de cada mês, o Mapa de Preços do DF. O banco fica no ramo `dados`.

Para rodar só o teste das fontes no seu computador: `python -m historico_precos viabilidade --so-fontes`.

## Regras que o agente segue

- **Respeita o `robots.txt`** de cada site. Se o site proíbe o acesso, ele não acessa.
- Espera **2 segundos entre acessos ao mesmo site** (ajuste com `--intervalo`).
- Se identifica como `HistoricoPrecosBot`.
- **Não faz login nem burla bloqueios.** Por isso o Menor Preço Brasil (que exige gov.br) fica de fora.
- Guarda só preços de produtos, sem nenhum dado pessoal.

## Limitações conhecidas

- **O preço online pode ser diferente do preço da loja física**, e algumas lojas VTEX mudam o preço por região. Use o campo `sc` em `lojas.json` para escolher o canal de venda do DF, se a loja tiver um.
- **O Wayback não arquiva tudo.** Produtos populares em lojas grandes costumam ter cópias; produtos menos procurados podem não ter nenhuma.
- **Os domínios em `lojas.json` são candidatos ainda não verificados.** Rode `detectar-lojas` para confirmar.
- **Encartes e tabloides** geralmente são imagens ou PDFs e precisam de OCR ou leitura por IA. Essa é a próxima etapa.

## Testes

```bash
python -m unittest discover -s tests -v
```
