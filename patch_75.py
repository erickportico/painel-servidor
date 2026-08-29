# -*- coding: utf-8 -*-
"""
PATCH 75 - APARENCIA DAS SUB-ABAS LANCAMENTOS E RESUMO DE PAGAMENTO
===================================================================

O QUE ESTE PATCH FAZ

  Deixa as duas sub-abas da aba Pagamento com a aparencia da imagem que
  voce enviou:

  1) A faixa com o nome da obra passa a ser AZUL-MARINHO com letra
     branca, e a metragem e o custo daquela obra aparecem na MESMA LINHA
     do nome, do lado direito, dentro de um selo:

         NOME DA OBRA            Metragem: 120 m2 | Custo: R$ 3.480,00

     A metragem sai em verde-claro e o custo em amarelo, como na imagem.

  2) O cabecalho das colunas das duas tabelas fica azul-marinho com
     letra branca em maiusculas.

  3) As linhas do meio ficam TODAS brancas: acabou o efeito zebrado
     (aquela alternancia cinza/branco). Ao passar o mouse a linha ainda
     se destaca de leve, so na tela.

  4) O quadro de colaboradores ganha uma linha final TOTAL GERAL em
     AMARELO, somando Total Profissional, Total Ajudante, Total a
     Receber e Valor Pago. A linha de Total de cada obra nos
     Lancamentos tambem fica amarela.

  5) No quadro "Totais Gerais do Mes", o Custo Total Producao fica
     realcado em amarelo e o Valor Pago em verde.

MUITO IMPORTANTE: NENHUMA CONTA FOI MEXIDA

  Este patch NAO altera calculo, preco, taxa, medida nem formula. A
  metragem, o custo e o TOTAL GERAL sao apenas a SOMA DO QUE JA ESTA
  ESCRITO na propria tabela da tela: o patch le os numeros que o painel
  ja mostrou e os repete no lugar novo. Se um numero mudar na tabela, o
  selo e o TOTAL GERAL se refazem sozinhos.

COMO FICA NA PRATICA

  1) Abra a aba Pagamento
  2) Sub-aba Lancamentos: cada obra aparece com a faixa azul-marinho e,
     na mesma linha, "Metragem: X m2 | Custo: R$ Y"
  3) Sub-aba Resumo de Pagamento: cabecalho azul-marinho, linhas
     brancas e a linha TOTAL GERAL em amarelo no fim do quadro
  4) Digitando na coluna VALOR PAGO, o TOTAL GERAL se atualiza na hora

O QUE CONTINUA EXATAMENTE COMO ESTA

  - As colunas e a ordem delas: COLABORADOR / TOTAL PROFISSIONAL /
    TOTAL AJUDANTE / TOTAL A RECEBER / VALOR PAGO
  - A digitacao do Valor Pago nas duas sub-abas (patch 74) e a gravacao
    em uma obra so (patch 70)
  - O titulo com o mes escrito por inteiro (patch 74)
  - O quadro Totais Gerais do Mes com Metragem, Profissionais,
    Ajudantes, Custo, Valor Pago e Saldo, com os mesmos numeros
  - As impressoes (aba inteira, quadro sozinho, PDF): as cores novas
    saem no papel iguais as da tela
  - As demais abas do painel, inclusive Centro de Custos, ficam intactas

SEGURANCA
  - Nao apaga nem reescreve nada: insere apenas UM bloco novo antes do
    fechamento da pagina
  - Backup automatico do index.html antes de gravar
  - Idempotente: rodar de novo nao duplica nada

NO PAINEL, PELO CONSOLE (F12), SE QUISER
  P75.situacao()   mostra quantas faixas e quantos TOTAL GERAL estao ok
  P75.aplicar()    refaz a aparencia na hora
  P75.ajuda()      lista os comandos

COMO USAR
  python patch_75.py
  depois abra o painel e pressione Ctrl+F5
"""

import os
import shutil
import sys
import datetime

FILE = r'C:/Users/OBRAS 8/Desktop/PAINEL SERVIDOR/index.html'

MARCADOR = 'PATCH 75: APARENCIA DAS SUB-ABAS'



# ---------------------------------------------------------------------------
# BLOCO INSERIDO NO index.html
# ---------------------------------------------------------------------------
BLOCO = r"""

<script>
/* PATCH 75: APARENCIA DAS SUB-ABAS LANCAMENTOS E RESUMO DE PAGAMENTO */
(function () {
  if (window.P75 && window.P75.__v75) return;
  var P75 = window.P75 = window.P75 || {};
  P75.__v75 = true;

  var trabalhando = false;
  var agendado = null;

  /* ------------------------------------------------------------------ */
  /* AJUDANTES                                                          */
  /* ------------------------------------------------------------------ */
  function porId(id) { return document.getElementById(id); }

  function texto(el) { return el ? String(el.textContent || '') : ''; }

  function paraNumero(v) {
    if (typeof v === 'number') return isFinite(v) ? v : 0;
    var s = String(v == null ? '' : v);
    s = s.replace(/R\$/gi, '').replace(/m\u00b2/gi, '').replace(/\s|\u00a0/g, '');
    if (s.indexOf(',') > -1) {
      if (s.indexOf('.') > -1) s = s.replace(/\./g, '');
      s = s.replace(',', '.');
    }
    s = s.replace(/[^0-9.\-]/g, '');
    var n = parseFloat(s);
    return isFinite(n) ? n : 0;
  }

  function numeroBonito(n, casas) {
    var v = paraNumero(n);
    try {
      return v.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
    } catch (e) {
      return v.toFixed(casas);
    }
  }

  function metragemBonita(n) {
    var v = paraNumero(n);
    var inteiro = Math.abs(v - Math.round(v)) < 0.0001;
    return numeroBonito(v, inteiro ? 0 : 2);
  }

  function dinheiro(n) { return 'R$ ' + numeroBonito(n, 2); }

  function limpar(t) {
    return String(t || '').replace(/\s|\u00a0/g, '').toLowerCase();
  }

  /* le a linha de Total que a propria tabela ja escreveu no pe dela:
     nada e recalculado, so aproveitado */
  function lerPeDaTabela(tabela) {
    var linha = tabela.querySelector('tfoot tr.lanc-totals-row') || tabela.querySelector('tfoot tr');
    if (!linha) return null;
    var celulas = linha.children;
    if (!celulas || celulas.length < 3) return null;

    var m2 = null;
    var custo = 0;
    var achouDinheiro = false;

    for (var i = 0; i < celulas.length; i++) {
      var bruto = texto(celulas[i]).trim();
      if (!bruto) continue;
      if (bruto.indexOf('R$') > -1) {
        custo += paraNumero(bruto);
        achouDinheiro = true;
        continue;
      }
      if (m2 === null && /[0-9]/.test(bruto)) m2 = paraNumero(bruto);
    }

    if (m2 === null && !achouDinheiro) return null;
    return { m2: m2 === null ? 0 : m2, custo: custo };
  }

  /* acha em qual coluna da tabela esta cada titulo procurado */
  function colunaPorTitulo(tabela, pedacos) {
    var ths = tabela.querySelectorAll('thead th');
    for (var i = 0; i < ths.length; i++) {
      var t = limpar(texto(ths[i]));
      for (var p = 0; p < pedacos.length; p++) {
        if (t.indexOf(pedacos[p]) === 0 || t === pedacos[p]) return i;
      }
    }
    return -1;
  }

  /* soma uma coluna do corpo da tabela, sem tocar em conta nenhuma:
     apenas le o que ja esta escrito na tela */
  function somaColuna(tabela, indice) {
    if (indice < 0) return 0;
    var total = 0;
    var linhas = tabela.querySelectorAll('tbody tr');
    for (var i = 0; i < linhas.length; i++) {
      if (linhas[i].getAttribute('data-p75tg')) continue;
      var tds = linhas[i].children;
      if (!tds || tds.length <= indice) continue;
      var cel = tds[indice];
      var campo = cel.querySelector ? cel.querySelector('input') : null;
      total += paraNumero(campo ? campo.value : texto(cel));
    }
    return total;
  }

  function contarLinhas(tabela) {
    var linhas = tabela.querySelectorAll('tbody tr');
    var n = 0;
    for (var i = 0; i < linhas.length; i++) {
      if (!linhas[i].getAttribute('data-p75tg')) n++;
    }
    return n;
  }

  /* ------------------------------------------------------------------ */
  /* 1) FAIXA DA OBRA: NOME NA ESQUERDA, MEDIDAS NA MESMA LINHA         */
  /* ------------------------------------------------------------------ */
  function arrumarFaixasDeObra() {
    var painel = porId('panelPgtoLancamentos');
    if (!painel) return 0;
    var grupos = painel.querySelectorAll('.lanc-obra-group');
    var feitos = 0;

    for (var i = 0; i < grupos.length; i++) {
      var grupo = grupos[i];
      var faixa = grupo.querySelector('.lanc-obra-header');
      var tabela = grupo.querySelector('table');
      if (!faixa || !tabela) continue;

      /* o nome da obra e guardado na primeira passada e reusado depois */
      var nome = faixa.getAttribute('data-p75-nome');
      if (nome == null) {
        var solto = faixa.querySelector('.p75-obra-nome');
        nome = solto ? texto(solto).trim() : texto(faixa).trim();
        faixa.setAttribute('data-p75-nome', nome);
      }

      var pe = lerPeDaTabela(tabela);
      if (!pe) continue;
      var m2 = pe.m2;
      var custo = pe.custo;

      var novo = '<span class="p75-obra-nome"></span>' +
        '<span class="p75-selo">' +
        '<span class="p75-m2">Metragem: ' + metragemBonita(m2) + ' m\u00b2</span>' +
        '<span class="p75-risco">|</span>' +
        '<span class="p75-custo">Custo: ' + dinheiro(custo) + '</span>' +
        '</span>';

      var assinatura = nome + '||' + metragemBonita(m2) + '||' + numeroBonito(custo, 2);
      if (faixa.getAttribute('data-p75') === '1' && faixa.getAttribute('data-p75-selo') === assinatura) continue;

      faixa.innerHTML = novo;
      /* o nome entra como texto puro, nunca como pedaco de pagina */
      faixa.firstChild.textContent = nome;
      faixa.setAttribute('data-p75', '1');
      faixa.setAttribute('data-p75-selo', assinatura);
      feitos++;
    }
    return feitos;
  }

  /* ------------------------------------------------------------------ */
  /* 2) LINHA TOTAL GERAL AMARELA NO QUADRO DE COLABORADORES            */
  /* ------------------------------------------------------------------ */
  var QUADROS = ['containerResumoPgto', 'p63ResumoTabela'];

  function arrumarTotalGeral() {
    var feitos = 0;
    for (var q = 0; q < QUADROS.length; q++) {
      var caixa = porId(QUADROS[q]);
      if (!caixa) continue;
      var tabela = caixa.querySelector('table');
      if (!tabela) continue;
      var corpo = tabela.querySelector('tbody');
      if (!corpo) continue;

      var antiga = corpo.querySelector('tr[data-p75tg]');

      if (contarLinhas(tabela) === 0) {
        if (antiga && antiga.parentNode) antiga.parentNode.removeChild(antiga);
        continue;
      }

      var colunas = tabela.querySelectorAll('thead th').length;
      if (colunas < 2) continue;

      var iProf = colunaPorTitulo(tabela, ['totalprofissional']);
      var iAjud = colunaPorTitulo(tabela, ['totalajudante']);
      var iRec = colunaPorTitulo(tabela, ['totalareceber']);
      var iPago = colunaPorTitulo(tabela, ['valorpago']);

      var valores = [];
      valores.push({ i: iProf, v: somaColuna(tabela, iProf) });
      valores.push({ i: iAjud, v: somaColuna(tabela, iAjud) });
      valores.push({ i: iRec, v: somaColuna(tabela, iRec) });
      valores.push({ i: iPago, v: somaColuna(tabela, iPago) });

      var partes = [];
      var assinatura = '';
      for (var c = 0; c < colunas; c++) {
        if (c === 0) {
          partes.push('<td class="p75-rotulo-total">TOTAL GERAL</td>');
          continue;
        }
        var achou = null;
        for (var k = 0; k < valores.length; k++) {
          if (valores[k].i === c) { achou = valores[k]; break; }
        }
        if (achou) {
          partes.push('<td>' + dinheiro(achou.v) + '</td>');
          assinatura += c + ':' + numeroBonito(achou.v, 2) + ';';
        } else {
          partes.push('<td></td>');
        }
      }

      if (antiga && antiga.getAttribute('data-p75tg') === assinatura) continue;

      var linha = document.createElement('tr');
      linha.className = 'p75-total-geral';
      linha.setAttribute('data-p75tg', assinatura);
      linha.innerHTML = partes.join('');

      if (antiga && antiga.parentNode) {
        antiga.parentNode.replaceChild(linha, antiga);
      } else {
        corpo.appendChild(linha);
      }
      feitos++;
    }
    return feitos;
  }

  /* ------------------------------------------------------------------ */
  /* PASSADA COMPLETA                                                   */
  /* ------------------------------------------------------------------ */
  function passar() {
    if (trabalhando) return;
    trabalhando = true;
    try {
      arrumarFaixasDeObra();
      arrumarTotalGeral();
    } catch (e) { /* nunca atrapalha o painel */ }
    trabalhando = false;
  }

  function agendar() {
    if (trabalhando) return;
    if (agendado) return;
    agendado = setTimeout(function () { agendado = null; passar(); }, 60);
  }

  /* ------------------------------------------------------------------ */
  /* LIGACOES: DESENHO, TROCA DE ABA, TROCA DE MES, DIGITACAO           */
  /* ------------------------------------------------------------------ */
  function embrulhar(nome) {
    var antiga = window[nome];
    if (typeof antiga !== 'function') return false;
    if (antiga.__p75) return true;
    var nova = function () {
      var r;
      try { r = antiga.apply(this, arguments); } finally { agendar(); }
      return r;
    };
    nova.__p75 = true;
    nova.__p75antiga = antiga;
    try { window[nome] = nova; } catch (e) { return false; }
    return true;
  }

  var ALVOS = ['renderLancamentosPgto', 'renderResumoPgto', 'trocarSubTabPgtoNovo',
    'mudarMesPgto', 'atualizarValorPagoPgto', 'renderPagamentoProducao'];

  function ligar() {
    for (var i = 0; i < ALVOS.length; i++) embrulhar(ALVOS[i]);

    var caixas = ['containerLancamentosPgto', 'containerResumoPgto',
      'p63ResumoTabela', 'panelPgtoLancamentos', 'panelPgtoResumo'];
    for (var c = 0; c < caixas.length; c++) {
      var el = porId(caixas[c]);
      if (!el || el.getAttribute('data-p75-olho') === '1') continue;
      try {
        var olho = new MutationObserver(function () { agendar(); });
        olho.observe(el, { childList: true, subtree: true });
        el.setAttribute('data-p75-olho', '1');
      } catch (e) { /* ignora */ }
    }

    if (!document.__p75digita) {
      document.addEventListener('input', function (ev) {
        var alvo = ev && ev.target;
        if (!alvo || !alvo.closest) return;
        if (alvo.closest('.valor-pago-cell')) agendar();
      }, true);
      document.addEventListener('change', function (ev) {
        var alvo = ev && ev.target;
        if (!alvo || !alvo.closest) return;
        if (alvo.closest('.valor-pago-cell')) agendar();
      }, true);
      document.__p75digita = true;
    }

    passar();
  }

  /* ------------------------------------------------------------------ */
  /* COMANDOS DE CONSOLE                                                */
  /* ------------------------------------------------------------------ */
  P75.aplicar = function () { passar(); return true; };

  P75.situacao = function () {
    var painel = porId('panelPgtoLancamentos');
    var faixas = painel ? painel.querySelectorAll('.lanc-obra-header[data-p75="1"]').length : 0;
    var totais = 0;
    for (var q = 0; q < QUADROS.length; q++) {
      var caixa = porId(QUADROS[q]);
      if (caixa && caixa.querySelector('tr[data-p75tg]')) totais++;
    }
    console.log('[P75] faixas de obra com metragem e custo: ' + faixas);
    console.log('[P75] quadros com linha TOTAL GERAL: ' + totais);
    return true;
  };

  P75.ajuda = function () {
    console.log('[P75] P75.aplicar() refaz a aparencia agora');
    console.log('[P75] P75.situacao() mostra o que esta arrumado');
    return true;
  };

  function esperar(vezes) {
    if (porId('panelPgtoLancamentos') || typeof window.renderLancamentosPgto === 'function') {
      ligar();
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
  var HORAS = [900, 1500, 2600, 3200, 4800, 6500, 9000];
  for (var h = 0; h < HORAS.length; h++) {
    (function (t) {
      setTimeout(function () { try { ligar(); } catch (e) { /* ignora */ } }, t);
    }(HORAS[h]));
  }

  console.log('PATCH 75 ativo: faixa da obra com Metragem e Custo na mesma linha, quadros sem zebra e TOTAL GERAL em amarelo. Use P75.ajuda().');
})();
</script>

<style>
/* PATCH 75: APARENCIA DAS DUAS SUB-ABAS DO PAGAMENTO */

/* ------------------------------------------------------------------ */
/* 1) FAIXA DO NOME DA OBRA: AZUL-MARINHO, NOME E MEDIDAS NA MESMA LINHA */
/* ------------------------------------------------------------------ */
#tab-pagamento .lanc-obra-header,
#panelPgtoLancamentos .lanc-obra-header {
  background: #1e3a5f !important;
  color: #ffffff !important;
  border-bottom: 1px solid #16304f !important;
  padding: 10px 14px;
  font-weight: 700;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

/* nome da obra fica na esquerda */
#tab-pagamento .lanc-obra-header .p75-obra-nome {
  color: #ffffff;
  font-weight: 700;
  letter-spacing: 0.2px;
}

/* selo com Metragem e Custo, na mesma linha do nome, do lado direito */
#tab-pagamento .lanc-obra-header .p75-selo {
  background: #4b5e6f;
  border: 1px solid #5c7185;
  border-radius: 6px;
  padding: 3px 10px;
  font-size: 0.8rem;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}
#tab-pagamento .lanc-obra-header .p75-selo .p75-m2 { color: #86efac; }
#tab-pagamento .lanc-obra-header .p75-selo .p75-custo { color: #fde047; }
#tab-pagamento .lanc-obra-header .p75-selo .p75-risco { color: #94a3b8; font-weight: 400; }

/* ------------------------------------------------------------------ */
/* 2) CABECALHO DAS COLUNAS: AZUL-MARINHO COM LETRA BRANCA            */
/* ------------------------------------------------------------------ */
#tab-pagamento .lanc-table thead th,
#tab-pagamento .resumo-table thead th,
#p63ResumoTabela table thead th,
#containerResumoPgto table thead th {
  background: #34495e !important;
  color: #ffffff !important;
  border-bottom: 2px solid #1e3a5f !important;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  font-size: 0.78rem;
}

/* ------------------------------------------------------------------ */
/* 3) SEM ZEBRA: TODAS AS LINHAS BRANCAS                              */
/* ------------------------------------------------------------------ */
#tab-pagamento .lanc-table tbody tr,
#tab-pagamento .lanc-table tbody tr:nth-child(even),
#tab-pagamento .resumo-table tbody tr,
#tab-pagamento .resumo-table tbody tr:nth-child(even),
#p63ResumoTabela table tbody tr,
#p63ResumoTabela table tbody tr:nth-child(even),
#containerResumoPgto table tbody tr,
#containerResumoPgto table tbody tr:nth-child(even) {
  background: #ffffff !important;
}
#tab-pagamento .lanc-table tbody td,
#tab-pagamento .resumo-table tbody td,
#p63ResumoTabela table tbody td {
  border-bottom: 1px solid #e5e9f0;
}

/* a linha embaixo do ponteiro fica levemente marcada, so na tela */
#tab-pagamento .lanc-table tbody tr:hover,
#tab-pagamento .resumo-table tbody tr:hover,
#p63ResumoTabela table tbody tr:hover {
  background: #f7fafc !important;
}

/* ------------------------------------------------------------------ */
/* 4) LINHA DE TOTAL GERAL EM AMARELO                                 */
/* ------------------------------------------------------------------ */
#tab-pagamento .lanc-table tfoot tr,
#tab-pagamento .lanc-totals-row,
#tab-pagamento .resumo-table .total-row,
#tab-pagamento .p75-total-geral,
#p63ResumoTabela table .p75-total-geral,
#containerResumoPgto table .p75-total-geral {
  background: #fde047 !important;
  color: #6b4b06 !important;
  font-weight: 800 !important;
  border-top: 2px solid #ca8a04 !important;
}
#tab-pagamento .lanc-totals-row td,
#tab-pagamento .resumo-table .total-row td,
#tab-pagamento .p75-total-geral td,
#p63ResumoTabela table .p75-total-geral td,
#containerResumoPgto table .p75-total-geral td {
  background: #fde047 !important;
  color: #6b4b06 !important;
  font-weight: 800 !important;
  border-top: 2px solid #ca8a04 !important;
  border-bottom: none !important;
  padding: 9px 12px !important;
}
#tab-pagamento .p75-total-geral .p75-rotulo-total {
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

/* ------------------------------------------------------------------ */
/* 5) QUADRO DE TOTAIS: CUSTO EM AMARELO, VALOR PAGO EM VERDE         */
/* ------------------------------------------------------------------ */
#tab-pagamento .totais-panel h3,
#p63ResumoTotais h3 {
  color: #1e3a5f;
}
#tab-pagamento .totais-item.totais-yellow,
#p63ResumoTotais .totais-item.totais-yellow {
  background: #fef9c3;
  border-radius: 6px;
  padding: 8px 10px;
}
#tab-pagamento .totais-item.totais-yellow .totais-value,
#p63ResumoTotais .totais-item.totais-yellow .totais-value {
  color: #92400e;
}
#tab-pagamento .totais-item.totais-green,
#p63ResumoTotais .totais-item.totais-green {
  background: #f0fdf4;
  border-radius: 6px;
  padding: 8px 10px;
}
#tab-pagamento .totais-item.totais-green .totais-value,
#p63ResumoTotais .totais-item.totais-green .totais-value {
  color: #166534;
}

/* ------------------------------------------------------------------ */
/* 6) MODO ESCURO                                                     */
/* ------------------------------------------------------------------ */
body.dark-mode #tab-pagamento .lanc-obra-header {
  background: #16304f !important;
  color: #ffffff !important;
  border-color: #0f2340 !important;
}
body.dark-mode #tab-pagamento .lanc-obra-header .p75-selo {
  background: #24405f;
  border-color: #35577c;
}
body.dark-mode #tab-pagamento .lanc-table thead th,
body.dark-mode #tab-pagamento .resumo-table thead th,
body.dark-mode #p63ResumoTabela table thead th,
body.dark-mode #containerResumoPgto table thead th {
  background: #24405f !important;
  color: #ffffff !important;
  border-bottom-color: #16304f !important;
}
body.dark-mode #tab-pagamento .lanc-table tbody tr,
body.dark-mode #tab-pagamento .lanc-table tbody tr:nth-child(even),
body.dark-mode #tab-pagamento .resumo-table tbody tr,
body.dark-mode #tab-pagamento .resumo-table tbody tr:nth-child(even),
body.dark-mode #p63ResumoTabela table tbody tr,
body.dark-mode #p63ResumoTabela table tbody tr:nth-child(even),
body.dark-mode #containerResumoPgto table tbody tr,
body.dark-mode #containerResumoPgto table tbody tr:nth-child(even) {
  background: var(--card-bg,#1e293b) !important;
}
body.dark-mode #tab-pagamento .lanc-table tbody tr:hover,
body.dark-mode #tab-pagamento .resumo-table tbody tr:hover,
body.dark-mode #p63ResumoTabela table tbody tr:hover {
  background: #24344c !important;
}
body.dark-mode #tab-pagamento .lanc-totals-row,
body.dark-mode #tab-pagamento .lanc-totals-row td,
body.dark-mode #tab-pagamento .resumo-table .total-row,
body.dark-mode #tab-pagamento .resumo-table .total-row td,
body.dark-mode #tab-pagamento .p75-total-geral,
body.dark-mode #tab-pagamento .p75-total-geral td,
body.dark-mode #p63ResumoTabela table .p75-total-geral,
body.dark-mode #p63ResumoTabela table .p75-total-geral td {
  background: #3d2f05 !important;
  color: #fde047 !important;
  border-top-color: #a16207 !important;
}

/* ------------------------------------------------------------------ */
/* 7) NO PAPEL AS CORES SAIEM IGUAIS A TELA                           */
/* ------------------------------------------------------------------ */
@media print {
  #tab-pagamento .lanc-obra-header {
    background: #1e3a5f !important;
    color: #ffffff !important;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  #tab-pagamento .lanc-obra-header .p75-selo {
    background: #4b5e6f !important;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  #tab-pagamento .lanc-table thead th,
  #tab-pagamento .resumo-table thead th,
  #p63ResumoTabela table thead th,
  #containerResumoPgto table thead th {
    background: #34495e !important;
    color: #ffffff !important;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  #tab-pagamento .lanc-table tbody tr,
  #tab-pagamento .resumo-table tbody tr,
  #p63ResumoTabela table tbody tr {
    background: #ffffff !important;
  }
  #tab-pagamento .lanc-totals-row,
  #tab-pagamento .lanc-totals-row td,
  #tab-pagamento .resumo-table .total-row,
  #tab-pagamento .resumo-table .total-row td,
  #tab-pagamento .p75-total-geral,
  #tab-pagamento .p75-total-geral td,
  #p63ResumoTabela table .p75-total-geral,
  #p63ResumoTabela table .p75-total-geral td {
    background: #fde047 !important;
    color: #6b4b06 !important;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
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
    fala(' PATCH 75 - Aparencia das sub-abas Lancamentos e Resumo de Pagamento')
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
        fala('[info] O Patch 75 JA esta aplicado neste arquivo. Nada a fazer.')
        fala('       Se quiser reaplicar, remova o bloco "%s" antes.' % MARCADOR)
        return 0

    baixo = html.lower()
    if '<body' not in baixo:
        fala('[erro] Este arquivo nao parece ser a pagina do painel (sem <body>).')
        fala('       Nenhuma alteracao foi feita.')
        return 1
    fala('[ok] Pagina do painel reconhecida.')

    if 'lanc-obra-header' in html:
        fala('[ok] Faixa com o nome da obra encontrada: vai ficar azul-marinho')
        fala('     com a Metragem e o Custo na mesma linha do nome.')
    else:
        fala('[aviso] Nao achei a faixa do nome da obra agora.')
        fala('        Ela e montada quando a aba Pagamento abre; o patch se')
        fala('        liga nesse momento.')

    for chave, rotulo in (
        ('containerLancamentosPgto', 'tabela da sub-aba Lancamentos'),
        ('containerResumoPgto', 'quadro da sub-aba Resumo'),
        ('containerTotaisPgto', 'Totais Gerais do Mes (Resumo)'),
        ('p63ResumoTabela', 'quadro dentro dos Lancamentos'),
        ('p63ResumoTotais', 'Totais Gerais do Mes (Lancamentos)'),
    ):
        if chave in html:
            fala('[ok] Encontrado: ' + rotulo)
        else:
            fala('[aviso] Nao encontrado agora: ' + rotulo)

    if 'nth-child(even)' in html:
        fala('[ok] Efeito zebrado localizado: sera desligado nos dois quadros.')

    if 'lanc-totals-row' in html:
        fala('[ok] Linha de Total dos Lancamentos localizada: ficara amarela.')

    if 'Totais Gerais do M' in html:
        fala('[ok] Rotulos Custo Total Producao / Valor Pago / Saldo detectados.')

    if 'PATCH 70' in html:
        fala('[ok] Patch 70 detectado: o valor continua guardado em uma obra so.')
    if 'PATCH 71' in html:
        fala('[ok] Patch 71 detectado: o resumo copiado continua no lugar.')
    if 'PATCH 73' in html:
        fala('[ok] Patch 73 detectado: a impressao de uma aba so fica intacta.')
    if 'PATCH 74' in html:
        fala('[ok] Patch 74 detectado: Valor Pago nos dois lados e titulo com')
        fala('     o mes escrito continuam funcionando.')

    pos = baixo.rfind('</body>')
    if pos < 0:
        pos = baixo.rfind('</html>')
    if pos < 0:
        fala('[erro] Nao achei o fechamento da pagina (</body> ou </html>).')
        return 1
    fala('[ok] Lugar de insercao conferido (fim da pagina).')

    selo = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    bkp = FILE + '.bak_patch75_' + selo
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
    fala('  3) Na sub-aba Lancamentos, cada obra aparece com a faixa')
    fala('     azul-marinho e, na MESMA LINHA do nome:')
    fala('     "Metragem: X m2 | Custo: R$ Y"')
    fala('  4) Nas duas sub-abas o cabecalho fica azul-marinho com letra')
    fala('     branca e as linhas do meio ficam todas brancas (sem zebra)')
    fala('  5) O quadro de colaboradores termina com a linha TOTAL GERAL')
    fala('     em amarelo, e ela se atualiza quando voce digita o Valor Pago')
    fala('')
    fala('  Nenhum calculo, preco, medida, formula ou coluna foi alterado:')
    fala('  os numeros novos sao a soma do que a tabela ja mostrava.')
    fala('')
    fala('>>> Agora abra o painel e pressione Ctrl+F5 para recarregar. <<<')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        fala('[erro] Algo deu errado: %s' % e)
        fala('       Nenhuma alteracao foi concluida. Se existir um arquivo')
        fala('       .bak_patch75_, ele e a copia do seu index.html antes da')
        fala('       tentativa.')
        sys.exit(1)
