# -*- coding: utf-8 -*-
"""
PATCH 76 - BOTAO QUE TRAZ O PAINEL GERAL DE PRODUCAO PARA O RECEBIMENTO
=======================================================================

O QUE ESTE PATCH FAZ

  Coloca na aba "Recebimento de Materiais", ao lado dos botoes que ja
  existem, o botao:

      Importar do Painel Geral

  Ao clicar, ele le TODOS os itens do "Painel Geral de Producao" da obra
  que esta aberta e cria uma linha de recebimento para cada item, ja com
  todas as informacoes do item preenchidas:

      Referencia, Tipologia, Vidro, Localizacao, Quantidade, Largura,
      Altura, Area total, FEM, Fabricado, Instalado e Data de instalacao

  A Referencia do item vira o Codigo/Cor da linha, a Tipologia mais o
  Vidro e a medida viram a Descricao do material, a Quantidade do item
  vira a Quantidade Prevista, e o restante das informacoes fica na
  Observacao da linha, para nada se perder.

  Junto vai um segundo botao, "Limpar Importados", que apaga SOMENTE as
  linhas que vieram do Painel Geral, caso voce queira comecar de novo.

O QUE VOCE PREENCHE DEPOIS, E O PATCH NUNCA APAGA

  Nota Fiscal, Fornecedor, Marca, Quantidade Recebida, Status e
  Responsavel ficam em branco para voce preencher. Se voce clicar em
  "Importar do Painel Geral" outra vez, essas informacoes que voce
  digitou continuam la: o patch apenas atualiza os dados que vem do
  Painel Geral e acrescenta os itens novos que ainda nao estavam na
  lista.

SEM DUPLICAR LINHAS

  Cada linha criada guarda uma marca discreta do item de origem. Por
  isso, clicando duas ou dez vezes no botao, o mesmo item nao aparece
  duas vezes.

MUITO IMPORTANTE: NENHUMA CONTA FOI MEXIDA

  Este patch NAO altera calculo, preco, taxa, medida nem formula. Ele
  apenas COPIA para o recebimento os numeros que o Painel Geral de
  Producao ja mostra. A Area total, por exemplo, e a mesma conta que o
  painel ja usa (quantidade x largura x altura), so escrita na linha.

COMO FICA NA PRATICA

  1) Abra a aba Recebimento de Materiais
  2) Clique em "Importar do Painel Geral"
  3) Aparece um aviso dizendo quantos itens foram lidos, quantas linhas
     novas entraram e quantas foram atualizadas
  4) A tabela de recebimento passa a mostrar uma linha por item, com
     todas as informacoes do item
  5) Preencha NF, Fornecedor e Quantidade Recebida conforme o material
     chegar

O QUE CONTINUA EXATAMENTE COMO ESTA

  - Os botoes que ja existiam na aba: Inserir Recebimentos, Imprimir /
    Gerar PDF e Novo Recebimento
  - O filtro de busca, os cartoes de indicadores no topo da aba e o
    quadro de Materiais Consolidados
  - Os recebimentos que voce digitou ou importou por outro caminho
  - As demais abas do painel e os patches anteriores, do 63 ao 75

SEGURANCA
  - Nao apaga nem reescreve nada: insere apenas UM bloco novo antes do
    fechamento da pagina
  - Backup automatico do index.html antes de gravar
  - Idempotente: rodar de novo nao duplica nada

NO PAINEL, PELO CONSOLE (F12), SE QUISER
  P76.situacao()          mostra quantos itens e quantas linhas existem
  P76.importarDoPainel()  faz a importacao sem usar o botao
  P76.limparImportados()  apaga so o que veio do Painel Geral
  P76.ajuda()             lista os comandos

COMO USAR
  python patch_76.py
  depois abra o painel e pressione Ctrl+F5
"""

import os
import shutil
import sys
import datetime

FILE = r'C:/Users/OBRAS 8/Desktop/PAINEL SERVIDOR/index.html'

MARCADOR = 'PATCH 76: IMPORTAR O PAINEL GERAL'



# ---------------------------------------------------------------------------
# BLOCO INSERIDO NO index.html
# ---------------------------------------------------------------------------
BLOCO = r"""

<script>
/* PATCH 76: IMPORTAR O PAINEL GERAL DE PRODUCAO PARA O RECEBIMENTO DE MATERIAIS */
(function () {
  if (window.P76 && window.P76.__v76) return;
  var P76 = window.P76 = window.P76 || {};
  P76.__v76 = true;

  var MARCA_OBS = 'P76 item ';
  var LISTA_PADRAO = 'PAINEL GERAL';
  var CLASSE_PADRAO = 'Esquadria';

  /* ------------------------------------------------------------------ */
  /* AJUDANTES                                                          */
  /* ------------------------------------------------------------------ */
  function porId(id) { return document.getElementById(id); }

  function num(v) {
    var n = parseFloat(String(v == null ? '' : v).replace(',', '.'));
    return isFinite(n) ? n : 0;
  }

  function texto(v) { return String(v == null ? '' : v).trim(); }

  function numeroBonito(v, casas) {
    var n = num(v);
    try {
      return n.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
    } catch (e) {
      return n.toFixed(casas);
    }
  }

  function hoje() {
    try { return new Date().toISOString().slice(0, 10); } catch (e) { return ''; }
  }

  function obraAtual() {
    try {
      if (typeof window.getObraAtual === 'function') return window.getObraAtual();
    } catch (e) { /* ignora */ }
    try {
      var b = window.db;
      if (b && b.obras && b.obras.length) {
        return b.obras.filter(function (o) { return o && o.id === b.obraAtualId; })[0] || b.obras[0];
      }
    } catch (e) { /* ignora */ }
    return null;
  }

  function novoId() {
    return Date.now() + Math.random();
  }

  /* marca propria: assim o patch reconhece o que ele mesmo trouxe e nao
     repete o item na proxima importacao */
  function selo(item) { return '[' + MARCA_OBS + texto(item.id) + ']'; }

  function ehDoPatch(r) {
    return String(r && r.obs || '').indexOf('[' + MARCA_OBS) >= 0;
  }

  function seloDe(r) {
    var m = String(r && r.obs || '').match(/\[P76 item ([^\]]+)\]/);
    return m ? m[1] : '';
  }

  /* ------------------------------------------------------------------ */
  /* LEITURA DE UM ITEM DO PAINEL GERAL                                 */
  /* ------------------------------------------------------------------ */
  function medidas(item) {
    var larg = num(item.larg || item.largura);
    var alt = num(item.alt || item.altura);
    var qtd = num(item.qtd || item.quantidade) || 1;
    return { larg: larg, alt: alt, qtd: qtd, area: qtd * larg * alt };
  }

  function descricaoDoItem(item) {
    var m = medidas(item);
    var partes = [];
    var tipo = texto(item.tipo || item.descricao || item.nome);
    partes.push(tipo || 'Item do Painel Geral');
    if (texto(item.vidro)) partes.push('Vidro: ' + texto(item.vidro));
    if (m.larg > 0 || m.alt > 0) {
      partes.push(numeroBonito(m.larg, 3) + ' x ' + numeroBonito(m.alt, 3) + ' m');
    }
    return partes.join(' - ');
  }

  /* observacao com TODO o resto que a aba de itens mostra */
  function observacaoDoItem(item) {
    var m = medidas(item);
    var p = [selo(item)];
    if (texto(item.ref)) p.push('Ref.: ' + texto(item.ref));
    if (texto(item.loc)) p.push('Local: ' + texto(item.loc));
    p.push('Qtd: ' + numeroBonito(m.qtd, 0));
    if (m.larg > 0) p.push('Larg.: ' + numeroBonito(m.larg, 3) + ' m');
    if (m.alt > 0) p.push('Alt.: ' + numeroBonito(m.alt, 3) + ' m');
    p.push('Area total: ' + numeroBonito(m.area, 2) + ' m2');
    p.push('FEM: ' + numeroBonito(item.fem || 0, 0));
    p.push('Fabricado: ' + numeroBonito(item.fabricado || 0, 0));
    p.push('Instalado: ' + numeroBonito(item.instalado || 0, 0));
    if (texto(item.dataInstalacao)) p.push('Data inst.: ' + texto(item.dataInstalacao));
    return p.join(' | ');
  }

  /* ------------------------------------------------------------------ */
  /* IMPORTACAO                                                         */
  /* ------------------------------------------------------------------ */
  function importar(obra) {
    obra = obra || obraAtual();
    var resumo = { itens: 0, novos: 0, atualizados: 0 };
    if (!obra) return resumo;

    if (!Array.isArray(obra.recebimentos)) obra.recebimentos = [];
    var itens = Array.isArray(obra.itens) ? obra.itens : [];
    resumo.itens = itens.length;
    if (!itens.length) return resumo;

    /* mapa do que ja veio do Painel Geral antes */
    var jaTem = {};
    obra.recebimentos.forEach(function (r) {
      var s = seloDe(r);
      if (s) jaTem[s] = r;
    });

    itens.forEach(function (item) {
      if (!item) return;
      var m = medidas(item);
      var chave = texto(item.id);
      var desc = descricaoDoItem(item);
      var obs = observacaoDoItem(item);
      var data = texto(item.dataInstalacao) || hoje();
      var codigo = texto(item.ref) || chave;
      var antigo = chave && jaTem[chave];

      if (antigo) {
        /* atualiza so o que vem do Painel Geral; o que o usuario digitou
           na aba de recebimento (NF, fornecedor, qtd recebida, status,
           responsavel) fica como esta */
        antigo.listaCorte = texto(antigo.listaCorte) || LISTA_PADRAO;
        antigo.classe = texto(antigo.classe) || CLASSE_PADRAO;
        antigo.codigoCor = codigo;
        antigo.ref = codigo;
        antigo.descricao = desc;
        antigo.material = desc;
        antigo.qtdPrevista = m.qtd;
        antigo.local = texto(item.loc) || texto(antigo.local);
        antigo.obs = obs;
        if (!texto(antigo.data)) antigo.data = data;
        resumo.atualizados++;
        return;
      }

      obra.recebimentos.push({
        id: novoId(),
        data: data,
        listaCorte: LISTA_PADRAO,
        nf: '',
        fornecedor: '',
        classe: CLASSE_PADRAO,
        marca: '',
        codigoCor: codigo,
        descricao: desc,
        material: desc,
        ref: codigo,
        qtdPrevista: m.qtd,
        qtdRecebida: 0,
        unidade: 'UN',
        status: 'Pendente',
        responsavel: '',
        local: texto(item.loc),
        obs: obs
      });
      resumo.novos++;
    });

    return resumo;
  }

  function gravarEDesenhar(obra) {
    try {
      if (typeof window.salvarDB === 'function') window.salvarDB(false);
    } catch (e) { /* ignora */ }
    try {
      if (typeof window.renderRecebimentos === 'function') window.renderRecebimentos(obra);
    } catch (e) { /* ignora */ }
    garantirBotoes();
  }

  /* ------------------------------------------------------------------ */
  /* ACAO DO BOTAO                                                      */
  /* ------------------------------------------------------------------ */
  P76.importarDoPainel = function () {
    var obra = obraAtual();
    if (!obra) {
      alert('Nenhuma obra selecionada.');
      return false;
    }
    var itens = Array.isArray(obra.itens) ? obra.itens : [];
    if (!itens.length) {
      alert('O Painel Geral de Producao desta obra ainda nao tem itens cadastrados.');
      return false;
    }
    var r = importar(obra);
    gravarEDesenhar(obra);
    var msg = 'Painel Geral de Producao importado para o Recebimento de Materiais.\n\n'
      + 'Itens lidos no Painel Geral: ' + r.itens + '\n'
      + 'Registros novos criados: ' + r.novos + '\n'
      + 'Registros ja existentes atualizados: ' + r.atualizados + '\n\n'
      + 'Cada linha traz Referencia, Tipologia, Vidro, Localizacao, Qtd,\n'
      + 'Largura, Altura, Area, FEM, Fabricado, Instalado e Data de\n'
      + 'instalacao. A Quantidade Recebida, a NF e o Fornecedor ficam para\n'
      + 'voce preencher, e nao sao apagados numa proxima importacao.';
    alert(msg);
    return true;
  };

  P76.limparImportados = function (semPerguntar) {
    var obra = obraAtual();
    if (!obra || !Array.isArray(obra.recebimentos)) return 0;
    var alvo = obra.recebimentos.filter(ehDoPatch);
    if (!alvo.length) {
      if (!semPerguntar) alert('Nao ha registros vindos do Painel Geral para apagar.');
      return 0;
    }
    if (!semPerguntar) {
      var ok = confirm('Apagar ' + alvo.length + ' registro(s) que vieram do Painel Geral?\n\n'
        + 'Os recebimentos que voce digitou ou importou de outra forma NAO serao tocados.');
      if (!ok) return 0;
    }
    obra.recebimentos = obra.recebimentos.filter(function (r) { return !ehDoPatch(r); });
    gravarEDesenhar(obra);
    return alvo.length;
  };

  /* ------------------------------------------------------------------ */
  /* BOTOES NA ABA RECEBIMENTO DE MATERIAIS                             */
  /* ------------------------------------------------------------------ */
  function caixaDeBotoes() {
    var aba = porId('tab-recebimento');
    if (!aba) return null;
    return aba.querySelector('.recebimento-actions');
  }

  function criarBotao(id, classe, rotulo, titulo, acao) {
    var b = document.createElement('button');
    b.id = id;
    b.type = 'button';
    b.className = classe;
    b.setAttribute('data-p76', '1');
    b.textContent = rotulo;
    b.title = titulo;
    b.addEventListener('click', acao);
    return b;
  }

  function garantirBotoes() {
    var caixa = caixaDeBotoes();
    if (!caixa) return false;

    if (!porId('p76BtnImportar')) {
      var bi = criarBotao(
        'p76BtnImportar',
        'secondary p76-btn',
        '\uD83D\uDCE5 Importar do Painel Geral',
        'Traz todos os itens do Painel Geral de Producao para esta lista de recebimento',
        function () { P76.importarDoPainel(); }
      );
      var referencia = caixa.querySelector('button.success') || null;
      if (referencia) caixa.insertBefore(bi, referencia);
      else caixa.appendChild(bi);
    }

    if (!porId('p76BtnLimpar')) {
      var bl = criarBotao(
        'p76BtnLimpar',
        'secondary p76-btn p76-btn-limpar',
        '\uD83E\uDDF9 Limpar Importados',
        'Apaga apenas os registros que vieram do Painel Geral de Producao',
        function () { P76.limparImportados(false); }
      );
      var bi2 = porId('p76BtnImportar');
      if (bi2 && bi2.parentNode === caixa) caixa.insertBefore(bl, bi2.nextSibling);
      else caixa.appendChild(bl);
    }

    return true;
  }

  /* deixa os botoes de pe mesmo quando o painel redesenha a aba */
  function ligar() {
    garantirBotoes();

    if (!P76.__envolveu && typeof window.renderRecebimentos === 'function') {
      var original = window.renderRecebimentos;
      window.renderRecebimentos = function () {
        var saida = original.apply(this, arguments);
        try { garantirBotoes(); } catch (e) { /* ignora */ }
        return saida;
      };
      P76.__envolveu = true;
    }

    if (!P76.__envolveuAba && typeof window.trocarAba === 'function') {
      var abaOriginal = window.trocarAba;
      window.trocarAba = function () {
        var saida = abaOriginal.apply(this, arguments);
        try { garantirBotoes(); } catch (e) { /* ignora */ }
        return saida;
      };
      P76.__envolveuAba = true;
    }
  }

  /* ------------------------------------------------------------------ */
  /* COMANDOS DE CONSOLE                                                */
  /* ------------------------------------------------------------------ */
  P76.aplicar = function () { ligar(); return true; };

  P76.situacao = function () {
    var obra = obraAtual();
    var itens = obra && Array.isArray(obra.itens) ? obra.itens.length : 0;
    var vindos = obra && Array.isArray(obra.recebimentos) ? obra.recebimentos.filter(ehDoPatch).length : 0;
    var total = obra && Array.isArray(obra.recebimentos) ? obra.recebimentos.length : 0;
    console.log('[P76] itens no Painel Geral: ' + itens);
    console.log('[P76] recebimentos vindos do Painel Geral: ' + vindos);
    console.log('[P76] recebimentos no total: ' + total);
    console.log('[P76] botao na tela: ' + (porId('p76BtnImportar') ? 'sim' : 'nao'));
    return true;
  };

  P76.ajuda = function () {
    console.log('[P76] P76.importarDoPainel() traz os itens do Painel Geral');
    console.log('[P76] P76.limparImportados() apaga so o que veio do Painel Geral');
    console.log('[P76] P76.situacao() mostra a contagem atual');
    console.log('[P76] P76.aplicar() recoloca o botao na aba');
    return true;
  };

  function esperar(vezes) {
    if (porId('tab-recebimento') || typeof window.renderRecebimentos === 'function') {
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

  /* os patches antigos re-embrulham funcoes do painel depois de alguns
     segundos; a nossa camada volta por cima nessas horas */
  var HORAS = [900, 1500, 2600, 3200, 4800, 6500, 9000];
  for (var h = 0; h < HORAS.length; h++) {
    (function (t) {
      setTimeout(function () { try { ligar(); } catch (e) { /* ignora */ } }, t);
    }(HORAS[h]));
  }

  console.log('PATCH 76 ativo: botao "Importar do Painel Geral" na aba Recebimento de Materiais. Use P76.ajuda().');
})();
</script>

<style>
/* PATCH 76: BOTAO IMPORTAR O PAINEL GERAL NO RECEBIMENTO DE MATERIAIS */

#tab-recebimento .recebimento-actions .p76-btn {
  background: #1e3a5f;
  color: #ffffff;
  border: 1px solid #16304f;
  font-weight: 600;
  cursor: pointer;
}

#tab-recebimento .recebimento-actions .p76-btn:hover {
  background: #2a4d7a;
  color: #ffffff;
}

#tab-recebimento .recebimento-actions .p76-btn-limpar {
  background: #ffffff;
  color: #1e3a5f;
}

#tab-recebimento .recebimento-actions .p76-btn-limpar:hover {
  background: #eef3f9;
  color: #16304f;
}

@media print {
  #tab-recebimento .recebimento-actions .p76-btn {
    display: none !important;
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
    fala(' PATCH 76 - Importar o Painel Geral de Producao para o Recebimento')
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
        fala('[info] O Patch 76 JA esta aplicado neste arquivo. Nada a fazer.')
        fala('       Se quiser reaplicar, remova o bloco "%s" antes.' % MARCADOR)
        return 0

    baixo = html.lower()
    if '<body' not in baixo:
        fala('[erro] Este arquivo nao parece ser a pagina do painel (sem <body>).')
        fala('       Nenhuma alteracao foi feita.')
        return 1
    fala('[ok] Pagina do painel reconhecida.')

    if 'tab-recebimento' in html:
        fala('[ok] Aba Recebimento de Materiais encontrada.')
    else:
        fala('[aviso] Nao achei a aba Recebimento de Materiais agora.')
        fala('        O patch procura a aba de novo quando a pagina abre.')

    if 'recebimento-actions' in html:
        fala('[ok] Barra de botoes da aba encontrada: o botao novo entra ali,')
        fala('     antes do botao Novo Recebimento.')
    else:
        fala('[aviso] Barra de botoes da aba nao localizada agora.')

    for chave, rotulo in (
        ('renderRecebimentos', 'desenho da tabela de recebimento'),
        ('tbodyRecebimento', 'corpo da tabela de recebimento'),
        ('salvarNovoRecebimento', 'gravacao de um recebimento'),
        ('processarImportacaoRecebimento', 'importacao pela lista de materiais'),
        ('renderTabelaPrincipal', 'Painel Geral de Producao'),
    ):
        if chave in html:
            fala('[ok] Encontrado: ' + rotulo)
        else:
            fala('[aviso] Nao encontrado agora: ' + rotulo)

    if 'dataInstalacao' in html:
        fala('[ok] Campos dos itens conferidos: qtd, largura, altura, FEM,')
        fala('     fabricado, instalado e data de instalacao serao copiados.')

    if 'abrirModalRecebimento' in html:
        fala('[ok] Botao Novo Recebimento continua no lugar.')
    if 'exportarMateriaisConsolidados' in html:
        fala('[ok] Quadro de Materiais Consolidados continua no lugar.')

    for n in ('70', '71', '73', '74', '75'):
        if ('PATCH ' + n) in html:
            fala('[ok] Patch ' + n + ' detectado: segue funcionando como antes.')

    pos = baixo.rfind('</body>')
    if pos < 0:
        pos = baixo.rfind('</html>')
    if pos < 0:
        fala('[erro] Nao achei o fechamento da pagina (</body> ou </html>).')
        return 1
    fala('[ok] Lugar de insercao conferido (fim da pagina).')

    selo = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    bkp = FILE + '.bak_patch76_' + selo
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
    fala('  2) Abra a aba Recebimento de Materiais')
    fala('  3) Clique no botao novo "Importar do Painel Geral"')
    fala('  4) Cada item do Painel Geral de Producao vira uma linha de')
    fala('     recebimento com Referencia, Tipologia, Vidro, Localizacao,')
    fala('     Qtd, Largura, Altura, Area, FEM, Fabricado, Instalado e')
    fala('     Data de instalacao')
    fala('  5) Preencha NF, Fornecedor e Quantidade Recebida quando o')
    fala('     material chegar: uma nova importacao nao apaga isso')
    fala('  6) Se precisar recomecar, use "Limpar Importados": ele apaga')
    fala('     somente as linhas que vieram do Painel Geral')
    fala('')
    fala('  Nenhum calculo, preco, medida, formula ou coluna foi alterado:')
    fala('  as informacoes sao copiadas do que o painel ja mostrava.')
    fala('')
    fala('>>> Agora abra o painel e pressione Ctrl+F5 para recarregar. <<<')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        fala('[erro] Algo deu errado: %s' % e)
        fala('       Nenhuma alteracao foi concluida. Se existir um arquivo')
        fala('       .bak_patch76_, ele e a copia do seu index.html antes da')
        fala('       tentativa.')
        sys.exit(1)
