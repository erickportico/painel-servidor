# Migração do login do Painel Servidor para o Supabase

## O que foi preparado

O pacote contém `supabase_auth_usuarios.sql`, que cria a tabela `public.usuarios_perfis`, o gatilho de criação de perfil, as funções de verificação administrativa e as políticas RLS. O arquivo `supabase_auth_client.js` usa o Supabase Auth para login por e-mail e senha, consulta o perfil centralizado, observa a sessão e verifica o administrador.

As senhas não são gravadas na tabela pública, no `index.html`, no GitHub ou no arquivo `dados_painel.json`. Elas ficam sob responsabilidade do Supabase Auth.

## Ordem de implantação

1. No Supabase, abra **SQL Editor**, revise `supabase_auth_usuarios.sql` e execute o conteúdo.
2. No Supabase, abra **Authentication > Users** e crie o primeiro usuário administrador com um e-mail real e uma senha temporária forte.
3. Copie o UUID desse usuário e execute no SQL Editor, substituindo os valores:

```sql
insert into public.usuarios_perfis (id, usuario, nome, perfil, ativo)
values ('UUID_DO_PRIMEIRO_ADMIN', 'admin', 'Administrador', 'admin', true)
on conflict (id) do update set perfil = 'admin', ativo = true;
```

4. Crie os demais usuários em **Authentication > Users**. Cada usuário precisa de um e-mail individual. Depois insira seus perfis:

```sql
insert into public.usuarios_perfis (id, usuario, nome, perfil, ativo)
values
  ('UUID_MARDEN', 'marden', 'Marden Oliveira', 'editor', true),
  ('UUID_ERICK_SANTOS', 'erick_santos', 'Erick Santos', 'editor', true),
  ('UUID_ERICK', 'erick', 'Erick', 'editor', true)
on conflict (id) do update set nome = excluded.nome, perfil = excluded.perfil, ativo = true;
```

Use os UUIDs reais fornecidos pelo Supabase. Não invente UUIDs e não coloque senhas nesse arquivo.

5. Hospede `supabase_auth_client.js` junto com o painel e integre a tela de login para chamar `PainelAuthSupabase.entrarComEmail(email, senha)`. A sessão deve ser recuperada com `PainelAuthSupabase.sessaoAtual()` ao carregar o painel.
6. No cadastro de usuários, somente um perfil `admin` deve chamar `cadastrarComEmail`. A senha será processada pelo Supabase Auth; o formulário não deve gravá-la em `localStorage`.
7. Teste com dois computadores: login simultâneo, cadastro de um usuário pelo administrador, logout, recarga e tentativa de acesso por usuário `visitante`, `editor` e `admin`.
8. Só depois de confirmar os testes, remova gradualmente o login local. Mantenha a lista local como fallback temporário durante a migração, mas não permita que ela substitua um usuário centralizado já autenticado.

## Observações importantes

O arquivo SQL deve ser executado no projeto Supabase correto. A política RLS permite que o usuário consulte seu próprio perfil e que administradores gerenciem perfis. O primeiro administrador precisa ser criado pelo painel do Supabase ou por SQL administrativo, pois ainda não existe um administrador para autorizar o primeiro cadastro.

Essa integração ainda não deve ser publicada como se estivesse pronta para produção sem adaptar a tela de login existente. O painel atual foi construído em HTML com várias rotinas locais; a troca automática de todas as funções de login exigiria substituir com cuidado os handlers atuais, mantendo os dados das obras e a senha administrativa compatíveis.
