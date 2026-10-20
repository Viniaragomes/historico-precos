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
  criado_em timestamptz not null default now()
);

-- ---------- segurança por linha ----------

alter table public.perfis enable row level security;
alter table public.votos enable row level security;
alter table public.evidencias_sugeridas enable row level security;

-- perfil: cada um cria e lê o próprio; só o apelido pode ser alterado
create policy "cria o próprio perfil" on public.perfis for insert to authenticated with check (id = auth.uid() and pontos = 0);
create policy "lê o próprio perfil" on public.perfis for select to authenticated using (id = auth.uid());
create policy "altera o próprio apelido" on public.perfis for update to authenticated using (id = auth.uid());
revoke update on public.perfis from authenticated, anon;
grant update (apelido) on public.perfis to authenticated;

-- votos e evidências: cada um insere os próprios; ninguém lê votos individuais de outras pessoas
create policy "vota em nome próprio" on public.votos for insert to authenticated with check (usuario = auth.uid());
create policy "lê os próprios votos" on public.votos for select to authenticated using (usuario = auth.uid());
create policy "sugere em nome próprio" on public.evidencias_sugeridas for insert to authenticated with check (usuario = auth.uid());

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

revoke all on public.resumo_votos, public.ranking from anon, authenticated;
grant select on public.resumo_votos, public.ranking to anon, authenticated;
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
  delete from evidencias_sugeridas where status = 'recusada' and criado_em < now() - interval '12 months';
  delete from auth.users u where u.is_anonymous and u.last_sign_in_at < now() - interval '12 months';
$$;
revoke all on function public.limpar_dados_antigos() from public, anon, authenticated;
