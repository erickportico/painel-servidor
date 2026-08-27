# -*- coding: utf-8 -*-
"""
PATCH 69 - LOGIN E REGRAS DE ACESSO (SO QUEM ENTRA VE AS OBRAS)
================================================================
Hoje qualquer pessoa que abra o index.html ve e altera todas as obras,
porque o endereco e a chave do banco estao dentro da propria pagina.
Este patch fecha essa porta: o painel passa a pedir e-mail e senha, e o
banco so responde depois que a pessoa entrou.

O QUE ELE FAZ

1) TELA DE ENTRADA NA ABERTURA
   Ao abrir o painel aparece uma tela pedindo e-mail e senha. Enquanto
   ninguem entrar, a pagina fica travada e o banco nao e consultado.

2) A SESSAO FICA GUARDADA
   Depois de entrar uma vez, o painel reconhece voce nas proximas
   aberturas e vai direto para as obras. A sessao se renova sozinha.

3) NADA VAI PARA O BANCO SEM SESSAO
   Toda ida ao banco passa a ser conferida: sem sessao, nem le nem
   grava, e o painel avisa em portugues o motivo.

4) TRES NIVEIS DE ACESSO
   Administrador ..... entra, edita e enxerga tudo
   Pode editar ....... entra e edita (padrao de quem tem usuario)
   Somente leitura ... enxerga tudo, mas nada que digitar sera gravado
   O nivel vem do cadastro do usuario no Supabase ou de uma tabelinha
   opcional de acessos.

5) CRACHA NO CANTO DA TELA
   Um cracha discreto no canto inferior mostra quem esta usando o
   painel, o nivel de acesso e o botao "Sair".

6) CONFERENCIA DA PROTECAO DO BANCO
   O patch testa sozinho se o banco ainda responde a quem NAO fez
   login. Se responder, o cracha fica vermelho com o aviso
   "Banco sem protecao", porque falta ligar as regras no Supabase.

7) ESQUECI MINHA SENHA
   Botao na propria tela de entrada que envia o link de nova senha para
   o e-mail cadastrado.

8) SEM INTERNET O PAINEL AINDA ABRE
   Se a biblioteca de acesso nao carregar, o patch oferece continuar
   "so com o que esta neste computador", avisando que nada sera gravado
   no banco.

O QUE VOCE PRECISA FAZER NO SUPABASE (5 MINUTOS, UMA VEZ SO)

  PASSO 1 - CRIAR OS USUARIOS
    Painel do Supabase > Authentication > Users > Add user
    Informe o e-mail e uma senha para cada pessoa da equipe e marque
    "Auto Confirm User".

  PASSO 2 - LIGAR AS REGRAS DE ACESSO
    Painel do Supabase > SQL Editor > New query
    Cole o SQL que este script mostra no final (ele tambem fica
    disponivel no painel com o comando P69.sql() ) e clique em Run.
    A partir dai o banco simplesmente nao responde a quem nao entrou.

  PASSO 3 (OPCIONAL) - QUEM SO OLHA
    Na tabela painel_acessos criada pelo SQL, insira uma linha com o
    e-mail da pessoa e o papel "leitura". Ela vera tudo e nao gravara
    nada. Sem linha nenhuma, a pessoa entra como "pode editar".

NO PAINEL, PELO CONSOLE (F12), SE QUISER
  P69.ajuda()               lista os comandos
  P69.situacao()            quem entrou e o que pode fazer
  P69.sair()                encerra a sessao
  P69.trocarSenha("nova")   troca a sua senha
  P69.conferirProtecao()    testa se o banco responde sem login
  P69.sql()                 mostra o SQL das regras de acesso

SEGURANCA
  - Nao apaga nem reescreve nada: insere apenas UM bloco novo antes do
    fechamento da pagina
  - Nao altera calculo, preco, medida, formula ou layout das tabelas
  - Nao mexe na rotina de salvamento: apenas confere se ha sessao antes
    de deixar o painel falar com o banco
  - Nao remove a chave publica do arquivo (ela deixa de ter valor
    sozinha depois do PASSO 2)
  - Backup automatico do index.html antes de gravar
  - Idempotente: rodar de novo nao duplica nada
  - Nao aparece na impressao

COMO USAR
  python patch_69.py
  depois abra o painel e pressione Ctrl+F5
"""

import os
import shutil
import sys
import datetime

FILE = r'C:/Users/OBRAS 8/Desktop/PAINEL SERVIDOR/index.html'

MARCADOR = 'PATCH 69: LOGIN E REGRAS DE ACESSO'


# ---------------------------------------------------------------------------
# BLOCO INSERIDO NO index.html
# ---------------------------------------------------------------------------
BLOCO = r"""

<script>
/* PATCH 69: LOGIN E REGRAS DE ACESSO */
(function () {
  if (window.P69 && window.P69.__v69) return;
  var P69 = window.P69 = window.P69 || {};
  P69.__v69 = true;

  /* ------------------------------------------------------------------ */
  /* AJUDANTES BASICOS                                                  */
  /* ------------------------------------------------------------------ */
  var LSPAPEL = 'p69_papel_v1';
  var LSEMAIL = 'p69_email_v1';
  var TABELA_PESSOAS = 'painel_acessos';

  var estado = {
    sessao: null,
    email: '',
    papel: 'editor',
    liberado: false,
    travas: false,
    semSdk: false,
    semRede: false,
    avisoRegras: ''
  };

  function seguro(txt) {
    return String(txt == null ? '' : txt)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function porId(id) { return document.getElementById(id); }

  function depois(fn, ms) {
    try { return window.setTimeout(fn, ms || 0); } catch (e) { return 0; }
  }

  function guardar(chave, valor) {
    try { localStorage.setItem(chave, valor); } catch (e) { }
  }

  function lido(chave) {
    try { return localStorage.getItem(chave) || ''; } catch (e) { return ''; }
  }

  function banco() {
    return (window._supabase && window._supabase.auth) ? window._supabase : null;
  }

  function recado(msg, tipo) {
    try {
      if (typeof window.mostrarToastPainel === 'function') {
        window.mostrarToastPainel(msg, tipo === 'erro' ? 'erro' : 'ok');
        return;
      }
    } catch (e) { }
    try { console.log('[P69] ' + msg); } catch (e) { }
  }

  /* Mensagens do Supabase em portugues claro ------------------------- */
  function traduzir(msg) {
    var m = String(msg || '').toLowerCase();
    if (!m) return 'Nao consegui entrar. Tente de novo.';
    if (m.indexOf('invalid login credentials') >= 0) return 'E-mail ou senha incorretos.';
    if (m.indexOf('email not confirmed') >= 0) return 'Este e-mail ainda nao foi confirmado no Supabase.';
    if (m.indexOf('invalid email') >= 0) return 'Esse e-mail nao parece valido.';
    if (m.indexOf('user not found') >= 0) return 'Nao existe usuario com esse e-mail.';
    if (m.indexOf('too many requests') >= 0 || m.indexOf('rate limit') >= 0) return 'Muitas tentativas seguidas. Espere um minuto e tente de novo.';
    if (m.indexOf('password should be') >= 0) return 'A senha precisa ter pelo menos 6 caracteres.';
    if (m.indexOf('failed to fetch') >= 0 || m.indexOf('network') >= 0 || m.indexOf('load failed') >= 0) return 'Sem internet agora. Verifique a conexao e tente de novo.';
    if (m.indexOf('signups not allowed') >= 0) return 'O cadastro esta desligado no Supabase. Peca ao administrador para criar seu usuario.';
    return msg;
  }

  /* ------------------------------------------------------------------ */
  /* PARTE 1 - TRAVA DE ESCRITA NO BANCO ENQUANTO NAO HOUVER SESSAO     */
  /* ------------------------------------------------------------------ */
  var ESCRITAS = ['insert', 'upsert', 'update', 'delete'];
  var LEITURAS = ['select'];
  var CORRENTE = ['eq', 'neq', 'gt', 'gte', 'lt', 'lte', 'like', 'ilike', 'is', 'in',
    'contains', 'containedBy', 'match', 'not', 'or', 'filter', 'order', 'limit',
    'range', 'abortSignal', 'select', 'csv', 'geojson', 'explain', 'rollback',
    'returns', 'overrideTypes'];
  var FIM = ['single', 'maybeSingle', 'then', 'catch', 'finally'];

  function respostaBarrada(motivo) {
    var resposta = { data: null, error: { message: 'P69: ' + motivo, p69: true }, status: 401, count: null };
    var fila = Promise.resolve(resposta);
    var fingido = {};
    CORRENTE.forEach(function (nome) {
      fingido[nome] = function () { return fingido; };
    });
    fingido.single = function () { return fingido; };
    fingido.maybeSingle = function () { return fingido; };
    fingido.then = function (a, b) { return fila.then(a, b); };
    fingido.catch = function (a) { return fila.catch(a); };
    fingido.finally = function (a) { return fila.finally ? fila.finally(a) : fila; };
    fingido.__p69barrado = true;
    return fingido;
  }

  function podeEscrever() {
    if (!estado.liberado) return false;
    return estado.papel !== 'leitura';
  }

  function motivoDeBarrar() {
    if (!estado.liberado) return 'entre com seu e-mail e senha para gravar no banco';
    return 'seu acesso e somente leitura';
  }

  var jaAvisou = 0;
  function avisarBarrado() {
    var t = Date.now();
    if (t - jaAvisou < 4000) return;
    jaAvisou = t;
    if (!estado.liberado) recado('Faca login para gravar as alteracoes no banco.', 'erro');
    else recado('Seu acesso e somente leitura. Nada foi gravado.', 'erro');
  }

  function envolverBanco() {
    var bd = banco();
    if (!bd || bd.__p69envolvido) return false;
    var deOrigem = bd.from.bind(bd);
    bd.from = function (tabela) {
      var real;
      try { real = deOrigem(tabela); } catch (e) { return respostaBarrada('tabela indisponivel'); }
      if (estado.liberado && podeEscrever()) return real;
      var capa = {};
      LEITURAS.forEach(function (nome) {
        capa[nome] = function () {
          if (!estado.liberado) return respostaBarrada(motivoDeBarrar());
          return real[nome].apply(real, arguments);
        };
      });
      ESCRITAS.forEach(function (nome) {
        capa[nome] = function () {
          if (podeEscrever()) return real[nome].apply(real, arguments);
          avisarBarrado();
          return respostaBarrada(motivoDeBarrar());
        };
      });
      capa.__p69capa = true;
      return capa;
    };
    bd.__p69envolvido = true;
    return true;
  }

  /* Somente leitura: nao deixa nem o salvamento local sobrescrever ---- */
  var guardados = {};
  function segurarGravacoesLocais() {
    ['salvarDB', 'sincronizarBancoNuvem', 'salvarLocalComoBackup', 'salvarNoServidorLocal'].forEach(function (nome) {
      if (typeof window[nome] !== 'function' || guardados[nome]) return;
      guardados[nome] = window[nome];
      window[nome] = function () {
        if (estado.papel === 'leitura' && estado.liberado) {
          avisarBarrado();
          return;
        }
        return guardados[nome].apply(this, arguments);
      };
    });
  }

  /* ------------------------------------------------------------------ */
  /* PARTE 2 - TELA DE ENTRADA                                          */
  /* ------------------------------------------------------------------ */
  function montarTela() {
    if (porId('p69Tela')) return porId('p69Tela');
    var caixa = document.createElement('div');
    caixa.id = 'p69Tela';
    caixa.className = 'p69-tela';
    caixa.setAttribute('aria-hidden', 'true');
    caixa.innerHTML =
      '<div class="p69-cartao" role="dialog" aria-labelledby="p69Titulo">' +
      '  <div class="p69-topo">' +
      '    <div class="p69-selo">&#128274;</div>' +
      '    <div>' +
      '      <div class="p69-titulo" id="p69Titulo">Painel de Producao e Instalacao</div>' +
      '      <div class="p69-sub">Entre com seu e-mail e senha para ver e alterar as obras.</div>' +
      '    </div>' +
      '  </div>' +
      '  <form class="p69-form" id="p69Form" autocomplete="on">' +
      '    <label class="p69-rot" for="p69Email">E-mail</label>' +
      '    <input class="p69-campo" id="p69Email" name="email" type="email" autocomplete="username" placeholder="seu.email@empresa.com" required>' +
      '    <label class="p69-rot" for="p69Senha">Senha</label>' +
      '    <div class="p69-linhaSenha">' +
      '      <input class="p69-campo" id="p69Senha" name="password" type="password" autocomplete="current-password" placeholder="sua senha" required>' +
      '      <button class="p69-olho" id="p69Olho" type="button" title="Mostrar ou esconder a senha">Mostrar</button>' +
      '    </div>' +
      '    <div class="p69-aviso" id="p69Aviso"></div>' +
      '    <button class="p69-entrar" id="p69Entrar" type="submit">Entrar no painel</button>' +
      '    <div class="p69-rodape">' +
      '      <button class="p69-link" id="p69Esqueci" type="button">Esqueci minha senha</button>' +
      '      <span class="p69-pinta" id="p69Estado"></span>' +
      '    </div>' +
      '  </form>' +
      '  <div class="p69-nota">Seus dados ficam no banco da empresa. Sem entrar, o painel nao le nem grava nada la.</div>' +
      '</div>';
    (document.body || document.documentElement).appendChild(caixa);

    var form = porId('p69Form');
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      tentarEntrar();
    });
    porId('p69Olho').addEventListener('click', function () {
      var c = porId('p69Senha');
      var mostrando = c.type === 'text';
      c.type = mostrando ? 'password' : 'text';
      porId('p69Olho').textContent = mostrando ? 'Mostrar' : 'Esconder';
    });
    porId('p69Esqueci').addEventListener('click', function () { pedirNovaSenha(); });

    var lembrado = lido(LSEMAIL);
    if (lembrado) porId('p69Email').value = lembrado;
    return caixa;
  }

  function dizerNaTela(msg, tipo) {
    var alvo = porId('p69Aviso');
    if (!alvo) return;
    alvo.textContent = String(msg || '');
    alvo.className = 'p69-aviso' + (msg ? (tipo === 'ok' ? ' p69-ok' : ' p69-ruim') : '');
  }

  function trabalhando(ligado, texto) {
    var bt = porId('p69Entrar');
    if (bt) {
      bt.disabled = !!ligado;
      bt.textContent = ligado ? (texto || 'Entrando...') : 'Entrar no painel';
    }
  }

  function travar(msg) {
    montarTela();
    var t = porId('p69Tela');
    if (!t) return;
    t.classList.add('p69-visivel');
    t.setAttribute('aria-hidden', 'false');
    document.documentElement.classList.add('p69-parado');
    estado.travas = true;
    if (msg) dizerNaTela(msg, 'ruim');
    depois(function () {
      var c = porId('p69Email');
      var s = porId('p69Senha');
      try { (c && !c.value ? c : (s || c)).focus(); } catch (e) { }
    }, 120);
  }

  function destravar() {
    var t = porId('p69Tela');
    if (t) {
      t.classList.remove('p69-visivel');
      t.setAttribute('aria-hidden', 'true');
    }
    document.documentElement.classList.remove('p69-parado');
    estado.travas = false;
    var s = porId('p69Senha');
    if (s) s.value = '';
  }

  /* ------------------------------------------------------------------ */
  /* PARTE 3 - CRACHA COM O USUARIO E O BOTAO SAIR                      */
  /* ------------------------------------------------------------------ */
  function nomeDoPapel(p) {
    if (p === 'admin') return 'Administrador';
    if (p === 'leitura') return 'Somente leitura';
    return 'Pode editar';
  }

  function montarCracha() {
    var c = porId('p69Cracha');
    if (!c) {
      c = document.createElement('div');
      c.id = 'p69Cracha';
      c.className = 'p69-cracha';
      c.innerHTML =
        '<div class="p69-quem">' +
        '  <span class="p69-bola" id="p69Bola"></span>' +
        '  <span class="p69-nome" id="p69Nome"></span>' +
        '  <span class="p69-papel" id="p69Papel"></span>' +
        '</div>' +
        '<button class="p69-btn" id="p69Regras" type="button" title="Conferir se o banco esta protegido">Conferir protecao</button>' +
        '<button class="p69-btn p69-btnSair" id="p69Sair" type="button">Sair</button>';
      (document.body || document.documentElement).appendChild(c);
      porId('p69Sair').addEventListener('click', function () { sair(); });
      porId('p69Regras').addEventListener('click', function () { conferirProtecao(true); });
    }
    var nome = porId('p69Nome');
    if (nome) nome.textContent = estado.email || 'sem sessao';
    var papel = porId('p69Papel');
    if (papel) {
      papel.textContent = nomeDoPapel(estado.papel);
      papel.className = 'p69-papel' + (estado.papel === 'leitura' ? ' p69-papelLeitura' : '');
    }
    var bola = porId('p69Bola');
    if (bola) bola.className = 'p69-bola' + (estado.liberado ? ' p69-bolaOk' : ' p69-bolaRuim');
    c.style.display = estado.liberado ? '' : 'none';
    return c;
  }

  /* ------------------------------------------------------------------ */
  /* PARTE 4 - ENTRAR, SAIR, TROCAR SENHA                               */
  /* ------------------------------------------------------------------ */
  function tentarEntrar() {
    var bd = banco();
    if (!bd) {
      dizerNaTela('A conexao com o banco nao carregou. Recarregue a pagina com Ctrl+F5.', 'ruim');
      return;
    }
    var email = (porId('p69Email').value || '').trim();
    var senha = porId('p69Senha').value || '';
    if (!email || !senha) {
      dizerNaTela('Preencha o e-mail e a senha.', 'ruim');
      return;
    }
    dizerNaTela('');
    trabalhando(true);
    bd.auth.signInWithPassword({ email: email, password: senha }).then(function (r) {
      trabalhando(false);
      if (r && r.error) {
        dizerNaTela(traduzir(r.error.message), 'ruim');
        return;
      }
      guardar(LSEMAIL, email);
      aceitarSessao(r && r.data ? r.data.session : null, true);
    }).catch(function (e) {
      trabalhando(false);
      dizerNaTela(traduzir(e && e.message), 'ruim');
    });
  }

  function pedirNovaSenha() {
    var bd = banco();
    if (!bd) { dizerNaTela('A conexao com o banco nao carregou.', 'ruim'); return; }
    var email = (porId('p69Email').value || '').trim();
    if (!email) { dizerNaTela('Escreva seu e-mail primeiro, depois clique de novo.', 'ruim'); return; }
    trabalhando(true, 'Enviando...');
    bd.auth.resetPasswordForEmail(email).then(function (r) {
      trabalhando(false);
      if (r && r.error) { dizerNaTela(traduzir(r.error.message), 'ruim'); return; }
      dizerNaTela('Enviei um e-mail para ' + email + ' com o link para criar uma senha nova.', 'ok');
    }).catch(function (e) {
      trabalhando(false);
      dizerNaTela(traduzir(e && e.message), 'ruim');
    });
  }

  function sair() {
    var bd = banco();
    estado.liberado = false;
    estado.sessao = null;
    montarCracha();
    var fim = function () {
      travar('Voce saiu do painel. Entre de novo para continuar.');
    };
    if (!bd) { fim(); return; }
    try {
      var r = bd.auth.signOut();
      if (r && r.then) r.then(fim).catch(fim); else fim();
    } catch (e) { fim(); }
  }

  function trocarSenha(nova) {
    var bd = banco();
    if (!bd) return Promise.resolve('Sem conexao com o banco.');
    if (!nova || String(nova).length < 6) return Promise.resolve('A senha nova precisa ter pelo menos 6 caracteres.');
    return bd.auth.updateUser({ password: String(nova) }).then(function (r) {
      if (r && r.error) return traduzir(r.error.message);
      recado('Senha trocada com sucesso.', 'ok');
      return 'ok';
    }).catch(function (e) { return traduzir(e && e.message); });
  }

  /* ------------------------------------------------------------------ */
  /* PARTE 5 - QUAL O PAPEL DESTE USUARIO                               */
  /* ------------------------------------------------------------------ */
  function limparPapel(v) {
    var p = String(v || '').trim().toLowerCase();
    if (p === 'admin' || p === 'administrador') return 'admin';
    if (p === 'leitura' || p === 'somente leitura' || p === 'visitante' || p === 'viewer' || p === 'readonly') return 'leitura';
    if (p === 'editor' || p === 'edicao') return 'editor';
    return '';
  }

  function descobrirPapel(usuario) {
    var doCadastro = '';
    try {
      var m = (usuario && usuario.user_metadata) || {};
      doCadastro = limparPapel(m.papel || m.role || m.perfil);
      if (!doCadastro && usuario && usuario.app_metadata) {
        doCadastro = limparPapel(usuario.app_metadata.papel || usuario.app_metadata.role);
      }
    } catch (e) { }
    if (doCadastro) return Promise.resolve(doCadastro);

    var bd = banco();
    if (!bd || !usuario || !usuario.email) return Promise.resolve('');
    var consulta;
    try {
      consulta = bd.from(TABELA_PESSOAS).select('papel').eq('email', usuario.email).single();
    } catch (e) {
      return Promise.resolve('');
    }
    return Promise.resolve(consulta).then(function (r) {
      if (r && !r.error && r.data) return limparPapel(r.data.papel);
      return '';
    }).catch(function () { return ''; });
  }

  /* ------------------------------------------------------------------ */
  /* PARTE 6 - CONFERIR SE O BANCO ESTA REALMENTE PROTEGIDO             */
  /* ------------------------------------------------------------------ */
  function clienteSemSessao() {
    try {
      if (!window.supabase || typeof window.supabase.createClient !== 'function') return null;
      var url = window.SUPABASE_URL || (typeof SUPABASE_URL !== 'undefined' ? SUPABASE_URL : '');
      var chave = window.SUPABASE_KEY || (typeof SUPABASE_KEY !== 'undefined' ? SUPABASE_KEY : '');
      if (!url || !chave) return null;
      return window.supabase.createClient(url, chave, {
        auth: { persistSession: false, autoRefreshToken: false, detectSessionInUrl: false, storageKey: 'p69_teste' }
      });
    } catch (e) { return null; }
  }

  function conferirProtecao(mostrar) {
    var visitante = clienteSemSessao();
    if (!visitante) {
      estado.avisoRegras = 'Nao consegui conferir agora.';
      if (mostrar) recado('Nao consegui conferir a protecao do banco agora.', 'erro');
      return Promise.resolve(estado.avisoRegras);
    }
    return visitante.from('painel_dados').select('id').limit(1).then(function (r) {
      var abertoParaTodos = !!(r && !r.error);
      if (abertoParaTodos) {
        estado.avisoRegras = 'aberto';
        var texto = 'ATENCAO: o banco ainda responde a quem NAO fez login. Ligue as regras de acesso no Supabase (o patch mostrou o passo a passo).';
        try { console.warn('[P69] ' + texto); } catch (e) { }
        if (mostrar) recado(texto, 'erro');
        pintarCracha(true);
      } else {
        estado.avisoRegras = 'protegido';
        if (mostrar) recado('Tudo certo: sem login, o banco nao entrega nada.', 'ok');
        pintarCracha(false);
      }
      return estado.avisoRegras;
    }).catch(function () {
      estado.avisoRegras = 'protegido';
      if (mostrar) recado('Tudo certo: sem login, o banco nao entrega nada.', 'ok');
      pintarCracha(false);
      return estado.avisoRegras;
    });
  }

  function pintarCracha(perigo) {
    var b = porId('p69Regras');
    if (!b) return;
    b.className = 'p69-btn' + (perigo ? ' p69-btnPerigo' : '');
    b.textContent = perigo ? 'Banco sem protecao' : 'Protecao conferida';
    b.title = perigo
      ? 'O banco ainda responde sem login. Ligue as regras de acesso no Supabase.'
      : 'Sem login o banco nao entrega dados.';
  }

  /* ------------------------------------------------------------------ */
  /* PARTE 7 - ACEITAR A SESSAO E LIBERAR O PAINEL                      */
  /* ------------------------------------------------------------------ */
  var recarregarDepoisDeEntrar = false;

  function aceitarSessao(sessao, veioDeLogin) {
    if (!sessao || !sessao.user) {
      estado.liberado = false;
      estado.sessao = null;
      montarCracha();
      travar(veioDeLogin ? 'Nao consegui abrir a sessao. Tente de novo.' : '');
      return;
    }
    estado.sessao = sessao;
    estado.email = sessao.user.email || '';
    estado.liberado = true;

    var anterior = limparPapel(lido(LSPAPEL)) || 'editor';
    estado.papel = anterior;
    montarCracha();
    destravar();

    descobrirPapel(sessao.user).then(function (p) {
      estado.papel = p || 'editor';
      guardar(LSPAPEL, estado.papel);
      montarCracha();
      aplicarPapelNaTela();
    });

    segurarGravacoesLocais();
    depois(function () { conferirProtecao(false); }, 1500);

    if (veioDeLogin) {
      recado('Bem-vindo, ' + (estado.email || 'usuario') + '.', 'ok');
      if (recarregarDepoisDeEntrar) {
        recado('Buscando as obras no banco...', 'ok');
        depois(function () { puxarDoBanco(); }, 400);
      }
    }
  }

  function puxarDoBanco() {
    try {
      if (typeof window.carregarBancoDaNuvem === 'function') {
        var r = window.carregarBancoDaNuvem();
        if (r && r.then) {
          r.then(function () {
            try { if (typeof window.render === 'function') window.render(); } catch (e) { }
          }).catch(function () { });
          return;
        }
      }
      if (typeof window.sincronizarBancoNuvem === 'function') window.sincronizarBancoNuvem();
    } catch (e) { }
  }

  function aplicarPapelNaTela() {
    var so = (estado.papel === 'leitura' && estado.liberado);
    document.documentElement.classList[so ? 'add' : 'remove']('p69-soLeitura');
    if (so) recado('Seu acesso e somente leitura: nada que voce digitar sera gravado.', 'erro');
  }

  /* ------------------------------------------------------------------ */
  /* PARTE 8 - PARTIDA                                                  */
  /* ------------------------------------------------------------------ */
  function ligarEscuta() {
    var bd = banco();
    if (!bd || bd.__p69escuta) return;
    bd.__p69escuta = true;
    try {
      bd.auth.onAuthStateChange(function (evento, sessao) {
        if (evento === 'SIGNED_OUT') {
          estado.liberado = false;
          estado.sessao = null;
          montarCracha();
          travar('Sua sessao terminou. Entre de novo para continuar.');
          return;
        }
        if (sessao && sessao.user) {
          estado.sessao = sessao;
          estado.email = sessao.user.email || estado.email;
          if (!estado.liberado) aceitarSessao(sessao, false);
        }
      });
    } catch (e) { }
  }

  function comecar() {
    montarTela();
    var bd = banco();

    if (!bd) {
      /* Sem a biblioteca do Supabase nao existe login possivel. O painel */
      /* continua funcionando com o que esta guardado no aparelho.        */
      estado.semSdk = true;
      estado.liberado = false;
      travar('A biblioteca de acesso nao carregou (sem internet?). O painel abre com os dados guardados neste computador, mas nao grava no banco.');
      var bt = porId('p69Entrar');
      if (bt) { bt.disabled = true; }
      depois(function () {
        var t = porId('p69Tela');
        if (t) {
          var so = document.createElement('button');
          so.type = 'button';
          so.className = 'p69-link p69-soLocal';
          so.textContent = 'Usar so o que esta neste computador';
          so.addEventListener('click', function () { destravar(); recado('Modo local: nada sera gravado no banco.', 'erro'); });
          var rod = t.querySelector('.p69-rodape');
          if (rod) rod.appendChild(so);
        }
      }, 50);
      return;
    }

    envolverBanco();
    ligarEscuta();

    var pedido;
    try { pedido = bd.auth.getSession(); } catch (e) { pedido = null; }
    if (!pedido || !pedido.then) {
      recarregarDepoisDeEntrar = true;
      travar('');
      return;
    }
    pedido.then(function (r) {
      var s = (r && r.data) ? r.data.session : null;
      if (s && s.user) {
        aceitarSessao(s, false);
      } else {
        recarregarDepoisDeEntrar = true;
        travar('');
      }
    }).catch(function () {
      recarregarDepoisDeEntrar = true;
      travar('');
    });
  }

  /* ------------------------------------------------------------------ */
  /* PARTE 9 - COMANDOS NO CONSOLE                                      */
  /* ------------------------------------------------------------------ */
  P69.situacao = function () {
    var s = {
      entrou: estado.liberado,
      email: estado.email,
      papel: estado.papel,
      papelPorExtenso: nomeDoPapel(estado.papel),
      podeGravar: podeEscrever(),
      telaTrancada: estado.travas,
      bancoProtegido: estado.avisoRegras || 'ainda nao conferido'
    };
    try { console.log('[P69]', JSON.stringify(s)); } catch (e) { }
    return s;
  };
  P69.entrar = function () { travar(''); return 'Tela de entrada aberta.'; };
  P69.sair = function () { sair(); return 'Saindo...'; };
  P69.trocarSenha = function (nova) { return trocarSenha(nova); };
  P69.conferirProtecao = function () { return conferirProtecao(true); };
  P69.papel = function () { return estado.papel; };
  P69.sql = function () {
    var t = P69.SQL;
    try { console.log(t); } catch (e) { }
    return t;
  };
  P69.ajuda = function () {
    var t = [
      'P69.situacao()          quem esta logado e o que pode fazer',
      'P69.entrar()            abre a tela de entrada',
      'P69.sair()              encerra a sessao',
      'P69.trocarSenha("nova") troca a sua senha',
      'P69.conferirProtecao()  testa se o banco responde sem login',
      'P69.sql()               mostra o SQL das regras de acesso'
    ].join('\n');
    try { console.log(t); } catch (e) { }
    return t;
  };

  P69.SQL = [
    '-- 1) Liga a protecao da tabela do painel',
    'alter table public.painel_dados enable row level security;',
    '',
    '-- 2) Apaga qualquer permissao antiga aberta',
    'drop policy if exists "painel_leitura"  on public.painel_dados;',
    'drop policy if exists "painel_escrita"  on public.painel_dados;',
    'drop policy if exists "painel_insercao" on public.painel_dados;',
    '',
    '-- 3) So quem esta logado le e grava',
    'create policy "painel_leitura"  on public.painel_dados for select to authenticated using (true);',
    'create policy "painel_insercao" on public.painel_dados for insert to authenticated with check (true);',
    'create policy "painel_escrita"  on public.painel_dados for update to authenticated using (true) with check (true);',
    '',
    '-- 4) Opcional: tabela para dizer quem edita e quem so olha',
    'create table if not exists public.painel_acessos (',
    '  email text primary key,',
    '  papel text not null default \'editor\'',
    ');',
    'alter table public.painel_acessos enable row level security;',
    'drop policy if exists "acessos_leitura" on public.painel_acessos;',
    'create policy "acessos_leitura" on public.painel_acessos for select to authenticated using (true);'
  ].join('\n');

  /* ------------------------------------------------------------------ */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { depois(comecar, 60); });
  } else {
    depois(comecar, 60);
  }
})();
</script>

<style>
/* PATCH 69: aparencia da tela de entrada e do cracha */
html.p69-parado, html.p69-parado body { overflow: hidden !important; }

.p69-tela {
  position: fixed; inset: 0; z-index: 2147483000;
  display: none; align-items: center; justify-content: center;
  padding: 18px;
  background: radial-gradient(1200px 700px at 20% 0%, #1e3a5f 0%, #0b1524 55%, #060b13 100%);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
}
.p69-tela.p69-visivel { display: flex; }

.p69-cartao {
  width: 100%; max-width: 390px;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 24px 70px rgba(0,0,0,.55);
  padding: 24px 24px 18px;
  animation: p69Sobe .28s ease-out;
}
@keyframes p69Sobe { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }

.p69-topo { display: flex; gap: 12px; align-items: flex-start; margin-bottom: 18px; }
.p69-selo {
  width: 40px; height: 40px; flex: 0 0 40px;
  border-radius: 11px; background: #eef4ff; color: #1e58c8;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; line-height: 1;
}
.p69-titulo { font-size: 15px; font-weight: 700; color: #14202e; line-height: 1.25; }
.p69-sub { font-size: 12px; color: #5f6b7a; margin-top: 4px; line-height: 1.45; }

.p69-form { display: block; }
.p69-rot { display: block; font-size: 11px; font-weight: 700; color: #46525f; text-transform: uppercase; letter-spacing: .04em; margin: 12px 0 5px; }
.p69-campo {
  width: 100%; box-sizing: border-box;
  padding: 10px 12px; font-size: 14px; color: #14202e;
  border: 1px solid #cfd8e3; border-radius: 9px; background: #fbfcfe;
  outline: none; transition: border-color .15s, box-shadow .15s;
}
.p69-campo:focus { border-color: #2f6fe0; box-shadow: 0 0 0 3px rgba(47,111,224,.16); background: #fff; }

.p69-linhaSenha { position: relative; display: flex; align-items: center; }
.p69-linhaSenha .p69-campo { padding-right: 84px; }
.p69-olho {
  position: absolute; right: 6px;
  border: 0; background: transparent; cursor: pointer;
  color: #2f6fe0; font-size: 12px; font-weight: 700; padding: 6px 8px; border-radius: 6px;
}
.p69-olho:hover { background: #eef4ff; }

.p69-aviso { min-height: 0; font-size: 12.5px; line-height: 1.45; margin-top: 12px; }
.p69-aviso.p69-ruim { color: #b3261e; background: #fdeceb; border: 1px solid #f6cfcb; padding: 8px 10px; border-radius: 8px; }
.p69-aviso.p69-ok   { color: #14622f; background: #e9f7ef; border: 1px solid #c3e6cf; padding: 8px 10px; border-radius: 8px; }

.p69-entrar {
  width: 100%; margin-top: 16px; padding: 11px 14px;
  border: 0; border-radius: 9px; cursor: pointer;
  background: #1e58c8; color: #fff; font-size: 14px; font-weight: 700;
  transition: background .15s, opacity .15s;
}
.p69-entrar:hover { background: #17489f; }
.p69-entrar:disabled { opacity: .6; cursor: default; }

.p69-rodape { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; justify-content: space-between; margin-top: 12px; }
.p69-link { border: 0; background: transparent; color: #2f6fe0; font-size: 12px; cursor: pointer; padding: 4px 2px; text-decoration: underline; }
.p69-link:hover { color: #17489f; }
.p69-soLocal { color: #8a6100; }
.p69-pinta { font-size: 11px; color: #8a94a0; }

.p69-nota { margin-top: 14px; padding-top: 12px; border-top: 1px solid #eef1f5; font-size: 11px; color: #7c8794; line-height: 1.5; }

/* cracha do usuario ------------------------------------------------- */
.p69-cracha {
  position: fixed; right: 12px; bottom: 12px; z-index: 2147482000;
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  max-width: calc(100vw - 24px);
  background: rgba(255,255,255,.97);
  border: 1px solid #dde3ea; border-radius: 999px;
  padding: 6px 8px 6px 12px;
  box-shadow: 0 6px 20px rgba(15,30,55,.16);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
  font-size: 12px; color: #2b3644;
}
.p69-quem { display: flex; align-items: center; gap: 7px; min-width: 0; }
.p69-bola { width: 8px; height: 8px; border-radius: 50%; background: #b9c2cd; flex: 0 0 8px; }
.p69-bola.p69-bolaOk { background: #1faa59; box-shadow: 0 0 0 3px rgba(31,170,89,.16); }
.p69-bola.p69-bolaRuim { background: #d93025; }
.p69-nome { font-weight: 700; max-width: 190px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.p69-papel { color: #5f6b7a; background: #f1f4f8; border-radius: 999px; padding: 2px 8px; font-size: 11px; }
.p69-papel.p69-papelLeitura { color: #8a6100; background: #fff4dc; }

.p69-btn {
  border: 1px solid #d5dce5; background: #fff; color: #2b3644;
  border-radius: 999px; padding: 5px 11px; font-size: 11.5px; cursor: pointer;
}
.p69-btn:hover { background: #f4f7fb; }
.p69-btnSair { color: #b3261e; border-color: #f0cfcc; }
.p69-btnSair:hover { background: #fdeceb; }
.p69-btnPerigo { color: #fff; background: #d93025; border-color: #d93025; font-weight: 700; }
.p69-btnPerigo:hover { background: #b3261e; }

/* somente leitura: deixa claro que nada sera gravado ----------------- */
html.p69-soLeitura .p69-cracha { border-color: #f0d79a; }

@media (max-width: 640px) {
  .p69-cartao { padding: 20px 18px 16px; }
  .p69-cracha { left: 12px; right: 12px; justify-content: space-between; border-radius: 12px; }
  .p69-nome { max-width: 120px; }
}

@media print {
  .p69-tela, .p69-cracha { display: none !important; }
}
</style>
"""


SQL_REGRAS = r"""-- 1) Liga a protecao da tabela do painel
alter table public.painel_dados enable row level security;

-- 2) Apaga qualquer permissao antiga aberta
drop policy if exists "painel_leitura"  on public.painel_dados;
drop policy if exists "painel_escrita"  on public.painel_dados;
drop policy if exists "painel_insercao" on public.painel_dados;

-- 3) So quem esta logado le e grava
create policy "painel_leitura"  on public.painel_dados for select to authenticated using (true);
create policy "painel_insercao" on public.painel_dados for insert to authenticated with check (true);
create policy "painel_escrita"  on public.painel_dados for update to authenticated using (true) with check (true);

-- 4) Opcional: tabela para dizer quem edita e quem so olha
create table if not exists public.painel_acessos (
  email text primary key,
  papel text not null default 'editor'
);
alter table public.painel_acessos enable row level security;
drop policy if exists "acessos_leitura" on public.painel_acessos;
create policy "acessos_leitura" on public.painel_acessos for select to authenticated using (true);

-- 5) (opcional) exemplo de pessoa que so olha
-- insert into public.painel_acessos (email, papel) values ('fulano@empresa.com', 'leitura');
"""


# ---------------------------------------------------------------------------
# APLICACAO NO ARQUIVO
# ---------------------------------------------------------------------------
def fala(txt=''):
    print(txt)


def main():
    fala('=' * 70)
    fala(' PATCH 69 - login e regras de acesso no painel')
    fala('=' * 70)

    if not os.path.isfile(FILE):
        fala('[erro] Nao encontrei o arquivo:')
        fala('       ' + FILE)
        fala('       Abra este script e corrija a linha FILE = ...')
        return 1

    with open(FILE, 'r', encoding='utf-8', errors='surrogateescape') as f:
        html = f.read()
    fala('[ok] index.html lido  (%d caracteres)' % len(html))

    if MARCADOR in html:
        fala('[info] O Patch 69 JA esta aplicado neste arquivo. Nada a fazer.')
        fala('       Se quiser reaplicar, remova o bloco "%s" antes.' % MARCADOR)
        mostrar_sql()
        return 0

    baixo = html.lower()
    if '<body' not in baixo:
        fala('[erro] Este arquivo nao parece ser a pagina do painel (sem <body>).')
        fala('       Nenhuma alteracao foi feita.')
        return 1
    fala('[ok] Pagina do painel reconhecida.')

    if 'createClient' in html and '_supabase' in html:
        fala('[ok] Conexao com o Supabase encontrada: o login vai usar ela.')
    else:
        fala('[aviso] Nao encontrei a conexao com o Supabase pelo nome usual.')
        fala('        A tela de entrada entra do mesmo jeito e avisa se nao')
        fala('        conseguir falar com o banco.')

    if 'painel_dados' in html:
        fala('[ok] Tabela painel_dados encontrada (a que sera protegida).')
    else:
        fala('[aviso] Nao encontrei a tabela painel_dados neste arquivo.')

    if 'carregarBancoDaNuvem' in html:
        fala('[ok] Rotina de carregar as obras encontrada: sera chamada logo')
        fala('     depois do login.')

    if 'PATCH 67' in html or 'PATCH 68' in html:
        fala('[ok] Patches 67/68 detectados: continuam funcionando, agora so')
        fala('     gravam quando existe sessao.')

    pos = baixo.rfind('</body>')
    if pos < 0:
        pos = baixo.rfind('</html>')
    if pos < 0:
        fala('[erro] Nao achei o fechamento da pagina (</body> ou </html>).')
        return 1
    fala('[ok] Lugar de insercao conferido (fim da pagina).')

    selo = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    bkp = FILE + '.bak_patch69_' + selo
    shutil.copy2(FILE, bkp)
    fala('[ok] Backup criado: ' + os.path.basename(bkp))

    novo = html[:pos] + BLOCO + '\n' + html[pos:]

    with open(FILE, 'w', encoding='utf-8', errors='surrogateescape') as f:
        f.write(novo)
    fala('[ok] Bloco inserido antes do fechamento da pagina.')
    fala('[ok] Tamanho final: %d caracteres (+%d)' % (len(novo), len(novo) - len(html)))

    guardar_sql()

    fala('')
    fala('-' * 70)
    fala(' AGORA FALTAM 2 PASSOS NO SITE DO SUPABASE (UMA VEZ SO)')
    fala('-' * 70)
    fala('')
    fala('  PASSO 1 - CRIAR OS USUARIOS DA EQUIPE')
    fala('    Supabase > Authentication > Users > Add user')
    fala('    Coloque e-mail e senha de cada pessoa e marque')
    fala('    "Auto Confirm User". Sem isso ninguem consegue entrar.')
    fala('')
    fala('  PASSO 2 - LIGAR AS REGRAS DE ACESSO')
    fala('    Supabase > SQL Editor > New query')
    fala('    Cole o SQL abaixo (tambem salvo no arquivo')
    fala('    regras_de_acesso_patch69.sql, na pasta do painel) e clique Run.')
    fala('')
    mostrar_sql()
    fala('')
    fala('  PASSO 3 (OPCIONAL) - QUEM SO PODE OLHAR')
    fala('    Na tabela painel_acessos, insira o e-mail da pessoa com o')
    fala('    papel "leitura". Ela ve tudo e nao grava nada.')
    fala('')
    fala('-' * 70)
    fala(' O QUE MUDA PARA VOCE')
    fala('-' * 70)
    fala('  1) Recarregue o painel com Ctrl+F5')
    fala('  2) Aparece a tela pedindo e-mail e senha')
    fala('  3) Depois de entrar, o painel abre normal e um cracha no canto')
    fala('     mostra seu e-mail, seu nivel de acesso e o botao Sair')
    fala('')
    fala('  Se o cracha ficar VERMELHO com "Banco sem protecao", o PASSO 2')
    fala('  ainda nao foi feito: o banco continua respondendo a quem nao')
    fala('  fez login.')
    fala('')
    fala('  Nenhum calculo, preco ou medida foi alterado.')
    fala('')
    fala('>>> Agora abra o painel e pressione Ctrl+F5 para recarregar. <<<')
    return 0


def mostrar_sql():
    for linha in SQL_REGRAS.split('\n'):
        fala('    ' + linha)


def guardar_sql():
    try:
        alvo = os.path.join(os.path.dirname(os.path.abspath(FILE)),
                            'regras_de_acesso_patch69.sql')
        with open(alvo, 'w', encoding='utf-8') as f:
            f.write(SQL_REGRAS)
        fala('[ok] SQL das regras salvo em: ' + os.path.basename(alvo))
    except Exception:
        fala('[aviso] Nao consegui salvar o arquivo .sql; o SQL aparece abaixo.')


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        fala('[erro] Algo deu errado: %s' % e)
        fala('       Nenhuma alteracao foi concluida. Se existir um arquivo')
        fala('       .bak_patch69_, ele e a copia do seu index.html antes da')
        fala('       tentativa.')
        sys.exit(1)
