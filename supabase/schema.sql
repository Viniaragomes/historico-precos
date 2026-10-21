-- Comunidade do Preço com Prova (Supabase / Postgres).
-- Como usar: crie um projeto (região São Paulo), abra o SQL Editor, cole e rode este arquivo.
-- Depois: Authentication > Sign In / Providers > ative "Allow anonymous sign-ins".
--
-- Regras de privacidade aplicadas aqui, no banco:
--   * sem e-mail, telefone, CPF ou localização; o login é anônimo;
--   * ninguém lê os votos individuais: o público só vê totais (resumo_votos), sem identificação de quem votou;
--   * pontos não podem ser editados pelo usuário, só pelas regras abaixo;
--   * a própria pessoa apaga tudo (apagar_minha_conta), e votos com mais de 12 meses são removidos (limpar_dados_antigos).

-- ---------- tabelas ----------

create table public.perfis (
  id uuid primary key references auth.users (id) on delete cascade,
  apelido text unique check (apelido is null or (char_length(apelido) between 2 and 24 and apelido ~ '^[[:alnum:] ._-]+$')),
  pontos integer not null default 0,
  versao_termos text not null,
  criado_em timestamptz not null default now()
);

create table public.votos (
  id bigint generated always as identity primary key,
  usuario uuid not null default auth.uid() references public.perfis (id) on delete cascade,
  ean text not null check (ean ~ '^[0-9]{8,14}$'),
  alvo text not null check (alvo in ('preco', 'causa')),
  chave text not null check (char_length(chave) <= 200),
  valor boolean not null,
  preco_informado numeric(10, 2) check (preco_informado is null or (preco_informado > 0 and preco_informado < 100000)),
  dia date not null default current_date,
  criado_em timestamptz not null default now(),
  unique (usuario, ean, alvo, chave, dia)  -- um voto por item por dia
);
create index votos_ean on public.votos (ean);

create table public.evidencias_sugeridas (
  id bigint generated always as identity primary key,
  usuario uuid not null default auth.uid() references public.perfis (id) on delete cascade,
  ean text not null check (ean ~ '^[0-9]{8,14}$'),
  chave text not null check (char_length(chave) <= 200),
  url text not null check (url ~ '^https?://' and char_length(url) <= 1000),
  descricao text check (char_length(descricao) <= 500),
  status text not null default 'pendente' check (status in ('pendente', 'aceita', 'recusada')),
  nivel text check (nivel in ('DECLARADO', 'ASSOCIADO')),  -- definido por quem modera; nunca COMPROVADO
  motivo text check (char_length(motivo) <= 300),
  moderado_em timestamptz,
  criado_em timestamptz not null default now()
);

-- reportes de erro e contestações de lojas: não exigem conta nem aceite dos termos da comunidade
create table public.reportes (
  id bigint generated always as identity primary key,
  ean text check (ean is null or ean ~ '^[0-9]{8,14}$'),
  tipo text not null check (tipo in ('preco', 'produto', 'foto', 'causa', 'imposto', 'contestacao_loja', 'outro')),
  descricao text not null check (char_length(descricao) between 5 and 1000),
  link text check (link is null or (link ~ '^https?://' and char_length(link) <= 1000)),
  contato text check (contato is null or char_length(contato) <= 200),  -- opcional, só para quem quer resposta
  status text not null default 'aberto' check (status in ('aberto', 'resolvido', 'descartado')),
  resposta text check (char_length(resposta) <= 1000),
  criado_em timestamptz not null default now()
);

-- quem modera: inclua o id manualmente (a página #/moderar mostra o seu)
create table public.moderadores (
  id uuid primary key references auth.users (id) on delete cascade
);

-- ---------- segurança por linha ----------

alter table public.perfis enable row level security;
alter table public.votos enable row level security;
alter table public.evidencias_sugeridas enable row level security;
alter table public.reportes enable row level security;
alter table public.moderadores enable row level security;

create or replace function public.eh_moderador() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from moderadores where id = auth.uid());
$$;

-- perfil: cada um cria e lê o próprio; só o apelido pode ser alterado
create policy "cria o próprio perfil" on public.perfis for insert to authenticated with check (id = auth.uid() and pontos = 0);
create policy "lê o próprio perfil" on public.perfis for select to authenticated using (id = auth.uid());
create policy "altera o próprio apelido" on public.perfis for update to authenticated using (id = auth.uid());
revoke update on public.perfis from authenticated, anon;
grant update (apelido) on public.perfis to authenticated;

-- votos e evidências: cada um insere os próprios; ninguém lê votos individuais de outras pessoas
create policy "vota em nome próprio" on public.votos for insert to authenticated with check (usuario = auth.uid());
create policy "lê os próprios votos" on public.votos for select to authenticated using (usuario = auth.uid());
create policy "sugere em nome próprio" on public.evidencias_sugeridas for insert to authenticated with check (usuario = auth.uid() and status = 'pendente');
create policy "moderação lê evidências" on public.evidencias_sugeridas for select to authenticated using (public.eh_moderador());
create policy "moderação decide evidências" on public.evidencias_sugeridas for update to authenticated using (public.eh_moderador());

-- qualquer pessoa pode reportar; só a moderação lê e responde
create policy "qualquer um reporta" on public.reportes for insert to anon, authenticated with check (status = 'aberto' and resposta is null);
create policy "moderação lê reportes" on public.reportes for select to authenticated using (public.eh_moderador());
create policy "moderação responde reportes" on public.reportes for update to authenticated using (public.eh_moderador());
create policy "moderador se vê" on public.moderadores for select to authenticated using (id = auth.uid());

-- limite global de reportes anônimos, contra enxurrada
create or replace function public.antes_de_reportar() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if (select count(*) from reportes where criado_em > now() - interval '1 hour') >= 300 then
    raise exception 'limite de reportes por hora atingido';
  end if;
  return new;
end $$;
create trigger antes_de_reportar before insert on public.reportes for each row execute function public.antes_de_reportar();

-- preço que a pessoa viu na prateleira, em qualquer mercado (cobre mercados sem site)
create table public.precos_informados (
  id bigint generated always as identity primary key,
  usuario uuid not null default auth.uid() references public.perfis (id) on delete cascade,
  ean text not null check (ean ~ '^[0-9]{8,14}$'),
  mercado text not null check (char_length(mercado) between 2 and 60),
  local text check (local is null or char_length(local) <= 60),  -- bairro ou região administrativa, opcional
  preco numeric(10, 2) not null check (preco > 0 and preco < 100000),
  dia date not null default current_date,
  criado_em timestamptz not null default now(),
  unique (usuario, ean, mercado, dia)  -- um preço por produto, mercado e dia
);
create index precos_informados_ean on public.precos_informados (ean);
alter table public.precos_informados enable row level security;
create policy "informa em nome próprio" on public.precos_informados for insert to authenticated with check (usuario = auth.uid());
create policy "lê os próprios preços" on public.precos_informados for select to authenticated using (usuario = auth.uid());

create or replace function public.antes_de_informar_preco() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if (select count(*) from precos_informados where usuario = new.usuario and criado_em > now() - interval '1 hour') >= 40 then
    raise exception 'limite de contribuições por hora atingido';
  end if;
  new.mercado := btrim(regexp_replace(new.mercado, '\s+', ' ', 'g'));
  return new;
end $$;
create trigger antes_de_informar_preco before insert on public.precos_informados for each row execute function public.antes_de_informar_preco();

create or replace function public.pontuar_preco_informado() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  update perfis set pontos = pontos + 3 where id = new.usuario;
  return new;
end $$;
create trigger pontuar_preco_informado after insert on public.precos_informados for each row execute function public.pontuar_preco_informado();

-- pedido de inclusão: quando alguém escaneia um código que o app não conhece. Só o código e a data, sem pessoa.
create table public.pedidos_codigo (
  ean text primary key check (ean ~ '^[0-9]{8,14}$'),
  pedidos integer not null default 1,
  primeiro_em timestamptz not null default now(),
  ultimo_em timestamptz not null default now()
);
alter table public.pedidos_codigo enable row level security;  -- ninguém lê ou grava direto: só pela função abaixo

create or replace function public.pedir_codigo(codigo text) returns void
language plpgsql security definer set search_path = public as $$
begin
  if codigo !~ '^[0-9]{8,14}$' then raise exception 'código inválido'; end if;
  if (select count(*) from pedidos_codigo where ultimo_em > now() - interval '1 hour') >= 2000 then
    raise exception 'limite de pedidos por hora atingido';
  end if;
  insert into pedidos_codigo (ean) values (codigo)
    on conflict (ean) do update set pedidos = pedidos_codigo.pedidos + 1, ultimo_em = now();
end $$;
revoke all on function public.pedir_codigo(text) from public;
grant execute on function public.pedir_codigo(text) to anon, authenticated;

-- a coleta diária lê os códigos pedidos (é público: não identifica ninguém)
create view public.codigos_pedidos as
  select ean, pedidos, ultimo_em from public.pedidos_codigo order by ultimo_em desc limit 2000;
grant select on public.codigos_pedidos to anon, authenticated;

-- ---------- limite de contribuições e pontos ----------

create or replace function public.antes_de_votar() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if (select count(*) from votos where usuario = new.usuario and criado_em > now() - interval '1 hour') >= 60 then
    raise exception 'limite de contribuições por hora atingido';
  end if;
  return new;
end $$;
create trigger antes_de_votar before insert on public.votos for each row execute function public.antes_de_votar();

-- pontos: confirmar = 1, corrigir com preço = 3, avaliar causa = 1 (evidência só pontua quando aceita)
create or replace function public.pontuar_voto() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  update perfis set pontos = pontos + case
      when new.alvo = 'causa' then 1
      when not new.valor and new.preco_informado is not null then 3
      else 1 end
    where id = new.usuario;
  return new;
end $$;
create trigger pontuar_voto after insert on public.votos for each row execute function public.pontuar_voto();

create or replace function public.pontuar_evidencia() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.status = 'aceita' and old.status <> 'aceita' then
    update perfis set pontos = pontos + 5 where id = new.usuario;
  end if;
  return new;
end $$;
create trigger pontuar_evidencia after update on public.evidencias_sugeridas for each row execute function public.pontuar_evidencia();

-- ---------- o que o público vê: só totais, sem identificação ----------

-- hora arredondada e só a faixa de nível de quem votou (o mínimo de pontos do nível), para não identificar ninguém
create view public.resumo_votos as
  select v.ean, v.alvo, v.chave, v.valor, v.preco_informado,
         date_trunc('hour', v.criado_em) as criado_em,
         case when p.pontos >= 1000 then 1000 when p.pontos >= 300 then 300 when p.pontos >= 100 then 100
              when p.pontos >= 20 then 20 else 0 end as pontos_autor
  from public.votos v join public.perfis p on p.id = v.usuario;

create view public.meus_votos with (security_invoker = true) as
  select ean, alvo, chave, valor, preco_informado, dia from public.votos where usuario = auth.uid();

-- ranking: só quem escolheu um apelido aparece
create view public.ranking as
  select apelido, pontos from public.perfis where apelido is not null and pontos > 0 order by pontos desc limit 20;

-- evidências aceitas pela moderação, sem identificar quem enviou
create view public.evidencias_publicas as
  select ean, chave, url, descricao, nivel, moderado_em from public.evidencias_sugeridas where status = 'aceita';

-- preços informados: por produto e mercado, só a mediana dos últimos 14 dias e quantas pessoas informaram
create view public.precos_comunidade as
  select ean, lower(mercado) as mercado_chave, min(mercado) as mercado,
         percentile_cont(0.5) within group (order by preco)::numeric(10, 2) as preco_mediano,
         min(preco) as preco_minimo, max(preco) as preco_maximo,
         count(distinct usuario) as pessoas, max(dia) as ultimo_dia
  from public.precos_informados
  where dia >= current_date - 14
  group by ean, lower(mercado);

create view public.meus_precos with (security_invoker = true) as
  select ean, mercado, local, preco, dia from public.precos_informados where usuario = auth.uid();

revoke all on public.resumo_votos, public.ranking, public.evidencias_publicas, public.precos_comunidade from anon, authenticated;
grant select on public.resumo_votos, public.ranking, public.evidencias_publicas, public.precos_comunidade to anon, authenticated;
grant select on public.meus_precos to authenticated;
grant select on public.meus_votos to authenticated;

-- ---------- direitos do titular e retenção ----------

-- a pessoa apaga o próprio perfil, votos e evidências (cascata) e o usuário anônimo
create or replace function public.apagar_minha_conta() returns void
language plpgsql security definer set search_path = public as $$
begin
  delete from auth.users where id = auth.uid();
end $$;
revoke all on function public.apagar_minha_conta() from public, anon;
grant execute on function public.apagar_minha_conta() to authenticated;

-- retenção: votos e evidências recusadas com mais de 12 meses são apagados.
-- Agende com pg_cron (Database > Extensions > pg_cron):
--   select cron.schedule('limpeza-mensal', '0 4 1 * *', 'select public.limpar_dados_antigos()');
create or replace function public.limpar_dados_antigos() returns void
language sql security definer set search_path = public as $$
  delete from votos where criado_em < now() - interval '12 months';
  delete from precos_informados where criado_em < now() - interval '12 months';
  delete from evidencias_sugeridas where status = 'recusada' and criado_em < now() - interval '12 months';
  delete from reportes where status <> 'aberto' and criado_em < now() - interval '12 months';
  delete from auth.users u where u.is_anonymous and u.last_sign_in_at < now() - interval '12 months';
$$;
revoke all on function public.limpar_dados_antigos() from public, anon, authenticated;
