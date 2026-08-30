# -*- coding: utf-8 -*-
"""
PATCH 88 - Centraliza a caixa "Usuarios cadastrados", mostra quem
            esta acessando o painel e guarda o historico de alteracoes

O que faz:
  1) A caixa vai para o centro da tela:
     a janela "Usuarios cadastrados" passa a ficar exatamente no meio da
     tela (na horizontal e na vertical) e fica um pouco menor, mais
     compacta. O visual, as cores, as colunas e os botoes continuam
     iguais - so mudou a posicao e o tamanho.

  2) Mostra quem esta acessando:
     dentro da tela de usuarios aparece uma faixa verde "Quem esta
     acessando agora", com o nome de cada pessoa conectada, o tipo de
     acesso e a marca "voce" no seu proprio nome. Na lista de usuarios,
     cada pessoa ganha uma etiqueta: "online" para quem esta no painel
     neste momento, ou "visto ha X minutos" para quem acessou antes. O
     botao roxo do menu tambem passa a mostrar quantas janelas do painel
     estao abertas agora.

  3) Guarda todas as alteracoes:
     nasce a tela "Historico de alteracoes" (botao no Menu de Abas e
     tambem dentro da tela de usuarios). Cada vez que alguem mexe em algo
     no painel, o sistema anota a data, a hora, quem fez, o que
     aconteceu e o detalhe. Fica registrado, por exemplo: entrada no
     painel, cadastro de usuario, troca de senha, mudanca de tipo de
     acesso, exclusao de acesso e as alteracoes das telas do painel
     (lancamentos, diario de obra, boletim, configuracoes e outras).
     Da para procurar por pessoa ou por tipo de alteracao, baixar tudo
     em CSV para abrir no Excel, e o administrador pode limpar a lista.
     O painel guarda as ultimas 900 alteracoes.

  Observacao: as informacoes ficam guardadas no proprio navegador do
  computador, por isso a lista de acessos e o historico sao os daquele
  aparelho.

Como usar:
  Coloque este arquivo na mesma pasta do index.html e execute:
      python patch88_centralizar_presenca_historico.py

Seguranca:
  - cria backup automatico do index.html antes de mexer
  - nao altera nem reescreve nada do que ja existe na pagina;
    apenas acrescenta um bloco novo no final
  - pode rodar varias vezes (na segunda ele avisa e nao faz nada)
"""

import io
import os
import sys
import shutil
from datetime import datetime

MARCA = 'PATCH88_CENTRO_PRESENCA_HISTORICO_OK'

JS = r"""/* PATCH 88 - centraliza e reduz a caixa "Usuarios cadastrados",
   mostra quem esta acessando o painel agora e grava um historico
   de todas as alteracoes feitas.
   Nao reescreve nada do painel nem do patch 87: apenas acrescenta. */
(function () {
  'use strict';

  if (window.__p88) { return; }
  window.__p88 = true;

  var K_USERS = 'painel_seg_usuarios_v1';
  var K_SESS  = 'painel_seg_sessao_v1';
  var K_PRES  = 'painel_seg_presenca_v1';
  var K_HIST  = 'painel_seg_historico_v1';
  var K_MEUID = 'painel_seg_presenca_id';

  var VIVO   = 60000;    /* considerado online se deu sinal nos ultimos 60s */
  var BATIDA = 8000;     /* manda sinal de presenca a cada 8s */
  var LIMITE = 900;      /* quantidade maxima de linhas guardadas no historico */

  var IGNORAR = [K_PRES, K_HIST, K_MEUID, K_SESS];

  var dentro = false;          /* evita gravar historico das nossas proprias gravacoes */
  var ultimosUsuarios = null;  /* foto anterior da lista de usuarios */
  var atrasados = {};          /* junta varias gravacoes seguidas da mesma informacao */

  /* ================================================================ *
   * utilidades
   * ================================================================ */
  function esc(v) {
    return String(v === undefined || v === null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function ler(k, def) {
    try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch (e) { return def; }
  }

  function gravar(k, v) {
    dentro = true;
    try { localStorage.setItem(k, JSON.stringify(v)); return true; }
    catch (e) { return false; }
    finally { dentro = false; }
  }

  function sessao() {
    var s = null;
    try { s = JSON.parse(sessionStorage.getItem(K_SESS) || 'null'); } catch (e) { s = null; }
    if (!s) { s = ler(K_SESS, null); }
    if (s && s.exp && Date.now() > s.exp) { s = null; }
    return s;
  }

  function ehAdmin() {
    var s = sessao();
    if (!s) { return true; }
    return String(s.perfil || '').toLowerCase() === 'admin';
  }

  function nomePerfil(p) {
    var v = String(p || '').toLowerCase();
    if (v === 'admin') { return 'Administrador'; }
    if (v === 'editor') { return 'Pode lan\u00e7ar e editar'; }
    if (v === 'visitante' || v === 'leitor') { return 'Somente consulta'; }
    return p ? String(p) : 'Sem tipo definido';
  }

  function hora(ms) {
    try {
      var d = new Date(Number(ms));
      if (isNaN(d.getTime())) { return '-'; }
      return d.toLocaleDateString('pt-BR') + ' ' +
             d.toLocaleTimeString('pt-BR').slice(0, 5);
    } catch (e) { return '-'; }
  }

  function faz(ms) {
    var seg = Math.max(0, Math.round((Date.now() - Number(ms)) / 1000));
    if (seg < 60) { return 'agora mesmo'; }
    var min = Math.round(seg / 60);
    if (min < 60) { return 'h\u00e1 ' + min + (min === 1 ? ' minuto' : ' minutos'); }
    var hh = Math.round(min / 60);
    if (hh < 24) { return 'h\u00e1 ' + hh + (hh === 1 ? ' hora' : ' horas'); }
    return 'em ' + hora(ms);
  }

  function aviso(msg, tipo) {
    try {
      var d = document.createElement('div');
      d.className = 'p87-aviso' + (tipo === 'err' ? ' err' : '');
      d.setAttribute('data-ps79', '1');
      d.textContent = msg;
      document.body.appendChild(d);
      setTimeout(function () { if (d.parentNode) { d.parentNode.removeChild(d); } }, 3600);
    } catch (e) { /* ignora */ }
  }

  /* ================================================================ *
   * BLOCO A - caixa centralizada e um pouco menor
   * ================================================================ */
  function estilo() {
    if (document.getElementById('p88Estilo')) { return; }
    var s = document.createElement('style');
    s.id = 'p88Estilo';
    s.textContent = [
      /* centraliza de verdade e diminui um pouco, mantendo o mesmo visual */
      'body > #p87Fundo,#p87Fundo{display:flex !important;align-items:center !important;justify-content:center !important;padding:18px !important;overflow:auto !important}',
      'body > #p87Fundo > #p87Caixa,#p87Caixa{position:fixed !important;left:50% !important;top:50% !important;right:auto !important;bottom:auto !important;transform:translate(-50%,-50%) !important;margin:0 !important;width:760px !important;max-width:94vw !important;max-height:86vh !important;height:auto !important}',
      '#p87Caixa header{padding:10px 14px !important}',
      '#p87Caixa header h3{font-size:15px !important}',
      '#p87Corpo{padding:14px !important;overflow:auto !important}',
      '#p87Corpo p.sb{font-size:12px !important;margin:0 0 10px !important}',
      '#p87Pe{padding:10px 14px !important}',
      'table.p87-tab{font-size:12.5px !important}',
      'table.p87-tab th{padding:7px !important}',
      'table.p87-tab td{padding:6px 7px !important}',
      '.p87-info{margin:12px 0 0 !important;padding:9px 11px !important}',

      /* quem esta acessando */
      '#p88Pres{margin:0 0 12px;padding:10px 12px;border:1px solid #bbf7d0;background:#f0fdf4;border-radius:10px;font-size:12.5px;color:#14532d;line-height:1.6}',
      '#p88Pres b{color:#14532d}',
      '#p88Pres .tit{display:block;font-size:11px;font-weight:700;letter-spacing:.3px;text-transform:uppercase;color:#15803d;margin:0 0 6px}',
      '#p88Pres ul{margin:0;padding:0;list-style:none;display:flex;flex-wrap:wrap;gap:6px}',
      '#p88Pres li{background:#fff;border:1px solid #bbf7d0;border-radius:999px;padding:4px 10px;display:flex;align-items:center;gap:6px}',
      '.p88-bola{width:8px;height:8px;border-radius:50%;background:#22c55e;box-shadow:0 0 0 3px rgba(34,197,94,.22);flex:0 0 auto}',
      '.p88-bola.off{background:#94a3b8;box-shadow:none}',
      '.p88-eu{font-size:10.5px;font-weight:700;color:#15803d;text-transform:uppercase}',
      '.p88-onoff{display:inline-block;font-size:10.5px;font-weight:700;border-radius:999px;padding:2px 7px;margin-left:6px}',
      '.p88-onoff.on{background:#dcfce7;color:#15803d}',
      '.p88-onoff.off{background:#f1f5f9;color:#64748b}',
      '#p88Badge{display:inline-block;margin-left:6px;font-size:11px;font-weight:700;background:rgba(255,255,255,.22);border-radius:999px;padding:1px 7px}',

      /* historico */
      '#p88Fundo{position:fixed;inset:0;z-index:2147483300;background:rgba(15,23,42,.62);display:flex;align-items:center;justify-content:center;padding:18px;font-family:Segoe UI,Arial,sans-serif}',
      '#p88Caixa{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);background:#fff;border-radius:14px;width:860px;max-width:94vw;max-height:86vh;height:auto;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.4)}',
      '#p88Caixa header{display:flex;align-items:center;justify-content:space-between;gap:10px;background:#16304f;color:#fff;padding:10px 14px}',
      '#p88Caixa header h3{margin:0;font-size:15px}',
      '#p88Caixa header .p87-btn{background:#e2e8f0}',
      '#p88Corpo{padding:14px;overflow:auto}',
      '#p88Pe{display:flex;gap:8px;flex-wrap:wrap;padding:10px 14px;border-top:1px solid #e2e8f0;background:#f8fafc}',
      '#p88Busca{flex:1;min-width:160px;padding:7px 10px;border:1px solid #cbd5e1;border-radius:8px;font-size:12.5px;background:#fff;color:#1e293b}',
      'table.p88-tab{width:100%;border-collapse:collapse;font-size:12.5px}',
      'table.p88-tab th{background:#1e3a5f;color:#fff;text-align:left;padding:7px;font-size:11px;text-transform:uppercase;letter-spacing:.3px}',
      'table.p88-tab td{border-bottom:1px solid #e2e8f0;padding:6px 7px;color:#1e293b;vertical-align:top}',
      'table.p88-tab td.q{white-space:nowrap;color:#475569}',
      'table.p88-tab tr:nth-child(even) td{background:#f8fafc}',
      '#p88Botao{background:#0f766e;color:#fff;border:none;border-radius:10px;padding:8px 14px;font-weight:600;cursor:pointer;margin:4px;font-size:13px}',
      '#p88Botao:hover{filter:brightness(1.1)}',
      '#meu-menu-abas #p88Botao{display:block;width:100%;box-sizing:border-box;margin:3px 0 !important;text-align:left}',

      'body.dark-mode #p88Caixa{background:#0f172a}',
      'body.dark-mode #p88Pe{background:#111c33;border-color:#334155}',
      'body.dark-mode table.p88-tab td{color:#e2e8f0;border-color:#334155}',
      'body.dark-mode table.p88-tab tr:nth-child(even) td{background:#111c33}',
      'body.dark-mode #p88Pres{background:#0b2a1c;border-color:#166534;color:#dcfce7}',
      'body.dark-mode #p88Pres li{background:#0f172a;border-color:#166534;color:#dcfce7}'
    ].join('\n');
    (document.head || document.documentElement).appendChild(s);
  }

  /* ================================================================ *
   * BLOCO B - quem esta acessando agora
   * ================================================================ */
  function meuId() {
    var id = '';
    try { id = sessionStorage.getItem(K_MEUID) || ''; } catch (e) { id = ''; }
    if (!id) {
      id = 'a' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
      try { sessionStorage.setItem(K_MEUID, id); } catch (e2) { /* ignora */ }
    }
    return id;
  }

  function presencas() {
    var l = ler(K_PRES, []);
    return (l && l.length) ? l : [];
  }

  function limpaVelhos(l) {
    var corte = Date.now() - (24 * 60 * 60 * 1000);
    return l.filter(function (p) { return p && p.visto && Number(p.visto) > corte; });
  }

  function bater() {
    var s = sessao();
    var id = meuId();
    var l = limpaVelhos(presencas());
    var achou = false;
    var agora = Date.now();
    var i;
    for (i = 0; i < l.length; i++) {
      if (l[i].id === id) {
        l[i].visto = agora;
        l[i].usuario = s ? s.usuario : '';
        l[i].nome = s ? (s.nome || s.usuario) : 'Sem login neste navegador';
        l[i].perfil = s ? s.perfil : '';
        achou = true;
        break;
      }
    }
    if (!achou) {
      l.push({
        id: id,
        usuario: s ? s.usuario : '',
        nome: s ? (s.nome || s.usuario) : 'Sem login neste navegador',
        perfil: s ? s.perfil : '',
        desde: agora,
        visto: agora
      });
    }
    gravar(K_PRES, l);
  }

  function online() {
    var corte = Date.now() - VIVO;
    return presencas().filter(function (p) { return Number(p.visto) > corte; });
  }

  function ultimoDe(usu) {
    var alvo = String(usu || '').toLowerCase();
    var l = presencas();
    var melhor = 0;
    var i;
    for (i = 0; i < l.length; i++) {
      if (String(l[i].usuario || '').toLowerCase() === alvo) {
        if (Number(l[i].visto) > melhor) { melhor = Number(l[i].visto); }
      }
    }
    return melhor;
  }

  function htmlPresenca() {
    var l = online();
    var id = meuId();
    var s = sessao();
    var h = '<span class="tit">Quem est\u00e1 acessando agora</span>';

    if (!l.length) {
      h += 'Nenhum acesso ativo registrado neste momento.';
      return h;
    }

    h += '<ul>';
    l.sort(function (a, b) { return Number(b.visto) - Number(a.visto); });
    l.forEach(function (p) {
      var eu = (p.id === id);
      h += '<li><span class="p88-bola"></span><b>' + esc(p.nome || p.usuario || 'Sem login') + '</b>' +
           (p.perfil ? ' <span style="color:#15803d">(' + esc(nomePerfil(p.perfil)) + ')</span>' : '') +
           (eu ? ' <span class="p88-eu">voc\u00ea</span>' : '') +
           '</li>';
    });
    h += '</ul>';
    h += '<div style="margin-top:7px;font-size:11.5px;color:#166534">' +
         'Aberto agora em <b>' + l.length + '</b> ' + (l.length === 1 ? 'janela' : 'janelas') +
         '. Esta contagem vale para este computador/navegador' +
         (s ? '' : ' (ningu\u00e9m fez login nesta janela)') + '.</div>';
    return h;
  }

  /* coloca o bloco verde dentro da tela de usuarios e marca online/offline */
  function enfeitar() {
    var corpo = document.getElementById('p87Corpo');
    if (!corpo) { return; }

    var bl = document.getElementById('p88Pres');
    if (!bl) {
      bl = document.createElement('div');
      bl.id = 'p88Pres';
      bl.setAttribute('data-ps79', '1');
      corpo.insertBefore(bl, corpo.firstChild);
    }
    bl.innerHTML = htmlPresenca();

    var linhas = corpo.querySelectorAll('table.p87-tab tbody tr');
    var corte = Date.now() - VIVO;
    Array.prototype.forEach.call(linhas, function (tr) {
      var tds = tr.getElementsByTagName('td');
      if (tds.length < 2) { return; }
      var b = tds[1].getElementsByTagName('b')[0];
      if (!b) { return; }
      var usu = String(b.textContent || '').trim();
      var vis = ultimoDe(usu);
      var tag = tds[0].querySelector('.p88-onoff');
      if (!tag) {
        tag = document.createElement('span');
        tag.className = 'p88-onoff';
        tds[0].appendChild(tag);
      }
      if (vis && vis > corte) {
        tag.className = 'p88-onoff on';
        tag.textContent = 'online';
        tag.title = 'Acessando o painel agora';
      } else if (vis) {
        tag.className = 'p88-onoff off';
        tag.textContent = 'visto ' + faz(vis);
        tag.title = 'Ultimo acesso em ' + hora(vis);
      } else {
        tag.className = 'p88-onoff off';
        tag.textContent = 'sem acesso ainda';
        tag.title = 'Este usuario ainda nao entrou neste navegador';
      }
    });

    var pe = document.getElementById('p87Pe');
    if (pe && !document.getElementById('p88VerHist')) {
      var bt = document.createElement('button');
      bt.id = 'p88VerHist';
      bt.type = 'button';
      bt.className = 'p87-btn';
      bt.textContent = 'Hist\u00f3rico de altera\u00e7\u00f5es';
      bt.addEventListener('click', function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        abrirHistorico();
      });
      pe.appendChild(bt);
    }
  }

  function badge() {
    var b = document.getElementById('p87Botao');
    if (!b) { return; }
    var g = document.getElementById('p88Badge');
    if (!g) {
      g = document.createElement('span');
      g.id = 'p88Badge';
      b.appendChild(g);
    }
    var n = online().length;
    g.textContent = n + (n === 1 ? ' acessando' : ' acessando');
    g.title = 'Janelas do painel abertas agora neste computador';
  }

  /* ================================================================ *
   * BLOCO C - guardar tudo que for alterado
   * ================================================================ */
  function historico() {
    var l = ler(K_HIST, []);
    return (l && l.length) ? l : [];
  }

  function registrar(acao, detalhe) {
    var s = sessao();
    var l = historico();
    l.push({
      ms: Date.now(),
      usuario: s ? s.usuario : '',
      nome: s ? (s.nome || s.usuario) : 'Sem login',
      perfil: s ? s.perfil : '',
      acao: String(acao || ''),
      detalhe: String(detalhe || '')
    });
    if (l.length > LIMITE) { l = l.slice(l.length - LIMITE); }
    gravar(K_HIST, l);
    var f = document.getElementById('p88Fundo');
    if (f) { desenharHist(); }
  }

  function apelido(k) {
    var t = String(k || '');
    t = t.replace(/^painel[_-]?/i, '').replace(/^ps\d+[_-]?/i, '');
    t = t.replace(/[_-]?v\d+$/i, '');
    t = t.replace(/[_-]+/g, ' ').trim();
    if (!t) { return String(k); }
    return t.charAt(0).toUpperCase() + t.slice(1);
  }

  function quantos(txt) {
    try {
      var v = JSON.parse(txt);
      if (v && v.length !== undefined && typeof v !== 'string') {
        return v.length + (v.length === 1 ? ' registro' : ' registros');
      }
      if (v && typeof v === 'object') {
        return Object.keys(v).length + ' itens';
      }
    } catch (e) { /* ignora */ }
    var n = String(txt || '').length;
    return n + ' caracteres';
  }

  function fotoUsuarios() {
    var l = ler(K_USERS, []);
    return (l && l.length) ? l : [];
  }

  function acharPor(lista, usu) {
    var i;
    for (i = 0; i < lista.length; i++) {
      if (String(lista[i].usuario).toLowerCase() === String(usu).toLowerCase()) { return lista[i]; }
    }
    return null;
  }

  function diffUsuarios() {
    var antes = ultimosUsuarios || [];
    var agora = fotoUsuarios();
    ultimosUsuarios = JSON.parse(JSON.stringify(agora));

    agora.forEach(function (u) {
      var v = acharPor(antes, u.usuario);
      if (!v) {
        registrar('Novo usu\u00e1rio cadastrado',
                  u.usuario + ' (' + (u.nome || u.usuario) + ') como ' + nomePerfil(u.perfil));
        return;
      }
      if (String(v.perfil || '') !== String(u.perfil || '')) {
        registrar('Tipo de acesso alterado',
                  u.usuario + ': de ' + nomePerfil(v.perfil) + ' para ' + nomePerfil(u.perfil));
      }
      if (String(v.hash || '') !== String(u.hash || '')) {
        registrar('Senha trocada', 'usu\u00e1rio ' + u.usuario);
      }
      if (String(v.nome || '') !== String(u.nome || '')) {
        registrar('Nome alterado', u.usuario + ': de ' + (v.nome || '-') + ' para ' + (u.nome || '-'));
      }
    });

    antes.forEach(function (v) {
      if (!acharPor(agora, v.usuario)) {
        registrar('Usu\u00e1rio exclu\u00eddo', v.usuario + ' (' + (v.nome || v.usuario) + ')');
      }
    });
  }

  function anotarChave(k, valor) {
    if (k === K_USERS) { diffUsuarios(); return; }
    if (atrasados[k]) { clearTimeout(atrasados[k]); }
    atrasados[k] = setTimeout(function () {
      delete atrasados[k];
      registrar('Alterou ' + apelido(k), 'agora com ' + quantos(valor));
    }, 1800);
  }

  function ligarEscuta() {
    var proto = null;
    try { proto = Object.getPrototypeOf(localStorage) || window.Storage.prototype; }
    catch (e) { proto = null; }
    if (!proto || proto.__p88ok) { return; }

    var oSet = proto.setItem;
    var oDel = proto.removeItem;

    proto.setItem = function (k, v) {
      var r = oSet.apply(this, arguments);
      try {
        if (!dentro && this === window.localStorage && IGNORAR.indexOf(String(k)) < 0) {
          anotarChave(String(k), v);
        }
      } catch (e) { /* ignora */ }
      return r;
    };

    proto.removeItem = function (k) {
      var r = oDel.apply(this, arguments);
      try {
        if (!dentro && this === window.localStorage && IGNORAR.indexOf(String(k)) < 0) {
          registrar('Apagou ' + apelido(String(k)), 'informa\u00e7\u00e3o removida do painel');
        }
      } catch (e) { /* ignora */ }
      return r;
    };

    proto.__p88ok = true;

    window.addEventListener('storage', function (ev) {
      if (!ev || !ev.key) { return; }
      if (ev.key === K_USERS) { try { diffUsuarios(); } catch (e) { /* ignora */ } }
      if (ev.key === K_HIST || ev.key === K_PRES) {
        try { if (document.getElementById('p88Fundo')) { desenharHist(); } } catch (e2) { /* ignora */ }
      }
    });
  }

  function anotarEntrada() {
    var s = sessao();
    if (!s) { return; }
    var marca = 'p88_entrada_' + String(s.usuario || '');
    try {
      if (sessionStorage.getItem(marca)) { return; }
      sessionStorage.setItem(marca, '1');
    } catch (e) { /* ignora */ }
    registrar('Entrou no painel', (s.nome || s.usuario) + ' - ' + nomePerfil(s.perfil));
  }

  /* ================================================================ *
   * tela do historico
   * ================================================================ */
  function fecharHist() {
    var f = document.getElementById('p88Fundo');
    if (f && f.parentNode) { f.parentNode.removeChild(f); }
  }

  function abrirHistorico() {
    estilo();
    fecharHist();

    var f = document.createElement('div');
    f.id = 'p88Fundo';
    f.setAttribute('data-ps79', '1');
    f.innerHTML =
      '<div id="p88Caixa" role="dialog" aria-modal="true" aria-labelledby="p88Tit">' +
        '<header><h3 id="p88Tit">Hist\u00f3rico de altera\u00e7\u00f5es</h3>' +
        '<button class="p87-btn" type="button" data-b="fechar">Fechar</button></header>' +
        '<div id="p88Corpo"></div>' +
        '<div id="p88Pe">' +
          '<input id="p88Busca" type="text" placeholder="Procurar por pessoa ou altera\u00e7\u00e3o...">' +
          '<button class="p87-btn" type="button" data-b="csv">Baixar hist\u00f3rico (CSV)</button>' +
          '<button class="p87-btn" type="button" data-b="atualizar">Atualizar</button>' +
          '<button class="p87-btn dan" type="button" data-b="limpar">Limpar hist\u00f3rico</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(f);

    f.addEventListener('click', function (ev) { if (ev.target === f) { fecharHist(); } });
    f.addEventListener('click', cliqueHist);
    var bu = document.getElementById('p88Busca');
    if (bu) { bu.addEventListener('input', function () { desenharHist(); }); }
    desenharHist();
  }

  function desenharHist() {
    var c = document.getElementById('p88Corpo');
    if (!c) { return; }
    var bu = document.getElementById('p88Busca');
    var filtro = bu ? String(bu.value || '').trim().toLowerCase() : '';
    var l = historico().slice().reverse();

    var h = '<div id="p88PresH" style="margin:0 0 12px"></div>';
    h += '<p style="margin:0 0 12px;font-size:12px;color:#475569;line-height:1.5">' +
         'Toda vez que algu\u00e9m mexe no painel (cadastro de usu\u00e1rio, troca de senha, ' +
         'mudan\u00e7a de tipo de acesso, lan\u00e7amentos e ajustes das telas) o painel guarda aqui ' +
         'a data, a hora e quem fez. O registro fica salvo neste computador/navegador.</p>';

    var vis = l.filter(function (r) {
      if (!filtro) { return true; }
      var txt = (r.nome + ' ' + r.usuario + ' ' + r.acao + ' ' + r.detalhe).toLowerCase();
      return txt.indexOf(filtro) >= 0;
    });

    if (!vis.length) {
      h += '<div class="p87-info">' +
           (filtro ? 'Nada encontrado para essa procura.'
                   : 'Ainda n\u00e3o h\u00e1 altera\u00e7\u00f5es registradas. A partir de agora tudo que for ' +
                     'mudado no painel aparece nesta lista.') + '</div>';
      c.innerHTML = h;
      pintarPresH();
      return;
    }

    h += '<table class="p88-tab"><thead><tr>' +
         '<th style="width:120px">Quando</th><th style="width:150px">Quem fez</th>' +
         '<th style="width:190px">O que aconteceu</th><th>Detalhe</th>' +
         '</tr></thead><tbody>';
    vis.slice(0, 400).forEach(function (r) {
      h += '<tr>' +
           '<td class="q">' + esc(hora(r.ms)) + '</td>' +
           '<td>' + esc(r.nome || r.usuario || 'Sem login') +
             (r.usuario ? '<div style="font-size:10.5px;color:#94a3b8">' + esc(r.usuario) + '</div>' : '') +
           '</td>' +
           '<td><b>' + esc(r.acao) + '</b></td>' +
           '<td>' + esc(r.detalhe) + '</td>' +
           '</tr>';
    });
    h += '</tbody></table>';
    h += '<div class="p87-info">Registros guardados: <b>' + historico().length + '</b>' +
         (vis.length > 400 ? ' (mostrando os 400 mais recentes desta procura)' : '') +
         '. O painel guarda as \u00faltimas ' + LIMITE + ' altera\u00e7\u00f5es.</div>';
    c.innerHTML = h;
    pintarPresH();
  }

  function pintarPresH() {
    var bh = document.getElementById('p88PresH');
    if (!bh) { return; }
    bh.setAttribute('data-ps79', '1');
    bh.innerHTML = '<div style="padding:10px 12px;border:1px solid #bbf7d0;background:#f0fdf4;' +
                   'border-radius:10px;font-size:12.5px;color:#14532d;line-height:1.6">' +
                   htmlPresenca() + '</div>';
  }

  function baixarCsvHist() {
    var l = historico();
    var lin = ['Data e hora;Quem fez;Usuario;Tipo de acesso;O que aconteceu;Detalhe'];
    l.slice().reverse().forEach(function (r) {
      lin.push([
        hora(r.ms),
        String(r.nome || '').replace(/;/g, ','),
        String(r.usuario || '').replace(/;/g, ','),
        nomePerfil(r.perfil).replace(/;/g, ','),
        String(r.acao || '').replace(/;/g, ','),
        String(r.detalhe || '').replace(/;/g, ',')
      ].join(';'));
    });
    try {
      var bl = new Blob(['\ufeff' + lin.join('\r\n')], { type: 'text/csv;charset=utf-8' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(bl);
      a.download = 'historico_do_painel.csv';
      document.body.appendChild(a);
      a.click();
      setTimeout(function () {
        try { URL.revokeObjectURL(a.href); } catch (e) { /* ignora */ }
        if (a.parentNode) { a.parentNode.removeChild(a); }
      }, 1500);
      aviso('Hist\u00f3rico baixado em CSV.');
    } catch (e) {
      aviso('N\u00e3o consegui gerar o arquivo.', 'err');
    }
  }

  function cliqueHist(ev) {
    var b = ev.target && ev.target.closest ? ev.target.closest('[data-b]') : null;
    if (!b) { return; }
    ev.preventDefault();
    var a = b.getAttribute('data-b');
    if (a === 'fechar') { fecharHist(); return; }
    if (a === 'atualizar') { desenharHist(); aviso('Hist\u00f3rico atualizado.'); return; }
    if (a === 'csv') { baixarCsvHist(); return; }
    if (a === 'limpar') {
      if (!ehAdmin()) { aviso('Somente o administrador pode limpar o hist\u00f3rico.', 'err'); return; }
      if (!window.confirm('Apagar todo o historico de alteracoes? Nao tem como desfazer.')) { return; }
      gravar(K_HIST, []);
      registrar('Hist\u00f3rico apagado', 'a lista de altera\u00e7\u00f5es foi zerada');
      desenharHist();
      aviso('Hist\u00f3rico apagado.');
      return;
    }
  }

  /* botao do historico no menu de abas */
  function caixaMenu() {
    return document.querySelector('#meu-menu-abas .tabs') ||
           document.querySelector('details#meu-menu-abas .tabs') ||
           null;
  }

  function colocarBotao() {
    var cx = caixaMenu();
    var b = document.getElementById('p88Botao');
    if (!b) {
      b = document.createElement('button');
      b.id = 'p88Botao';
      b.type = 'button';
      b.textContent = 'Hist\u00f3rico de altera\u00e7\u00f5es';
      b.setAttribute('title', 'Ver quem mexeu no painel e o que foi alterado');
      b.addEventListener('click', function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        abrirHistorico();
      });
    }
    if (cx) {
      if (b.parentNode !== cx) { cx.appendChild(b); }
      b.style.position = '';
    } else if (!b.parentNode) {
      b.style.cssText += ';position:fixed;right:14px;bottom:152px;z-index:2147482000;';
      document.body.appendChild(b);
    }
  }

  /* ================================================================ *
   * inicio
   * ================================================================ */
  function iniciar() {
    try { estilo(); } catch (e) { /* ignora */ }
    try { ultimosUsuarios = fotoUsuarios(); } catch (e) { /* ignora */ }
    try { ligarEscuta(); } catch (e) { /* ignora */ }
    try { bater(); } catch (e) { /* ignora */ }
    try { anotarEntrada(); } catch (e) { /* ignora */ }
    try { colocarBotao(); } catch (e) { /* ignora */ }

    setInterval(function () { try { bater(); } catch (e) { /* ignora */ } }, BATIDA);

    setInterval(function () {
      try { colocarBotao(); } catch (e) { /* ignora */ }
      try { badge(); } catch (e2) { /* ignora */ }
      try { if (document.getElementById('p87Corpo')) { enfeitar(); } } catch (e3) { /* ignora */ }
      try { if (document.getElementById('p88Fundo')) { pintarPresH(); } } catch (e4) { /* ignora */ }
    }, 3000);

    /* quando a tela de usuarios se redesenha, coloca de novo o bloco verde */
    try {
      var ob = new MutationObserver(function () {
        try { if (document.getElementById('p87Corpo')) { enfeitar(); } } catch (e) { /* ignora */ }
      });
      ob.observe(document.body, { childList: true, subtree: true });
    } catch (e5) { /* ignora */ }

    document.addEventListener('keydown', function (ev) {
      var k = ev.key || ev.keyCode;
      if (k !== 'Escape' && k !== 'Esc' && k !== 27) { return; }
      if (document.getElementById('p88Fundo')) {
        ev.stopPropagation();
        fecharHist();
      }
    }, true);

    window.addEventListener('beforeunload', function () {
      try {
        var id = meuId();
        var l = presencas().filter(function (p) { return p.id !== id; });
        gravar(K_PRES, l);
      } catch (e) { /* ignora */ }
    });

    window.p88Historico = function () { abrirHistorico(); return true; };
    window.PainelHistorico = {
      abrir: abrirHistorico,
      lista: historico,
      online: online,
      anotar: registrar
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();
"""


def achar_arquivo():
    for nome in ('index.html', 'Index.html', 'INDEX.html'):
        if os.path.isfile(nome):
            return nome
    for nome in os.listdir('.'):
        if nome.lower() == 'index.html':
            return nome
    return None


def main():
    alvo = achar_arquivo()
    if not alvo:
        print('ERRO: index.html nao encontrado nesta pasta.')
        print('Coloque este script na mesma pasta do painel e rode de novo.')
        return 1

    with io.open(alvo, encoding='utf-8', errors='surrogateescape', newline='') as f:
        html = f.read()

    if MARCA in html:
        print('Este patch ja foi aplicado antes. Nada a fazer.')
        return 0

    pos = html.rfind('</body>')
    if pos < 0:
        pos = html.rfind('</html>')
    if pos < 0:
        print('ERRO: nao encontrei o final da pagina (</body>).')
        return 1

    quebra = '\r\n' if '\r\n' in html[:4000] else '\n'

    bloco = (
        quebra + '<!-- ' + MARCA + ' -->' + quebra
        + '<script>' + quebra
        + JS.replace('\n', quebra)
        + '</script>' + quebra
    )

    novo = html[:pos] + bloco + html[pos:]

    selo = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = alvo + '.bak_patch88_' + selo
    shutil.copyfile(alvo, backup)

    with io.open(alvo, 'w', encoding='utf-8', errors='surrogateescape', newline='') as f:
        f.write(novo)

    print('PATCH 88 aplicado com sucesso.')
    print('  - caixa "Usuarios cadastrados" centralizada na tela e um pouco menor')
    print('  - faixa verde "Quem esta acessando agora" com os conectados no momento')
    print('  - etiqueta online / visto ha X minutos em cada usuario da lista')
    print('  - contador de janelas abertas no botao do menu')
    print('  - nova tela "Historico de alteracoes" com data, hora, quem fez e o que mudou')
    print('  - busca no historico, download em CSV e limpeza pelo administrador')
    print('Backup salvo em: ' + backup)
    print('')
    print('Agora recarregue o painel (Ctrl + F5).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
