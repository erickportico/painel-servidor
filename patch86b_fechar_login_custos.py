# -*- coding: utf-8 -*-
"""
PATCH 86B - Botao Fechar, Login com cadastro de usuario e
            tabela Custos x Pagamentos

O que faz:
  1) Botao Fechar dos relatorios:
     nos relatorios Boletim de Inspecao (FORM 07) e Diario de Obra
     o botao Fechar volta a funcionar sempre, mesmo depois de
     salvar, imprimir ou gerar PDF. Alem do botao, a tecla Esc e o
     clique na area escura em volta tambem fecham a janela.
  2) Login com usuario e senha + cadastro:
     na tela de entrada aparece o botao "Criar novo usuario", que
     abre uma tela publica de cadastro (nome, usuario, senha,
     repetir a senha e tipo de acesso). O usuario criado ja pode
     entrar em seguida. Se a pagina ainda nao tiver nenhuma tela
     de login, este patch passa a cuidar da entrada, com a opcao
     "Manter conectado neste computador" e um botao Sair no canto.
     O primeiro usuario criado no computador entra como
     administrador. As senhas nao ficam guardadas em texto, apenas
     um codigo embaralhado delas.
  3) Tabela Custos x Pagamentos:
     dentro de Centro de Custos nasce a sub-aba
     "Custos x Pagamentos", que compara o que foi calculado nos
     lancamentos de producao com o que foi realmente pago:
       - resumo em cartoes: lancamentos, custo de producao, total
         pago, saldo, outras despesas e custo geral
       - tabela por colaborador: diarias, valor como profissional,
         valor como ajudante, devido, pago e saldo
       - tabela por obra: lancamentos, metragem, custo de producao,
         outras despesas, custo total, pago e saldo
       - lista "Em aberto" com quem ainda falta pagar
       - filtros por mes e por obra e botao para baixar a planilha
         em CSV para abrir no Excel
     A tela apenas calcula e mostra: nao grava e nao muda nenhum
     lancamento.

Como usar:
  Coloque este arquivo na mesma pasta do index.html e execute:
      python patch86b_fechar_login_custos.py

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

MARCA = 'PATCH86B_FECHAR_LOGIN_CUSTOS_OK'

JS = r"""/* PATCH 86B - botao Fechar dos relatorios, login com cadastro de usuario
   e tabela Custos x Pagamentos no Centro de Custos.
   Nao reescreve nada do painel: apenas acrescenta e envolve funcoes. */
(function () {
  'use strict';

  if (window.__p86b) { return; }
  window.__p86b = true;

  var PREFS = ['p83', 'p84', 'p86'];

  var K_USERS = 'painel_seg_usuarios_v1';
  var K_SESS  = 'painel_seg_sessao_v1';

  /* ================================================================ *
   * utilidades gerais
   * ================================================================ */
  function esc(v) {
    return String(v === undefined || v === null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function num(v) {
    var n = Number(v);
    return isFinite(n) ? n : 0;
  }

  function moeda(v) {
    return 'R$ ' + num(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function estilo() {
    if (document.getElementById('p86bEstilo')) { return; }
    var s = document.createElement('style');
    s.id = 'p86bEstilo';
    s.textContent = [
      /* bloco A */
      '#p83Fundo.p86b-oculto,#p84Fundo.p86b-oculto,#p86Fundo.p86b-oculto{display:none !important}',
      /* bloco B */
      '#p86bCad,#p86bLogin{position:fixed;inset:0;z-index:2147483400;background:linear-gradient(160deg,#0f172a,#1e293b);display:flex;align-items:center;justify-content:center;font-family:Segoe UI,Arial,sans-serif}',
      '#p86bCad .cx,#p86bLogin .cx{background:#fff;border-radius:14px;padding:24px 24px 18px;width:360px;max-height:92vh;overflow:auto;box-shadow:0 18px 50px rgba(0,0,0,.45)}',
      '#p86bCad h2,#p86bLogin h2{margin:0 0 4px;font-size:19px;color:#16304f}',
      '#p86bCad p.sb,#p86bLogin p.sb{margin:0 0 14px;font-size:12px;color:#64748b}',
      '#p86bCad label,#p86bLogin label{display:block;font-size:12px;color:#334155;margin:10px 0 4px;font-weight:600}',
      '#p86bCad input,#p86bCad select,#p86bLogin input{width:100%;box-sizing:border-box;padding:9px 10px;border:1px solid #cbd5e1;border-radius:8px;font-size:14px}',
      '#p86bCad .bt,#p86bLogin .bt{display:flex;gap:8px;margin-top:16px}',
      '#p86bCad button,#p86bLogin button{flex:1;padding:10px;border:0;border-radius:8px;background:#e2e8f0;color:#16304f;font-size:14px;font-weight:600;cursor:pointer}',
      '#p86bCad button.pri,#p86bLogin button.pri{background:#2563eb;color:#fff}',
      '#p86bCad .er,#p86bLogin .er{margin-top:10px;font-size:12px;color:#b91c1c;min-height:16px}',
      '#p86bCad .ok,#p86bLogin .ok{margin-top:10px;font-size:12px;color:#15803d;min-height:16px}',
      '#p86bCad .dica,#p86bLogin .dica{font-size:11px;color:#64748b;margin:8px 0 0;line-height:1.45}',
      '#p86bCad .lb,#p86bLogin .lb{display:flex;align-items:center;gap:6px;margin:12px 0 0;font-size:12px;color:#475569;font-weight:400}',
      '#p86bCad .lb input,#p86bLogin .lb input{width:auto}',
      '.p86b-cadlink{margin-top:14px;text-align:center;font-size:12px;color:#475569}',
      '.p86b-cadlink button{display:inline-block;width:auto;margin:6px 0 0;padding:8px 14px;border:1px solid #cbd5e1;border-radius:8px;background:#f1f5f9;color:#16304f;font-size:12px;font-weight:600;cursor:pointer}',
      '#p86bBarra{position:fixed;left:14px;bottom:14px;z-index:2147482000;display:flex;align-items:center;gap:8px;background:#16304f;color:#fff;border-radius:999px;padding:6px 8px 6px 14px;font:12px Segoe UI,Arial,sans-serif;box-shadow:0 6px 20px rgba(0,0,0,.28)}',
      '#p86bBarra button{border:0;border-radius:999px;padding:5px 11px;font-size:11px;font-weight:600;cursor:pointer;background:#e2e8f0;color:#16304f}',
      '.p86b-aviso{position:fixed;left:50%;top:22px;transform:translateX(-50%);z-index:2147483500;background:#15803d;color:#fff;padding:11px 18px;border-radius:10px;font:13px Segoe UI,Arial,sans-serif;box-shadow:0 8px 24px rgba(0,0,0,.3)}',
      '.p86b-aviso.err{background:#b91c1c}',
      /* bloco C */
      '#p86bCxpCaixa{font-size:0.86rem}',
      '#p86bCxpCaixa .p86b-fil{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;margin:0 0 14px}',
      '#p86bCxpCaixa .p86b-fil label{display:block;font-size:0.72rem;font-weight:700;color:var(--text-light,#64748b);margin-bottom:4px;text-transform:uppercase;letter-spacing:.4px}',
      '#p86bCxpCaixa .p86b-fil select{padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:0.85rem;min-width:180px;background:#fff;color:#1e293b}',
      '#p86bCxpCaixa .p86b-fil button{padding:8px 14px;border:1px solid #cbd5e1;border-radius:6px;background:#f1f5f9;color:#16304f;font-size:0.8rem;font-weight:700;cursor:pointer}',
      '#p86bCxpCaixa .p86b-cards{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:16px}',
      '#p86bCxpCaixa .p86b-card{flex:1 1 150px;border:1px solid var(--border,#e2e8f0);border-left:5px solid #1e3a5f;border-radius:8px;padding:10px 12px;background:var(--card-bg,#fff)}',
      '#p86bCxpCaixa .p86b-card span{display:block;font-size:0.72rem;text-transform:uppercase;letter-spacing:.4px;color:var(--text-light,#64748b);font-weight:700}',
      '#p86bCxpCaixa .p86b-card b{display:block;margin-top:4px;font-size:1.05rem;color:var(--text,#1e293b)}',
      '#p86bCxpCaixa .p86b-card.ver{border-left-color:#16a34a}',
      '#p86bCxpCaixa .p86b-card.ver b{color:#16a34a}',
      '#p86bCxpCaixa .p86b-card.ama{border-left-color:#d97706}',
      '#p86bCxpCaixa .p86b-card.ama b{color:#d97706}',
      '#p86bCxpCaixa .p86b-card.ver2{border-left-color:#dc2626}',
      '#p86bCxpCaixa .p86b-card.ver2 b{color:#dc2626}',
      '#p86bCxpCaixa h4{margin:18px 0 8px;font-size:0.95rem;color:var(--text,#1e293b)}',
      '#p86bCxpCaixa table.p86b-tab{width:100%;border-collapse:collapse;font-size:0.82rem}',
      '#p86bCxpCaixa table.p86b-tab th{background:#1e3a5f;color:#fff;padding:8px 8px;text-align:left;font-size:0.74rem;text-transform:uppercase;letter-spacing:.3px}',
      '#p86bCxpCaixa table.p86b-tab td{border-bottom:1px solid var(--border,#e2e8f0);padding:7px 8px;color:var(--text,#1e293b)}',
      '#p86bCxpCaixa table.p86b-tab td.n,#p86bCxpCaixa table.p86b-tab th.n{text-align:right;white-space:nowrap}',
      '#p86bCxpCaixa table.p86b-tab tr.tot td{font-weight:700;background:rgba(30,58,95,.07)}',
      '#p86bCxpCaixa .neg{color:#dc2626;font-weight:700}',
      '#p86bCxpCaixa .pos{color:#16a34a;font-weight:700}',
      '#p86bCxpCaixa .p86b-vazio{padding:14px;color:var(--text-light,#64748b)}',
      '#p86bCxpCaixa .p86b-nota{margin-top:12px;padding:10px 12px;border-radius:8px;background:rgba(217,119,6,.10);border:1px solid rgba(217,119,6,.35);color:#92400e;font-size:0.8rem;line-height:1.5}',
      'body.dark-mode #p86bCxpCaixa .p86b-fil select{background:#1e293b;color:#e2e8f0;border-color:#334155}',
      'body.dark-mode #p86bCxpCaixa .p86b-fil button{background:#1e293b;color:#e2e8f0;border-color:#334155}'
    ].join('\n');
    (document.head || document.documentElement).appendChild(s);
  }

  function aviso(msg, tipo) {
    try {
      var d = document.createElement('div');
      d.className = 'p86b-aviso' + (tipo === 'err' ? ' err' : '');
      d.setAttribute('data-ps79', '1');
      d.textContent = msg;
      document.body.appendChild(d);
      setTimeout(function () { if (d.parentNode) { d.parentNode.removeChild(d); } }, 3600);
    } catch (e) { /* ignora */ }
  }

  /* ================================================================ *
   * BLOCO A - botao Fechar do Boletim de Inspecao e do Diario de Obra
   * ================================================================ */
  function esconder(f) {
    if (!f) { return; }
    try { f.style.setProperty('display', 'none', 'important'); } catch (e) { f.style.display = 'none'; }
    try { f.classList.add('p86b-oculto'); } catch (e2) { /* ignora */ }
  }

  function mostrar(f) {
    if (!f) { return; }
    try { f.classList.remove('p86b-oculto'); } catch (e) { /* ignora */ }
  }

  function fundoDe(no) {
    if (!no || !no.closest) { return null; }
    return no.closest('#p83Fundo') || no.closest('#p84Fundo') || no.closest('#p86Fundo') || null;
  }

  function visivel(f) {
    if (!f) { return false; }
    var d = '';
    try { d = window.getComputedStyle(f).display; } catch (e) { d = f.style.display; }
    return d !== 'none' && d !== '';
  }

  function abertoAgora() {
    var i, f;
    for (i = 0; i < PREFS.length; i++) {
      f = document.getElementById(PREFS[i] + 'Fundo');
      if (visivel(f)) { return f; }
    }
    return null;
  }

  /* quando o relatorio abrir de novo, tira a marca de oculto */
  function vigiarFundo(f) {
    if (!f || f.getAttribute('data-p86bolho') === '1') { return; }
    f.setAttribute('data-p86bolho', '1');
    try {
      var olho = new MutationObserver(function () {
        if (f.style && f.style.display && f.style.display !== 'none') { mostrar(f); }
      });
      olho.observe(f, { attributes: true, attributeFilter: ['style'] });
    } catch (e) { /* ignora */ }
  }

  function varrerFundos() {
    PREFS.forEach(function (p) {
      var f = document.getElementById(p + 'Fundo');
      if (f) { vigiarFundo(f); }
    });
  }

  function ajustarDica() {
    PREFS.forEach(function (p) {
      var f = document.getElementById(p + 'Fundo');
      if (!f) { return; }
      var b = f.querySelector('[data-a="fechar"]');
      if (b && !b.getAttribute('title')) {
        b.setAttribute('title', 'Fechar esta janela (a tecla Esc tamb\u00e9m fecha)');
      }
    });
  }

  function ligarFechar() {
    if (window.__p86bFechar) { return; }
    window.__p86bFechar = true;

    document.addEventListener('click', function (ev) {
      var alvo = ev.target;
      if (!alvo || !alvo.closest) { return; }

      var id = alvo.id || '';
      if (id === 'p83Fundo' || id === 'p84Fundo' || id === 'p86Fundo') {
        ev.preventDefault();
        esconder(alvo);
        return;
      }

      var b = alvo.closest('[data-a]');
      if (!b || b.getAttribute('data-a') !== 'fechar') { return; }
      var f = fundoDe(b);
      if (!f) { return; }
      ev.preventDefault();
      ev.stopPropagation();
      esconder(f);
    }, true);

    document.addEventListener('keydown', function (ev) {
      var k = ev.key || ev.keyCode;
      if (k !== 'Escape' && k !== 'Esc' && k !== 27) { return; }
      var f = abertoAgora();
      if (!f) { return; }
      ev.preventDefault();
      ev.stopPropagation();
      esconder(f);
    }, true);
  }

  /* ================================================================ *
   * BLOCO B - login por usuario e senha + cadastro publico
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

  /* mesma conta usada pelo login que ja existe no painel */
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
    if (!u || !u.length) {
      u = [{ usuario: 'admin', nome: 'Administrador', perfil: 'admin', hash: hashSenha('admin', 'admin123'), trocar: true }];
      gravarJson(K_USERS, u);
    }
    return u;
  }

  function acharUsuario(nome) {
    var lista = usuarios(), i;
    for (i = 0; i < lista.length; i++) {
      if (String(lista[i].usuario).toLowerCase() === String(nome).toLowerCase()) { return lista[i]; }
    }
    return null;
  }

  function sessao() {
    var s = null;
    try { s = JSON.parse(sessionStorage.getItem(K_SESS) || 'null'); } catch (e) { s = null; }
    if (!s) { s = lerJson(K_SESS, null); }
    if (s && s.exp && Date.now() > s.exp) { s = null; }
    return s;
  }

  function abrirSessao(u, lembrar) {
    var s = { usuario: u.usuario, nome: u.nome || u.usuario, perfil: u.perfil, em: Date.now() };
    try { sessionStorage.setItem(K_SESS, JSON.stringify(s)); } catch (e) { /* ignora */ }
    if (lembrar) {
      s.exp = Date.now() + 30 * 86400000;
      gravarJson(K_SESS, s);
    } else {
      try { localStorage.removeItem(K_SESS); } catch (e) { /* ignora */ }
    }
  }

  function fecharSessao() {
    try { sessionStorage.removeItem(K_SESS); } catch (e) { /* ignora */ }
    try { localStorage.removeItem(K_SESS); } catch (e) { /* ignora */ }
  }

  function temSegurancaAntiga() {
    return !!(window.PainelSeg && typeof window.PainelSeg.login === 'function');
  }

  function campo(pai, rotulo, tipo, valor) {
    var l = document.createElement('label');
    l.textContent = rotulo;
    var i = document.createElement('input');
    i.type = tipo || 'text';
    if (valor != null) { i.value = valor; }
    pai.appendChild(l);
    pai.appendChild(i);
    return i;
  }

  function botao(pai, texto, classe, fn) {
    var b = document.createElement('button');
    b.type = 'button';
    if (classe) { b.className = classe; }
    b.textContent = texto;
    b.addEventListener('click', fn);
    pai.appendChild(b);
    return b;
  }

  function fecharTela(id) {
    var t = document.getElementById(id);
    if (t && t.parentNode) { t.parentNode.removeChild(t); }
  }

  /* ---- tela publica de cadastro de usuario ---- */
  function telaCadastro() {
    estilo();
    if (document.getElementById('p86bCad')) { return; }

    var primeiro = !(lerJson(K_USERS, null) || []).length;

    var ov = document.createElement('div');
    ov.id = 'p86bCad';
    ov.setAttribute('data-ps79', '1');
    var cx = document.createElement('div');
    cx.className = 'cx';

    var h = document.createElement('h2');
    h.textContent = 'Criar usu\u00e1rio';
    var p = document.createElement('p');
    p.className = 'sb';
    p.textContent = 'Preencha os dados para ter seu acesso ao painel.';
    cx.appendChild(h);
    cx.appendChild(p);

    var inNome = campo(cx, 'Nome completo', 'text', '');
    var inUsu  = campo(cx, 'Usu\u00e1rio (sem espa\u00e7os)', 'text', '');
    var inSe1  = campo(cx, 'Senha (m\u00ednimo 4 caracteres)', 'password', '');
    var inSe2  = campo(cx, 'Repita a senha', 'password', '');

    var lp = document.createElement('label');
    lp.textContent = 'Tipo de acesso';
    var sel = document.createElement('select');
    [['visitante', 'Somente consulta (recomendado)'],
     ['editor', 'Pode lan\u00e7ar e editar']].forEach(function (o) {
      var op = document.createElement('option');
      op.value = o[0];
      op.textContent = o[1];
      sel.appendChild(op);
    });
    cx.appendChild(lp);
    cx.appendChild(sel);
    if (primeiro) {
      sel.value = 'editor';
      sel.disabled = true;
    }

    var er = document.createElement('div');
    er.className = 'er';

    var bt = document.createElement('div');
    bt.className = 'bt';
    cx.appendChild(bt);
    cx.appendChild(er);

    var dica = document.createElement('p');
    dica.className = 'dica';
    dica.textContent = primeiro
      ? 'Este \u00e9 o primeiro usu\u00e1rio deste computador, por isso ele entra como administrador.'
      : 'O administrador pode mudar depois o tipo de acesso de cada pessoa no bot\u00e3o "Usu\u00e1rios". Os usu\u00e1rios ficam guardados neste computador/navegador.';
    cx.appendChild(dica);

    ov.appendChild(cx);
    document.body.appendChild(ov);
    setTimeout(function () { try { inNome.focus(); } catch (e) { /* ignora */ } }, 60);

    function voltar() {
      fecharTela('p86bCad');
      if (temSegurancaAntiga()) {
        try { window.PainelSeg.login(); } catch (e) { /* ignora */ }
      } else {
        telaLogin();
      }
    }

    function criar() {
      var nome  = String(inNome.value || '').trim();
      var usu   = String(inUsu.value || '').trim().toLowerCase();
      var se1   = String(inSe1.value || '');
      var se2   = String(inSe2.value || '');

      if (!nome) { er.textContent = 'Escreva o nome completo.'; return; }
      if (usu.length < 3) { er.textContent = 'O usu\u00e1rio precisa de pelo menos 3 caracteres.'; return; }
      if (!/^[a-z0-9._-]+$/.test(usu)) { er.textContent = 'Use apenas letras sem acento, n\u00fameros, ponto, tra\u00e7o ou sublinhado no usu\u00e1rio.'; return; }
      if (se1.length < 4) { er.textContent = 'A senha precisa de pelo menos 4 caracteres.'; return; }
      if (se1 !== se2) { er.textContent = 'As duas senhas est\u00e3o diferentes.'; return; }

      var lista = usuarios();
      if (acharUsuario(usu)) { er.textContent = 'J\u00e1 existe um usu\u00e1rio com esse nome.'; return; }

      lista.push({
        usuario: usu,
        nome: nome,
        perfil: primeiro ? 'admin' : sel.value,
        hash: hashSenha(usu, se1),
        trocar: false,
        criadoEm: Date.now()
      });
      if (!gravarJson(K_USERS, lista)) {
        er.textContent = 'N\u00e3o foi poss\u00edvel salvar neste navegador.';
        return;
      }
      aviso('Usu\u00e1rio criado. Agora entre com ele.');
      voltar();
    }

    botao(bt, 'Voltar', '', voltar);
    botao(bt, 'Criar usu\u00e1rio', 'pri', criar);

    [inNome, inUsu, inSe1, inSe2].forEach(function (el) {
      el.addEventListener('keydown', function (ev) { if (ev.key === 'Enter') { criar(); } });
    });
  }

  /* ---- coloca o botao de cadastro na tela de login que ja existe ---- */
  function enfeitarLogin() {
    var ov = document.getElementById('ps79Login');
    if (!ov || ov.getAttribute('data-p86b') === '1') { return; }
    var cx = ov.querySelector('.cx');
    if (!cx) { return; }
    ov.setAttribute('data-p86b', '1');

    var d = document.createElement('div');
    d.className = 'p86b-cadlink';
    var t = document.createElement('div');
    t.textContent = 'Ainda n\u00e3o tem acesso?';
    d.appendChild(t);
    var b = document.createElement('button');
    b.type = 'button';
    b.textContent = 'Criar novo usu\u00e1rio';
    b.addEventListener('click', function () {
      fecharTela('ps79Login');
      telaCadastro();
    });
    d.appendChild(b);
    cx.appendChild(d);
  }

  /* ---- login proprio (usado somente se o painel nao tiver login) ---- */
  function barraPropria() {
    var s = sessao();
    var b = document.getElementById('p86bBarra');
    if (b && b.parentNode) { b.parentNode.removeChild(b); }
    if (!s) { return; }
    b = document.createElement('div');
    b.id = 'p86bBarra';
    b.setAttribute('data-ps79', '1');
    var nm = document.createElement('b');
    nm.textContent = (s.nome || s.usuario) + ' (' + s.perfil + ')';
    b.appendChild(nm);
    botao(b, 'Sair', '', function () {
      fecharSessao();
      if (b.parentNode) { b.parentNode.removeChild(b); }
      telaLogin();
    });
    document.body.appendChild(b);
  }

  function telaLogin() {
    estilo();
    if (document.getElementById('p86bLogin') || document.getElementById('ps79Login')) { return; }

    var ov = document.createElement('div');
    ov.id = 'p86bLogin';
    ov.setAttribute('data-ps79', '1');
    var cx = document.createElement('div');
    cx.className = 'cx';
    var h = document.createElement('h2');
    h.textContent = 'Painel de Acompanhamento';
    var p = document.createElement('p');
    p.className = 'sb';
    p.textContent = 'Entre com seu usu\u00e1rio e senha para continuar.';
    cx.appendChild(h);
    cx.appendChild(p);

    var iu = campo(cx, 'Usu\u00e1rio', 'text', '');
    var is = campo(cx, 'Senha', 'password', '');

    var lb = document.createElement('label');
    lb.className = 'lb';
    var ck = document.createElement('input');
    ck.type = 'checkbox';
    var sp = document.createElement('span');
    sp.textContent = 'Manter conectado neste computador';
    lb.appendChild(ck);
    lb.appendChild(sp);
    cx.appendChild(lb);

    var er = document.createElement('div');
    er.className = 'er';
    var bt = document.createElement('div');
    bt.className = 'bt';
    cx.appendChild(bt);
    cx.appendChild(er);

    var d = document.createElement('div');
    d.className = 'p86b-cadlink';
    var t = document.createElement('div');
    t.textContent = 'Ainda n\u00e3o tem acesso?';
    d.appendChild(t);
    var bc = document.createElement('button');
    bc.type = 'button';
    bc.textContent = 'Criar novo usu\u00e1rio';
    bc.addEventListener('click', function () {
      fecharTela('p86bLogin');
      telaCadastro();
    });
    d.appendChild(bc);
    cx.appendChild(d);

    ov.appendChild(cx);
    document.body.appendChild(ov);
    setTimeout(function () { try { iu.focus(); } catch (e) { /* ignora */ } }, 60);

    function entrar() {
      var nome = String(iu.value || '').trim().toLowerCase();
      var senha = String(is.value || '');
      if (!nome || !senha) { er.textContent = 'Preencha usu\u00e1rio e senha.'; return; }
      var u = acharUsuario(nome);
      if (!u || u.hash !== hashSenha(nome, senha)) {
        er.textContent = 'Usu\u00e1rio ou senha inv\u00e1lidos.';
        is.value = '';
        return;
      }
      abrirSessao(u, ck.checked);
      fecharTela('p86bLogin');
      barraPropria();
      aviso('Bem-vindo, ' + (u.nome || u.usuario) + '!');
    }

    botao(bt, 'Entrar', 'pri', entrar);
    is.addEventListener('keydown', function (ev) { if (ev.key === 'Enter') { entrar(); } });
    iu.addEventListener('keydown', function (ev) { if (ev.key === 'Enter') { is.focus(); } });
  }

  function ligarLogin() {
    /* fica de olho na tela de login para acrescentar o botao de cadastro */
    enfeitarLogin();
    try {
      var olho = new MutationObserver(function () { enfeitarLogin(); });
      olho.observe(document.body, { childList: true });
    } catch (e) { /* ignora */ }
    var voltas = 0;
    var t = setInterval(function () {
      voltas++;
      enfeitarLogin();
      if (voltas > 30) { clearInterval(t); }
    }, 500);

    /* se o painel nao tiver nenhum login, este patch passa a cuidar disso */
    setTimeout(function () {
      if (temSegurancaAntiga() || document.getElementById('ps79Login')) { return; }
      if (sessao()) { barraPropria(); } else { telaLogin(); }
    }, 2500);

    window.PainelCadastro = {
      criar: telaCadastro,
      login: function () {
        if (temSegurancaAntiga()) { window.PainelSeg.login(); } else { telaLogin(); }
      }
    };
  }

  /* ================================================================ *
   * BLOCO C - tabela Custos x Pagamentos
   * ================================================================ */
  var ID_BTN = 'custoSubBtn-p86bcxp';
  var ID_PAN = 'custoSubPainel-p86bcxp';
  var ID_CX  = 'p86bCxpCaixa';

  function obras() {
    try {
      if (window.db && Object.prototype.toString.call(window.db.obras) === '[object Array]') {
        return window.db.obras;
      }
    } catch (e) { /* ignora */ }
    return [];
  }

  function lista(v) {
    return Object.prototype.toString.call(v) === '[object Array]' ? v : [];
  }

  /* nome de cada colaborador, juntando todas as fontes do painel */
  function mapaNomes() {
    var m = {};
    function por(arr) {
      lista(arr).forEach(function (c) {
        if (!c || c.id === undefined || c.id === null) { return; }
        var k = String(c.id);
        if (!m[k] || !m[k].nome) {
          m[k] = { nome: String(c.nome || '').trim(), funcao: String(c.funcao || '').trim() };
        }
      });
    }
    try {
      if (typeof window.getColaboradoresAll === 'function') { por(window.getColaboradoresAll()); }
    } catch (e) { /* ignora */ }
    obras().forEach(function (o) {
      if (!o) { return; }
      por(o.colaboradores);
      por(o.colaboradoresPgto);
    });
    return m;
  }

  function mesesComDados() {
    var vistos = {}, out = [];
    obras().forEach(function (o) {
      if (!o) { return; }
      lista(o.lancamentosProducao).forEach(function (l) {
        var k = l && l.mesAnoKey ? String(l.mesAnoKey) : '';
        if (k && !vistos[k]) { vistos[k] = 1; out.push(k); }
      });
      lista(o.colaboradoresPgto).forEach(function (c) {
        if (!c || !c.valorPagoManual) { return; }
        Object.keys(c.valorPagoManual).forEach(function (k) {
          if (k && !vistos[k]) { vistos[k] = 1; out.push(k); }
        });
      });
      lista(o.centrosCusto).forEach(function (c) {
        var k = c && c.data ? String(c.data).substring(0, 7) : '';
        if (k.length === 7 && !vistos[k]) { vistos[k] = 1; out.push(k); }
      });
    });
    out.sort();
    out.reverse();
    return out;
  }

  function rotuloMes(k) {
    var NOMES = ['janeiro', 'fevereiro', 'mar\u00e7o', 'abril', 'maio', 'junho', 'julho',
                 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
    var p = String(k || '').split('-');
    var i = parseInt(p[1], 10);
    if (!p[0] || !i || i < 1 || i > 12) { return String(k || ''); }
    return NOMES[i - 1] + '/' + p[0];
  }

  function ehEspelho(c) {
    return !!(c && typeof c.id === 'string' && c.id.indexOf('p54_prod_') === 0);
  }

  /* junta tudo o que interessa para a comparacao */
  function calcular(mesSel, obraSel) {
    var nomes = mapaNomes();
    var colabs = {};
    var porObra = [];
    var tot = { lanc: 0, m2: 0, prof: 0, ajud: 0, desp: 0, pago: 0 };

    function reg(id) {
      var k = String(id);
      if (!colabs[k]) {
        var inf = nomes[k] || {};
        colabs[k] = {
          id: k,
          nome: inf.nome || ('colaborador ' + k),
          prof: 0, ajud: 0, pago: 0, dias: 0
        };
      }
      return colabs[k];
    }

    obras().forEach(function (o) {
      if (!o) { return; }
      if (obraSel && String(o.id) !== String(obraSel)) { return; }

      var lin = { nome: String(o.nome || 'Obra sem nome'), lanc: 0, m2: 0, custo: 0, desp: 0, pago: 0 };

      lista(o.lancamentosProducao).forEach(function (l) {
        if (!l) { return; }
        if (mesSel && String(l.mesAnoKey) !== mesSel) { return; }
        var vp = num(l.valorProf), va = num(l.valorAjud);
        lin.lanc++;
        lin.m2 += num(l.instalacaoM2);
        lista(l.profissionais).forEach(function (pid) {
          if (!pid) { return; }
          var r = reg(pid);
          r.prof += vp;
          r.dias++;
          lin.custo += vp;
        });
        lista(l.ajudantes).forEach(function (aid) {
          if (!aid) { return; }
          var r = reg(aid);
          r.ajud += va;
          r.dias++;
          lin.custo += va;
        });
      });

      lista(o.colaboradoresPgto).forEach(function (c) {
        if (!c || !c.valorPagoManual) { return; }
        Object.keys(c.valorPagoManual).forEach(function (k) {
          if (mesSel && k !== mesSel) { return; }
          var v = num(c.valorPagoManual[k]);
          if (!v) { return; }
          lin.pago += v;
          reg(c.id).pago += v;
        });
      });

      lista(o.centrosCusto).forEach(function (c) {
        if (!c || ehEspelho(c)) { return; }
        var d = String(c.data || '');
        if (mesSel && d.substring(0, 7) !== mesSel) { return; }
        lin.desp += num(c.valor);
      });

      if (lin.lanc || lin.custo || lin.desp || lin.pago) {
        porObra.push(lin);
        tot.lanc += lin.lanc;
        tot.m2 += lin.m2;
        tot.desp += lin.desp;
        tot.pago += lin.pago;
      }
    });

    var linhas = [];
    Object.keys(colabs).forEach(function (k) {
      var c = colabs[k];
      c.devido = c.prof + c.ajud;
      c.saldo = c.pago - c.devido;
      tot.prof += c.prof;
      tot.ajud += c.ajud;
      linhas.push(c);
    });
    linhas.sort(function (a, b) { return String(a.nome).localeCompare(String(b.nome), 'pt-BR'); });

    porObra.sort(function (a, b) { return String(a.nome).localeCompare(String(b.nome), 'pt-BR'); });

    tot.devido = tot.prof + tot.ajud;
    tot.saldo = tot.pago - tot.devido;
    tot.geral = tot.devido + tot.desp;

    return { colabs: linhas, obras: porObra, tot: tot };
  }

  function celSaldo(v) {
    var c = Math.round(num(v) * 100) / 100;
    if (c === 0) { return '<td class="n">' + esc(moeda(0)) + '</td>'; }
    return '<td class="n ' + (c < 0 ? 'neg' : 'pos') + '">' + esc(moeda(c)) + '</td>';
  }

  function caixa() {
    var pan = document.getElementById(ID_PAN);
    if (!pan) { return null; }
    var cx = document.getElementById(ID_CX);
    if (!cx) {
      cx = document.createElement('div');
      cx.id = ID_CX;
      pan.appendChild(cx);
    }
    return cx;
  }

  var ultimoCsv = '';

  function desenhar() {
    var cx = caixa();
    if (!cx) { return; }

    var meses = mesesComDados();
    var selMes = document.getElementById('p86bMes');
    var selObra = document.getElementById('p86bObra');
    var mesSel = selMes ? selMes.value : '';
    var obraSel = selObra ? selObra.value : '';

    if (!selMes) {
      var f = document.getElementById('custoFilterMes');
      mesSel = f && f.value ? f.value : '';
      if (mesSel && meses.indexOf(mesSel) < 0) { meses.unshift(mesSel); }
    }

    var d = calcular(mesSel, obraSel);

    var h = '';
    h += '<div class="p86b-fil">';
    h += '<div><label>M\u00eas</label><select id="p86bMes"><option value="">Todos os meses</option>';
    meses.forEach(function (m) {
      h += '<option value="' + esc(m) + '"' + (m === mesSel ? ' selected' : '') + '>' + esc(rotuloMes(m)) + '</option>';
    });
    h += '</select></div>';
    h += '<div><label>Obra</label><select id="p86bObra"><option value="">Todas as obras</option>';
    obras().forEach(function (o) {
      if (!o) { return; }
      h += '<option value="' + esc(o.id) + '"' + (String(o.id) === String(obraSel) ? ' selected' : '') + '>' +
           esc(o.nome || 'Obra sem nome') + '</option>';
    });
    h += '</select></div>';
    h += '<div><button type="button" id="p86bAtualizar">Atualizar</button></div>';
    h += '<div><button type="button" id="p86bCsv">Baixar planilha (CSV)</button></div>';
    h += '</div>';

    h += '<div class="p86b-cards">';
    h += '<div class="p86b-card"><span>Lan\u00e7amentos</span><b>' + esc(d.tot.lanc) + '</b></div>';
    h += '<div class="p86b-card ama"><span>Custo de produ\u00e7\u00e3o</span><b>' + esc(moeda(d.tot.devido)) + '</b></div>';
    h += '<div class="p86b-card ver"><span>Total pago</span><b>' + esc(moeda(d.tot.pago)) + '</b></div>';
    h += '<div class="p86b-card ' + (d.tot.saldo < 0 ? 'ver2' : 'ver') + '"><span>Saldo (pago - devido)</span><b>' +
         esc(moeda(d.tot.saldo)) + '</b></div>';
    h += '<div class="p86b-card"><span>Outras despesas</span><b>' + esc(moeda(d.tot.desp)) + '</b></div>';
    h += '<div class="p86b-card"><span>Custo geral (produ\u00e7\u00e3o + despesas)</span><b>' + esc(moeda(d.tot.geral)) + '</b></div>';
    h += '</div>';

    /* tabela por colaborador */
    h += '<h4>Por colaborador</h4>';
    if (!d.colabs.length) {
      h += '<div class="p86b-vazio">Nenhum lan\u00e7amento ou pagamento para o filtro escolhido.</div>';
    } else {
      h += '<table class="p86b-tab"><thead><tr>' +
           '<th>Colaborador</th><th class="n">Di\u00e1rias</th>' +
           '<th class="n">Como profissional</th><th class="n">Como ajudante</th>' +
           '<th class="n">Devido</th><th class="n">Pago</th><th class="n">Saldo</th>' +
           '</tr></thead><tbody>';
      d.colabs.forEach(function (c) {
        h += '<tr>';
        h += '<td>' + esc(c.nome) + '</td>';
        h += '<td class="n">' + esc(c.dias) + '</td>';
        h += '<td class="n">' + esc(moeda(c.prof)) + '</td>';
        h += '<td class="n">' + esc(moeda(c.ajud)) + '</td>';
        h += '<td class="n">' + esc(moeda(c.devido)) + '</td>';
        h += '<td class="n">' + esc(moeda(c.pago)) + '</td>';
        h += celSaldo(c.saldo);
        h += '</tr>';
      });
      h += '<tr class="tot"><td>TOTAL</td><td class="n"></td>' +
           '<td class="n">' + esc(moeda(d.tot.prof)) + '</td>' +
           '<td class="n">' + esc(moeda(d.tot.ajud)) + '</td>' +
           '<td class="n">' + esc(moeda(d.tot.devido)) + '</td>' +
           '<td class="n">' + esc(moeda(d.tot.pago)) + '</td>' +
           celSaldo(d.tot.saldo) + '</tr>';
      h += '</tbody></table>';
    }

    /* tabela por obra */
    h += '<h4>Por obra</h4>';
    if (!d.obras.length) {
      h += '<div class="p86b-vazio">Nenhuma obra com movimento no filtro escolhido.</div>';
    } else {
      h += '<table class="p86b-tab"><thead><tr>' +
           '<th>Obra</th><th class="n">Lan\u00e7amentos</th><th class="n">Metragem</th>' +
           '<th class="n">Custo produ\u00e7\u00e3o</th><th class="n">Outras despesas</th>' +
           '<th class="n">Custo total</th><th class="n">Pago</th><th class="n">Saldo</th>' +
           '</tr></thead><tbody>';
      d.obras.forEach(function (o) {
        h += '<tr>';
        h += '<td>' + esc(o.nome) + '</td>';
        h += '<td class="n">' + esc(o.lanc) + '</td>';
        h += '<td class="n">' + esc(num(o.m2).toLocaleString('pt-BR')) + ' m\u00b2</td>';
        h += '<td class="n">' + esc(moeda(o.custo)) + '</td>';
        h += '<td class="n">' + esc(moeda(o.desp)) + '</td>';
        h += '<td class="n">' + esc(moeda(o.custo + o.desp)) + '</td>';
        h += '<td class="n">' + esc(moeda(o.pago)) + '</td>';
        h += celSaldo(o.pago - o.custo);
        h += '</tr>';
      });
      h += '</tbody></table>';
    }

    /* pendencias */
    var pend = d.colabs.filter(function (c) { return Math.round(c.saldo * 100) !== 0; });
    if (pend.length) {
      h += '<h4>Em aberto</h4>';
      h += '<table class="p86b-tab"><thead><tr><th>Colaborador</th>' +
           '<th class="n">Devido</th><th class="n">Pago</th><th class="n">Falta pagar</th>' +
           '</tr></thead><tbody>';
      pend.forEach(function (c) {
        var falta = c.devido - c.pago;
        h += '<tr><td>' + esc(c.nome) + '</td>' +
             '<td class="n">' + esc(moeda(c.devido)) + '</td>' +
             '<td class="n">' + esc(moeda(c.pago)) + '</td>' +
             '<td class="n ' + (falta > 0 ? 'neg' : 'pos') + '">' + esc(moeda(falta)) + '</td></tr>';
      });
      h += '</tbody></table>';
      h += '<div class="p86b-nota">Valor negativo em "Saldo" quer dizer que ainda falta pagar. ' +
           'Valor positivo quer dizer que foi pago mais do que o calculado nos lan\u00e7amentos.</div>';
    }

    h += '<div class="p86b-nota">Os n\u00fameros s\u00e3o calculados na hora a partir dos lan\u00e7amentos de ' +
         'produ\u00e7\u00e3o e dos valores pagos. Nada \u00e9 gravado por esta tela.</div>';

    cx.innerHTML = h;

    /* CSV para conferir no Excel */
    var linhasCsv = [];
    linhasCsv.push(['Colaborador', 'Diarias', 'Profissional', 'Ajudante', 'Devido', 'Pago', 'Saldo']);
    d.colabs.forEach(function (c) {
      linhasCsv.push([c.nome, c.dias, c.prof.toFixed(2), c.ajud.toFixed(2),
                      c.devido.toFixed(2), c.pago.toFixed(2), c.saldo.toFixed(2)]);
    });
    linhasCsv.push([]);
    linhasCsv.push(['Obra', 'Lancamentos', 'Metragem', 'Custo producao', 'Outras despesas', 'Custo total', 'Pago', 'Saldo']);
    d.obras.forEach(function (o) {
      linhasCsv.push([o.nome, o.lanc, num(o.m2).toFixed(2), o.custo.toFixed(2), o.desp.toFixed(2),
                      (o.custo + o.desp).toFixed(2), o.pago.toFixed(2), (o.pago - o.custo).toFixed(2)]);
    });
    ultimoCsv = linhasCsv.map(function (l) {
      return l.map(function (v) { return '"' + String(v).replace(/"/g, '""').replace(/\./g, ',') + '"'; }).join(';');
    }).join('\r\n');

    var bm = document.getElementById('p86bMes');
    if (bm) { bm.addEventListener('change', desenhar); }
    var bo = document.getElementById('p86bObra');
    if (bo) { bo.addEventListener('change', desenhar); }
    var ba = document.getElementById('p86bAtualizar');
    if (ba) { ba.addEventListener('click', desenhar); }
    var bc = document.getElementById('p86bCsv');
    if (bc) { bc.addEventListener('click', baixarCsv); }
  }

  function baixarCsv() {
    try {
      var b = new Blob(['\ufeff' + ultimoCsv], { type: 'text/csv;charset=utf-8' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(b);
      a.download = 'custos_x_pagamentos.csv';
      document.body.appendChild(a);
      a.click();
      setTimeout(function () {
        try { URL.revokeObjectURL(a.href); } catch (e) { /* ignora */ }
        if (a.parentNode) { a.parentNode.removeChild(a); }
      }, 1200);
    } catch (e) {
      aviso('N\u00e3o foi poss\u00edvel gerar o arquivo neste navegador.', 'err');
    }
  }

  function abrirNossa() {
    var pan = document.getElementById(ID_PAN);
    if (!pan) { return; }
    var todos = document.querySelectorAll('.custo-sub-painel');
    var i;
    for (i = 0; i < todos.length; i++) {
      if (todos[i].id !== ID_PAN) { todos[i].style.display = 'none'; }
    }
    var bts = document.querySelectorAll('.custo-sub-btn');
    for (i = 0; i < bts.length; i++) {
      bts[i].className = (bts[i].id === ID_BTN) ? 'custo-sub-btn ativo' : 'custo-sub-btn';
    }
    pan.style.display = 'block';
    desenhar();
  }

  function esconderNossa() {
    var pan = document.getElementById(ID_PAN);
    if (pan) { pan.style.display = 'none'; }
    var b = document.getElementById(ID_BTN);
    if (b) { b.className = 'custo-sub-btn'; }
  }

  function envolverSub() {
    var ant = window.abrirSubAbaCusto;
    if (typeof ant !== 'function' || ant.__p86b) { return; }
    var nova = function () {
      esconderNossa();
      return ant.apply(this, arguments);
    };
    nova.__p86b = true;
    window.abrirSubAbaCusto = nova;
  }

  function envolverRender() {
    var ant = window.renderCustoDashboard;
    if (typeof ant !== 'function' || ant.__p86b) { return; }
    var nova = function () {
      var r = ant.apply(this, arguments);
      try {
        var pan = document.getElementById(ID_PAN);
        if (pan && pan.style.display !== 'none') { desenhar(); }
      } catch (e) { /* ignora */ }
      return r;
    };
    nova.__p86b = true;
    window.renderCustoDashboard = nova;
  }

  function montarSub() {
    if (document.getElementById(ID_PAN)) { envolverSub(); envolverRender(); return true; }

    var nav = document.getElementById('custoSubNav');
    var painel = document.getElementById('tab-custo');

    if (nav && nav.parentNode) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'custo-sub-btn';
      b.id = ID_BTN;
      b.textContent = '\u2696\uFE0F Custos x Pagamentos';
      b.addEventListener('click', abrirNossa);
      nav.appendChild(b);

      var p = document.createElement('div');
      p.className = 'custo-sub-painel';
      p.id = ID_PAN;
      p.style.display = 'none';
      nav.parentNode.appendChild(p);

      envolverSub();
      envolverRender();
      return true;
    }

    /* painel sem sub-abas: coloca a tabela no fim da aba de custos */
    if (painel) {
      var cxa = document.createElement('div');
      cxa.className = 'custo-sub-painel';
      cxa.id = ID_PAN;
      cxa.style.marginTop = '18px';
      var t = document.createElement('h3');
      t.textContent = 'Custos x Pagamentos';
      cxa.appendChild(t);
      painel.appendChild(cxa);
      envolverRender();
      desenhar();
      return true;
    }

    return false;
  }

  function tentarSub(voltas) {
    if (montarSub()) { return; }
    if (voltas <= 0) { return; }
    setTimeout(function () { tentarSub(voltas - 1); }, 400);
  }

  function ligarCustos() {
    tentarSub(30);

    var ant = window.trocarAba;
    if (typeof ant === 'function' && !ant.__p86b) {
      var nova = function (aba) {
        var r = ant.apply(this, arguments);
        if (aba === 'custo') {
          try { montarSub(); } catch (e) { /* ignora */ }
        }
        return r;
      };
      nova.__p86b = true;
      window.trocarAba = nova;
    }

    window.abrirCustosXPagamentos = function () {
      try {
        if (typeof window.trocarAba === 'function') { window.trocarAba('custo'); }
      } catch (e) { /* ignora */ }
      montarSub();
      abrirNossa();
    };
  }

  /* ================================================================ *
   * inicio
   * ================================================================ */
  function iniciar() {
    try { estilo(); } catch (e) { /* ignora */ }
    try { ligarFechar(); } catch (e) { /* ignora */ }
    try { varrerFundos(); ajustarDica(); } catch (e) { /* ignora */ }
    try { ligarLogin(); } catch (e) { /* ignora */ }
    try { ligarCustos(); } catch (e) { /* ignora */ }

    var voltas = 0;
    var t = setInterval(function () {
      voltas++;
      try { varrerFundos(); ajustarDica(); } catch (e) { /* ignora */ }
      if (voltas > 20) { clearInterval(t); }
    }, 900);
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
    backup = alvo + '.bak_patch86b_' + selo
    shutil.copyfile(alvo, backup)

    with io.open(alvo, 'w', encoding='utf-8', errors='surrogateescape', newline='') as f:
        f.write(novo)

    print('PATCH 86B aplicado com sucesso.')
    print('  - botao Fechar dos relatorios funcionando sempre (Esc e clique fora tambem)')
    print('  - botao "Criar novo usuario" na tela de login, com cadastro completo')
    print('  - login proprio com "Manter conectado" caso a pagina nao tenha login')
    print('  - sub-aba "Custos x Pagamentos" no Centro de Custos, com filtros e CSV')
    print('Backup salvo em: ' + backup)
    print('')
    print('Agora recarregue o painel (Ctrl + F5).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
