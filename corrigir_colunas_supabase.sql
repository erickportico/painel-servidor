-- =====================================================================
-- CORRECAO DAS COLUNAS - painel_nuvem e painel_registros
-- =====================================================================
--
-- O QUE ACONTECEU
-- O script anterior criou as duas tabelas, mas com nomes de coluna que
-- nao sao os que o painel usa. O proprio console mostrou:
--     column painel_nuvem.valor does not exist
--     column painel_registros.colecao does not exist
-- Este script deixa as colunas exatamente como o painel pede:
--     painel_nuvem      chave, valor, marca, atualizado_em
--     painel_registros  id, colecao, dados, atualizado_em, removido
--
-- O QUE ELE FAZ
--   1. Confere se as tabelas estao vazias (elas estao - foram criadas
--      agora e nunca receberam dado de verdade). Se acharem qualquer
--      linha que nao seja das seis linhas de teste que eu mesmo criei,
--      ele PARA na hora e nao mexe em nada.
--   2. Acrescenta as colunas que faltam.
--   3. Ajusta o codigo dos registros para aceitar numero ou texto, e faz
--      a chave ser a dupla colecao + codigo (cada colecao tem os seus
--      codigos, sem se atropelarem).
--   4. Apaga as seis linhas de teste que eu criei sem necessidade
--      (usuarios, permissoes, agenda, boletins, diarios, fpdo) - elas
--      estao vazias e com nome errado; o painel usa outro nome de chave.
--   5. Mostra no fim as colunas de cada tabela, para conferir.
--
-- NAO MEXE em painel_dados, nem nas permissoes de acesso, nem em
-- nenhum dado seu. Pode rodar quantas vezes quiser.
--
-- COMO USAR
--   SQL Editor -> New query -> cola tudo -> Run.
--   Depois abra o painel e pressione Ctrl+F5. Os erros 400 do console
--   devem desaparecer.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) TRAVA DE SEGURANCA: so continua se as tabelas estiverem vazias
-- ---------------------------------------------------------------------
do $trava$
declare
  n_nuvem     bigint := 0;
  n_registros bigint := 0;
begin
  if to_regclass('public.painel_nuvem') is not null then
    execute $q$select count(*) from public.painel_nuvem
              where chave not in ('usuarios','permissoes','agenda','boletins','diarios','fpdo')$q$
       into n_nuvem;
  end if;
  if to_regclass('public.painel_registros') is not null then
    execute 'select count(*) from public.painel_registros' into n_registros;
  end if;

  if n_nuvem > 0 or n_registros > 0 then
    raise exception
      'PAREI POR SEGURANCA: ja existe dado nessas tabelas (painel_nuvem: %, painel_registros: %). Me avise antes de continuar.',
      n_nuvem, n_registros;
  end if;

  raise notice 'tabelas vazias, seguindo com a correcao.';
end;
$trava$;

-- ---------------------------------------------------------------------
-- 2) painel_nuvem: chave, valor, marca, atualizado_em
-- ---------------------------------------------------------------------
create table if not exists public.painel_nuvem (
  chave          text primary key,
  valor          text,
  marca          text,
  atualizado_em  timestamptz default now()
);

alter table public.painel_nuvem add column if not exists valor         text;
alter table public.painel_nuvem add column if not exists marca         text;
alter table public.painel_nuvem add column if not exists atualizado_em timestamptz default now();

-- as colunas que eu tinha inventado antes deixam de ser obrigatorias,
-- para nao atrapalhar a gravacao do painel
do $solta$
begin
  if exists (select 1 from information_schema.columns
              where table_schema='public' and table_name='painel_nuvem'
                and column_name='dados' and is_nullable='NO') then
    alter table public.painel_nuvem alter column dados drop not null;
    alter table public.painel_nuvem alter column dados drop default;
  end if;
end;
$solta$;

-- tira as seis linhas de teste (vazias, com nome de chave que o painel nao usa)
delete from public.painel_nuvem
 where chave in ('usuarios','permissoes','agenda','boletins','diarios','fpdo')
   and coalesce(valor, '') = '';

create index if not exists painel_nuvem_atualizado_em_idx
  on public.painel_nuvem (atualizado_em desc);

-- marca a hora sozinho quando o painel nao mandar
create or replace function public.painel_nuvem_ajustar()
returns trigger
language plpgsql
set search_path = public
as $ajuste$
begin
  if new.chave is null or new.chave = '' then
    raise exception 'painel_nuvem: chave vazia';
  end if;
  if new.atualizado_em is null then new.atualizado_em := now(); end if;
  begin
    new.id := new.chave;
  exception when others then null;
  end;
  return new;
end;
$ajuste$;

drop trigger if exists painel_nuvem_ajustar_trg on public.painel_nuvem;
create trigger painel_nuvem_ajustar_trg
  before insert or update on public.painel_nuvem
  for each row execute function public.painel_nuvem_ajustar();

-- ---------------------------------------------------------------------
-- 3) painel_registros: id, colecao, dados, atualizado_em, removido
-- ---------------------------------------------------------------------
create table if not exists public.painel_registros (
  colecao        text not null default '',
  id             text not null,
  dados          jsonb,
  atualizado_em  timestamptz default now(),
  removido       boolean default false
);

alter table public.painel_registros add column if not exists colecao       text;
alter table public.painel_registros add column if not exists dados         jsonb;
alter table public.painel_registros add column if not exists atualizado_em timestamptz default now();
alter table public.painel_registros add column if not exists removido      boolean default false;

-- o codigo do registro passa a aceitar numero OU texto
do $codigo$
declare
  tipo_id text;
  n       bigint;
begin
  select count(*) into n from public.painel_registros;
  if n > 0 then
    raise notice 'painel_registros ja tem % linha(s) - estrutura mantida como esta.', n;
  else
  select data_type into tipo_id
    from information_schema.columns
   where table_schema='public' and table_name='painel_registros' and column_name='id';

  if tipo_id is not null and tipo_id <> 'text' then
    alter table public.painel_registros alter column id drop default;
    alter table public.painel_registros alter column id type text using id::text;
    raise notice 'codigo do registro agora aceita numero ou texto.';
  end if;

  update public.painel_registros set colecao = coalesce(colecao, '') where colecao is null;
  alter table public.painel_registros alter column colecao set default '';
  alter table public.painel_registros alter column colecao set not null;
  alter table public.painel_registros alter column id set not null;
  end if;
end;
$codigo$;

-- a chave passa a ser a dupla colecao + codigo
do $chave$
declare
  nome_pk text;
  n       bigint;
begin
  select count(*) into n from public.painel_registros;
  if n > 0 then
    raise notice 'painel_registros com dados - chave mantida como esta.';
  else
  select conname into nome_pk
    from pg_constraint
   where conrelid = 'public.painel_registros'::regclass and contype = 'p';

  if nome_pk is not null and not exists (
       select 1 from pg_constraint c
        where c.conrelid = 'public.painel_registros'::regclass
          and c.contype = 'p'
          and (select array_agg(a.attname::text order by a.attname)
                 from unnest(c.conkey) k
                 join pg_attribute a on a.attrelid = c.conrelid and a.attnum = k)
              = array['colecao','id']) then
    execute format('alter table public.painel_registros drop constraint %I', nome_pk);
    nome_pk := null;
  end if;

  if nome_pk is null then
    alter table public.painel_registros
      add constraint painel_registros_pk primary key (colecao, id);
    raise notice 'chave da painel_registros agora e colecao + codigo.';
  end if;
  end if;
end;
$chave$;

create index if not exists painel_registros_colecao_idx
  on public.painel_registros (colecao, atualizado_em desc);

create or replace function public.painel_registros_ajustar()
returns trigger
language plpgsql
set search_path = public
as $reg$
begin
  if new.atualizado_em is null then new.atualizado_em := now(); end if;
  if new.removido is null then new.removido := false; end if;
  return new;
end;
$reg$;

drop trigger if exists painel_registros_updated_at_trg on public.painel_registros;
drop trigger if exists painel_registros_ajustar_trg on public.painel_registros;
create trigger painel_registros_ajustar_trg
  before insert or update on public.painel_registros
  for each row execute function public.painel_registros_ajustar();

-- ---------------------------------------------------------------------
-- 4) TESTE DE ESCRITA (grava e apaga so a propria linha de teste)
-- ---------------------------------------------------------------------
insert into public.painel_nuvem (chave, valor, marca)
values ('teste_do_script', 'funcionou', 'sql-editor')
 on conflict (chave) do update
 set valor = excluded.valor, marca = excluded.marca, atualizado_em = now();

insert into public.painel_registros (colecao, id, dados, removido)
values ('teste_do_script', '1', '{"ok":true}'::jsonb, false)
 on conflict (colecao, id) do update
 set dados = excluded.dados, atualizado_em = now();

select 'teste' as etapa,
       (select count(*) from public.painel_nuvem where chave = 'teste_do_script') as gravou_na_nuvem,
       (select count(*) from public.painel_registros where colecao = 'teste_do_script') as gravou_no_historico;

delete from public.painel_nuvem where chave = 'teste_do_script';
delete from public.painel_registros where colecao = 'teste_do_script';

-- ---------------------------------------------------------------------
-- 5) CONFERENCIA: as colunas que o painel precisa
-- ---------------------------------------------------------------------
select table_name as tabela, column_name as coluna, data_type as tipo,
       is_nullable as aceita_vazio
  from information_schema.columns
 where table_schema = 'public'
   and table_name in ('painel_nuvem', 'painel_registros')
 order by table_name, ordinal_position;

select 'painel_nuvem' as tabela,
       count(*) filter (where column_name = 'chave')         as tem_chave,
       count(*) filter (where column_name = 'valor')         as tem_valor,
       count(*) filter (where column_name = 'marca')         as tem_marca,
       count(*) filter (where column_name = 'atualizado_em') as tem_atualizado_em
  from information_schema.columns
 where table_schema='public' and table_name='painel_nuvem'
union all
select 'painel_registros',
       count(*) filter (where column_name = 'id'),
       count(*) filter (where column_name = 'colecao'),
       count(*) filter (where column_name = 'dados'),
       count(*) filter (where column_name = 'removido')
  from information_schema.columns
 where table_schema='public' and table_name='painel_registros';

-- =====================================================================
-- FIM.
--
-- O QUE OLHAR AGORA
--   * Na linha de teste, gravou_na_nuvem e gravou_no_historico devem
--     mostrar 1 e 1 (depois a linha de teste e apagada sozinha).
--   * Na ultima lista, todos os "tem_..." devem mostrar 1.
--   * Abra o painel e pressione Ctrl+F5, nos tres computadores. No
--     console os erros 400 de painel_nuvem e painel_registros devem
--     desaparecer, e o aviso PATCH104 deve parar de listar problema.
--
-- SE AINDA APARECER ERRO NO CONSOLE
--   Copie a mensagem inteira. Se disser algo como "invalid input syntax"
--   ou "column ... is of type", e so o tipo de uma coluna (texto x JSON)
--   e eu acerto em um script curto. Nenhum dado seu corre risco: as
--   telas continuam gravando no navegador enquanto isso.
-- =====================================================================
