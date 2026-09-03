# -*- coding: utf-8 -*-
"""
PATCH 104 - Guardar tudo na nuvem (Supabase)

O que este script faz no SEU index.html:
  - faz uma copia de seguranca antes de mexer (arquivo .bak_patch104_...)
  - acrescenta UM bloco novo no fim da pagina, entre as marcas
    <!-- PATCH104_INI --> e <!-- PATCH104_FIM -->
  - NAO apaga, NAO reescreve e NAO reorganiza nada do que voce ja tem
  - pode ser executado varias vezes: se o bloco ja existir, ele avisa e sai
  - cria tambem o arquivo painel_nuvem_v104.sql (para colar no Supabase)

Como usar:
  1) coloque este arquivo na MESMA pasta do seu index.html
  2) rode:  python patch104.py
  3) abra o Supabase > SQL Editor, cole o conteudo de painel_nuvem_v104.sql e execute
  4) recarregue o painel e faca login normalmente
"""

import os
import sys
import time
import shutil

ALVO = 'index.html'
MARCA_INI = '<!-- PATCH104_INI -->'
MARCA_FIM = '<!-- PATCH104_FIM -->'
SQL_NOME = 'painel_nuvem_v104.sql'


def achar_arquivo():
    aqui = os.path.dirname(os.path.abspath(__file__))
    for pasta in (os.getcwd(), aqui):
        caminho = os.path.join(pasta, ALVO)
        if os.path.isfile(caminho):
            return caminho
    return None


BLOCO = r'''
<!-- PATCH104_INI -->
<script>
/* PATCH 104 - Guardar tudo na nuvem (Supabase).
   Espelha no servidor: usuarios/senhas, permissoes, agenda (calendario),
   boletins de inspecao, diarios de obra e relatorios FPDO.
   A nuvem manda: ao abrir o painel, o que estiver mais novo no servidor
   entra na maquina; o que voce alterar aqui sobe sozinho.
   Nao reescreve nenhuma funcao existente: apenas acompanha e sincroniza. */
(function () {
  'use strict';
  if (window.__p104) { return; }
  window.__p104 = true;

  var TAB_KV  = 'painel_nuvem';
  var TAB_REG = 'painel_registros';

  var CHAVES = [
    'painel_seg_usuarios_v1',
    'painel_seg_permissoes_v1',
    'painel_seg_config_v1',
    'painel_seg_presenca_v1',
    'painel_seg_historico_v1',
    'painel_seg_log_v1',
    'painelAgendaObras_v1'
  ];
  var SO_ADMIN = { 'painel_seg_usuarios_v1': 1, 'painel_seg_permissoes_v1': 1 };

  var COLECOES = [
    { nome: 'p83_boletins', base: 'p83_boletins_v1', loja: 'reg', ls: 'p83_boletins_ls_v1' },
    { nome: 'p84_diarios',  base: 'p84_diarios_v1',  loja: 'reg', ls: 'p84_diarios_ls_v1' },
    { nome: 'p92_fpdo',     base: 'p92_fpdo_v1',     loja: 'reg', ls: 'p92_fpdo_ls_v1' }
  ];

  var K_STAMP  = 'p104_stamp_v1';
  var K_IDS    = 'p104_ids_v1';
  var K_REMOV  = 'p104_removidos_v1';
  var F_RELOAD = 'p104_recarregou_v1';
  var TOLER    = 2000;

  var ocupado = false;

  /* ---------------------------------------------------------------- *
   * utilidades
   * ---------------------------------------------------------------- */
  function sb() {
    try { return (window._supabase && window._supabase.from) ? window._supabase : null; } catch (e) { return null; }
  }

  function sessaoPainel() {
    var v = null;
    try { v = sessionStorage.getItem('painel_seg_sessao_v1') || localStorage.getItem('painel_seg_sessao_v1'); } catch (e) {}
    try { return v ? JSON.parse(v) : null; } catch (e) { return null; }
  }

  function souAdmin() {
    var s = sessaoPainel();
    return !!(s && String(s.perfil || '').toLowerCase() === 'admin');
  }

  function quem() {
    var s = sessaoPainel();
    return s ? String(s.usuario || s.nome || 'painel') : 'painel';
  }

  function agora() { return new Date().toISOString(); }

  function ms(v) {
    var t = Date.parse(String(v || ''));
    return isNaN(t) ? 0 : t;
  }

  function lerJSON(k, def) {
    try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch (e) { return def; }
  }

  function gravarJSON(k, v) {
    try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; }
  }

  function bruto(k) {
    try { return localStorage.getItem(k); } catch (e) { return null; }
  }

  function stamps() { return lerJSON(K_STAMP, {}) || {}; }
  function salvarStamps(m) { gravarJSON(K_STAMP, m); }
  function idsVistos() { return lerJSON(K_IDS, {}) || {}; }
  function salvarIds(m) { gravarJSON(K_IDS, m); }
  function removidos() { return lerJSON(K_REMOV, {}) || {}; }
  function salvarRemovidos(m) { gravarJSON(K_REMOV, m); }

  /* anota que um registro foi apagado nesta maquina, para sair de todas */
  function anotarRemocao(colNome, id) {
    if (!colNome || !id) { return; }
    var m = removidos();
    if (!m[colNome]) { m[colNome] = {}; }
    m[colNome][id] = agora();
    salvarRemovidos(m);
  }

  function marcador(txt) {
    var s = String(txt == null ? '' : txt), h = 5381, i;
    for (i = 0; i < s.length; i++) { h = ((h * 33) ^ s.charCodeAt(i)) >>> 0; }
    return s.length + '_' + h;
  }

  function horaReg(r) {
    if (!r) { return 0; }
    return ms(r.alterado || r.alteradoEm || r.criado || 0);
  }

  function badge(txt, cor) {
    var d = document.getElementById('p104Status');
    if (!d) {
      d = document.createElement('div');
      d.id = 'p104Status';
      d.setAttribute('title', 'Situacao da nuvem. Clique para sincronizar agora.');
      d.style.cssText = 'position:fixed;left:10px;bottom:10px;z-index:2147483000;background:#0f172a;' +
        'color:#fff;font:12px Arial;padding:6px 11px;border-radius:20px;opacity:.92;cursor:pointer;' +
        'box-shadow:0 2px 8px rgba(0,0,0,.25)';
      d.onclick = function () { sincronizar(true); };
      if (document.body) { document.body.appendChild(d); }
    }
    d.textContent = 'Nuvem: ' + txt;
    d.style.background = cor || '#0f172a';
  }

  function aviso(msg) {
    try {
      if (typeof window.mostrarToastPainel === 'function') { window.mostrarToastPainel(msg, 'ok'); return; }
    } catch (e) {}
    badge(msg, '#166534');
  }
'''

BLOCO += r'''
  /* ---------------------------------------------------------------- *
   * IndexedDB das colecoes (boletins, diarios, FPDO)
   * ---------------------------------------------------------------- */
  function abrirBase(col, ok, falhou) {
    try {
      if (!window.indexedDB) { falhou(true); return; }
      var req = window.indexedDB.open(col.base, 1);
      req.onupgradeneeded = function () {
        var d = req.result;
        if (!d.objectStoreNames.contains(col.loja)) { d.createObjectStore(col.loja, { keyPath: 'id' }); }
      };
      req.onsuccess = function () { ok(req.result); };
      req.onerror = function () { falhou(false); };
    } catch (e) { falhou(false); }
  }

  function lerLocais(col, depois) {
    abrirBase(col, function (d) {
      try {
        var t = d.transaction(col.loja, 'readonly');
        var r = t.objectStore(col.loja).getAll();
        r.onsuccess = function () { depois(r.result || [], true); };
        r.onerror = function () { depois(lerJSON(col.ls, []) || [], false); };
      } catch (e) { depois(lerJSON(col.ls, []) || [], false); }
    }, function (semBanco) {
      /* sem IndexedDB neste navegador: a reserva no navegador vale como fonte */
      depois(lerJSON(col.ls, []) || [], semBanco === true);
    });
  }

  function gravarLocais(col, novos, apagar, depois) {
    if ((!novos || !novos.length) && (!apagar || !apagar.length)) { depois(); return; }
    abrirBase(col, function (d) {
      try {
        var t = d.transaction(col.loja, 'readwrite');
        var loja = t.objectStore(col.loja), i;
        for (i = 0; i < novos.length; i++) { loja.put(novos[i]); }
        for (i = 0; i < apagar.length; i++) { loja.delete(apagar[i]); }
        t.oncomplete = function () { espelhoLS(col, novos, apagar); depois(); };
        t.onerror = function () { espelhoLS(col, novos, apagar); depois(); };
      } catch (e) { espelhoLS(col, novos, apagar); depois(); }
    }, function () { espelhoLS(col, novos, apagar); depois(); });
  }

  function espelhoLS(col, novos, apagar) {
    var arr = lerJSON(col.ls, []) || [], i, j, achou;
    for (i = 0; i < novos.length; i++) {
      achou = false;
      for (j = 0; j < arr.length; j++) {
        if (arr[j] && arr[j].id === novos[i].id) { arr[j] = novos[i]; achou = true; break; }
      }
      if (!achou) { arr.push(novos[i]); }
    }
    if (apagar && apagar.length) {
      arr = arr.filter(function (r) { return apagar.indexOf(r && r.id) < 0; });
    }
    gravarJSON(col.ls, arr);
  }

  /* ---------------------------------------------------------------- *
   * chaves simples (usuarios, permissoes, agenda, historico...)
   * ---------------------------------------------------------------- */
  function juntarListas(a, b) {
    var saida = [], visto = {}, i, ch;
    function por(arr) {
      if (!arr || !arr.length) { return; }
      for (i = 0; i < arr.length; i++) {
        try { ch = JSON.stringify(arr[i]); } catch (e) { ch = String(arr[i]); }
        if (!visto[ch]) { visto[ch] = 1; saida.push(arr[i]); }
      }
    }
    por(a); por(b);
    if (saida.length > 800) { saida = saida.slice(saida.length - 800); }
    return saida;
  }

  function eListaDeEventos(k) {
    return k === 'painel_seg_log_v1' || k === 'painel_seg_historico_v1' || k === 'painel_seg_presenca_v1';
  }

  function sincronizarChaves(depois) {
    var s = sb();
    if (!s) { depois(false, 'sem conexao'); return; }
    s.from(TAB_KV).select('chave,valor,marca,atualizado_em').in('chave', CHAVES).then(function (res) {
      if (res.error) { depois(false, res.error.message || 'erro na nuvem'); return; }
      var linhas = res.data || [], mapa = {}, i;
      for (i = 0; i < linhas.length; i++) { mapa[linhas[i].chave] = linhas[i]; }

      var st = stamps(), subir = [], recarrega = false, mudou = false;

      for (i = 0; i < CHAVES.length; i++) {
        (function (k) {
          if (SO_ADMIN[k] && !souAdmin()) {
            var so = mapa[k];
            if (so && so.valor !== undefined && so.valor !== null) {
              var textoSo = JSON.stringify(so.valor);
              if (bruto(k) !== textoSo) {
                try { localStorage.setItem(k, textoSo); } catch (e) {}
                st[k] = { marca: marcador(textoSo), at: so.atualizado_em || agora() };
                mudou = true; recarrega = true;
              }
            }
            return;
          }
          var local = bruto(k);
          var mLocal = local === null ? '' : marcador(local);
          var ref = st[k] || { marca: '', at: '' };
          var serv = mapa[k];
          var mServ = serv ? String(serv.marca || '') : '';
          var textoServ = serv && serv.valor !== undefined && serv.valor !== null ? JSON.stringify(serv.valor) : null;
          if (textoServ !== null && !mServ) { mServ = marcador(textoServ); }

          var localMudou = mLocal !== ref.marca;
          var servMudou = mServ !== ref.marca;

          if (!serv || textoServ === null) {
            if (local !== null) {
              subir.push({ chave: k, valor: JSON.parse(local), marca: mLocal });
              st[k] = { marca: mLocal, at: agora() };
            }
            return;
          }
          if (mServ === mLocal) { st[k] = { marca: mLocal, at: serv.atualizado_em || agora() }; return; }

          if (localMudou && servMudou && eListaDeEventos(k)) {
            var juntos, aLocal = null, aServ = null;
            try { aLocal = JSON.parse(local || '[]'); } catch (e) { aLocal = []; }
            try { aServ = JSON.parse(textoServ); } catch (e) { aServ = []; }
            if (aLocal instanceof Array && aServ instanceof Array) {
              juntos = juntarListas(aServ, aLocal);
              var textoJ = JSON.stringify(juntos);
              try { localStorage.setItem(k, textoJ); } catch (e) {}
              subir.push({ chave: k, valor: juntos, marca: marcador(textoJ) });
              st[k] = { marca: marcador(textoJ), at: agora() };
              mudou = true;
              return;
            }
          }

          if (servMudou || !localMudou) {
            try { localStorage.setItem(k, textoServ); } catch (e) {}
            st[k] = { marca: mServ, at: serv.atualizado_em || agora() };
            mudou = true;
            recarrega = true;
            return;
          }

          subir.push({ chave: k, valor: JSON.parse(local), marca: mLocal });
          st[k] = { marca: mLocal, at: agora() };
        }(CHAVES[i]));
      }

      salvarStamps(st);

      function terminar(erro) {
        depois(!erro, erro, recarrega, mudou);
      }

      if (!subir.length) { terminar(null); return; }
      var j, quando = agora(), autor = quem();
      for (j = 0; j < subir.length; j++) { subir[j].atualizado_em = quando; subir[j].autor = autor; }
      s.from(TAB_KV).upsert(subir, { onConflict: 'chave' }).then(function (r2) {
        terminar(r2.error ? (r2.error.message || 'erro ao enviar') : null);
      });
    });
  }
'''

BLOCO += r'''
  /* ---------------------------------------------------------------- *
   * colecoes: boletins, diarios e FPDO (um registro por linha)
   * ---------------------------------------------------------------- */
  function sincronizarColecao(col, depois) {
    var s = sb();
    if (!s) { depois(false, 'sem conexao'); return; }

    lerLocais(col, function (locais, lidoOk) {
      s.from(TAB_REG).select('id,colecao,dados,atualizado_em,removido')
        .eq('colecao', col.nome).then(function (res) {
        if (res.error) { depois(false, res.error.message || 'erro na nuvem'); return; }

        var linhas = res.data || [];
        var mapaServ = {}, mapaLocal = {}, i, r;
        for (i = 0; i < linhas.length; i++) { mapaServ[linhas[i].id] = linhas[i]; }
        for (i = 0; i < locais.length; i++) { if (locais[i] && locais[i].id) { mapaLocal[locais[i].id] = locais[i]; } }

        var vistos = idsVistos();
        var jaVi = vistos[col.nome] || {};
        var apagadosAqui = (removidos()[col.nome] || {});
        var subir = [], baixar = [], apagarLocal = [], mudou = false, sumiram = [];

        for (i = 0; i < locais.length; i++) {
          r = locais[i];
          if (!r || !r.id) { continue; }
          var serv = mapaServ[r.id];
          if (serv && serv.removido === true) {
            if (horaReg(r) > ms(serv.atualizado_em) + TOLER) {
              subir.push({ id: r.id, colecao: col.nome, dados: r, atualizado_em: agora(), removido: false, autor: quem() });
            } else {
              apagarLocal.push(r.id);
              mudou = true;
            }
            continue;
          }
          if (!serv) {
            if (apagadosAqui[r.id]) { apagarLocal.push(r.id); mudou = true; }
            else { subir.push({ id: r.id, colecao: col.nome, dados: r, atualizado_em: (r.alterado || r.criado || agora()), removido: false, autor: quem() }); }
            continue;
          }
          var hLocal = horaReg(r), hServ = ms(serv.atualizado_em);
          if (hLocal > hServ + TOLER) {
            subir.push({ id: r.id, colecao: col.nome, dados: r, atualizado_em: (r.alterado || r.criado || agora()), removido: false, autor: quem() });
          } else if (hServ > hLocal + TOLER) {
            baixar.push(serv.dados);
            mudou = true;
          }
        }

        var podeApagarNaNuvem = lidoOk;

        for (i = 0; i < linhas.length; i++) {
          if (linhas[i].removido === true) { continue; }
          if (mapaLocal[linhas[i].id]) { continue; }
          if (podeApagarNaNuvem && (apagadosAqui[linhas[i].id] || jaVi[linhas[i].id])) {
            /* apagado nesta maquina: tira de todas as maquinas */
            subir.push({ id: linhas[i].id, colecao: col.nome, dados: null, atualizado_em: agora(), removido: true, autor: quem() });
            sumiram.push(linhas[i].id);
            continue;
          }
          if (linhas[i].dados) { baixar.push(linhas[i].dados); mudou = true; }
        }

        var novoJaVi = {};
        for (i = 0; i < locais.length; i++) { if (locais[i] && locais[i].id) { novoJaVi[locais[i].id] = 1; } }
        for (i = 0; i < baixar.length; i++) { if (baixar[i] && baixar[i].id) { novoJaVi[baixar[i].id] = 1; } }
        for (i = 0; i < subir.length; i++) {
          if (subir[i].removido === true) { delete novoJaVi[subir[i].id]; } else { novoJaVi[subir[i].id] = 1; }
        }
        for (i = 0; i < apagarLocal.length; i++) { delete novoJaVi[apagarLocal[i]]; }
        vistos[col.nome] = novoJaVi;
        salvarIds(vistos);

        gravarLocais(col, baixar, apagarLocal, function () {
          if (!subir.length) { limparAnotacoes(); depois(true, null, mudou); return; }
          s.from(TAB_REG).upsert(subir, { onConflict: 'id' }).then(function (r2) {
            if (!r2.error) { limparAnotacoes(); }
            depois(!r2.error, r2.error ? (r2.error.message || 'erro ao enviar') : null, mudou);
          });
        });

        /* remocoes ja avisadas a nuvem nao precisam mais ficar anotadas */
        function limparAnotacoes() {
          if (!sumiram.length && !apagarLocal.length) { return; }
          var m = removidos(), j, mexeu = false;
          if (m[col.nome]) {
            for (j = 0; j < sumiram.length; j++) { if (m[col.nome][sumiram[j]]) { delete m[col.nome][sumiram[j]]; mexeu = true; } }
            for (j = 0; j < apagarLocal.length; j++) { if (m[col.nome][apagarLocal[j]]) { delete m[col.nome][apagarLocal[j]]; mexeu = true; } }
          }
          if (mexeu) { salvarRemovidos(m); }
        }
      });
    });
  }

  /* apagou aqui? marca como removido na nuvem, para sair de todas as maquinas */
  function anunciarRemocao(colNome, id) {
    anotarRemocao(colNome, id);
    var s = sb();
    if (!s || !id) { return; }
    s.from(TAB_REG).upsert([{ id: id, colecao: colNome, dados: null, atualizado_em: agora(), removido: true, autor: quem() }],
      { onConflict: 'id' }).then(function () {}, function () {});
    var v = idsVistos();
    if (v[colNome]) { delete v[colNome][id]; salvarIds(v); }
  }
  window.p104Removeu = anunciarRemocao;
'''

BLOCO += r'''
  /* ---------------------------------------------------------------- *
   * maestro: junta tudo
   * ---------------------------------------------------------------- */
  function sincronizar(pedidoManual) {
    if (ocupado) { return; }
    var s = sb();
    if (!s) { badge('sem conexao', '#7f1d1d'); return; }
    ocupado = true;
    badge('sincronizando...', '#1d4ed8');

    var erros = [], precisaRecarregar = false, houveMudanca = false;

    sincronizarChaves(function (ok, erro, recarrega, mudou) {
      if (!ok && erro) { erros.push(erro); }
      if (recarrega) { precisaRecarregar = true; }
      if (mudou) { houveMudanca = true; }

      var n = 0;
      function proxima() {
        if (n >= COLECOES.length) { fim(); return; }
        var col = COLECOES[n++];
        sincronizarColecao(col, function (ok2, erro2, mudou2) {
          if (!ok2 && erro2) { erros.push(col.nome + ': ' + erro2); }
          if (mudou2) { houveMudanca = true; precisaRecarregar = true; }
          proxima();
        });
      }
      proxima();

      function fim() {
        ocupado = false;
        if (erros.length) {
          badge('erro ao salvar', '#7f1d1d');
          try { console.warn('PATCH104', erros); } catch (e) {}
        } else {
          var h = new Date();
          var hh = ('0' + h.getHours()).slice(-2) + ':' + ('0' + h.getMinutes()).slice(-2);
          badge('salvo ' + hh, '#166534');
        }
        if (pedidoManual && !erros.length) { aviso('Dados sincronizados com a nuvem.'); }

        if (precisaRecarregar && houveMudanca) {
          var ja = false;
          try { ja = sessionStorage.getItem(F_RELOAD) === '1'; } catch (e) {}
          if (!ja || pedidoManual) {
            try { sessionStorage.setItem(F_RELOAD, '1'); } catch (e) {}
            badge('atualizando tela...', '#1d4ed8');
            setTimeout(function () { try { location.reload(); } catch (e) {} }, 700);
          }
        }
      }
    });
  }
  window.p104Sincronizar = function () { sincronizar(true); };

  /* ---------------------------------------------------------------- *
   * gatilhos
   * ---------------------------------------------------------------- */
  var pendente = null;
  function agendar(atraso) {
    if (pendente) { clearTimeout(pendente); }
    pendente = setTimeout(function () { pendente = null; sincronizar(false); }, atraso || 2500);
  }

  /* mudanca nas chaves simples: sobe logo depois */
  try {
    var setOriginal = localStorage.setItem.bind(localStorage);
    var removeOriginal = localStorage.removeItem.bind(localStorage);
    localStorage.setItem = function (k, v) {
      setOriginal(k, v);
      if (CHAVES.indexOf(String(k)) >= 0) { agendar(1800); }
    };
    localStorage.removeItem = function (k) {
      removeOriginal(k);
      if (CHAVES.indexOf(String(k)) >= 0) { agendar(1800); }
    };
  } catch (e) {}

  /* boletins, diarios e FPDO: confere de tempo em tempo e ao voltar para a aba */
  setInterval(function () { sincronizar(false); }, 60000);

  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) { agendar(1200); }
  });

  window.addEventListener('online', function () { agendar(1000); });

  window.addEventListener('beforeunload', function () {
    try { sessionStorage.removeItem(F_RELOAD); } catch (e) {}
  });

  function comecar() {
    badge('conectando...', '#1d4ed8');
    if (sb()) { setTimeout(function () { sincronizar(false); }, 300); return; }
    var tentativas = 0;
    var t = setInterval(function () {
      tentativas++;
      if (sb()) { clearInterval(t); setTimeout(function () { sincronizar(false); }, 300); return; }
      if (tentativas > 40) { clearInterval(t); badge('sem conexao', '#7f1d1d'); }
    }, 500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', comecar);
  } else {
    comecar();
  }
})();
</script>
<!-- PATCH104_FIM -->
'''

SQL = r'''-- ================================================================
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
'''

def escrever_sql(pasta):
    destino = os.path.join(pasta, SQL_NOME)
    with open(destino, 'w', encoding='utf-8') as f:
        f.write(SQL)
    return destino


def aplicar(caminho):
    with open(caminho, 'r', encoding='utf-8', errors='ignore') as f:
        html = f.read()

    if MARCA_INI in html:
        print('AVISO: o Patch 104 ja esta neste index.html. Nada foi alterado.')
        return False

    corte = html.rfind('</body>')
    if corte < 0:
        corte = html.rfind('</html>')
    if corte < 0:
        novo = html + '\n' + BLOCO + '\n'
    else:
        novo = html[:corte] + BLOCO + '\n' + html[corte:]

    copia = caminho + '.bak_patch104_' + time.strftime('%Y%m%d_%H%M%S')
    shutil.copy2(caminho, copia)

    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(novo)

    print('Copia de seguranca: ' + os.path.basename(copia))
    print('Bloco do Patch 104 adicionado no fim da pagina.')
    return True


def main():
    caminho = achar_arquivo()
    if not caminho:
        print('ERRO: nao encontrei o arquivo ' + ALVO + ' nesta pasta.')
        print('Coloque este script na mesma pasta do seu ' + ALVO + ' e rode de novo.')
        sys.exit(1)

    print('Arquivo encontrado: ' + os.path.basename(caminho))
    aplicar(caminho)

    sql = escrever_sql(os.path.dirname(os.path.abspath(caminho)))
    print('Arquivo do banco criado: ' + os.path.basename(sql))
    print('')
    print('FALTA APENAS 1 PASSO:')
    print('  abra o Supabase > SQL Editor > New query,')
    print('  cole o conteudo de ' + os.path.basename(sql) + ' e clique em Run.')
    print('Depois recarregue o painel. Vai aparecer um aviso "Nuvem: salvo hh:mm"')
    print('no canto de baixo, do lado esquerdo. Clicar nele sincroniza na hora.')


if __name__ == '__main__':
    main()
