# -*- coding: utf-8 -*-
"""
PATCH 74 - VALOR PAGO VALE NAS DUAS SUB-ABAS E TITULO COM O MES ESCRITO
=======================================================================

O QUE ESTE PATCH RESOLVE

  Na aba Pagamento existem duas sub-abas: "Lancamentos de Pagamento" e
  "Resumo de Pagamento". As duas mostram o mesmo quadro de colaboradores
  (COLABORADOR / TOTAL PROFISSIONAL / TOTAL AJUDANTE / TOTAL A RECEBER /
  VALOR PAGO) e as duas mostram o quadro "Totais Gerais do Mes".

  Problema 1: digitar na coluna VALOR PAGO so valia de um lado. No outro
  lado o campo nao aceitava, ou aceitava e o quadro de totais nao mexia.
  Agora vale nos DOIS lados: voce digita onde quiser e, na hora, o mesmo
  colaborador recebe o valor no outro lado e os DOIS quadros "Totais
  Gerais do Mes" refazem o Valor Pago e o Saldo, sem precisar sair do
  campo, sem trocar de aba e sem recarregar a pagina.

  Problema 2: o titulo dos dois blocos ficava com o mes abreviado ou com
  um tracinho no lugar do nome. Agora os dois blocos aparecem assim:

      Resumo de Pagamento do Mes Agosto

  com o mes escrito por inteiro (Janeiro, Fevereiro, Marco, Abril, Maio,
  Junho, Julho, Agosto, Setembro, Outubro, Novembro, Dezembro), sempre
  acompanhando o mes que esta selecionado na tela.

COMO FICA NA PRATICA

  1) Abra a aba Pagamento
  2) Clique em qualquer uma das duas sub-abas
  3) Digite na coluna VALOR PAGO de um colaborador
  4) O numero aparece nos dois lados e os dois quadros "Totais Gerais do
     Mes" ja mostram o novo Valor Pago e o novo Saldo
  5) Os dois blocos aparecem com o titulo "Resumo de Pagamento do Mes"
     seguido do nome do mes escrito por inteiro

O QUE CONTINUA EXATAMENTE COMO ESTA

  - A gravacao do valor e feita pela mesma funcao de sempre do painel:
    nao existe conta nova, nem outro lugar de guardar
  - O valor digitado continua ficando em UMA obra so (como o patch 70 ja
    fazia), sem repetir o mesmo pagamento em varias obras
  - O Saldo continua sendo o custo total do mes menos o valor pago, com a
    mesma cor vermelha quando sobra saldo
  - As colunas, a ordem, as larguras e as cores do quadro nao mudaram
  - As impressoes (aba inteira, quadro sozinho, PDF) continuam iguais: no
    papel sai o numero, nao a caixinha de digitar
  - Nenhum calculo, preco, medida, formula ou layout foi alterado

SEGURANCA
  - Nao apaga nem reescreve nada: insere apenas UM bloco novo antes do
    fechamento da pagina
  - Backup automatico do index.html antes de gravar
  - Idempotente: rodar de novo nao duplica nada

NO PAINEL, PELO CONSOLE (F12), SE QUISER
  P74.situacao()      mostra o mes escrito, o titulo e o total somado
  P74.sincronizar()   alinha os dois lados e refaz os dois quadros
  P74.recalcular()    refaz so os dois quadros de Totais Gerais do Mes

COMO USAR
  python patch_74.py
  depois abra o painel e pressione Ctrl+F5
"""

import os
import shutil
import sys
import datetime

FILE = r'C:/Users/OBRAS 8/Desktop/PAINEL SERVIDOR/index.html'

MARCADOR = 'PATCH 74: VALOR PAGO VALE NAS DUAS SUB-ABAS'



# ---------------------------------------------------------------------------
# BLOCO INSERIDO NO index.html
# ---------------------------------------------------------------------------
BLOCO = r"""

<script>
/* PATCH 74: VALOR PAGO VALE NAS DUAS SUB-ABAS E TITULO COM O MES ESCRITO */
(function () {
  if (window.P74 && window.P74.__v74) return;
  var P74 = window.P74 = window.P74 || {};
  P74.__v74 = true;

  /* nomes de mes escritos por inteiro (o painel usa a forma curta) */
  var MES_CHEIO = ['Janeiro', 'Fevereiro', 'Mar\u00e7o', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'];
  var MES_CURTO = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun',
    'jul', 'ago', 'set', 'out', 'nov', 'dez'];

  var TITULO_BASE = 'Resumo de Pagamento do M\u00eas ';

  /* os dois lados: tabela do resumo + quadro de totais de cada lado */
  var LADOS = [
    ['containerResumoPgto', 'containerTotaisPgto'],
    ['p63ResumoTabela', 'p63ResumoTotais']
  ];

  /* ------------------------------------------------------------------ */
  /* AJUDANTES                                                          */
  /* ------------------------------------------------------------------ */
  function porId(id) { return document.getElementById(id); }

  function paraNumero(v) {
    if (typeof v === 'number') return isFinite(v) ? v : 0;
    var s = String(v == null ? '' : v).replace(/\s/g, '').replace(/R\$/gi, '');
    if (s.indexOf(',') > -1) {
      if (s.indexOf('.') > -1) s = s.replace(/\./g, '');
      s = s.replace(',', '.');
    }
    s = s.replace(/[^0-9.\-]/g, '');
    var n = parseFloat(s);
    return isFinite(n) ? n : 0;
  }

  function dinheiro(n) {
    var v = paraNumero(n);
    try {
      return 'R$ ' + v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    } catch (e) {
      return 'R$ ' + v.toFixed(2);
    }
  }

  /* ------------------------------------------------------------------ */
  /* 1) MES ESCRITO POR INTEIRO E TITULO DOS DOIS BLOCOS                */
  /* ------------------------------------------------------------------ */
  function chaveMes() {
    try {
      if (typeof window.getChaveMesPgto === 'function') return String(window.getChaveMesPgto() || '');
    } catch (e) { /* ignora */ }
    return '';
  }

  function mesDaChave() {
    var m = /^(\d{4})-(\d{1,2})$/.exec(chaveMes());
    if (!m) return -1;
    var i = parseInt(m[2], 10) - 1;
    return (i >= 0 && i < 12) ? i : -1;
  }

  /* se a chave do mes nao vier, le o rotulo da tela (ex.: Ago/2026) */
  function mesDoRotulo() {
    var ids = ['pgtoMesAnoLabelResumo', 'pgtoMesAnoLabel', 'pgtoMesAnoLabelColab'];
    for (var k = 0; k < ids.length; k++) {
      var el = porId(ids[k]);
      if (!el) continue;
      var txt = String(el.textContent || '').toLowerCase();
      for (var i = 0; i < 12; i++) {
        if (txt.indexOf(MES_CURTO[i]) > -1) return i;
      }
    }
    return -1;
  }

  function mesEscrito() {
    var i = mesDaChave();
    if (i < 0) i = mesDoRotulo();
    if (i < 0) return '';
    return MES_CHEIO[i];
  }
  P74.mes = mesEscrito;

  function textoDoTitulo() {
    var nome = mesEscrito();
    return nome ? (TITULO_BASE + nome) : TITULO_BASE.replace(/\s+$/, '');
  }
  P74.textoTitulo = textoDoTitulo;

  /* o bloco de resumo que fica no fim dos Lancamentos */
  function blocoDosLancamentos() {
    return porId('p63BlocoResumo') || porId('p71BlocoResumo') || null;
  }

  function tituloDoBloco(bloco) {
    if (!bloco) return null;
    var t = bloco.querySelector('.p63-resumo-titulo, .p74-titulo-mes');
    if (t) return t;
    var h = bloco.getElementsByTagName('h3');
    for (var i = 0; i < h.length; i++) {
      var txt = String(h[i].textContent || '').toLowerCase();
      if (txt.indexOf('resumo de pagamento') > -1) return h[i];
    }
    return null;
  }

  function titulos() {
    var texto = textoDoTitulo();
    var mudou = false;

    /* bloco de baixo, dentro dos Lancamentos */
    var alvo1 = tituloDoBloco(blocoDosLancamentos());
    if (alvo1) {
      if ((alvo1.className || '').indexOf('p74-titulo-mes') < 0) {
        alvo1.className = String(alvo1.className || '') + ' p74-titulo-mes';
      }
      if (alvo1.textContent !== texto) { alvo1.textContent = texto; mudou = true; }
    }

    /* bloco da sub-aba Resumo */
    var alvo2 = porId('p71TituloResumo') || porId('p74TituloResumo');
    if (!alvo2) {
      var painel = porId('panelPgtoResumo');
      if (painel) {
        alvo2 = document.createElement('div');
        alvo2.id = 'p74TituloResumo';
        alvo2.className = 'p71-titulo';
        painel.insertBefore(alvo2, painel.firstChild);
      }
    }
    if (alvo2) {
      if ((alvo2.className || '').indexOf('p74-titulo-mes') < 0) {
        alvo2.className = String(alvo2.className || '') + ' p74-titulo-mes';
      }
      if (alvo2.textContent !== texto) { alvo2.textContent = texto; mudou = true; }
    }
    return mudou;
  }
  P74.titulos = titulos;

  /* ------------------------------------------------------------------ */
  /* 2) OS CAMPOS DE VALOR PAGO DOS DOIS LADOS                          */
  /* ------------------------------------------------------------------ */
  function camposDe(raiz) {
    if (!raiz) return [];
    return raiz.querySelectorAll(
      '.valor-pago-cell input, input[data-p71], input[data-p70-alvo], input[data-p74], td:last-child input');
  }

  function dadosDoCampo(campo) {
    if (!campo) return null;
    var colab = campo.getAttribute('data-p74-colab') || campo.getAttribute('data-p71-colab');
    var obra = campo.getAttribute('data-p74-obra') || campo.getAttribute('data-p71-obra');
    if (colab) return { colabId: colab, obraId: obra || '' };
    var attr = campo.getAttribute('onchange') || campo.getAttribute('data-p70-alvo') || '';
    var m = /atualizarValorPagoPgto\(\s*'([^']*)'\s*,\s*'([^']*)'/.exec(attr);
    if (!m) return null;
    return { colabId: m[1], obraId: m[2] };
  }

  function eNossoCampo(campo) {
    if (!campo || campo.tagName !== 'INPUT') return false;
    for (var i = 0; i < LADOS.length; i++) {
      var raiz = porId(LADOS[i][0]);
      if (raiz && raiz.contains(campo)) return true;
    }
    return false;
  }

  /* deixa o campo pronto para digitar nos dois lados */
  function liberarCampo(campo) {
    var d = dadosDoCampo(campo);
    if (!d) return null;

    campo.setAttribute('data-p74', '1');
    campo.setAttribute('data-p74-colab', d.colabId);
    if (d.obraId) campo.setAttribute('data-p74-obra', d.obraId);

    if (campo.disabled) campo.disabled = false;
    if (campo.readOnly) campo.readOnly = false;
    campo.removeAttribute('disabled');
    campo.removeAttribute('readonly');

    /* eco do numero: nao aparece na tela, aparece no papel */
    var cel = campo.parentNode;
    if (cel && cel.tagName === 'TD') {
      var eco = cel.querySelector('.p70-eco-papel, .p63-eco-papel');
      if (!eco) {
        eco = document.createElement('span');
        eco.className = 'p63-eco-papel p70-eco-papel';
        cel.appendChild(eco);
      }
      var certo = dinheiro(campo.value);
      if (eco.textContent !== certo) eco.textContent = certo;
    }
    return d;
  }

  function liberarTodos() {
    var quantos = 0;
    for (var i = 0; i < LADOS.length; i++) {
      var campos = camposDe(porId(LADOS[i][0]));
      for (var k = 0; k < campos.length; k++) {
        if (liberarCampo(campos[k])) quantos++;
      }
    }
    return quantos;
  }
  P74.liberar = liberarTodos;

  /* o mesmo colaborador aparece nos dois lados: os dois campos andam juntos */
  function espelhar(colabId, texto) {
    var alvo = String(colabId);
    for (var i = 0; i < LADOS.length; i++) {
      var campos = camposDe(porId(LADOS[i][0]));
      for (var k = 0; k < campos.length; k++) {
        var campo = campos[k];
        var d = dadosDoCampo(campo);
        if (!d || String(d.colabId) !== alvo) continue;
        if (campo !== document.activeElement && String(campo.value) !== String(texto)) {
          campo.value = texto;
        }
        var cel = campo.parentNode;
        if (cel && cel.tagName === 'TD') {
          var eco = cel.querySelector('.p70-eco-papel, .p63-eco-papel');
          if (eco) eco.textContent = dinheiro(texto);
        }
      }
    }
  }

  /* ------------------------------------------------------------------ */
  /* 3) OS DOIS QUADROS DE TOTAIS GERAIS DO MES, NA HORA                */
  /* ------------------------------------------------------------------ */
  function acharItem(caixa, rotulo) {
    var itens = caixa ? caixa.querySelectorAll('.totais-item') : [];
    for (var i = 0; i < itens.length; i++) {
      if ((itens[i].textContent || '').toLowerCase().indexOf(rotulo) > -1) return itens[i];
    }
    return null;
  }

  function valorDoItem(item) {
    if (!item) return 0;
    var v = item.querySelector('.totais-value');
    return v ? paraNumero(v.textContent) : 0;
  }

  function escreverTotais(caixaId, totalPago) {
    var caixa = porId(caixaId);
    if (!caixa) return false;

    var itemPago = acharItem(caixa, 'valor pago');
    if (itemPago) {
      var alvo = itemPago.querySelector('.totais-value');
      if (alvo) alvo.textContent = dinheiro(totalPago);
    }

    /* saldo = custo total que ja esta na tela menos o que foi pago
       (a conta do painel nao muda: so refazemos a subtracao) */
    var itemCusto = acharItem(caixa, 'custo total');
    var itemSaldo = acharItem(caixa, 'saldo');
    if (itemCusto && itemSaldo) {
      var saldo = valorDoItem(itemCusto) - paraNumero(totalPago);
      var alvoS = itemSaldo.querySelector('.totais-value');
      if (alvoS) {
        alvoS.textContent = dinheiro(saldo);
        if (saldo > 0) {
          if ((alvoS.className || '').indexOf('totais-red') < 0) alvoS.className += ' totais-red';
        } else {
          alvoS.className = String(alvoS.className || '').replace(/\s*totais-red/g, '');
        }
      }
    }
    return true;
  }

  /* soma um valor por colaborador (o mesmo nome nao conta duas vezes) */
  function somaDoLado(raizId) {
    var raiz = porId(raizId);
    if (!raiz) return null;
    var campos = camposDe(raiz);
    if (!campos || !campos.length) return null;
    var total = 0, vistos = {}, achou = false;
    for (var i = 0; i < campos.length; i++) {
      var d = dadosDoCampo(campos[i]);
      if (!d) continue;
      var chave = String(d.colabId);
      if (vistos[chave]) continue;
      vistos[chave] = true;
      total += paraNumero(campos[i].value);
      achou = true;
    }
    return achou ? total : null;
  }

  function recalcular() {
    var total = null;
    for (var i = 0; i < LADOS.length && total === null; i++) {
      total = somaDoLado(LADOS[i][0]);
    }
    if (total === null) return false;
    for (var k = 0; k < LADOS.length; k++) {
      escreverTotais(LADOS[k][1], total);
    }
    P74.ultimoTotal = total;
    return true;
  }
  P74.recalcular = recalcular;

  /* ------------------------------------------------------------------ */
  /* 4) GRAVACAO SEM PERDER O QUE ESTA SENDO DIGITADO                   */
  /* ------------------------------------------------------------------ */
  /* usa a mesma funcao de sempre do painel (nada de conta nova), mas
     segura o redesenho para o campo nao piscar no meio da digitacao */
  function gravar(colabId, obraId, valor) {
    var f = window.atualizarValorPagoPgto;
    if (typeof f !== 'function') return false;
    var guardaR = window.renderResumoPgto;
    var guardaL = window.renderLancamentosPgto;
    var nada = function () { };
    try {
      if (typeof guardaR === 'function') window.renderResumoPgto = nada;
      if (typeof guardaL === 'function') window.renderLancamentosPgto = nada;
      f(colabId, obraId, paraNumero(valor));
    } catch (e) {
      return false;
    } finally {
      if (typeof guardaR === 'function') window.renderResumoPgto = guardaR;
      if (typeof guardaL === 'function') window.renderLancamentosPgto = guardaL;
    }
    return true;
  }

  var pendente = null, relogio = null;

  function despejar() {
    if (relogio) { clearTimeout(relogio); relogio = null; }
    if (!pendente) return false;
    var p = pendente;
    pendente = null;
    return gravar(p.colabId, p.obraId, p.valor);
  }
  P74.despejar = despejar;

  function agendar(colabId, obraId, valor) {
    pendente = { colabId: colabId, obraId: obraId, valor: valor };
    if (relogio) clearTimeout(relogio);
    relogio = setTimeout(function () { relogio = null; despejar(); }, 150);
  }

  /* ------------------------------------------------------------------ */
  /* 5) ESCUTA DA DIGITACAO NOS DOIS LADOS                             */
  /* ------------------------------------------------------------------ */
  function sincronizar() {
    try { if (window.P71 && typeof window.P71.arrumar === 'function') window.P71.arrumar(); } catch (e) { /* ignora */ }
    try { liberarTodos(); } catch (e2) { /* ignora */ }
    try { recalcular(); } catch (e3) { /* ignora */ }
    try { titulos(); } catch (e4) { /* ignora */ }
    return true;
  }
  P74.sincronizar = sincronizar;

  function tratar(ev) {
    var campo = ev && ev.target;
    if (!eNossoCampo(campo)) return;
    var d = liberarCampo(campo);
    if (!d) return;

    var texto = String(campo.value);

    /* na hora: o outro lado recebe o mesmo numero e os dois quadros
       de Totais Gerais do Mes sao refeitos */
    espelhar(d.colabId, texto);
    recalcular();

    if (ev.type === 'change') {
      despejar();
      gravar(d.colabId, d.obraId, texto);
      /* depois de gravar, o painel redesenha: alinhamos tudo de novo */
      setTimeout(function () { try { sincronizar(); } catch (e) { /* ignora */ } }, 0);
    } else {
      agendar(d.colabId, d.obraId, texto);
    }
  }

  function ligarDigitacao() {
    if (P74.__digitacao) return false;
    P74.__digitacao = true;
    document.addEventListener('input', tratar, true);
    document.addEventListener('change', tratar, true);
    document.addEventListener('blur', function (ev) {
      if (eNossoCampo(ev && ev.target)) despejar();
    }, true);
    return true;
  }

  /* ------------------------------------------------------------------ */
  /* 6) LIGACOES NAS FUNCOES DO PAINEL                                  */
  /* ------------------------------------------------------------------ */
  function marcar(f) {
    f.__p74 = true;
    f.__p71 = true;
    f.__p70 = true;
    f.__p63 = true;
    return f;
  }

  function embrulhar(nome, depois) {
    var original = window[nome];
    if (typeof original !== 'function' || original.__p74) return false;
    var novo = function () {
      try { despejar(); } catch (e) { /* ignora */ }
      var r = original.apply(this, arguments);
      try { depois(); } catch (e2) { /* ignora */ }
      return r;
    };
    window[nome] = marcar(novo);
    return true;
  }

  function ligarTudo() {
    embrulhar('renderResumoPgto', function () { liberarTodos(); recalcular(); titulos(); });
    embrulhar('renderLancamentosPgto', function () { liberarTodos(); recalcular(); titulos(); });
    embrulhar('renderPagamento', function () { titulos(); recalcular(); });
    embrulhar('trocarSubTabPgtoNovo', function () { sincronizar(); });
    embrulhar('mudarMesPgto', function () { sincronizar(); });
    embrulhar('atualizarValorPagoPgto', function () { liberarTodos(); recalcular(); titulos(); });
    return true;
  }

  function comecar() {
    ligarTudo();
    ligarDigitacao();
    try { sincronizar(); } catch (e) { /* ignora */ }
    return true;
  }
  P74.comecar = comecar;

  P74.situacao = function () {
    console.log('Patch 74 ativo. Mes escrito: ' + (mesEscrito() || '(nao identificado)'));
    console.log('Titulo dos dois blocos: ' + textoDoTitulo());
    console.log('Campos de Valor Pago liberados: ' + liberarTodos());
    console.log('Total pago somado agora: ' + dinheiro(P74.ultimoTotal || 0));
    console.log('Quadros de totais encontrados: ' +
      (porId('containerTotaisPgto') ? 'Resumo sim' : 'Resumo nao') + ', ' +
      (porId('p63ResumoTotais') ? 'Lancamentos sim' : 'Lancamentos nao'));
    return true;
  };

  function esperar(vezes) {
    if (typeof window.renderResumoPgto === 'function' &&
        typeof window.atualizarValorPagoPgto === 'function') {
      comecar();
      return;
    }
    if (vezes <= 0) return;
    setTimeout(function () { esperar(vezes - 1); }, 300);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { esperar(60); });
  } else {
    esperar(60);
  }

  /* os patches antigos re-embrulham as funcoes do painel depois de uns
     segundos; a nossa camada volta por cima nessas horas */
  var HORAS = [900, 1500, 2600, 3200, 4800, 6500];
  for (var h = 0; h < HORAS.length; h++) {
    (function (t) {
      setTimeout(function () { try { comecar(); } catch (e) { /* ignora */ } }, t);
    }(HORAS[h]));
  }
})();
</script>

<style>
/* PATCH 74: TITULO COM O MES ESCRITO E VALOR PAGO NOS DOIS LADOS */

/* o titulo dos dois blocos usa o mesmo desenho de sempre */
.p74-titulo-mes {
  font-size: 1.05rem;
  font-weight: 700;
  color: #1e293b;
}

/* campo de Valor Pago segue liberado nas duas sub-abas */
#containerResumoPgto .valor-pago-cell input[data-p74],
#p63ResumoTabela .valor-pago-cell input[data-p74] {
  background: #ffffff;
  cursor: text;
  pointer-events: auto;
}

/* eco do numero digitado: escondido na tela, visivel no papel */
.p63-eco-papel,
.p70-eco-papel {
  display: none;
}

@media print {
  .p74-titulo-mes {
    background: transparent !important;
    border-left: 0 !important;
    padding-left: 0 !important;
  }

  /* no papel sai o numero, nao a caixinha de digitar */
  #containerResumoPgto .valor-pago-cell input[data-p74],
  #p63ResumoTabela .valor-pago-cell input[data-p74] {
    display: none !important;
  }

  .p63-eco-papel,
  .p70-eco-papel {
    display: inline !important;
  }
}
</style>
"""


# ---------------------------------------------------------------------------
# APLICACAO NO ARQUIVO
# ---------------------------------------------------------------------------
def fala(txt=''):
    print(txt)


def main():
    fala('=' * 70)
    fala(' PATCH 74 - Valor Pago nas duas sub-abas e titulo com o mes escrito')
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
        fala('[info] O Patch 74 JA esta aplicado neste arquivo. Nada a fazer.')
        fala('       Se quiser reaplicar, remova o bloco "%s" antes.' % MARCADOR)
        return 0

    baixo = html.lower()
    if '<body' not in baixo:
        fala('[erro] Este arquivo nao parece ser a pagina do painel (sem <body>).')
        fala('       Nenhuma alteracao foi feita.')
        return 1
    fala('[ok] Pagina do painel reconhecida.')

    if 'atualizarValorPagoPgto' in html:
        fala('[ok] Campo de VALOR PAGO encontrado: a gravacao de sempre sera usada.')
    else:
        fala('[aviso] Nao achei o campo de VALOR PAGO pelo nome usual.')
        fala('        O bloco entra do mesmo jeito e se liga quando a aba abrir.')

    if 'getChaveMesPgto' in html:
        fala('[ok] Mes do Pagamento encontrado: o titulo vai acompanhar a tela.')

    for chave, rotulo in (
        ('containerResumoPgto', 'quadro da sub-aba Resumo'),
        ('containerTotaisPgto', 'Totais Gerais do Mes (Resumo)'),
        ('p63ResumoTabela', 'quadro dentro dos Lancamentos'),
        ('p63ResumoTotais', 'Totais Gerais do Mes (Lancamentos)'),
    ):
        if chave in html:
            fala('[ok] Encontrado: ' + rotulo)
        else:
            fala('[aviso] Nao encontrado agora: ' + rotulo)
            fala('        Ele e montado quando a aba Pagamento abre; o patch')
            fala('        se liga nesse momento.')

    if 'Totais Gerais do M' in html:
        fala('[ok] Rotulos Custo Total Producao / Valor Pago / Saldo detectados.')

    if 'p71TituloResumo' in html or 'p63BlocoResumo' in html:
        fala('[ok] Titulos dos dois blocos detectados: serao escritos com o mes.')

    if 'PATCH 70' in html:
        fala('[ok] Patch 70 detectado: o valor continua guardado em uma obra so.')
    if 'PATCH 71' in html:
        fala('[ok] Patch 71 detectado: o resumo copiado continua no lugar.')
    if 'PATCH 73' in html:
        fala('[ok] Patch 73 detectado: a impressao de uma aba so fica intacta.')

    pos = baixo.rfind('</body>')
    if pos < 0:
        pos = baixo.rfind('</html>')
    if pos < 0:
        fala('[erro] Nao achei o fechamento da pagina (</body> ou </html>).')
        return 1
    fala('[ok] Lugar de insercao conferido (fim da pagina).')

    selo = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    bkp = FILE + '.bak_patch74_' + selo
    shutil.copy2(FILE, bkp)
    fala('[ok] Backup criado: ' + os.path.basename(bkp))

    novo = html[:pos] + BLOCO + '\n' + html[pos:]

    with open(FILE, 'w', encoding='utf-8', errors='surrogateescape') as f:
        f.write(novo)
    fala('[ok] Bloco inserido antes do fechamento da pagina.')
    fala('[ok] Tamanho final: %d caracteres (+%d)' % (len(novo), len(novo) - len(html)))

    fala('')
    fala('-' * 70)
    fala(' O QUE MUDA PARA VOCE')
    fala('-' * 70)
    fala('  1) Recarregue o painel com Ctrl+F5')
    fala('  2) Abra a aba Pagamento')
    fala('  3) Digite na coluna VALOR PAGO em QUALQUER uma das duas')
    fala('     sub-abas (Lancamentos ou Resumo): agora vale nas duas')
    fala('  4) Na hora, o mesmo colaborador recebe o valor no outro lado')
    fala('     e os DOIS quadros "Totais Gerais do Mes" refazem o')
    fala('     Valor Pago e o Saldo')
    fala('  5) Os dois blocos passam a mostrar o titulo:')
    fala('     "Resumo de Pagamento do Mes" + o mes escrito por inteiro')
    fala('     (por exemplo: Resumo de Pagamento do Mes Agosto)')
    fala('')
    fala('  Nenhum calculo, preco, medida, formula ou layout foi alterado.')
    fala('')
    fala('>>> Agora abra o painel e pressione Ctrl+F5 para recarregar. <<<')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        fala('[erro] Algo deu errado: %s' % e)
        fala('       Nenhuma alteracao foi concluida. Se existir um arquivo')
        fala('       .bak_patch74_, ele e a copia do seu index.html antes da')
        fala('       tentativa.')
        sys.exit(1)
