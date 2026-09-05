-- =====================================================================
-- AJUSTE FINAL DAS TABELAS - painel_nuvem e painel_registros
-- =====================================================================
--
-- POR QUE ESTE SCRIPT
-- Olhando o codigo do painel (as linhas que voce colou) apareceram tres
-- diferencas em relacao ao script anterior:
--
--   1. O painel manda tambem quem fez a alteracao (coluna autor) nas
--      duas tabelas. Sem essa coluna, toda gravacao volta com erro.
--   2. Nos registros (boletins, diarios, FPDO) o painel usa APENAS o
--      codigo para decidir se e novo ou se e atualizacao. Ou seja, a
--      chave da tabela tem que ser so o codigo, nao a dupla
--      colecao + codigo como eu tinha deixado.
--   3. O valor guardado na nuvem e um pacote de dados (lista de
--      usuarios, permissoes, agenda...), nao um texto simples. Se ficar
--      como texto, o painel entende que mudou toda hora e fica subindo
--      e descendo a mesma coisa sem parar.
--
-- Este script arruma esses tres pontos. Pode rodar mesmo que o anterior
-- tenha sido rodado, ou que nem tenha sido: ele confere tudo antes.
--
-- NAO MEXE na sua tabela antiga de dados nem nas permissoes dela, e nao
-- apaga nenhum registro seu. Pode rodar quantas vezes quiser.
--
-- COMO USAR
--   SQL Editor -> New query -> cola tudo -> Run.
--   Depois abra o painel e pressione Ctrl+F5 nos tres computadores.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) garante que as duas tabelas existem no formato certo
-- ---------------------------------------------------------------------
create table if not exists public.painel_nuvem (
  chave          text primary key,
  valor          jsonb,
  marca          text,
  autor          text,
  atualizado_em  timestamptz default now()
);

create table if not exists public.painel_registros (
  id             text primary key,
  colecao        text not null default '',
  dados          jsonb,
  autor          text,
  atualizado_em  timestamptz default now(),
  removido       boolean default false
);

-- ---------------------------------------------------------------------
-- 2) coluna autor nas duas tabelas (era o que faltava para gravar)
-- ---------------------------------------------------------------------
alter table public.painel_nuvem     add column if not exists autor text;
alter table public.painel_registros add column if not exists autor text;

alter table public.painel_nuvem     add column if not exists marca         text;
alter table public.painel_nuvem     add column if not exists atualizado_em timestamptz default now();
alter table public.painel_registros add column if not exists colecao       text;
alter table public.painel_registros add column if not exists dados         jsonb;
alter table public.painel_registros add column if not exists removido      boolean default false;
alter table public.painel_registros add column if not exists atualizado_em timestamptz default now();

-- ---------------------------------------------------------------------
-- 3) o valor da nuvem passa a ser pacote de dados (e nao texto solto)
-- ---------------------------------------------------------------------
do $valor$
declare
  tipo text;
begin
  select data_type into tipo
    from information_schema.columns
   where table_schema='public' and table_name='painel_nuvem' and column_name='valor';

  if tipo is null then
    alter table public.painel_nuvem add column valor jsonb;
    raise notice 'coluna valor criada.';
  elsif tipo <> 'jsonb' then
    begin
      alter table public.painel_nuvem alter column valor drop default;
      alter table public.painel_nuvem
        alter column valor type jsonb
        using (case when valor is null or valor = '' then null else valor::jsonb end);
      raise notice 'coluna valor agora guarda pacote de dados.';
    exception when others then
      raise notice 'nao consegui converter a coluna valor (%). Me avise.', sqlerrm;
    end;
  else
    raise notice 'coluna valor ja estava certa.';
  end if;
end;
$valor$;

-- ---------------------------------------------------------------------
-- 4) o codigo do registro passa a aceitar numero OU texto
-- ---------------------------------------------------------------------
do $tipo_id$
declare
  tipo text;
begin
  select data_type into tipo
    from information_schema.columns
   where table_schema='public' and table_name='painel_registros' and column_name='id';

  if tipo is not null and tipo <> 'text' then
    alter table public.painel_registros alter column id drop default;
    alter table public.painel_registros alter column id type text using id::text;
    raise notice 'codigo do registro agora aceita numero ou texto.';
  end if;
end;
$tipo_id$;

-- ---------------------------------------------------------------------
-- 5) a chave dos registros volta a ser SO o codigo
--    (e assim que o painel procura: mesmo codigo = mesmo registro)
-- ---------------------------------------------------------------------
do $chave$
declare
  nome_pk  text;
  colunas  text[];
  repetido bigint;
begin
  -- se o mesmo codigo aparecer em duas colecoes, paro e aviso
  select count(*) into repetido
    from (select id from public.painel_registros group by id having count(*) > 1) x;

  if repetido > 0 then
    raise notice 'PAREI ESTA PARTE: % codigo(s) repetido(s) em colecoes diferentes. Me avise para eu resolver sem perder nada.', repetido;
  else
    select c.conname,
           (select array_agg(a.attname::text order by a.attname)
              from unnest(c.conkey) k
              join pg_attribute a on a.attrelid = c.conrelid and a.attnum = k)
      into nome_pk, colunas
      from pg_constraint c
     where c.conrelid = 'public.painel_registros'::regclass and c.contype = 'p';

    if nome_pk is not null and colunas <> array['id'] then
      execute format('alter table public.painel_registros drop constraint %I', nome_pk);
      nome_pk := null;
    end if;

    if nome_pk is null then
      update public.painel_registros set colecao = coalesce(colecao, '') where colecao is null;
      alter table public.painel_registros alter column id set not null;
      alter table public.painel_registros
        add constraint painel_registros_pk primary key (id);
      raise notice 'chave dos registros agora e so o codigo.';
    else
      raise notice 'chave dos registros ja estava certa.';
    end if;
  end if;
end;
$chave$;

-- a colecao continua sendo guardada e serve para separar as telas
alter table public.painel_registros alter column colecao set default '';
create index if not exists painel_registros_colecao_idx
  on public.painel_registros (colecao, atualizado_em desc);
create index if not exists painel_nuvem_atualizado_em_idx
  on public.painel_nuvem (atualizado_em desc);

-- ---------------------------------------------------------------------
-- 6) qualquer coluna sobrando do script antigo deixa de ser obrigatoria
--    (senao ela barra a gravacao do painel)
-- ---------------------------------------------------------------------
do $sobra$
declare
  c record;
begin
  for c in
    select table_name, column_name
      from information_schema.columns
     where table_schema = 'public'
       and table_name in ('painel_nuvem','painel_registros')
       and is_nullable = 'NO'
       and column_name not in ('chave','id')
       and not (table_name = 'painel_registros' and column_name = 'colecao')
  loop
    execute format('alter table public.%I alter column %I drop not null', c.table_name, c.column_name);
    raise notice 'coluna % da tabela % nao e mais obrigatoria.', c.column_name, c.table_name;
  end loop;
end;
$sobra$;

-- ---------------------------------------------------------------------
-- 7) hora preenchida sozinha quando o painel nao mandar
-- ---------------------------------------------------------------------
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
  return new;
end;
$ajuste$;

drop trigger if exists painel_nuvem_ajustar_trg on public.painel_nuvem;
create trigger painel_nuvem_ajustar_trg
  before insert or update on public.painel_nuvem
  for each row execute function public.painel_nuvem_ajustar();

create or replace function public.painel_registros_ajustar()
returns trigger
language plpgsql
set search_path = public
as $reg$
begin
  if new.atualizado_em is null then new.atualizado_em := now(); end if;
  if new.removido is null then new.removido := false; end if;
  if new.colecao is null then new.colecao := ''; end if;
  return new;
end;
$reg$;

drop trigger if exists painel_registros_ajustar_trg on public.painel_registros;
create trigger painel_registros_ajustar_trg
  before insert or update on public.painel_registros
  for each row execute function public.painel_registros_ajustar();

-- ---------------------------------------------------------------------
-- 8) libera leitura e gravacao para o painel (mesma coisa de antes)
-- ---------------------------------------------------------------------
alter table public.painel_nuvem     disable row level security;
alter table public.painel_registros disable row level security;
grant select, insert, update, delete on public.painel_nuvem     to anon, authenticated;
grant select, insert, update, delete on public.painel_registros to anon, authenticated;

-- avisa o servico do painel para reler as colunas novas na hora
do $recarrega$
begin
  perform pg_notify('pgrst', 'reload schema');
exception when others then null;
end;
$recarrega$;

-- ---------------------------------------------------------------------
-- 9) teste rapido: grava igual o painel grava e depois apaga
-- ---------------------------------------------------------------------
do $teste$
begin
  insert into public.painel_nuvem (chave, valor, marca, autor, atualizado_em)
  values ('teste_painel_ok', '{"ok":true}'::jsonb, 'marca-teste', 'teste', now())
  on conflict (chave) do update
     set valor = excluded.valor, marca = excluded.marca,
         autor = excluded.autor, atualizado_em = excluded.atualizado_em;
exception when others then
  raise notice 'teste da nuvem nao passou: %', sqlerrm;
end;
$teste$;

do $teste2$
begin
  insert into public.painel_registros (id, colecao, dados, autor, atualizado_em, removido)
  values ('teste-painel-ok', 'p83_boletins', '{"ok":true}'::jsonb, 'teste', now(), false)
  on conflict (id) do update
     set colecao = excluded.colecao, dados = excluded.dados, autor = excluded.autor,
         atualizado_em = excluded.atualizado_em, removido = excluded.removido;
exception when others then
  raise notice 'teste dos registros nao passou: %', sqlerrm;
end;
$teste2$;

select (select count(*) from public.painel_nuvem     where chave = 'teste_painel_ok')  as gravou_na_nuvem,
       (select count(*) from public.painel_registros where id    = 'teste-painel-ok') as gravou_no_historico;

delete from public.painel_nuvem     where chave = 'teste_painel_ok';
delete from public.painel_registros where id    = 'teste-painel-ok';

-- ---------------------------------------------------------------------
-- 10) conferencia final
-- ---------------------------------------------------------------------
select 'painel_nuvem' as tabela,
       count(*) filter (where column_name = 'chave')         as tem_chave,
       count(*) filter (where column_name = 'valor')         as tem_valor,
       count(*) filter (where column_name = 'marca')         as tem_marca,
       count(*) filter (where column_name = 'autor')         as tem_autor,
       count(*) filter (where column_name = 'atualizado_em') as tem_data
  from information_schema.columns
 where table_schema = 'public' and table_name = 'painel_nuvem';

select 'painel_registros' as tabela,
       count(*) filter (where column_name = 'id')       as tem_codigo,
       count(*) filter (where column_name = 'colecao')  as tem_colecao,
       count(*) filter (where column_name = 'dados')    as tem_dados,
       count(*) filter (where column_name = 'autor')    as tem_autor,
       count(*) filter (where column_name = 'removido') as tem_removido
  from information_schema.columns
 where table_schema = 'public' and table_name = 'painel_registros';

select 'chave dos registros' as item, string_agg(a.attname, ' + ') as colunas
  from pg_constraint c
  join unnest(c.conkey) k on true
  join pg_attribute a on a.attrelid = c.conrelid and a.attnum = k
 where c.conrelid = 'public.painel_registros'::regclass and c.contype = 'p';

-- =====================================================================
-- FIM.
--
-- O QUE OLHAR AGORA
--   * No teste, os dois numeros devem aparecer como 1 e 1.
--   * Nas duas listas, todos os "tem_..." devem mostrar 1.
--   * Em "chave dos registros" deve aparecer apenas: id
--   * Abra o painel e pressione Ctrl+F5 nos tres computadores. No
--     console os erros de gravacao devem desaparecer e o aviso do
--     PATCH104 deve parar de reclamar.
--
-- SE AINDA SOBRAR ERRO
--   Copie a mensagem inteira do console. Nenhum dado seu corre risco:
--   as telas continuam gravando no navegador enquanto isso.
-- =====================================================================
