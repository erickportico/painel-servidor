/* Cliente centralizado de autenticação do Painel Servidor.
 * Usa somente a chave pública/anon do Supabase. Nunca coloque service_role key no navegador.
 */
(function (global) {
  'use strict';

  function client() {
    var sb = global._supabase;
    if (!sb || !sb.auth || !sb.from) {
      throw new Error('Cliente Supabase não inicializado.');
    }
    return sb;
  }

  function sincronizarSessaoPainel(resultado) {
    if (!resultado || !resultado.user || !resultado.perfil) { return; }
    var perfil = resultado.perfil;
    var usuario = resultado.user;
    var sessao = {
      usuario: perfil.usuario,
      nome: perfil.nome || perfil.usuario,
      perfil: String(perfil.perfil || 'visitante').toLowerCase(),
      authId: usuario.id,
      at: Date.now()
    };
    var valor = JSON.stringify(sessao);
    try { global.localStorage.setItem('painel_seg_sessao_v1', valor); } catch (e) {}
    try { global.sessionStorage.setItem('painel_seg_sessao_v1', valor); } catch (e) {}
  }

  async function entrarComEmail(email, senha) {
    var result = await client().auth.signInWithPassword({
      email: String(email || '').trim().toLowerCase(),
      password: String(senha || '')
    });
    if (result.error) { throw result.error; }
    var autenticado = await perfilAtual(result.data.user);
    sincronizarSessaoPainel(autenticado);
    return autenticado;
  }

  async function cadastrarComEmail(email, senha, nome, usuario, perfil) {
    var result = await client().auth.signUp({
      email: String(email || '').trim().toLowerCase(),
      password: String(senha || ''),
      options: { data: { nome: String(nome || '').trim(), usuario: String(usuario || '').trim().toLowerCase() } }
    });
    if (result.error) { throw result.error; }
    if (result.data.user && result.data.session) {
      await client().from('usuarios_perfis').upsert({
        id: result.data.user.id,
        nome: String(nome || '').trim(),
        usuario: String(usuario || '').trim().toLowerCase(),
        perfil: perfil === 'admin' || perfil === 'editor' ? perfil : 'visitante',
        ativo: true
      }, { onConflict: 'id' });
    }
    return result.data;
  }

  async function perfilAtual(userOpcional) {
    var user = userOpcional;
    if (!user) {
      var sessao = await client().auth.getSession();
      if (sessao.error) { throw sessao.error; }
      user = sessao.data.session && sessao.data.session.user;
    }
    if (!user) { return null; }
    var result = await client().from('usuarios_perfis')
      .select('id,usuario,nome,perfil,ativo,criado_em,atualizado_em')
      .eq('id', user.id).maybeSingle();
    if (result.error) { throw result.error; }
    if (!result.data || result.data.ativo !== true) {
      await client().auth.signOut();
      throw new Error('Usuário sem perfil ativo no painel.');
    }
    var resultado = { user: user, perfil: result.data };
    sincronizarSessaoPainel(resultado);
    return resultado;
  }

  async function sessaoAtual() {
    return await perfilAtual();
  }

  async function sair() {
    var result = await client().auth.signOut();
    if (result.error) { throw result.error; }
    try { global.localStorage.removeItem('painel_seg_sessao_v1'); } catch (e) {}
    try { global.sessionStorage.removeItem('painel_seg_sessao_v1'); } catch (e) {}
  }

  function observarSessao(callback) {
    return client().auth.onAuthStateChange(function (event, session) {
      try { callback(event, session); } catch (e) { setTimeout(function () { throw e; }, 0); }
    });
  }

  async function somenteAdmin() {
    var atual = await perfilAtual();
    return !!(atual && atual.perfil && atual.perfil.perfil === 'admin');
  }

  global.PainelAuthSupabase = {
    entrarComEmail: entrarComEmail,
    cadastrarComEmail: cadastrarComEmail,
    perfilAtual: perfilAtual,
    sessaoAtual: sessaoAtual,
    observarSessao: observarSessao,
    somenteAdmin: somenteAdmin,
    sair: sair
  };
})(window);
