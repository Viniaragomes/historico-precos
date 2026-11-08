# Dados abertos e agregadores de preços de varejo alimentar: DF e modelos de outros estados

Nota de método (nov/2026): esta sessão não tinha acesso direto à rede. Por curl, todos os hosts deram "CONNECT 403": procon.df.gov.br, dados.df.gov.br, apisidra.ibge.gov.br, dieese.org.br, precodahora.ba.gov.br, menorpreco.notaparana.pr.gov.br e dados.gov.br. Pelo WebFetch, apisidra.ibge.gov.br deu ENOTFOUND. Tudo abaixo vem de resultados de busca (trechos e resumos). Os itens marcados **[não verificado]** não foram conferidos na fonte primária. Não consegui checar o robots.txt de nenhum site.

## 1. Existe algum conjunto aberto de preços de varejo por estabelecimento e por código de barras que cubra o DF?

### Takeaway
Não encontrei nenhum. Preço por loja e por GTIN só existe dentro dos apps das Sefaz, alimentados pela NFC-e. No DF, esse papel é do Menor Preço Brasil, que exige login gov.br e já foi descartado. Nenhum desses apps tem download em massa nem API sem cadastro. A única API pública documentada, a do Economiza Alagoas, cobre só Alagoas e exige token pedido por e-mail.

### Cited Findings
- **Menor Preço Brasil**: um convênio do Confaz permitiu que 21 estados e o DF incorporassem a tecnologia gaúcha. Os preços vêm de NF-e e NFC-e e são atualizados em tempo real, num raio de até 30 km. O login gov.br é obrigatório desde 2020. — [NetCPA/Confaz](https://netcpa.com.br/colunas/confaz-lanca-aplicativo-menor-preco-brasil-destinado-a-ajudar-o-cidadao-a-encontrar-os-melhores-valores-no-comercio/3258); [Governo RS](https://www.estado.rs.gov.br/menor-preco-brasil-tecnologia-do-governo-gaucho-que-coloca-economia-na-palma-da-mao-de-milhoes-de-brasileiros)
- Um guia do Olhar Digital (ago/2025) inclui o DF entre as UFs em que o Menor Preço Brasil funciona. — [Olhar Digital](https://olhardigital.com.br/2025/08/03/dicas-e-tutoriais/quer-economizar-na-farmacia-e-supermercado-conheca-o-app-menor-preco-brasil/)
- Não achei nenhum anúncio da Secretaria de Economia do DF sobre a adesão ao app. A busca no DODF só retornou contratos sem relação com o tema. — [busca vLex/DODF](https://vlex.com.br/vid/secretaria-economia-1027172078)
- Não achei nenhum conjunto de preços de alimentos ou combustíveis no dados.df.gov.br. A busca trouxe só boletins do IPEDF. Há um indício indireto de base interna: a Secretaria de Economia apura o PMPF dos combustíveis a cada 15 dias, a partir do preço médio ponderado ao consumidor final. — [Correio Braziliense 2021](https://blogs.correiobraziliense.com.br/capital-sa/2021/03/15/imposto-sobre-combustiveis-no-df-nao-sofrera-aumento/amp/)
- O projeto comunitário "Esse Era o Preço" (GitHub) afirma que os dados de NFC-e "ficam espalhados em portais estaduais e não viram uma série histórica pública". A API pública e a licença de dados do projeto ainda são planos futuros. — [GitHub uJeFFF/essaeraopreco](https://github.com/uJeFFF/essaeraopreco)
- Consulta de NFC-e por chave de acesso, como o webservice JSON da Sefaz-GO revendido pela Infosimples, é uma consulta documento a documento, sem base agregada. — [Infosimples SEFAZ/GO NFC-e](https://infosimples.com/consultas/sefaz-go-nfce-completa/)
- **Agregadores privados**: o Buscapé compara lojas virtuais e não supermercados físicos. A Precifica aparece como ferramenta B2B de precificação para varejistas, não como comparador público. Não encontrei comparador com preço por loja física de supermercado em Brasília. — [Consumidor Moderno](https://consumidormoderno.com.br/9-aplicativos-economizar-compras/); [Monitor Mercantil](https://monitormercantil.com.br/a-relevancia-da-tecnologia-na-precificacao-das-vendas-de-supermercados-online/); [Buscapé supermercado online](https://www.buscape.com.br/cupom-de-desconto/c/supermercado-online)
- Uma pesquisa da Proteste, citada pelo Correio Braziliense, apontou Brasília como a cidade de maior variação de preços entre supermercados, com o Makro (EPIA Sul) como opção mais barata. A data não está clara e a pesquisa parece antiga. — [Blog do Consumidor/Correio](https://blogs.correiobraziliense.com.br/consumidor/brasilia_apresenta_a_maior_variacao_de_precos_entre_supermercados/)
- O Metrópoles publicou "Secretaria de Justiça lança app para brasilienses compararem preços". Não consegui abrir a matéria, nem confirmar a data ou se o app tem dados por loja. — [Metrópoles](https://www.metropoles.com/brasil/economia-br/secretaria-de-justica-lanca-app-para-brasilienses-compararem-precos)

### Inferences
- Para o app, a estratégia viável sem login segue sendo a de fontes próprias: cupom NFC-e do usuário, encartes e o Mapa de Preços DF (B2B), com as fontes oficiais servindo só para validar. Na busca, não apareceu nada de novo sobre uma API pública do "Mapa de Preços DF" além do painel Qlik já conhecido.
- Mercado Livre, Zoom e afins cobrem e-commerce, sem preço de gôndola por loja do DF. Valor baixo; descartar.

### Gaps
- Robots.txt de Buscapé, Zoom, Mercado Livre e Precifica: não foi possível buscar.
- Conteúdo e data da matéria do Metrópoles sobre o app da Secretaria de Justiça do DF: vale abrir manualmente.
- Busca direta no catálogo CKAN de dados.df.gov.br (`/api/3/action/package_search?q=preço`): não foi possível rodar. Recomenda-se repetir com a rede liberada.

## 2. Quais fontes públicas servem de referência ou validação (médias, tendências)?

### Takeaway
Para tendência no DF, a melhor fonte é o IBGE (IPCA/INPC por subitem na RM de Brasília, via API SIDRA). O DIEESE publica em PDF o custo mensal da cesta de Brasília. O preço médio por produto do DIEESE é pago desde 2018. Os boletins do IPEDF repetem o IPCA do IBGE. O Procon-DF faz pesquisas pontuais por estabelecimento, sem periodicidade nem formato aberto confirmados.

### Cited Findings
**DIEESE, Pesquisa Nacional da Cesta Básica (PNCBA)**
- Os relatórios mensais saem em PDF, no padrão `dieese.org.br/analisecestabasica/AAAA/AAAAMMcestabasica.pdf`. Brasília faz parte das 17 capitais com série histórica completa. Exemplos: queda de 7,80% em fev/2026 contra fev/2025 e de 3,90% em dez/2025 contra nov/2025. — [DIEESE fev/2026](https://www.dieese.org.br/analisecestabasica/2026/202602cestabasica.pdf); [DIEESE dez/2025](https://www.dieese.org.br/analisecestabasica/2025/202512cestabasica.pdf)
- Desde abril de 2018, os preços por produto das cidades deixaram de ser públicos e exigem assinatura anual. Sindicatos filiados pedem por precos@dieese.org.br. A base traz preço médio por produto, custo da cesta e tempo de trabalho. Os dados são médias por cidade, não por loja. — [DIEESE, nota sobre o banco de dados](https://www.dieese.org.br/analisecestabasica/notaBancoDados.html)
- A Conab republica a análise mensal da PNCBA em PDF no gov.br. — [Conab mar/2026](https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/precos-agropecuarios/analise-da-pesquisa-nacional-de-precos-da-cesta-basica-de-alimentos/analise-da-pesquisa-nacional-de-precos-da-cesta-basica-de-alimentos-todas-as-capitais-marco-2026.pdf/@@download/file)
- **Licença**: não encontrei termos de uso explícitos. A restrição de 2018 indica que a base por produto não deve ser republicada.

**IBGE, IPCA/INPC (SIDRA)**
- **[não verificado: a API não abriu nesta sessão]** O IPCA tem a tabela 7060 (desde jan/2020) e o INPC a tabela 7063, com abertura por subitem (classificação c315) para a RM de Brasília (código territorial n7/5301). Exemplo de consulta: `https://apisidra.ibge.gov.br/values/t/7060/n7/5301/v/63/p/last%201/c315/7171`. Saída em JSON e sem login. Os dados são mensais e de uso livre, citando o IBGE. — [Documentação da API SIDRA](https://apisidra.ibge.gov.br/)
- O IPEDF-Codeplan publica boletins mensais de IPCA/INPC do DF em PDF, com dados do IBGE, itens de maior contribuição e cálculo por faixa de renda. — [IPEDF boletim nov/2022](https://conjunturaeconomica.ipe.df.gov.br/wp-content/uploads/2022/12/2022.12.12_Boletim_IPCA_INPC_Novembro-2022.pdf); [IPEDF ago/2022](https://ipe.df.gov.br/documents/d/ipedf/20220909_boletim_ipca_inpc_agosto-2022)
- O IPEDF também tem um estudo pontual, "Os Preços da Gasolina C no Distrito Federal". Não encontrei nenhuma publicação do IPEDF sobre a cesta básica. — [IPEDF](https://ipe.df.gov.br/documents/9915964/10220346/Os-Pre%25C3%25A7os-da-Gasolina-C-no-Distrito-Federal.pdf)

**Procon-DF**
- Em jun/2024, o Procon-DF fiscalizou 94 estabelecimentos por causa do preço do arroz, que variou mais de 100%. Foi uma ação pontual. — [Correio Braziliense](https://www.correiobraziliense.com.br/cidades-df/2024/06/6868689-populacao-assustada-com-o-preco-do-arroz-procon-df-fiscaliza.html)
- O Procon-DF publica pesquisas sazonais por estabelecimento, como a de papelarias para a volta às aulas, com variação de até 125% e lista completa no site. — [Blog do Consumidor/Correio](https://blogs.correiobraziliense.com.br/consumidor/variacao-de-precos-entre-papelarias-no-df-chega-a-125-alerta-procon-df/)
- Em 2026, a busca não achou nenhuma pesquisa periódica de supermercado ou cesta básica do Procon-DF. A única menção recente é sobre pescados, em fev/2026. — [Correio Braziliense 21/02/2026 (PDF)](https://edicao.correiobraziliense.com.br/correiobraziliense/2026/02/21/090231/pdf/A15-CID-2102-DIG.pdf)
- Para comparação, outros Procons fazem pesquisa mensal por loja. O Procon-PE pesquisa a cesta da RM do Recife, em 26 supermercados em ago/2026. O Procon Fortaleza acompanha 100 produtos em 36 supermercados. — [Diario de Pernambuco](https://www.diariodepernambuco.com.br/economia/2026/09/11723509-precos-de-produtos-da-cesta-basica-cairam-067-em-agosto-segundo-pesquisa-do-procon-pe.html); [O POVO+](https://mais.opovo.com.br/reportagens-especiais/preco-comparado-supermercados/2026/09/26/tregua-na-inflacao-nao-impede-alta-de-ate-586-em-alguns-alimentos.html)

**Conab**: o Prohort/CEASA traz preços de atacado de hortifrúti, uma fonte já conhecida. Serve só de referência para FLV, sem preço de varejo por loja.

### Inferences
Recomendações por fonte:

| Fonte | Conteúdo | Cobertura DF | Formato | Frequência | Recomendação |
|---|---|---|---|---|---|
| IBGE SIDRA (IPCA/INPC subitem) | Variação % por subitem, sem R$ | RM Brasília | API JSON aberta | Mensal | **Usar já** (tendência e deflator; testar a URL quando a rede permitir) |
| DIEESE PNCBA | Custo da cesta (13 itens); preço por item pago desde 2018 | Brasília (média da cidade) | PDF/HTML | Mensal | **Usar já** como referência do total da cesta, extraindo do PDF; não republicar a base por item |
| IPEDF boletins | Reanálise do IPCA | DF | PDF | Mensal | Descartar como dado (é redundante com o SIDRA); citar no texto |
| Procon-DF pesquisas | Preço por loja, pontual e sazonal | DF | PDF/HTML no site (não verificado) | Irregular | **Testar**: monitorar e usar como validação pontual |
| Conab Prohort | Atacado FLV | CEASA-DF | Painel/planilha | Diário/semanal | Já conhecida; referência de FLV |
| Agregadores privados | E-commerce | Não há lojas físicas do DF | HTML | — | Descartar |

### Gaps
- Periodicidade, formato e endereço exato das pesquisas de preços do Procon-DF no site oficial: não foi possível acessar o procon.df.gov.br.
- Códigos de tabela e variável do SIDRA não confirmados ao vivo.
- Termos de uso das páginas públicas do DIEESE.

## 3. O que outros estados oferecem abertamente (modelo e argumento para recurso via LAI)?

### Takeaway
Todos os estados que olhei têm consulta pública de preço por loja via NFC-e (BA, PR, RS, PE, AL, AM, ES), mas nenhum publica dump aberto de preços. O precedente mais forte para um pedido via LAI é o Economiza Alagoas: uma Sefaz oferece API REST pública de preços de NFC-e a terceiros, com token. O Preço da Hora (BA) e o Menor Preço (PR) funcionam na web e no app sem login gov.br, mas sem API documentada.

### Cited Findings
- **Economiza Alagoas (Sefaz-AL)**: a plataforma tem página de consulta de preços e uma "API pública, que possibilita a construção de outras aplicações, contribuindo com a abertura de dados". A API é REST, em `api.sefaz.al.gov.br/sfz-economiza-alagoas-api/api/public/`. O token é pedido por e-mail a api@sefaz.al.gov.br, informando CPF, responsável, nome do app e empresa ou site. Há um manual do desenvolvedor v1.0 (2023) em economizaalagoas.sefaz.al.gov.br/desenvolvedor.htm. — [SBSI 2023 (SBC)](https://sol.sbc.org.br/index.php/sbsi_estendido/article/view/24590)
- Para usar todas as funções do Economiza Alagoas, o cidadão precisa se cadastrar na Nota Fiscal Cidadã. Existe um app de terceiros, o "Alagoas Preço Baixo", que consulta a base da Sefaz. Isso mostra reuso por terceiros. — [TNH1](https://www.tnh1.com.br/noticia/nid/economize-no-carnaval-plataforma-da-sefaz-al-facilita-pesquisa-de-precos/); [App Store](https://apps.apple.com/us/app/-/id6749063261)
- **Preço da Hora Bahia (Sefaz-BA/Prodeb)**: mais de 500 mil produtos, a partir de notas eletrônicas de cerca de 240 mil estabelecimentos, com histórico de preços e combustíveis. Não achei API pública nem dados abertos. Há um módulo de importação de NF-e que foi mostrado ao Ministério da Saúde, mas é integração interna. — [Prodeb](https://www.ba.gov.br/prodeb/node/62072); [Prodeb/MS](https://www.ba.gov.br/prodeb/node/61914); [Correio 24h](https://www.correio24horas.com.br/minha-bahia/saiba-como-economizar-nas-compras-com-o-aplicativo-preco-da-hora-bahia-0826)
- **Menor Preço (Nota Paraná, Sefaz-PR/Celepar, desde 2016)**: busca por nome ou código de barras, preços atualizados quando a NFC-e é emitida, versão web em menorpreco.notaparana.pr.gov.br e listas de compras. Não encontrei API documentada. A tecnologia foi replicada no ES e em PE. — [Fazenda PR](https://www.fazenda.pr.gov.br/Noticia/Nota-Parana-agora-tem-aplicativo-para-consumidor-comparar-precos-e-economizar); [AEN-PR](https://www.parana.pr.gov.br/aen/Noticia/Dia-do-Consumidor-aplicativo-Menor-Preco-e-o-maior-aliado-do-paranaense)
- **Menor Preço Pernambuco (Sefaz-PE, parceria com o PR)**: usa NFC-e e NF-e ao consumidor final. O nome não é "Preço Certo". — [Sefaz-PE](https://www.sefaz.pe.gov.br/Noticias/Paginas/Sefaz-PE-disponibiliza-aplicativo-de-pesquisa-de-pre%C3%A7os-ao-consumidor.aspx)
- **ES**: a Sefaz-ES adotou o Menor Preço Brasil como único aplicativo. — [Sefaz-ES](https://sefaz.es.gov.br/sefaz-adota-menor-preco-brasil-como-unico-apl)
- **RS (Nota Fiscal Gaúcha / Menor Preço)**: o FAQ explica que o preço exibido é o da última venda com CPF na nota, não uma oferta. A versão de 2026 calcula o total da cesta por loja. A escala citada é de mais de 300 mil estabelecimentos. Não achei dataset aberto. — [Receita RS FAQ](https://atendimento.receita.rs.gov.br/os-precos-mostrados-sao-ofertas); [Governo RS](https://estado.rs.gov.br/com-nova-versao-aplicativo-menor-preco-aprimora-busca-por-itens-mais-baratos-no-rio-grande-do-sul)
- **AM**: a Sefaz-AM lançou o "Busca Preço Amazonas" sobre a base de NFC-e, com filtros de local, período e distância, e depois um app. — [NF Amazonense](https://nfamazonense.sefaz.am.gov.br/sefaz-lanca-sistema-busca-preco-amazonas-para-ajudar-o-consumidor-a-economizar/); [Banzeiro News](https://banzeironews.com/busca-preco-amazonas-agora-tem-aplicativo-para-celular/)
- Uma thread antiga (cerca de 6 anos) do fórum dadosabertos.social menciona a API da Sefaz-AL e lista RS, PR, PI, PE e MS como estados com ferramentas parecidas. Os links podem estar desatualizados. — [dadosabertos.social](https://dadosabertos.social/t/dados-de-vendas-de-mercadoria-sefaz/305)
- No RS, só há CSV agregado de vendas por NFC-e por classe de atividade (painel da Fecomércio-RS), sem preço por produto. — [GitHub monitor-nfce-varejo](https://github.com/pietrosalvador5-boop/monitor-nfce-varejo)
- Ceará e Sergipe: não encontrei app ou API próprios nesta pesquisa. Há um TCC da UFS sobre o tema, que não foi aberto. — [UFS TCC](https://ri.ufs.br/bitstream/riufs/15903/2/Adan_Cordeiro_Araujo.pdf)

### Inferences
- Argumentos para o recurso via LAI ao DF:
  1. A Sefaz-AL mantém uma API pública de preços de NFC-e para terceiros, o que mostra que é viável sem ferir o sigilo fiscal. Preço praticado por estabelecimento e GTIN não identifica o consumidor.
  2. BA, PR, PE, AM e RS publicam preço por loja ao público sem login gov.br. A exigência de gov.br no Menor Preço Brasil é uma escolha de desenho, não uma obrigação legal.
  3. O DF já publica preços B2B no Mapa de Preços. Pedir o equivalente B2C, mesmo que agregado por loja, produto e semana, é proporcional.
  4. O pedido pode ser só o mesmo que o app já mostra ao cidadão logado, em formato aberto, ou acesso a uma API com token, como em AL.
- Recomendação: a API do Economiza Alagoas é a única que vale **testar** como modelo técnico, para conhecer o esquema de campos e montar o pedido. Ela não serve para dados do DF. O Preço da Hora e o Menor Preço do PR servem só como modelo de produto e de argumento: **descartar** como fonte de dados.

### Gaps
- Esquema de campos, limites e licença da API do Economiza Alagoas: o manual do desenvolvedor não foi aberto.
- Se o Preço da Hora ou o Menor Preço PR têm endpoints JSON públicos usados pelo front-end: não foi investigado, por falta de rede e por cautela com os termos de uso. Não há confirmação de que o uso seria autorizado.
- Situação de CE, SE e PI.
