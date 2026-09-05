-- =====================================================================
-- PATCH 128 - PARTE 2: FECHAR AS TABELAS (so gente logada entra)
-- =====================================================================
--
-- O QUE ESTA PARTE FAZ
-- Hoje as tabelas de dados do painel (painel_dados, painel_nuvem e
-- painel_registros) aceitam qualquer visita que tenha o arquivo em
-- maos, porque a chave publica que fica dentro do index.html basta.
-- Depois deste arquivo:
--   * Quem NAO esta logado nao le e nao grava mais nada.
--   * Quem esta logado como somente consulta LE, mas nao grava.
--   * Quem e administrador ou pode lancar LE e GRAVA.
-- As regras ficam no servidor, entao nao ha como burlar mexendo no
-- navegador.
--
-- QUANDO RODAR
-- Somente DEPOIS que as tres pessoas ja tiverem entrado uma vez com
-- e-mail e senha e trocado a senha provisoria. Se rodar antes, o painel
-- abre em branco para quem ainda nao entrou.
--
-- SEGURANCA
--   * Nao apaga nem altera nenhum dado. So mexe em quem pode ver.
--   * Se a tabela de perfis nao existir, ou se nao houver nenhum
--     administrador ativo, o script PARA na hora e nao fecha nada -
--     assim ninguem fica trancado do lado de fora.
--   * Pode rodar quantas vezes quiser.
--   * No fim do arquivo tem o comando para REABRIR tudo, caso precise
--     voltar atras as pressas.
--
-- COMO USAR
--   SQL Editor -> New query -> cola tudo -> Run.
--   Depois abra o painel e pressione Ctrl+F5.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1) TRAVA: nao fecha nada se ninguem puder entrar depois
-- ---------------------------------------------------------------------
do $trava$
declare
  admins int := 0;
  contas int := 0;
begin
  if to_regclass('public.painel_perfis') is null then
    raise exception 'PAREI POR SEGURANCA: a tabela de perfis nao existe. Rode primeiro o arquivo perfis_login_supabase.sql e crie as contas.';
  end if;

  select count(*) into contas from public.painel_perfis;
  select count(*) into admins from public.painel_perfis where perfil = 'admin' and ativo;

  if contas = 0 then
    raise exception 'PAREI POR SEGURANCA: nenhuma conta cadastrada. Crie as contas em Authentication > Users > Add user antes de fechar as tabelas.';
  end if;
  if admins = 0 then
    raise exception 'PAREI POR SEGURANCA: nenhum administrador ativo. Defina um administrador antes de fechar as tabelas.';
  end if;

  raise notice 'ok: % conta(s), sendo % administrador(es) ativo(s). Seguindo.', contas, admins;
end;
$trava$;

-- ---------------------------------------------------------------------
-- 2) QUEM PODE O QUE (perguntas que o banco faz a cada acesso)
-- ---------------------------------------------------------------------

-- esta logado e com a conta liberada?
create or replace function public.painel_logado()
returns boolean
language sql
stable
security definer
set search_path = public
as $log$
  select exists (
    select 1 from public.painel_perfis p
     where p.id = auth.uid() and p.ativo
  );
$log$;

-- pode gravar (administrador ou quem lanca)?
create or replace function public.painel_pode_editar()
returns boolean
language sql
stable
security definer
set search_path = public
as $edt$
  select exists (
    select 1 from public.painel_perfis p
     where p.id = auth.uid() and p.ativo and p.perfil in ('admin','editor')
  );
$edt$;

revoke all on function public.painel_logado() from anon;
revoke all on function public.painel_pode_editar() from anon;
grant execute on function public.painel_logado() to authenticated;
grant execute on function public.painel_pode_editar() to authenticated;

-- ---------------------------------------------------------------------
-- 3) FECHA AS TRES TABELAS DE DADOS
--    ler: qualquer pessoa logada  |  gravar: administrador ou editor
-- ---------------------------------------------------------------------
do $fecha$
declare
  tabela text;
  velha  text;
begin
  foreach tabela in array array['painel_dados','painel_nuvem','painel_registros']
  loop
    if to_regclass('public.' || tabela) is null then
      raise notice 'tabela % nao existe aqui - pulei.', tabela;
      continue;
    end if;

    execute format('alter table public.%I enable row level security', tabela);

    -- tira as regras antigas que deixavam todo mundo entrar
    for velha in
      select policyname from pg_policies
       where schemaname = 'public' and tablename = tabela
    loop
      execute format('drop policy if exists %I on public.%I', velha, tabela);
    end loop;

    execute format(
      'create policy painel_ler on public.%I for select to authenticated using (public.painel_logado())',
      tabela);
    execute format(
      'create policy painel_incluir on public.%I for insert to authenticated with check (public.painel_pode_editar())',
      tabela);
    execute format(
      'create policy painel_alterar on public.%I for update to authenticated using (public.painel_pode_editar()) with check (public.painel_pode_editar())',
      tabela);
    execute format(
      'create policy painel_apagar on public.%I for delete to authenticated using (public.painel_pode_editar())',
      tabela);

    -- quem nao esta logado perde o acesso a tabela
    execute format('revoke all on table public.%I from anon', tabela);
    execute format('revoke all on table public.%I from public', tabela);
    execute format('grant select, insert, update, delete on table public.%I to authenticated', tabela);

    raise notice 'tabela % fechada: leitura para logados, gravacao para admin e editor.', tabela;
  end loop;
end;
$fecha$;

-- contadores automaticos (se existirem) tambem saem das maos de quem nao entrou
do $seq$
declare
  s text;
begin
  for s in
    select c.relname from pg_class c
      join pg_namespace n on n.oid = c.relnamespace
     where n.nspname = 'public' and c.relkind = 'S'
       and c.relname like 'painel_%'
  loop
    execute format('revoke all on sequence public.%I from anon', s);
    execute format('grant usage, select on sequence public.%I to authenticated', s);
  end loop;
end;
$seq$;

-- ---------------------------------------------------------------------
-- 4) CONFERENCIA
-- ---------------------------------------------------------------------
select c.relname                                   as tabela,
       c.relrowsecurity                            as regra_ligada,
       has_table_privilege('anon', c.oid, 'SELECT')          as visita_le,
       has_table_privilege('authenticated', c.oid, 'SELECT') as logado_le,
       (select count(*) from pg_policies p
         where p.schemaname = 'public' and p.tablename = c.relname) as regras
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public'
   and c.relname in ('painel_dados','painel_nuvem','painel_registros','painel_perfis')
 order by c.relname;

select email, nome, perfil, ativo, trocar_senha, ultimo_acesso
  from public.painel_perfis
 order by perfil, email;

-- =====================================================================
-- FIM.
--
-- O QUE OLHAR AGORA
--   * Na primeira lista, as quatro tabelas devem mostrar:
--       regra_ligada = true
--       visita_le    = false   (quem nao entrou nao le nada)
--       logado_le    = true
--       regras       = 4
--   * Na segunda lista, confira se cada pessoa esta com o tipo certo
--     (admin, editor ou visitante) e ativo = true. Quem aparece com
--     trocar_senha = true ainda nao criou a senha definitiva.
--   * Depois abra o painel e pressione Ctrl+F5:
--       - com a sua conta de administrador, tudo deve salvar normal;
--       - numa conta somente consulta, a tela abre e mostra os dados,
--         mas a gravacao e recusada pelo servidor;
--       - sem fazer login, o painel nao mostra dado nenhum.
--
-- SE ALGUEM FICOU TRANCADO DO LADO DE FORA
--   Cheque primeiro se a pessoa esta na lista com ativo = true. Para
--   liberar ou promover:
--     update public.painel_perfis set ativo = true, perfil = 'editor'
--      where email = 'pessoa@empresa.com';
--   Tipos aceitos: admin (tudo), editor (lanca e edita),
--   visitante (somente consulta).
--
-- PARA REABRIR TUDO AS PRESSAS (volta ao estado anterior)
--   Rode somente se precisar mesmo - as tabelas ficam abertas de novo
--   para quem tiver o arquivo:
--     do $volta$
--     declare t text; v text;
--     begin
--       foreach t in array array['painel_dados','painel_nuvem','painel_registros']
--       loop
--         if to_regclass('public.' || t) is null then continue; end if;
--         for v in select policyname from pg_policies
--                   where schemaname='public' and tablename=t
--         loop execute format('drop policy if exists %I on public.%I', v, t); end loop;
--         execute format('create policy painel_acesso on public.%I for all to anon, authenticated using (true) with check (true)', t);
--         execute format('grant select, insert, update, delete on table public.%I to anon, authenticated', t);
--       end loop;
--     end;
--     $volta$;
--
-- LEMBRETE
--   A chave publica que fica dentro do index.html continua permitindo
--   conversar com o servidor - o que protege de verdade sao estas
--   regras. Guarde as senhas com cuidado e nao deixe o painel logado em
--   computador de terceiros.
-- =====================================================================
