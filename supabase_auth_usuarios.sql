-- Centralização de usuários do Painel Servidor
-- Execute no SQL Editor do Supabase depois de revisar os nomes dos usuários.
-- As senhas NÃO ficam nesta tabela; ficam no Supabase Auth.

create table if not exists public.usuarios_perfis (
  id uuid primary key references auth.users(id) on delete cascade,
  usuario text not null unique,
  nome text not null,
  perfil text not null default 'visitante'
    check (perfil in ('visitante', 'editor', 'admin')),
  ativo boolean not null default true,
  criado_em timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);

create index if not exists usuarios_perfis_usuario_idx
  on public.usuarios_perfis (lower(usuario));

create or replace function public.atualizar_usuarios_perfis_timestamp()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
  new.atualizado_em = now();
  return new;
end;
$$;

drop trigger if exists usuarios_perfis_timestamp on public.usuarios_perfis;
create trigger usuarios_perfis_timestamp
before update on public.usuarios_perfis
for each row execute function public.atualizar_usuarios_perfis_timestamp();

-- Cria o perfil quando um usuário é criado pelo Supabase Auth.
create or replace function public.criar_perfil_usuario_auth()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_usuario text;
  v_nome text;
begin
  v_usuario := coalesce(
    nullif(new.raw_user_meta_data->>'usuario', ''),
    split_part(new.email, '@', 1)
  );
  v_nome := coalesce(
    nullif(new.raw_user_meta_data->>'nome', ''),
    v_usuario
  );
  insert into public.usuarios_perfis (id, usuario, nome, perfil)
  values (new.id, lower(v_usuario), v_nome, 'visitante')
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists criar_perfil_usuario_auth on auth.users;
create trigger criar_perfil_usuario_auth
after insert on auth.users
for each row execute function public.criar_perfil_usuario_auth();

create or replace function public.usuario_perfil_atual()
returns text
language sql
stable
security definer
set search_path = public
as $$
  select p.perfil
  from public.usuarios_perfis p
  where p.id = auth.uid() and p.ativo = true
  limit 1;
$$;

create or replace function public.usuario_e_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select coalesce(public.usuario_perfil_atual() = 'admin', false);
$$;

alter table public.usuarios_perfis enable row level security;

-- Usuário autenticado consulta o próprio perfil.
drop policy if exists usuarios_perfis_select_proprio on public.usuarios_perfis;
create policy usuarios_perfis_select_proprio
on public.usuarios_perfis for select to authenticated
using (id = auth.uid() or public.usuario_e_admin());

-- Usuário pode atualizar apenas seu nome; administradores podem atualizar perfis.
drop policy if exists usuarios_perfis_update on public.usuarios_perfis;
create policy usuarios_perfis_update
on public.usuarios_perfis for update to authenticated
using (id = auth.uid() or public.usuario_e_admin())
with check (
  (id = auth.uid() and perfil = public.usuario_perfil_atual())
  or public.usuario_e_admin()
);

-- Somente administrador pode inserir perfis manualmente.
drop policy if exists usuarios_perfis_insert_admin on public.usuarios_perfis;
create policy usuarios_perfis_insert_admin
on public.usuarios_perfis for insert to authenticated
with check (public.usuario_e_admin());

-- Somente administrador pode remover perfis. A proteção contra último admin deve ser feita também na aplicação.
drop policy if exists usuarios_perfis_delete_admin on public.usuarios_perfis;
create policy usuarios_perfis_delete_admin
on public.usuarios_perfis for delete to authenticated
using (public.usuario_e_admin());

grant select, update on public.usuarios_perfis to authenticated;
grant insert, delete on public.usuarios_perfis to authenticated;

grant execute on function public.usuario_perfil_atual() to authenticated;
grant execute on function public.usuario_e_admin() to authenticated;

comment on table public.usuarios_perfis is
  'Perfil e permissões do painel; credenciais ficam exclusivamente no Supabase Auth.';
