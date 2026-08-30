# -*- coding: utf-8 -*-
"""
PATCH 87 - Conserta a reabertura das janelas e cria a tela
            "Usuarios cadastrados"

O que faz:
  1) Janela que fechava e nao abria mais:
     o Diario de Obra (e tambem o Boletim de Inspecao e a tela
     Cabecalho e logo) podia fechar e depois nao abrir de novo, ficando
     invisivel mesmo apertando o botao. Isto acontecia porque os
     patches anteriores deixavam uma marca de "escondido" na janela que
     nao era retirada na hora de abrir. Agora, sempre que voce clica no
     botao, o painel tira essa marca e forca a janela a aparecer,
     insistindo por alguns instantes ate ela ficar visivel. Vale para
     todas as vezes, quantas vezes voce abrir e fechar.

  2) Nova tela "Usuarios cadastrados":
     nasce no Menu de Abas um botao roxo "Usuarios cadastrados", que
     mostra a lista de todos os acessos criados no painel:
       - nome, usuario, tipo de acesso e data em que foi criado;
       - a senha nunca aparece (fica gravada embaralhada);
       - o administrador pode mudar o tipo de acesso de cada pessoa,
         trocar a senha de quem esqueceu e excluir um acesso;
       - quem nao e administrador ve a lista somente para consulta;
       - botao "Cadastrar usuario" para criar um acesso na hora;
       - botao para baixar a lista em CSV (abre no Excel);
       - o painel nao deixa apagar nem rebaixar o ultimo
         administrador, para nunca ficar sem ninguem no comando.
     Os usuarios ficam guardados no proprio navegador do computador,
     por isso a lista e a daquele aparelho.

Como usar:
  Coloque este arquivo na mesma pasta do index.html e execute:
      python patch87_reabrir_e_usuarios.py

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

MARCA = 'PATCH87_REABRIR_USUARIOS_OK'

JS = r"""/* PATCH 87 - conserta a reabertura das janelas (Diario de Obra, Boletim,
   Cabecalho) e cria a tela "Usuarios cadastrados".
   Nao reescreve nada do painel: apenas acrescenta e envolve funcoes. */
(function () {
  'use strict';

  if (window.__p87) { return; }
  window.__p87 = true;

  var PREFS = ['p83', 'p84', 'p86'];
  var OCULTAS = ['p86-oculto', 'p86b-oculto', 'p87-oculto'];

  var K_USERS = 'painel_seg_usuarios_v1';
  var K_SESS  = 'painel_seg_sessao_v1';

  /* ================================================================ *
   * utilidades
   * ================================================================ */
  function esc(v) {
    return String(v === undefined || v === null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
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

  function estilo() {
    if (document.getElementById('p87Estilo')) { return; }
    var s = document.createElement('style');
    s.id = 'p87Estilo';
    s.textContent = [
      '.p87-aviso{position:fixed;left:50%;top:22px;transform:translateX(-50%);z-index:2147483500;background:#15803d;color:#fff;padding:11px 18px;border-radius:10px;font:13px Segoe UI,Arial,sans-serif;box-shadow:0 8px 24px rgba(0,0,0,.3)}',
      '.p87-aviso.err{background:#b91c1c}',
      '#p87Botao{background:#7c3aed;color:#fff;border:none;border-radius:10px;padding:8px 14px;font-weight:600;cursor:pointer;margin:4px;font-size:13px}',
      '#p87Botao:hover{filter:brightness(1.1)}',
      '#meu-menu-abas #p87Botao{display:block;width:100%;box-sizing:border-box;margin:3px 0 !important;text-align:left}',
      '#p87Fundo{position:fixed;inset:0;z-index:2147483200;background:rgba(15,23,42,.62);display:flex;align-items:center;justify-content:center;padding:16px;font-family:Segoe UI,Arial,sans-serif}',
      '#p87Caixa{background:#fff;border-radius:14px;width:100%;max-width:860px;max-height:92vh;display:flex;flex-direction:column;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.4)}',
      '#p87Caixa header{display:flex;align-items:center;justify-content:space-between;gap:10px;background:#16304f;color:#fff;padding:12px 16px}',
      '#p87Caixa header h3{margin:0;font-size:16px}',
      '#p87Corpo{padding:16px;overflow:auto}',
      '#p87Pe{display:flex;gap:8px;flex-wrap:wrap;padding:12px 16px;border-top:1px solid #e2e8f0;background:#f8fafc}',
      '.p87-btn{border:1px solid #cbd5e1;border-radius:8px;background:#f1f5f9;color:#16304f;padding:8px 13px;font-size:13px;font-weight:600;cursor:pointer}',
      '.p87-btn.pri{background:#2563eb;border-color:#2563eb;color:#fff}',
      '.p87-btn.dan{background:#fee2e2;border-color:#fca5a5;color:#b91c1c}',
      '.p87-btn.mini{padding:5px 9px;font-size:11px}',
      '#p87Caixa header .p87-btn{background:#e2e8f0}',
      '#p87Corpo p.sb{margin:0 0 14px;font-size:12.5px;color:#475569;line-height:1.5}',
      'table.p87-tab{width:100%;border-collapse:collapse;font-size:13px}',
      'table.p87-tab th{background:#1e3a5f;color:#fff;text-align:left;padding:8px;font-size:11.5px;text-transform:uppercase;letter-spacing:.3px}',
      'table.p87-tab td{border-bottom:1px solid #e2e8f0;padding:7px 8px;color:#1e293b;vertical-align:middle}',
      'table.p87-tab td.ac{white-space:nowrap;display:flex;gap:5px;flex-wrap:wrap}',
      'table.p87-tab select{padding:5px 7px;border:1px solid #cbd5e1;border-radius:6px;font-size:12px;background:#fff;color:#1e293b}',
      '.p87-tagadm{display:inline-block;background:#dbeafe;color:#1d4ed8;border-radius:999px;padding:2px 8px;font-size:11px;font-weight:700}',
      '.p87-info{margin:14px 0 0;padding:10px 12px;border-radius:8px;background:#eff6ff;border:1px solid #bfdbfe;color:#1e3a5f;font-size:12px;line-height:1.55}',
      '.p87-novo{margin:0 0 16px;padding:12px;border:1px solid #e2e8f0;border-radius:10px;background:#f8fafc;display:none}',
      '.p87-novo.on{display:block}',
      '.p87-novo .lin{display:flex;gap:10px;flex-wrap:wrap}',
      '.p87-novo label{display:block;font-size:11px;font-weight:700;color:#475569;text-transform:uppercase;letter-spacing:.3px;margin:0 0 3px}',
      '.p87-novo input,.p87-novo select{padding:7px 9px;border:1px solid #cbd5e1;border-radius:7px;font-size:13px;min-width:150px;background:#fff;color:#1e293b}',
      '.p87-novo .er{margin-top:8px;font-size:12px;color:#b91c1c;min-height:15px}',
      'body.dark-mode #p87Caixa{background:#0f172a}',
      'body.dark-mode #p87Corpo p.sb{color:#94a3b8}',
      'body.dark-mode table.p87-tab td{color:#e2e8f0;border-color:#334155}',
      'body.dark-mode #p87Pe{background:#111c33;border-color:#334155}',
      'body.dark-mode .p87-novo{background:#111c33;border-color:#334155}'
    ].join('\n');
    (document.head || document.documentElement).appendChild(s);
  }

  /* ================================================================ *
   * BLOCO A - deixar as janelas reabrirem sempre
   * ================================================================ */
  function destravar(f) {
    if (!f) { return; }
    try {
      OCULTAS.forEach(function (c) { f.classList.remove(c); });
    } catch (e) { /* ignora */ }
    try { f.style.setProperty('display', 'flex', 'important'); } catch (e2) { f.style.display = 'flex'; }
  }

  function estaEscondido(f) {
    if (!f) { return false; }
    var i;
    for (i = 0; i < OCULTAS.length; i++) {
      try { if (f.classList.contains(OCULTAS[i])) { return true; } } catch (e) { /* ignora */ }
    }
    var d = '';
    try { d = window.getComputedStyle(f).display; } catch (e2) { d = f.style.display; }
    return d === 'none';
  }

  /* depois de clicar para abrir, insiste algumas vezes para a janela aparecer */
  function insistir(pref, vezes) {
    var n = vezes || 12;
    var conta = 0;
    var t = setInterval(function () {
      conta++;
      var f = document.getElementById(pref + 'Fundo');
      if (f) {
        var querAbrir = (f.style && f.style.display && f.style.display !== 'none');
        if (querAbrir || estaEscondido(f)) { destravar(f); }
      }
      if (conta >= n) { clearInterval(t); }
    }, 60);
  }

  /* olho permanente: quando qualquer uma dessas janelas pedir para aparecer,
     tira as marcas de oculto deixadas pelos patches anteriores */
  function vigiar(f) {
    if (!f || f.getAttribute('data-p87olho') === '1') { return; }
    f.setAttribute('data-p87olho', '1');
    try {
      var olho = new MutationObserver(function () {
        if (f.style && f.style.display && f.style.display !== 'none') {
          OCULTAS.forEach(function (c) {
            try { f.classList.remove(c); } catch (e) { /* ignora */ }
          });
        }
      });
      olho.observe(f, { attributes: true, attributeFilter: ['style', 'class'] });
    } catch (e) { /* ignora */ }
  }

  function varrer() {
    PREFS.forEach(function (p) {
      var f = document.getElementById(p + 'Fundo');
      if (f) { vigiar(f); }
    });
  }

  function envolverAbrir() {
    var mapa = [
      ['p84AbrirDiario', 'p84'],
      ['p83AbrirBoletim', 'p83'],
      ['p86AjustarCabecalho', 'p86']
    ];
    mapa.forEach(function (par) {
      var nome = par[0];
      var pref = par[1];
      var ant = window[nome];
      if (typeof ant !== 'function' || ant.__p87) { return; }
      var nova = function () {
        var f = document.getElementById(pref + 'Fundo');
        destravar(f);
        var r;
        try { r = ant.apply(this, arguments); } catch (e) { r = null; }
        destravar(document.getElementById(pref + 'Fundo'));
        insistir(pref, 12);
        return r;
      };
      nova.__p87 = true;
      window[nome] = nova;
    });
  }

  function ligarBotoes() {
    if (window.__p87Clique) { return; }
    window.__p87Clique = true;

    document.addEventListener('click', function (ev) {
      var alvo = ev.target;
      if (!alvo || !alvo.closest) { return; }
      var b = alvo.closest('#p83Botao,#p84Botao,#p86Botao');
      if (!b) { return; }
      var pref = String(b.id).replace('Botao', '');
      destravar(document.getElementById(pref + 'Fundo'));
      insistir(pref, 14);
    }, true);
  }

  function ligarReabrir() {
    varrer();
    envolverAbrir();
    ligarBotoes();

    /* o olho fica ligado para sempre: as janelas nascem so no primeiro uso */
    try {
      var olho = new MutationObserver(function () { varrer(); envolverAbrir(); });
      olho.observe(document.body, { childList: true });
    } catch (e) { /* ignora */ }
    setInterval(function () {
      try { varrer(); envolverAbrir(); } catch (e2) { /* ignora */ }
    }, 2500);

    /* atalho manual, caso precise abrir pelo console */
    window.p87AbrirDiario = function () {
      var f = document.getElementById('p84Fundo');
      destravar(f);
      if (typeof window.p84AbrirDiario === 'function') { window.p84AbrirDiario(); }
      insistir('p84', 14);
      return true;
    };
  }

  /* ================================================================ *
   * BLOCO B - tela "Usuarios cadastrados"
   * ================================================================ */
  var _K = [1116352408,1899447441,3049323471,3921009573,961987163,1508970993,2453635748,2870763221,3624381080,310598401,607225278,1426881987,1925078388,2162078206,2614888103,3248222580,3835390401,4022224774,264347078,604807628,770255983,1249150122,1555081692,1996064986,2554220882,2821834349,2952996808,3210313671,3336571891,3584528711,113926993,338241895,666307205,773529912,1294757372,1396182291,1695183700,1986661051,2177026350,2456956037,2730485921,2820302411,3259730800,3345764771,3516065817,3600352804,4094571909,275423344,430227734,506948616,659060556,883997877,958139571,1322822218,1537002063,1747873779,1955562222,2024104815,2227730452,2361852424,2428436474,2756734187,3204031479,3329325298];

  function sha256(str) {
    var bytes = [], i, s = encodeURIComponent(String(str));
    for (i = 0; i < s.length; i++) {
      if (s.charAt(i) === '%') { bytes.push(parseInt(s.substr(i + 1, 2), 16)); i += 2; }
      else { bytes.push(s.charCodeAt(i)); }
    }
    var l = bytes.length;
    bytes.push(0x80);
    while (bytes.length % 64 !== 56) { bytes.push(0); }
    var bits = l * 8;
    bytes.push(0, 0, 0, 0);
    bytes.push((bits >>> 24) & 255, (bits >>> 16) & 255, (bits >>> 8) & 255, bits & 255);
    var H = [1779033703,3144134277,1013904242,2773480762,1359893119,2600822924,528734635,1541459225];
    var w = new Array(64);
    function rr(x, n) { return (x >>> n) | (x << (32 - n)); }
    for (var off = 0; off < bytes.length; off += 64) {
      for (i = 0; i < 16; i++) {
        w[i] = (bytes[off+i*4] << 24) | (bytes[off+i*4+1] << 16) | (bytes[off+i*4+2] << 8) | bytes[off+i*4+3];
      }
      for (i = 16; i < 64; i++) {
        var s0 = rr(w[i-15],7) ^ rr(w[i-15],18) ^ (w[i-15] >>> 3);
        var s1 = rr(w[i-2],17) ^ rr(w[i-2],19) ^ (w[i-2] >>> 10);
        w[i] = (w[i-16] + s0 + w[i-7] + s1) | 0;
      }
      var a=H[0],b=H[1],c=H[2],d=H[3],e=H[4],f=H[5],g=H[6],h=H[7];
      for (i = 0; i < 64; i++) {
        var S1 = rr(e,6) ^ rr(e,11) ^ rr(e,25);
        var ch = (e & f) ^ ((~e) & g);
        var t1 = (h + S1 + ch + _K[i] + w[i]) | 0;
        var S0 = rr(a,2) ^ rr(a,13) ^ rr(a,22);
        var mj = (a & b) ^ (a & c) ^ (b & c);
        var t2 = (S0 + mj) | 0;
        h=g; g=f; f=e; e=(d+t1)|0; d=c; c=b; b=a; a=(t1+t2)|0;
      }
      H[0]=(H[0]+a)|0; H[1]=(H[1]+b)|0; H[2]=(H[2]+c)|0; H[3]=(H[3]+d)|0;
      H[4]=(H[4]+e)|0; H[5]=(H[5]+f)|0; H[6]=(H[6]+g)|0; H[7]=(H[7]+h)|0;
    }
    var out = '';
    for (i = 0; i < 8; i++) { out += ('00000000' + (H[i] >>> 0).toString(16)).slice(-8); }
    return out;
  }

  function hashSenha(usuario, senha) {
    return sha256('ps79|' + String(usuario).toLowerCase() + '|' + String(senha));
  }

  function lerJson(k, def) {
    try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch (e) { return def; }
  }

  function gravarJson(k, v) {
    try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; }
  }

  function usuarios() {
    var u = lerJson(K_USERS, null);
    return (u && u.length) ? u : [];
  }

  function sessao() {
    var s = null;
    try { s = JSON.parse(sessionStorage.getItem(K_SESS) || 'null'); } catch (e) { s = null; }
    if (!s) { s = lerJson(K_SESS, null); }
    if (s && s.exp && Date.now() > s.exp) { s = null; }
    return s;
  }

  function podeMexer() {
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

  function dataBr(ms) {
    if (!ms) { return '-'; }
    try {
      var d = new Date(Number(ms));
      if (isNaN(d.getTime())) { return '-'; }
      return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR').slice(0, 5);
    } catch (e) { return '-'; }
  }

  function quantosAdmins(lista) {
    var n = 0, i;
    for (i = 0; i < lista.length; i++) {
      if (String(lista[i].perfil || '').toLowerCase() === 'admin') { n++; }
    }
    return n;
  }

  function fecharTela() {
    var f = document.getElementById('p87Fundo');
    if (f && f.parentNode) { f.parentNode.removeChild(f); }
  }

  function abrirUsuarios() {
    estilo();
    fecharTela();

    var f = document.createElement('div');
    f.id = 'p87Fundo';
    f.setAttribute('data-ps79', '1');
    f.innerHTML =
      '<div id="p87Caixa" role="dialog" aria-modal="true" aria-labelledby="p87Tit">' +
        '<header><h3 id="p87Tit">Usu\u00e1rios cadastrados</h3>' +
        '<button class="p87-btn" type="button" data-a="fechar">Fechar</button></header>' +
        '<div id="p87Corpo"></div>' +
        '<div id="p87Pe">' +
          '<button class="p87-btn pri" type="button" data-a="novo">Cadastrar usu\u00e1rio</button>' +
          '<button class="p87-btn" type="button" data-a="csv">Baixar lista (CSV)</button>' +
          '<button class="p87-btn" type="button" data-a="atualizar">Atualizar</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(f);

    f.addEventListener('click', function (ev) {
      if (ev.target === f) { fecharTela(); }
    });
    f.addEventListener('click', aoClicar);
    f.addEventListener('change', aoTrocar);
    desenhar();
  }

  function desenhar() {
    var c = document.getElementById('p87Corpo');
    if (!c) { return; }
    var lista = usuarios();
    var s = sessao();
    var manda = podeMexer();

    var h = '';
    h += '<p class="sb">Esta \u00e9 a lista de acessos criados na tela de entrada do painel. ' +
         'Os usu\u00e1rios ficam guardados neste computador/navegador, por isso quem entrar de outro ' +
         'aparelho precisa criar o acesso dele l\u00e1 tamb\u00e9m. A senha nunca aparece: fica gravada ' +
         'embaralhada, s\u00f3 d\u00e1 para trocar por uma nova.</p>';

    if (s) {
      h += '<p class="sb">Voc\u00ea est\u00e1 conectado como <b>' + esc(s.nome || s.usuario) +
           '</b> (' + esc(nomePerfil(s.perfil)) + ').' +
           (manda ? '' : ' Como n\u00e3o \u00e9 administrador, esta tela fica somente para consulta.') + '</p>';
    }

    h += '<div class="p87-novo" id="p87Novo">' +
           '<div class="lin">' +
             '<div><label>Nome completo</label><input id="p87nNome" type="text"></div>' +
             '<div><label>Usu\u00e1rio</label><input id="p87nUsu" type="text"></div>' +
             '<div><label>Senha</label><input id="p87nSe" type="password"></div>' +
             '<div><label>Tipo de acesso</label><select id="p87nTipo">' +
               '<option value="visitante">Somente consulta</option>' +
               '<option value="editor">Pode lan\u00e7ar e editar</option>' +
               '<option value="admin">Administrador</option>' +
             '</select></div>' +
           '</div>' +
           '<div class="er" id="p87nEr"></div>' +
           '<div style="display:flex;gap:8px;margin-top:6px">' +
             '<button class="p87-btn pri" type="button" data-a="salvarNovo">Salvar usu\u00e1rio</button>' +
             '<button class="p87-btn" type="button" data-a="cancelarNovo">Cancelar</button>' +
           '</div>' +
         '</div>';

    if (!lista.length) {
      h += '<div class="p87-info">Ainda n\u00e3o existe nenhum usu\u00e1rio salvo neste navegador. ' +
           'Use o bot\u00e3o "Cadastrar usu\u00e1rio" aqui embaixo, ou o bot\u00e3o "Criar novo usu\u00e1rio" ' +
           'da tela de entrada do painel.</div>';
      c.innerHTML = h;
      return;
    }

    h += '<table class="p87-tab"><thead><tr>' +
         '<th>Nome</th><th>Usu\u00e1rio</th><th>Tipo de acesso</th><th>Criado em</th><th>A\u00e7\u00f5es</th>' +
         '</tr></thead><tbody>';

    lista.forEach(function (u, i) {
      var ehAdm = String(u.perfil || '').toLowerCase() === 'admin';
      h += '<tr>';
      h += '<td>' + esc(u.nome || u.usuario) + '</td>';
      h += '<td><b>' + esc(u.usuario) + '</b>' + (ehAdm ? ' <span class="p87-tagadm">admin</span>' : '') + '</td>';
      if (manda) {
        h += '<td><select data-a="tipo" data-i="' + i + '">' +
             ['visitante', 'editor', 'admin'].map(function (v) {
               var sel = (String(u.perfil || 'visitante').toLowerCase() === v) ? ' selected' : '';
               return '<option value="' + v + '"' + sel + '>' + esc(nomePerfil(v)) + '</option>';
             }).join('') + '</select></td>';
      } else {
        h += '<td>' + esc(nomePerfil(u.perfil)) + '</td>';
      }
      h += '<td>' + esc(dataBr(u.criadoEm)) + '</td>';
      h += '<td class="ac">';
      if (manda) {
        h += '<button class="p87-btn mini" type="button" data-a="senha" data-i="' + i + '">Trocar senha</button>';
        h += '<button class="p87-btn mini dan" type="button" data-a="excluir" data-i="' + i + '">Excluir</button>';
      } else {
        h += '<span style="font-size:11px;color:#94a3b8">somente consulta</span>';
      }
      h += '</td></tr>';
    });

    h += '</tbody></table>';
    h += '<div class="p87-info">Total de acessos: <b>' + lista.length + '</b>. ' +
         'Administradores: <b>' + quantosAdmins(lista) + '</b>. ' +
         'Guarde sempre pelo menos um administrador, sen\u00e3o ningu\u00e9m poder\u00e1 mexer nesta tela.</div>';
    c.innerHTML = h;
  }

  function aoTrocar(ev) {
    var el = ev.target;
    if (!el || el.getAttribute('data-a') !== 'tipo') { return; }
    if (!podeMexer()) { return; }
    var i = Number(el.getAttribute('data-i'));
    var lista = usuarios();
    if (!lista[i]) { return; }
    var antes = lista[i].perfil;
    lista[i].perfil = el.value;
    if (antes === 'admin' && el.value !== 'admin' && quantosAdmins(lista) === 0) {
      aviso('Precisa sobrar pelo menos um administrador.', 'err');
      desenhar();
      return;
    }
    if (gravarJson(K_USERS, lista)) {
      aviso('Tipo de acesso de ' + (lista[i].usuario) + ' alterado.');
    } else {
      aviso('N\u00e3o consegui salvar neste navegador.', 'err');
    }
    desenhar();
  }

  function baixarCsv() {
    var lista = usuarios();
    var lin = ['Nome;Usuario;Tipo de acesso;Criado em'];
    lista.forEach(function (u) {
      lin.push([
        String(u.nome || u.usuario).replace(/;/g, ','),
        String(u.usuario).replace(/;/g, ','),
        nomePerfil(u.perfil).replace(/;/g, ','),
        dataBr(u.criadoEm)
      ].join(';'));
    });
    try {
      var bl = new Blob(['\ufeff' + lin.join('\r\n')], { type: 'text/csv;charset=utf-8' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(bl);
      a.download = 'usuarios_do_painel.csv';
      document.body.appendChild(a);
      a.click();
      setTimeout(function () {
        try { URL.revokeObjectURL(a.href); } catch (e) { /* ignora */ }
        if (a.parentNode) { a.parentNode.removeChild(a); }
      }, 1500);
      aviso('Lista baixada em CSV.');
    } catch (e) {
      aviso('N\u00e3o consegui gerar o arquivo.', 'err');
    }
  }

  function salvarNovo() {
    var elN = document.getElementById('p87nNome');
    var elU = document.getElementById('p87nUsu');
    var elS = document.getElementById('p87nSe');
    var elT = document.getElementById('p87nTipo');
    var er  = document.getElementById('p87nEr');
    if (!elN || !elU || !elS || !er) { return; }

    var nome = String(elN.value || '').trim();
    var usu  = String(elU.value || '').trim().toLowerCase();
    var se   = String(elS.value || '');

    if (!nome) { er.textContent = 'Escreva o nome completo.'; return; }
    if (usu.length < 3) { er.textContent = 'O usu\u00e1rio precisa de pelo menos 3 caracteres.'; return; }
    if (!/^[a-z0-9._-]+$/.test(usu)) {
      er.textContent = 'Use apenas letras sem acento, n\u00fameros, ponto, tra\u00e7o ou sublinhado.';
      return;
    }
    if (se.length < 4) { er.textContent = 'A senha precisa de pelo menos 4 caracteres.'; return; }

    var lista = usuarios();
    var i;
    for (i = 0; i < lista.length; i++) {
      if (String(lista[i].usuario).toLowerCase() === usu) {
        er.textContent = 'J\u00e1 existe um usu\u00e1rio com esse nome.';
        return;
      }
    }
    lista.push({
      usuario: usu,
      nome: nome,
      perfil: elT ? elT.value : 'visitante',
      hash: hashSenha(usu, se),
      trocar: false,
      criadoEm: Date.now()
    });
    if (!gravarJson(K_USERS, lista)) {
      er.textContent = 'N\u00e3o consegui salvar neste navegador.';
      return;
    }
    aviso('Usu\u00e1rio ' + usu + ' cadastrado.');
    desenhar();
  }

  function aoClicar(ev) {
    var b = ev.target && ev.target.closest ? ev.target.closest('[data-a]') : null;
    if (!b) { return; }
    var a = b.getAttribute('data-a');
    if (a === 'tipo') { return; }
    ev.preventDefault();

    if (a === 'fechar') { fecharTela(); return; }
    if (a === 'atualizar') { desenhar(); aviso('Lista atualizada.'); return; }
    if (a === 'csv') { baixarCsv(); return; }

    if (a === 'novo') {
      if (!podeMexer()) { aviso('Somente o administrador pode cadastrar.', 'err'); return; }
      var cx = document.getElementById('p87Novo');
      if (cx) {
        cx.classList.add('on');
        var el = document.getElementById('p87nNome');
        if (el) { try { el.focus(); } catch (e) { /* ignora */ } }
      }
      return;
    }
    if (a === 'cancelarNovo') {
      var cx2 = document.getElementById('p87Novo');
      if (cx2) { cx2.classList.remove('on'); }
      return;
    }
    if (a === 'salvarNovo') { salvarNovo(); return; }

    if (!podeMexer()) { return; }
    var lista = usuarios();
    var i = Number(b.getAttribute('data-i'));
    if (!lista[i]) { return; }

    if (a === 'senha') {
      var nova = window.prompt('Nova senha para ' + lista[i].usuario + ' (m\u00ednimo 4 caracteres):', '');
      if (nova === null) { return; }
      nova = String(nova);
      if (nova.length < 4) { aviso('Senha muito curta. Nada foi mudado.', 'err'); return; }
      lista[i].hash = hashSenha(lista[i].usuario, nova);
      lista[i].trocar = false;
      if (gravarJson(K_USERS, lista)) {
        aviso('Senha de ' + lista[i].usuario + ' trocada.');
      } else {
        aviso('N\u00e3o consegui salvar neste navegador.', 'err');
      }
      return;
    }

    if (a === 'excluir') {
      var u = lista[i];
      if (String(u.perfil || '').toLowerCase() === 'admin' && quantosAdmins(lista) <= 1) {
        aviso('Este \u00e9 o \u00fanico administrador. N\u00e3o pode ser exclu\u00eddo.', 'err');
        return;
      }
      if (!window.confirm('Excluir o acesso de ' + (u.nome || u.usuario) + '? Nao tem como desfazer.')) { return; }
      lista.splice(i, 1);
      if (gravarJson(K_USERS, lista)) {
        aviso('Acesso exclu\u00eddo.');
      } else {
        aviso('N\u00e3o consegui salvar neste navegador.', 'err');
      }
      desenhar();
      return;
    }
  }

  /* ---- botao no menu de abas ---- */
  function caixaMenu() {
    return document.querySelector('#meu-menu-abas .tabs') ||
           document.querySelector('details#meu-menu-abas .tabs') ||
           null;
  }

  function colocarBotao() {
    var cx = caixaMenu();
    var b = document.getElementById('p87Botao');
    if (!b) {
      b = document.createElement('button');
      b.id = 'p87Botao';
      b.type = 'button';
      b.textContent = 'Usu\u00e1rios cadastrados';
      b.setAttribute('title', 'Ver quem tem acesso ao painel neste computador');
      b.addEventListener('click', function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        abrirUsuarios();
      });
    }
    if (cx) {
      if (b.parentNode !== cx) { cx.appendChild(b); }
      b.style.position = '';
    } else if (!b.parentNode) {
      b.style.cssText += ';position:fixed;right:14px;bottom:196px;z-index:2147482000;';
      document.body.appendChild(b);
    }
  }

  /* ================================================================ *
   * inicio
   * ================================================================ */
  function iniciar() {
    try { estilo(); } catch (e) { /* ignora */ }
    try { ligarReabrir(); } catch (e) { /* ignora */ }
    try { colocarBotao(); } catch (e) { /* ignora */ }
    setInterval(function () {
      try { colocarBotao(); } catch (e) { /* ignora */ }
    }, 2000);

    document.addEventListener('keydown', function (ev) {
      var k = ev.key || ev.keyCode;
      if (k !== 'Escape' && k !== 'Esc' && k !== 27) { return; }
      if (document.getElementById('p87Fundo')) {
        ev.stopPropagation();
        fecharTela();
      }
    }, true);

    window.p87Usuarios = function () { abrirUsuarios(); return true; };
    window.PainelUsuarios = { abrir: abrirUsuarios, lista: usuarios };
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
    backup = alvo + '.bak_patch87_' + selo
    shutil.copyfile(alvo, backup)

    with io.open(alvo, 'w', encoding='utf-8', errors='surrogateescape', newline='') as f:
        f.write(novo)

    print('PATCH 87 aplicado com sucesso.')
    print('  - Diario de Obra, Boletim e Cabecalho voltam a abrir sempre depois de fechar')
    print('  - novo botao roxo "Usuarios cadastrados" no Menu de Abas')
    print('  - lista com nome, usuario, tipo de acesso e data de criacao')
    print('  - administrador pode mudar o tipo de acesso, trocar senha e excluir')
    print('  - cadastro rapido de usuario e download da lista em CSV')
    print('  - protecao para nunca ficar sem administrador')
    print('Backup salvo em: ' + backup)
    print('')
    print('Agora recarregue o painel (Ctrl + F5).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
