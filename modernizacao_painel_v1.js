/* MODERNIZACAO PAINEL V1
 * Camada segura: nao substitui o formato do banco nem as funcoes existentes.
 */
(function () {
  'use strict';
  if (window.__modernizacaoPainelV1) return;
  window.__modernizacaoPainelV1 = true;

  var MAX_BACKUPS = 8;
  var BACKUP_PREFIX = 'obrasDB_backup_v1_';
  var LOG_KEY = 'painel_historico_local_v1';
  var PENDING_KEY = 'painel_sincronizacoes_pendentes_v1';
  var STATUS_ID = 'modernizacaoStatusPainel';

  function agora() { return new Date().toISOString(); }
  function banco() {
    if (window.db) return window.db;
    try {
      var bruto = localStorage.getItem('obrasDB_v8');
      return bruto ? JSON.parse(bruto) : null;
    } catch (e) { return null; }
  }
  function textoSeguro(v) { return String(v == null ? '' : v).replace(/[\r\n]+/g, ' ').slice(0, 180); }

  function registrar(acao, detalhe) {
    try {
      var lista = JSON.parse(localStorage.getItem(LOG_KEY) || '[]');
      lista.push({ data: agora(), acao: textoSeguro(acao), detalhe: textoSeguro(detalhe), origem: 'navegador' });
      if (lista.length > 300) lista = lista.slice(-300);
      localStorage.setItem(LOG_KEY, JSON.stringify(lista));
    } catch (e) {}
  }

  function backup() {
    try {
      var dbAtual = banco();
      if (!dbAtual) return false;
      var chave = BACKUP_PREFIX + agora().replace(/[.:]/g, '-');
      localStorage.setItem(chave, JSON.stringify(dbAtual));
      var chaves = [];
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        if (k && k.indexOf(BACKUP_PREFIX) === 0) chaves.push(k);
      }
      chaves.sort();
      while (chaves.length > MAX_BACKUPS) localStorage.removeItem(chaves.shift());
      return true;
    } catch (e) { return false; }
  }

  function criarStatus() {
    if (document.getElementById(STATUS_ID)) return document.getElementById(STATUS_ID);
    var el = document.createElement('div');
    el.id = STATUS_ID;
    el.setAttribute('role', 'status');
    el.title = 'Estado da conexão e da última sincronização';
    el.style.cssText = 'position:fixed;right:14px;bottom:14px;z-index:99998;padding:7px 10px;border-radius:999px;font:600 11px Arial,sans-serif;color:#fff;background:#64748b;box-shadow:0 2px 10px rgba(0,0,0,.18);opacity:.92;cursor:default;';
    el.textContent = '● Verificando conexão';
    document.body.appendChild(el);
    return el;
  }

  function pendentes() {
    try { return Number(localStorage.getItem(PENDING_KEY) || 0); } catch (e) { return 0; }
  }
  function marcarPendente() {
    try { localStorage.setItem(PENDING_KEY, String(pendentes() + 1)); } catch (e) {}
  }
  function limparPendentes() {
    try { localStorage.removeItem(PENDING_KEY); } catch (e) {}
  }
  function status(texto, cor) {
    var n = pendentes();
    var el = criarStatus();
    el.textContent = '● ' + texto + (n ? ' · ' + n + ' pendente(s)' : '');
    el.style.background = cor || '#64748b';
  }

  function atualizarConexao() {
    if (navigator.onLine) status('Online', '#168a55');
    else status('Offline — alterações ficam no aparelho', '#b45309');
  }
  function tentarSincronizarPendentes() {
    if (!navigator.onLine || !pendentes()) return;
    try {
      if (typeof window.sincronizarBancoNuvem === 'function') {
        status('Sincronizando pendências', '#2563eb');
        window.sincronizarBancoNuvem();
        setTimeout(function () { limparPendentes(); atualizarConexao(); registrar('pendencias_sincronizadas', 'Fila enviada ao Supabase'); }, 1800);
      }
    } catch (e) { status('Falha ao sincronizar', '#b91c1c'); }
  }

  function verificarIntegridade() {
    var b = banco();
    var r = { ok: true, obras: 0, problemas: [] };
    if (!b || !Array.isArray(b.obras)) { r.ok = false; r.problemas.push('Banco sem lista de obras'); return r; }
    r.obras = b.obras.length;
    b.obras.forEach(function (o, i) {
      if (!o || !o.id) r.problemas.push('Obra ' + (i + 1) + ' sem identificador');
      if (o && !Array.isArray(o.itens)) r.problemas.push('Obra ' + (i + 1) + ' sem lista de itens');
      if (o && !Array.isArray(o.recebimentos)) r.problemas.push('Obra ' + (i + 1) + ' sem lista de recebimentos');
      if (o && Array.isArray(o.centrosCusto)) o.centrosCusto.forEach(function (c, j) {
        if (!c || !c.id) r.problemas.push('Centro de custo ' + (i + 1) + '/' + (j + 1) + ' sem identificador');
        if (c && c.valor != null && !isFinite(Number(c.valor))) r.problemas.push('Centro de custo ' + (i + 1) + '/' + (j + 1) + ' com valor inválido');
      });
    });
    r.ok = r.problemas.length === 0;
    return r;
  }
  window.modernizacaoPainel = {
    backup: backup,
    registrar: registrar,
    diagnostico: verificarIntegridade,
    historico: function () {
      try { return JSON.parse(localStorage.getItem(LOG_KEY) || '[]'); } catch (e) { return []; }
    },
    exportarHistorico: function () { return JSON.stringify(this.historico(), null, 2); },
    status: status
  };

  window.addEventListener('online', function () { atualizarConexao(); registrar('conexao_online', 'Conexão restabelecida'); tentarSincronizarPendentes(); });
  window.addEventListener('offline', function () { atualizarConexao(); registrar('conexao_offline', 'Conexão perdida'); });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'visible') atualizarConexao();
  });

  var tentativas = 0;
  var ligar = setInterval(function () {
    tentativas++;
    if (typeof window.salvarDB === 'function') {
      var original = window.salvarDB;
      if (!original.__modernizacaoV1) {
        var envolvida = function () {
          var diagnostico = verificarIntegridade();
          if (!diagnostico.ok) registrar('integridade_alerta', diagnostico.problemas.slice(0, 5).join('; '));
          var ok = backup();
          registrar('salvar_db', ok ? 'Backup criado antes do salvamento' : 'Backup não criado');
          if (!navigator.onLine) marcarPendente();
          status(navigator.onLine ? 'Salvando alterações' : 'Offline — salvo localmente', navigator.onLine ? '#2563eb' : '#b45309');
          var saida = original.apply(this, arguments);
          setTimeout(function () { atualizarConexao(); }, 1200);
          return saida;
        };
        envolvida.__modernizacaoV1 = true;
        window.salvarDB = envolvida;
        clearInterval(ligar);
        registrar('modernizacao_iniciada', 'Backup, histórico, fila offline e status ativados');
        atualizarConexao();
        tentarSincronizarPendentes();
      }
    }
    if (tentativas > 60) clearInterval(ligar);
  }, 500);

  document.addEventListener('DOMContentLoaded', function () {
    criarStatus();
    atualizarConexao();
    registrar('painel_aberto', location.pathname || 'painel');
  });
}());
