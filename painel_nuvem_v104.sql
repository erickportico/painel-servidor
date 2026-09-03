-- ================================================================
-- PATCH 104 - Guardar tudo na nuvem (Supabase)
-- Cole este conteudo em: Supabase > SQL Editor > New query > Run
-- Pode rodar mais de uma vez sem problema.
-- ================================================================

-- 1) Caixa de chaves (usuarios, permissoes, agenda, historico, config)
create table if not exists public.painel_nuvem (
  chave          text primary key,
  valor          jsonb,
  marca          text,
  autor          text,
  atualizado_em  timestamptz not null default now()
);

-- 2) Registros um por um (boletins P83, diarios P84, relatorios FPDO P92)
create table if not exists public.painel_registros (
  id             text primary key,
  colecao        text not null,
  dados          jsonb,
  removido       boolean not null default false,
  autor          text,
  atualizado_em  timestamptz not null default now()
);

create index if not exists painel_registros_colecao_idx
  on public.painel_registros (colecao);
create index if not exists painel_registros_colecao_data_idx
  on public.painel_registros (colecao, atualizado_em desc);

-- 3) Liberacao de acesso
alter table public.painel_nuvem     enable row level security;
alter table public.painel_registros enable row level security;

-- Regras antigas (se existirem) sao refeitas
drop policy if exists painel_nuvem_ler      on public.painel_nuvem;
drop policy if exists painel_nuvem_gravar   on public.painel_nuvem;
drop policy if exists painel_nuvem_alterar  on public.painel_nuvem;
drop policy if exists painel_nuvem_apagar   on public.painel_nuvem;
drop policy if exists painel_reg_ler        on public.painel_registros;
drop policy if exists painel_reg_gravar     on public.painel_registros;
drop policy if exists painel_reg_alterar    on public.painel_registros;
drop policy if exists painel_reg_apagar     on public.painel_registros;

-- O painel usa a chave publica (anon), igual ao resto do sistema
create policy painel_nuvem_ler     on public.painel_nuvem
  for select using (true);
create policy painel_nuvem_gravar  on public.painel_nuvem
  for insert with check (true);
create policy painel_nuvem_alterar on public.painel_nuvem
  for update using (true) with check (true);
create policy painel_nuvem_apagar  on public.painel_nuvem
  for delete using (true);

create policy painel_reg_ler       on public.painel_registros
  for select using (true);
create policy painel_reg_gravar    on public.painel_registros
  for insert with check (true);
create policy painel_reg_alterar   on public.painel_registros
  for update using (true) with check (true);
create policy painel_reg_apagar    on public.painel_registros
  for delete using (true);

-- 4) Hora de alteracao sempre correta
create or replace function public.painel_marca_hora()
returns trigger language plpgsql as $$
begin
  if new.atualizado_em is null then
    new.atualizado_em := now();
  end if;
  return new;
end;
$$;

drop trigger if exists painel_nuvem_hora on public.painel_nuvem;
create trigger painel_nuvem_hora before insert or update on public.painel_nuvem
  for each row execute function public.painel_marca_hora();

drop trigger if exists painel_registros_hora on public.painel_registros;
create trigger painel_registros_hora before insert or update on public.painel_registros
  for each row execute function public.painel_marca_hora();
