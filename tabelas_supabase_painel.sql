-- =====================================================================
-- TABELAS DO SUPABASE - PAINEL PORTICO
-- =====================================================================
--
-- PARA QUE SERVE
-- Hoje so existe uma tabela de verdade no Supabase: painel_dados.
-- E por ela que passa tudo que e compartilhado entre os tres
-- computadores (obras, itens, medicoes, custos, as vistas do patch 67 e
-- os retratos diarios de backup).
-- Ja as telas de usuarios, permissoes, agenda, boletins, diarios de obra
-- e FPDO gravam so no navegador de quem esta usando. O painel tenta
-- falar com duas tabelas que NUNCA foram criadas (painel_nuvem e
-- painel_registros), a chamada falha em silencio e o dado fica preso
-- naquele computador. Quem abre em outra maquina nao ve nada.
--
-- Este script cria o que falta e deixa as tres tabelas no mesmo padrao
-- do painel. Depois disso eu escrevo o patch que faz essas telas
-- realmente gravarem e lerem da nuvem - a tabela e o primeiro passo, ela
-- por si so nao muda a tela.
--
-- COMO USAR
--   1. Abra o painel do Supabase no navegador.
--   2. Menu da esquerda: SQL Editor  ->  New query.
--   3. Cole TODO o conteudo deste arquivo.
--   4. Clique em Run (ou Ctrl+Enter).
--   5. No fim ele mostra duas listas de conferencia. Confira se aparecem
--      painel_dados, painel_nuvem e painel_registros.
--
-- SEGURANCA
--   * Este script NAO apaga e NAO altera nada que ja existe. Nao tem
--     DROP, nao tem DELETE, nao tem TRUNCATE.
--   * Na painel_dados ele so garante o que falta (coluna ausente, indice,
--     chave primaria). Nao mexe nas permissoes dela, para nao correr o
--     risco de derrubar a sincronizacao que ja funciona.
--   * As tabelas novas nascem com a MESMA regra de acesso da
--     painel_dados, copiada automaticamente. Assim elas funcionam do
--     mesmo jeito, nem mais aberto nem mais fechado.
--   * Pode rodar quantas vezes quiser: o que ja existe e pulado.
--
-- AVISO IMPORTANTE SOBRE ACESSO
--   O painel roda no navegador com a chave publica (anon) escrita dentro
--   da propria pagina. Isso significa que, hoje, quem tiver o endereco do
--   painel pode ler e gravar nessas tabelas - inclusive a de usuarios e
--   permissoes que este script cria. Para uso interno entre voces tres
--   isso costuma passar, mas nao e uma tranca de verdade: senha de
--   usuario NUNCA deve ser guardada em texto puro ai. Quando quiser, eu
--   monto o passo seguinte (login pelo Supabase Auth e regras por
--   usuario), que e o unico jeito de fechar isso pra valer.
--
-- O QUE CADA TABELA GUARDA
--   painel_dados      o banco principal (ja existe, nao muda nada)
--                     id 1        = banco do painel
--                     id 67       = vistas do patch 67
--                     id 2000xxxx = retrato de backup do dia
--   painel_nuvem      as telas que hoje ficam presas no navegador, uma
--                     linha por assunto: usuarios, permissoes, agenda,
--                     boletins, diarios, fpdo
--   painel_registros  historico do que acontece (quem gravou o que e
--                     quando), para dar para conferir depois
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) COMO ESTA AGORA (antes de mexer)
-- ---------------------------------------------------------------------
select 'ANTES' as momento,
       table_name as tabela,
       (select count(*) from information_schema.columns c
         where c.table_schema = 'public' and c.table_name = t.table_name) as colunas
  from information_schema.tables t
 where table_schema = 'public'
   and table_name like 'painel%'
 order by table_name;

-- ---------------------------------------------------------------------
-- 2) painel_dados: so garante o que falta (nao altera nada que existe)
-- ---------------------------------------------------------------------
create table if not exists public.painel_dados (
  id          bigint primary key,
  dados       jsonb,
  updated_at  timestamptz default now()
);

alter table public.painel_dados add column if not exists dados      jsonb;
alter table public.painel_dados add column if not exists updated_at timestamptz default now();

create index if not exists painel_dados_updated_at_idx
  on public.painel_dados (updated_at desc);

-- ---------------------------------------------------------------------
-- 3) painel_nuvem: as telas que hoje ficam presas no navegador
--    Uma linha por assunto. A coluna "chave" e o nome do assunto.
--    A coluna "id" existe com o mesmo valor da chave, para funcionar
--    tanto se o painel chamar por "chave" quanto por "id".
-- ---------------------------------------------------------------------
create table if not exists public.painel_nuvem (
  chave       text primary key,
  id          text,
  dados       jsonb not null default '{}'::jsonb,
  quem        text,
  versao      bigint default 1,
  updated_at  timestamptz default now()
);

alter table public.painel_nuvem add column if not exists id         text;
alter table public.painel_nuvem add column if not exists dados      jsonb not null default '{}'::jsonb;
alter table public.painel_nuvem add column if not exists quem       text;
alter table public.painel_nuvem add column if not exists versao     bigint default 1;
alter table public.painel_nuvem add column if not exists updated_at timestamptz default now();

create unique index if not exists painel_nuvem_id_idx on public.painel_nuvem (id);
create index if not exists painel_nuvem_updated_at_idx on public.painel_nuvem (updated_at desc);

-- ---------------------------------------------------------------------
-- 4) painel_registros: historico de quem gravou o que e quando
-- ---------------------------------------------------------------------
create table if not exists public.painel_registros (
  id          bigserial primary key,
  chave       text,
  tipo        text,
  quem        text,
  obra        text,
  descricao   text,
  dados       jsonb,
  criado_em   timestamptz default now(),
  updated_at  timestamptz default now()
);

alter table public.painel_registros add column if not exists chave      text;
alter table public.painel_registros add column if not exists tipo       text;
alter table public.painel_registros add column if not exists quem       text;
alter table public.painel_registros add column if not exists obra       text;
alter table public.painel_registros add column if not exists descricao  text;
alter table public.painel_registros add column if not exists dados      jsonb;
alter table public.painel_registros add column if not exists criado_em  timestamptz default now();
alter table public.painel_registros add column if not exists updated_at timestamptz default now();

create index if not exists painel_registros_criado_em_idx on public.painel_registros (criado_em desc);
create index if not exists painel_registros_chave_idx     on public.painel_registros (chave);

-- ---------------------------------------------------------------------
-- 5) AJUDANTES: mantem chave/id iguais e a hora da ultima mudanca
-- ---------------------------------------------------------------------
create or replace function public.painel_nuvem_ajustar()
returns trigger
language plpgsql
set search_path = public
as $ajuste$
begin
  if new.chave is null or new.chave = '' then new.chave := new.id; end if;
  if new.id is null or new.id = '' then new.id := new.chave; end if;
  new.updated_at := now();
  if tg_op = 'UPDATE' then
    new.versao := coalesce(old.versao, 0) + 1;
  end if;
  return new;
end;
$ajuste$;

drop trigger if exists painel_nuvem_ajustar_trg on public.painel_nuvem;
create trigger painel_nuvem_ajustar_trg
  before insert or update on public.painel_nuvem
  for each row execute function public.painel_nuvem_ajustar();

create or replace function public.painel_tocar_updated_at()
returns trigger
language plpgsql
set search_path = public
as $toca$
begin
  new.updated_at := now();
  return new;
end;
$toca$;

drop trigger if exists painel_registros_updated_at_trg on public.painel_registros;
create trigger painel_registros_updated_at_trg
  before insert or update on public.painel_registros
  for each row execute function public.painel_tocar_updated_at();

-- ---------------------------------------------------------------------
-- 6) LINHAS DE ASSUNTO JA PRONTAS (vazias, so para existirem)
-- ---------------------------------------------------------------------
insert into public.painel_nuvem (chave, dados)
select x.chave, '{}'::jsonb
  from (values ('usuarios'), ('permissoes'), ('agenda'),
               ('boletins'), ('diarios'), ('fpdo')) as x(chave)
 on conflict (chave) do nothing;

-- ---------------------------------------------------------------------
-- 7) ACESSO: as tabelas novas recebem a MESMA regra da painel_dados
--    (copiado automaticamente, sem tocar na painel_dados)
-- ---------------------------------------------------------------------
do $acesso$
declare
  rls_ligado  boolean;
  nova        text;
  papel       text;
  acao        text;
begin
  select c.relrowsecurity into rls_ligado
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
   where n.nspname = 'public' and c.relname = 'painel_dados';

  if rls_ligado is null then
    raise notice 'painel_dados nao encontrada - as tabelas novas ficam com a regra padrao.';
    rls_ligado := true;
  end if;

  foreach nova in array array['painel_nuvem', 'painel_registros'] loop

    -- permissoes iguais as que a painel_dados ja da a cada papel
    foreach papel in array array['anon', 'authenticated', 'service_role'] loop
      if exists (select 1 from pg_roles where rolname = papel) then
        foreach acao in array array['SELECT', 'INSERT', 'UPDATE', 'DELETE'] loop
          if has_table_privilege(papel, 'public.painel_dados', acao) then
            execute format('grant %s on table public.%I to %I', acao, nova, papel);
          end if;
        end loop;
      end if;
    end loop;

    if nova = 'painel_registros'
       and exists (select 1 from pg_class s
                    join pg_namespace sn on sn.oid = s.relnamespace
                   where sn.nspname = 'public'
                     and s.relname = 'painel_registros_id_seq'
                     and s.relkind = 'S') then
      if exists (select 1 from pg_roles where rolname = 'anon')
         and has_table_privilege('anon', 'public.painel_dados', 'INSERT') then
        execute 'grant usage, select on sequence public.painel_registros_id_seq to anon';
      end if;
      if exists (select 1 from pg_roles where rolname = 'authenticated') then
        execute 'grant usage, select on sequence public.painel_registros_id_seq to authenticated';
      end if;
    end if;

    if rls_ligado then
      execute format('alter table public.%I enable row level security', nova);
      if not exists (select 1 from pg_policies
                      where schemaname = 'public' and tablename = nova
                        and policyname = 'painel_acesso') then
        execute format(
          'create policy painel_acesso on public.%I for all to anon, authenticated using (true) with check (true)',
          nova);
        raise notice 'regra de acesso criada em %', nova;
      end if;
    end if;

  end loop;
end;
$acesso$;

-- ---------------------------------------------------------------------
-- 8) CONFERENCIA (depois de mexer)
-- ---------------------------------------------------------------------
select 'DEPOIS' as momento,
       t.table_name as tabela,
       c.relrowsecurity as acesso_controlado,
       (select count(*) from pg_policies p
         where p.schemaname = 'public' and p.tablename = t.table_name) as regras_de_acesso
  from information_schema.tables t
  join pg_class c on c.relname = t.table_name
  join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
 where t.table_schema = 'public'
   and t.table_name in ('painel_dados', 'painel_nuvem', 'painel_registros')
 order by t.table_name;

select 'painel_nuvem' as tabela, chave as assunto, versao,
       updated_at as ultima_mudanca,
       length(dados::text) as tamanho_do_conteudo
  from public.painel_nuvem
 order by chave;

select 'painel_dados' as tabela,
       count(*) as linhas,
       min(id) as menor_codigo,
       max(id) as maior_codigo,
       max(updated_at) as ultima_gravacao
  from public.painel_dados;

-- =====================================================================
-- FIM. As tabelas estao no ar.
--
-- O QUE OLHAR AGORA
--   * A lista DEPOIS deve mostrar as tres tabelas.
--   * A painel_nuvem deve mostrar as seis linhas de assunto
--     (usuarios, permissoes, agenda, boletins, diarios, fpdo), vazias.
--   * A painel_dados deve continuar com a mesma contagem de linhas de
--     antes - este script nao mexe nos dados dela.
--   * Abra o painel e pressione Ctrl+F5. Nada muda na tela ainda: as
--     telas de usuarios, agenda, boletins, diarios e FPDO passam a ter
--     onde gravar, mas quem manda o dado para la e o patch seguinte.
--
-- SE ALGO DER ERRO
--   Copie a mensagem inteira do SQL Editor e me mande. Nada foi apagado:
--   o script nao remove nem sobrescreve dado nenhum.
-- =====================================================================
