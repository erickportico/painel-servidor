# -*- coding: utf-8 -*-
"""
PATCH 85 - Salvar em PDF de verdade (Boletim de Inspecao e Diario de Obra)

O que faz:
  1) Coloca um botao vermelho "Salvar PDF" ao lado do botao
     "Imprimir / PDF" nos dois relatorios novos:
       - Boletim de Inspecao (patch 83)
       - Diario de Obra (patch 84)
  2) Ao clicar, o proprio painel monta o arquivo .pdf e baixa
     direto no aparelho. Nao abre a janela de impressao e nao
     depende de escolher "Salvar como PDF" na impressora.
  3) O PDF sai em folha A4 em pe, com margem, quebrando o
     conteudo em quantas paginas forem necessarias, com as fotos
     e o campo de assinatura do jeito que aparece na impressao.
  4) O arquivo recebe um nome automatico facil de achar depois,
     por exemplo:
       boletim_inspecao_N12_2026-08-30.pdf
       diario_de_obra_N7_2026-08-30.pdf
  5) Enquanto gera, aparece um aviso "Gerando PDF..." mostrando
     em qual pagina esta, para voce saber que esta trabalhando.
  6) Se o aparelho estiver sem internet na primeira vez que usar,
     o painel avisa e voce pode continuar usando o botao
     "Imprimir / PDF" normalmente.

Como usar:
  Coloque este arquivo na mesma pasta do index.html e execute:
      python patch85_exportar_pdf.py

Observacao:
  Este patch deve ser aplicado depois dos patches 83 e 84, porque
  ele acrescenta o botao dentro daqueles dois relatorios.

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

MARCA = 'PATCH85_EXPORTAR_PDF_OK'

JS = r"""/* PATCH 85 - exportar PDF de verdade nos relatorios 83 e 84 */
(function () {
  'use strict';

  if (window.__p85Pronto) { return; }
  window.__p85Pronto = true;

  var FONTES_CANVAS = [
    'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js',
    'https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js',
    'https://unpkg.com/html2canvas@1.4.1/dist/html2canvas.min.js'
  ];
  var FONTES_PDF = [
    'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js',
    'https://cdn.jsdelivr.net/npm/jspdf@2.5.1/dist/jspdf.umd.min.js',
    'https://unpkg.com/jspdf@2.5.1/dist/jspdf.umd.min.js'
  ];

  /* A4 com margem de 12mm */
  var LARG_MM = 186;
  var ALT_MM = 273;
  var MARG_MM = 12;
  var LARG_PX = 703;
  var ALT_PX = Math.floor(LARG_PX * (ALT_MM / LARG_MM));

  /* ================================================================ *
   * utilidades
   * ================================================================ */
  function aviso(msg, tipo) {
    var d = document.getElementById('p85Aviso');
    if (!d) {
      d = document.createElement('div');
      d.id = 'p85Aviso';
      document.body.appendChild(d);
    }
    d.className = 'p85-aviso ' + (tipo === 'erro' ? 'p85-erro' : 'p85-ok');
    d.textContent = msg;
    d.style.display = 'block';
    if (d.__t) { clearTimeout(d.__t); }
    d.__t = setTimeout(function () { d.style.display = 'none'; }, 4200);
  }

  function espera(ms, fn) { setTimeout(fn, ms); }

  function limpaNome(s) {
    s = String(s || '').replace(/[^0-9A-Za-z\u00C0-\u017F _.-]+/g, '');
    s = s.replace(/\s+/g, '_').replace(/_+/g, '_');
    return s.substring(0, 70) || 'relatorio';
  }

  function carregarUm(url, ok, falhou) {
    var s = document.createElement('script');
    s.src = url;
    s.async = true;
    s.onload = function () { ok(); };
    s.onerror = function () {
      try { s.parentNode.removeChild(s); } catch (e) {}
      falhou();
    };
    (document.head || document.documentElement).appendChild(s);
  }

  function carregarLista(lista, testar, ok, falhou) {
    if (testar()) { ok(); return; }
    var i = 0;
    function tenta() {
      if (i >= lista.length) { falhou(); return; }
      var url = lista[i++];
      carregarUm(url, function () {
        if (testar()) { ok(); } else { tenta(); }
      }, tenta);
    }
    tenta();
  }

  function temCanvas() { return typeof window.html2canvas === 'function'; }
  function temPdf() {
    return !!(window.jspdf && window.jspdf.jsPDF) || typeof window.jsPDF === 'function';
  }
  function classePdf() {
    if (window.jspdf && window.jspdf.jsPDF) { return window.jspdf.jsPDF; }
    return window.jsPDF;
  }

  function prepararLibs(ok, falhou) {
    carregarLista(FONTES_CANVAS, temCanvas, function () {
      carregarLista(FONTES_PDF, temPdf, ok, falhou);
    }, falhou);
  }

  /* ================================================================ *
   * estilo: espera, botao e folha do PDF
   * ================================================================ */
  function estilo() {
    if (document.getElementById('p85Estilo')) { return; }
    var s = document.createElement('style');
    s.id = 'p85Estilo';
    s.textContent = [
      '.p85-aviso{position:fixed;right:16px;bottom:16px;z-index:2147483647;padding:10px 14px;border-radius:10px;color:#fff;font:13px/1.4 system-ui,Segoe UI,Arial;box-shadow:0 8px 24px rgba(0,0,0,.35);display:none;max-width:min(420px,88vw)}',
      '.p85-ok{background:#0f766e}.p85-erro{background:#b91c1c}',
      '.p85-btn-pdf{background:#dc2626;color:#fff;border:1px solid #dc2626;border-radius:9px;padding:7px 12px;cursor:pointer;font-size:13px}',
      '.p85-btn-pdf:hover{filter:brightness(1.08)}',
      '.p85-btn-pdf[disabled]{opacity:.6;cursor:default}',
      '#p85Espera{position:fixed;inset:0;background:rgba(2,6,23,.78);z-index:2147483500;display:flex;align-items:center;justify-content:center;padding:16px}',
      '#p85Espera .cx{background:#0f172a;color:#e2e8f0;border:1px solid #334155;border-radius:12px;padding:18px 22px;font:14px/1.5 system-ui,Segoe UI,Arial;text-align:center;min-width:min(320px,86vw)}',
      '#p85Espera .cx b{display:block;margin-bottom:6px;font-size:15px}',
      '#p85Espera .cx small{color:#94a3b8}',
      '#p85Espera .bar{height:6px;border-radius:6px;background:#1e293b;overflow:hidden;margin-top:12px}',
      '#p85Espera .bar i{display:block;height:100%;width:30%;background:#38bdf8;border-radius:6px;animation:p85run 1.1s linear infinite}',
      '@keyframes p85run{0%{margin-left:-30%}100%{margin-left:100%}}',
      '#p85Palco{position:fixed;left:-20000px;top:0;z-index:-1;background:#fff}',
      '.p85-folha{width:' + LARG_PX + 'px;background:#fff;padding:0;margin:0}',
      '.p85-folha,.p85-folha *{color:#000;font-family:Arial,Helvetica,sans-serif;box-sizing:border-box}',
      '.p85-folha .pr-tit{text-align:center;font-size:16px;font-weight:700;margin:0 0 2px}',
      '.p85-folha .pr-sub{text-align:center;font-size:11px;margin:0 0 10px}',
      '.p85-folha table{width:100%;border-collapse:collapse;margin:0 0 10px;font-size:11px}',
      '.p85-folha th,.p85-folha td{border:1px solid #000;padding:4px 6px;vertical-align:top;text-align:left}',
      '.p85-folha th{background:#e5e7eb}',
      '.p85-folha h3{font-size:12px;margin:12px 0 4px;border-bottom:1px solid #000;padding-bottom:2px}',
      '.p85-folha .pr-tx{font-size:11px;white-space:pre-wrap;margin:0 0 6px}',
      '.p85-folha .pr-bl{border:1px solid #000;padding:6px;margin:0 0 8px}',
      '.p85-folha .pr-bl b{font-size:11px}',
      '.p85-folha .pr-fotos{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:6px}',
      '.p85-folha .pr-fotos figure{margin:0}',
      '.p85-folha .pr-fotos img{width:100%;height:auto;border:1px solid #000;display:block}',
      '.p85-folha .pr-fotos figcaption{font-size:10px;text-align:center;padding:2px}',
      '.p85-folha .pr-ass{margin-top:26px;text-align:center;font-size:11px}',
      '.p85-folha .pr-mk{font-weight:700}',
      '.p85-pag{width:' + LARG_PX + 'px;background:#fff}'
    ].join('\n');
    (document.head || document.documentElement).appendChild(s);
  }

  function espera_liga(texto) {
    var e = document.getElementById('p85Espera');
    if (!e) {
      e = document.createElement('div');
      e.id = 'p85Espera';
      e.innerHTML = '<div class="cx"><b>Gerando PDF...</b><small id="p85EsperaTxt"></small><div class="bar"><i></i></div></div>';
      document.body.appendChild(e);
    }
    e.style.display = 'flex';
    var t = document.getElementById('p85EsperaTxt');
    if (t) { t.textContent = texto || 'preparando as paginas'; }
  }

  function espera_texto(texto) {
    var t = document.getElementById('p85EsperaTxt');
    if (t) { t.textContent = texto; }
  }

  function espera_desliga() {
    var e = document.getElementById('p85Espera');
    if (e) { e.style.display = 'none'; }
  }

  /* ================================================================ *
   * pega o conteudo pronto de impressao do relatorio
   * (usa o mesmo desenho do botao Imprimir, sem abrir a janela)
   * ================================================================ */
  function pegarConteudo(pref, depois) {
    var pe = document.getElementById(pref + 'Pe');
    var bt = pe ? pe.querySelector('[data-a="imprimir"]') : null;
    if (!bt) { depois(''); return; }

    var original = window.print;
    var travado = true;
    try {
      window.print = function () { if (!travado) { original.apply(window, arguments); } };
    } catch (e) {}

    try { bt.click(); } catch (e2) {}

    espera(520, function () {
      var d = document.getElementById(pref + 'Impressao');
      var html = d ? d.innerHTML : '';
      espera(260, function () {
        travado = false;
        try { window.print = original; } catch (e3) {}
      });
      depois(html);
    });
  }

  function esperarImagens(raiz, depois) {
    var imgs = [].slice.call(raiz.querySelectorAll('img'));
    var faltam = imgs.length;
    if (!faltam) { depois(); return; }
    var pronto = false;
    function passo() {
      faltam--;
      if (faltam <= 0 && !pronto) { pronto = true; depois(); }
    }
    imgs.forEach(function (im) {
      if (im.complete && im.naturalWidth) { passo(); return; }
      im.addEventListener('load', passo);
      im.addEventListener('error', passo);
    });
    espera(9000, function () { if (!pronto) { pronto = true; depois(); } });
  }

  /* ================================================================ *
   * divide o conteudo em paginas A4
   * ================================================================ */
  function montarPaginas(palco, html) {
    var folha = document.createElement('div');
    folha.className = 'p85-folha';
    folha.innerHTML = html;
    palco.appendChild(folha);
    return folha;
  }

  function repartir(palco, folha) {
    var filhos = [].slice.call(folha.children);
    var grupos = [];
    var grupo = [];
    var alt = 0;

    filhos.forEach(function (el) {
      var r = el.getBoundingClientRect();
      var h = r.height + 6;
      if (grupo.length && (alt + h) > ALT_PX) {
        grupos.push(grupo);
        grupo = [];
        alt = 0;
      }
      grupo.push(el);
      alt += h;
    });
    if (grupo.length) { grupos.push(grupo); }

    var pags = [];
    grupos.forEach(function (g) {
      var p = document.createElement('div');
      p.className = 'p85-folha p85-pag';
      g.forEach(function (el) { p.appendChild(el); });
      palco.appendChild(p);
      pags.push(p);
    });
    try { palco.removeChild(folha); } catch (e) {}
    return pags;
  }

  function fatias(cv, alturaFatia) {
    var saida = [];
    var y = 0;
    while (y < cv.height) {
      var h = Math.min(alturaFatia, cv.height - y);
      var c2 = document.createElement('canvas');
      c2.width = cv.width;
      c2.height = h;
      var ctx = c2.getContext('2d');
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, c2.width, h);
      ctx.drawImage(cv, 0, y, cv.width, h, 0, 0, cv.width, h);
      saida.push({ url: c2.toDataURL('image/jpeg', 0.9), alt: h, larg: cv.width });
      y += h;
    }
    return saida;
  }

  /* ================================================================ *
   * geracao do PDF
   * ================================================================ */
  function gerarPdf(pref, fim) {
    pegarConteudo(pref, function (html) {
      if (!html || html.replace(/\s+/g, '').length < 30) {
        espera_desliga();
        aviso('Abra ou preencha o relatorio antes de gerar o PDF.', 'erro');
        fim();
        return;
      }

      var nome = nomeArquivo(pref);

      var palco = document.getElementById('p85Palco');
      if (!palco) {
        palco = document.createElement('div');
        palco.id = 'p85Palco';
        document.body.appendChild(palco);
      }
      palco.innerHTML = '';

      var folha = montarPaginas(palco, html);

      espera_texto('carregando as fotos');
      esperarImagens(folha, function () {
        var pags;
        try {
          pags = repartir(palco, folha);
        } catch (e) {
          palco.innerHTML = '';
          espera_desliga();
          aviso('Nao consegui montar as paginas do PDF.', 'erro');
          fim();
          return;
        }

        var PDF = classePdf();
        var doc = new PDF({ unit: 'mm', format: 'a4', orientation: 'portrait', compress: true });
        var primeira = true;
        var i = 0;

        function proxima() {
          if (i >= pags.length) {
            try {
              doc.save(nome + '.pdf');
              aviso('PDF gerado: ' + nome + '.pdf');
            } catch (e) {
              aviso('Nao consegui salvar o arquivo PDF.', 'erro');
            }
            palco.innerHTML = '';
            espera_desliga();
            fim();
            return;
          }

          espera_texto('pagina ' + (i + 1) + ' de ' + pags.length);
          var alvo = pags[i++];

          window.html2canvas(alvo, {
            scale: 2,
            backgroundColor: '#ffffff',
            useCORS: true,
            allowTaint: true,
            logging: false,
            windowWidth: LARG_PX,
            width: LARG_PX
          }).then(function (cv) {
            var altPagPx = Math.floor(cv.width * (ALT_MM / LARG_MM));
            var pedacos = (cv.height > (altPagPx + 4)) ? fatias(cv, altPagPx)
                        : [{ url: cv.toDataURL('image/jpeg', 0.9), alt: cv.height, larg: cv.width }];

            pedacos.forEach(function (pc) {
              if (!primeira) { doc.addPage(); }
              primeira = false;
              var hmm = pc.alt * (LARG_MM / pc.larg);
              if (hmm > ALT_MM) { hmm = ALT_MM; }
              doc.addImage(pc.url, 'JPEG', MARG_MM, MARG_MM, LARG_MM, hmm, undefined, 'FAST');
            });
            espera(20, proxima);
          })['catch'](function () {
            palco.innerHTML = '';
            espera_desliga();
            aviso('Nao consegui desenhar o PDF. Use Imprimir e escolha Salvar como PDF.', 'erro');
            fim();
          });
        }

        proxima();
      });
    });
  }

  function nomeArquivo(pref) {
    var d = document.getElementById(pref + 'Impressao');
    var sub = '';
    if (d) {
      var s = d.querySelector('.pr-sub');
      if (s) { sub = s.textContent || ''; }
    }
    var base = (pref === 'p83') ? 'boletim_inspecao' : 'diario_de_obra';
    var num = '';
    var mn = sub.match(/N[\u00ba\u00b0o]\s*([0-9A-Za-z\/-]+)/);
    if (mn) { num = '_' + limpaNome(mn[1]); }
    var dt = '';
    var md = sub.match(/(\d{2})\/(\d{2})\/(\d{4})/);
    if (md) { dt = '_' + md[3] + '-' + md[2] + '-' + md[1]; }
    if (!dt) {
      var n = new Date();
      function z(v) { return (v < 10 ? '0' : '') + v; }
      dt = '_' + n.getFullYear() + '-' + z(n.getMonth() + 1) + '-' + z(n.getDate());
    }
    return limpaNome(base + num + dt);
  }

  function aoPedirPdf(pref, botao) {
    if (botao.__ocupado) { return; }
    botao.__ocupado = true;
    botao.disabled = true;
    var rotulo = botao.textContent;
    botao.textContent = 'Gerando...';

    function fim() {
      botao.__ocupado = false;
      botao.disabled = false;
      botao.textContent = rotulo;
    }

    espera_liga('preparando o gerador de PDF');

    prepararLibs(function () {
      gerarPdf(pref, fim);
    }, function () {
      espera_desliga();
      aviso('Sem internet para o gerador de PDF. Use Imprimir / PDF e escolha Salvar como PDF.', 'erro');
      fim();
    });
  }

  /* ================================================================ *
   * coloca o botao nos dois relatorios
   * ================================================================ */
  function colocarBotao(pref, rotulo) {
    var pe = document.getElementById(pref + 'Pe');
    if (!pe) { return; }
    var id = 'p85Btn' + pref;
    if (document.getElementById(id)) { return; }
    var imp = pe.querySelector('[data-a="imprimir"]');
    if (!imp) { return; }

    var b = document.createElement('button');
    b.id = id;
    b.type = 'button';
    b.className = 'p85-btn-pdf';
    b.title = rotulo;
    b.textContent = 'Salvar PDF';
    b.addEventListener('click', function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      aoPedirPdf(pref, b);
    });

    if (imp.nextSibling) {
      pe.insertBefore(b, imp.nextSibling);
    } else {
      pe.appendChild(b);
    }
  }

  function varrer() {
    colocarBotao('p83', 'Salvar o boletim de inspecao em PDF');
    colocarBotao('p84', 'Salvar o diario de obra em PDF');
  }

  function iniciar() {
    estilo();
    varrer();
    setInterval(varrer, 1500);
  }

  window.p85SalvarPdfBoletim = function () {
    var b = document.getElementById('p85Btnp83');
    if (b) { b.click(); } else { aviso('Abra o Boletim de Inspecao primeiro.', 'erro'); }
  };
  window.p85SalvarPdfDiario = function () {
    var b = document.getElementById('p85Btnp84');
    if (b) { b.click(); } else { aviso('Abra o Diario de Obra primeiro.', 'erro'); }
  };

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
    backup = alvo + '.bak_patch85_' + selo
    shutil.copyfile(alvo, backup)

    with io.open(alvo, 'w', encoding='utf-8', errors='surrogateescape', newline='') as f:
        f.write(novo)

    print('PATCH 85 aplicado com sucesso.')
    print('  - botao vermelho "Salvar PDF" ao lado de Imprimir / PDF')
    print('  - vale para o Boletim de Inspecao e para o Diario de Obra')
    print('  - gera o arquivo .pdf e baixa direto, sem janela de impressao')
    print('  - folha A4 em pe, com quebra automatica de paginas e fotos')
    print('  - nome do arquivo automatico com numero e data do relatorio')
    print('Backup salvo em: ' + backup)
    print('')
    print('Agora recarregue o painel (Ctrl + F5).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
