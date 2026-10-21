# Ligar a comunidade online (Supabase)

Liga, para todo mundo: preços informados por quem compra, pedidos de inclusão de códigos, envio de cupom fiscal
e a busca na hora nas lojas. Plano gratuito. Uns 15 minutos.

## 1. Projeto
1. Crie uma conta em **supabase.com** e um projeto novo. Região: **South America (São Paulo)**.
2. Guarde a senha do banco num lugar seguro (não precisa me mandar).

## 2. Banco
1. Menu **SQL Editor** › *New query*.
2. Cole todo o conteúdo do arquivo `supabase/schema.sql` deste repositório e clique em **Run**.
   Deve terminar com "Success. No rows returned".

## 3. Login anônimo
**Authentication › Sign In / Providers** › ative **Allow anonymous sign-ins** e salve.

## 4. Busca na hora (função)
1. Menu **Edge Functions** › **Deploy a new function** › **Via Editor**.
2. Nome: `buscar-codigo`.
3. Apague o exemplo, cole todo o conteúdo de `supabase/functions/buscar-codigo/index.ts` e clique em **Deploy**.
4. Nos detalhes da função, desligue **Verify JWT** (ou "Enforce JWT verification") e salve.

## 5. Chaves
Em **Project Settings › API** (ou *API Keys*):
- **Project URL** e chave **anon public**: me mande as duas. São públicas por definição (vão dentro do app).
- Chave **service_role** (ou *secret*): **NÃO mande para ninguém, nem para mim.** Coloque direto no GitHub:
  repositório › **Settings › Secrets and variables › Actions › New repository secret**,
  nome `SUPABASE_SERVICE_ROLE`, valor = a chave. É ela que deixa a coleta ler os cupons enviados.

## 6. Limpeza automática (opcional, recomendado)
**Database › Extensions** › ative `pg_cron`. Depois, no SQL Editor:
```sql
select cron.schedule('limpeza-mensal', '0 4 1 * *', 'select public.limpar_dados_antigos()');
```
