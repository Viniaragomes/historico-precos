# Verificação direta das fontes candidatas (GitHub Actions, 2026-11-08)

Executado por ferramentas/diagnostico_fontes_estudo.py a partir de um servidor do GitHub (rede livre), com robô identificado e leitura só pública. Lê o robots.txt de cada site (urllib.robotparser), a página indicada, conta preços 'R$ x,xx' no HTML, procura gtin/ean e PDFs. ATENÇÃO: a coluna 'plataforma' é uma detecção por palavras no HTML e tem falso positivo para 'Magento' (o padrão 'mage/' casa com 'image/'): ignorar 'Magento'. HTTP 0 = falha de conexão/DNS/TLS a partir do GitHub (não quer dizer que o site não exista).

```
https://superveneza.instabuy.com.br/
   página HTTP 200 | robots: True | plataforma: ['Instabuy'] | preços R$ no HTML: 155 | gtin: False | pdfs: 0
https://supervenezacruzeiro811.instabuy.com.br/
   página HTTP 200 | robots: True | plataforma: ['Instabuy', 'Next.js'] | preços R$ no HTML: 115 | gtin: False | pdfs: 0
https://ofertas.comper.com.br/cidade/distrito-federal/
   página HTTP 403 | robots: robots HTTP 403 | plataforma: - | preços R$ no HTML: 0 | gtin: False | pdfs: 0
https://www.comper.com.br/
   página HTTP 403 | robots: robots HTTP 403 | plataforma: - | preços R$ no HTML: 0 | gtin: False | pdfs: 0
https://www.paodeacucar.com/
   página HTTP 200 | robots: True | plataforma: ['Next.js'] | preços R$ no HTML: 0 | gtin: False | pdfs: 0
https://www.taticobaratotododia.com.br/
   página HTTP 200 | robots: True | plataforma: ['WordPress'] | preços R$ no HTML: 0 | gtin: False | pdfs: 0
https://www.supermaia.com.br/
   página HTTP 0 | robots: robots HTTP 0 | plataforma: - | preços R$ no HTML: 0 | gtin: False | pdfs: 0 | erro: URLError(gaierror(-2, 'Name or service not known'))
https://www.ultraboxatacado.com.br/
   página HTTP 200 | robots: True | plataforma: ['VTEX', 'WordPress', 'Magento'] | preços R$ no HTML: 0 | gtin: False | pdfs: 0
https://www.megaboxatacado.com.br/
   página HTTP 200 | robots: True | plataforma: ['Magento'] | preços R$ no HTML: 7 | gtin: False | pdfs: 0
https://www.supermercadobistecao.com/
   página HTTP 522 | robots: True | plataforma: - | preços R$ no HTML: 0 | gtin: False | pdfs: 0
https://www.supermercadosmineirao.com.br/
   página HTTP 0 | robots: robots HTTP 0 | plataforma: - | preços R$ no HTML: 0 | gtin: False | pdfs: 0 | erro: URLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certifica
https://linktr.ee/supercei
   página HTTP 200 | robots: False | plataforma: ['Magento', 'Next.js'] | preços R$ no HTML: 0 | gtin: False | pdfs: 1
https://superdf.com.br/
   página HTTP 0 | robots: robots HTTP 0 | plataforma: - | preços R$ no HTML: 0 | gtin: False | pdfs: 0 | erro: URLError(gaierror(-3, 'Temporary failure in name resolution'))
https://superdf.com.br/feed/
   página HTTP 0 | robots: robots HTTP 0 | plataforma: - | preços R$ no HTML: 0 | gtin: False | pdfs: 0 | erro: URLError(gaierror(-3, 'Temporary failure in name resolution'))
https://encartesdf.com.br/feed/
   página HTTP 200 | robots: True | plataforma: ['osuper', 'WordPress'] | preços R$ no HTML: 0 | gtin: False | pdfs: 0
https://www.kimbino.com.br/brasilia/
   página HTTP 200 | robots: True | plataforma: ['Magento'] | preços R$ no HTML: 0 | gtin: False | pdfs: 2
https://www.shopfully.com.br/
   página HTTP 200 | robots: True | plataforma: ['Magento'] | preços R$ no HTML: 0 | gtin: False | pdfs: 0
https://www.catalogosofertas.com.br/
   página HTTP 202 | robots: robots HTTP 202 | plataforma: - | preços R$ no HTML: 0 | gtin: False | pdfs: 0
https://www.portafolhetos.com.br/
   página HTTP 200 | robots: True | plataforma: ['Magento'] | preços R$ no HTML: 0 | gtin: False | pdfs: 2
https://www.shopper.com.br/
   página HTTP 200 | robots: sem robots (permitido) | plataforma: ['Magento'] | preços R$ no HTML: 0 | gtin: False | pdfs: 0
https://www.ifood.com.br/
   página HTTP 403 | robots: True | plataforma: - | preços R$ no HTML: 0 | gtin: False | pdfs: 0
https://www.rappi.com.br/
   página HTTP 200 | robots: True | plataforma: ['Magento', 'Next.js'] | preços R$ no HTML: 0 | gtin: False | pdfs: 0
https://mercado.carrefour.com.br/
   página HTTP 200 | robots: True | plataforma: ['VTEX', 'Magento'] | preços R$ no HTML: 22 | gtin: False | pdfs: 0
https://www.ubereats.com/br/city/brasilia-df
   página HTTP 404 | robots: True | plataforma: - | preços R$ no HTML: 0 | gtin: False | pdfs: 0
https://api.sefaz.al.gov.br/sfz-economiza-alagoas-api/api/public/
   página HTTP 0 | robots: robots HTTP 0 | plataforma: - | preços R$ no HTML: 0 | gtin: False | pdfs: 0 | erro: URLError(SSLCertVerificationError(1, "[SSL: CERTIFICATE_VERIFY_FAILED] certifica
https://www.procon.df.gov.br/
   página HTTP 200 | robots: False | plataforma: ['Magento'] | preços R$ no HTML: 0 | gtin: False | pdfs: 0
https://apisidra.ibge.gov.br/values/t/7060/n7/5301/v/63/p/last%201/c315/7169
   página HTTP 400 | robots: sem robots (permitido) | plataforma: - | preços R$ no HTML: 0 | gtin: False | pdfs: 0
https://www.dieese.org.br/analisecestabasica/
   página HTTP 403 | robots: True | plataforma: - | preços R$ no HTML: 0 | gtin: False | pdfs: 0
https://dados.df.gov.br/
   página HTTP 0 | robots: robots HTTP 0 | plataforma: - | preços R$ no HTML: 0 | gtin: False | pdfs: 0 | erro: URLError(TimeoutError('_ssl.c:994: The handshake operation timed out'))
https://precodahora.ba.gov.br/
   página HTTP 0 | robots: robots HTTP 0 | plataforma: - | preços R$ no HTML: 0 | gtin: False | pdfs: 0 | erro: URLError(TimeoutError('timed out'))
https://menorpreco.notaparana.pr.gov.br/
   página HTTP 200 | robots: sem robots (permitido) | plataforma: ['Magento'] | preços R$ no HTML: 0 | gtin: False | pdfs: 0
```

Leitura dos resultados (pelo coordenador):
- Super Veneza (superveneza.instabuy.com.br e supervenezacruzeiro811.instabuy.com.br): HTTP 200, robots permite, 155 e 115 preços visíveis no HTML, plataforma Instabuy (mesma do Big Box, coletor já existe no app). Sem GTIN no HTML. FONTE NOVA CONFIRMADA.
- Comper (www e ofertas.comper.com.br): 403 até no robots.txt = recusa robôs. Descartar.
- Pão de Açúcar (paodeacucar.com): 200, robots permite a home, Next.js; home sem preços no HTML (preços provavelmente carregados por API). Testar páginas de produto.
- Tatico (taticobaratotododia.com.br): 200, robots permite, WordPress, sem preços na home: procurar página de encarte e /wp-json.
- Ultrabox (ultraboxatacado.com.br): 200, robots permite, indício de VTEX: testar /api/catalog_system.
- Mega Box (megaboxatacado.com.br): 200, robots permite, 7 preços na home. Presença no DF não confirmada.
- Kimbino (/brasilia/) e Portafolhetos: 200, robots permite, PDFs de folhetos. Agregadores alternativos ao encartesdf.
- encartesdf.com.br/feed/: 200, robots permite (já em uso).
- Shopper: 200, sem robots.txt. Dark store (preço próprio, não de loja física).
- iFood: 403. Rappi e mercado.carrefour.com.br: 200 e robots permite a home (Carrefour já em uso).
- Procon-DF: robots NÃO permite a home para o nosso robô.
- SIDRA/IBGE: a URL testada deu 400 (parâmetros errados), API existe e sem robots.
- Menor Preço Paraná web (menorpreco.notaparana.pr.gov.br): 200 sem robots; só Paraná.
- supermaia.com.br não resolve; supermercadosmineirao.com.br com certificado inválido; superdf.com.br não resolveu; precodahora.ba e dados.df.gov.br sem resposta.
