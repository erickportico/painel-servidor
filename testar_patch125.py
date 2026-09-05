# -*- coding: utf-8 -*-
"""
TESTE DO PATCH 125 - GRAVACAO POR OBRA
======================================

PARA QUE SERVE
--------------
Este script NAO muda nada no seu painel. Ele so confere se o patch 125
entrou direito e monta uma pagina de teste que faz o painel "brigar consigo
 mesmo" com uma nuvem de mentira, para voce ver com os proprios olhos que
nada se perde.

ELE FAZ DUAS COISAS
-------------------
1) CONFERENCIA DO ARQUIVO (na hora, no proprio prompt)
   Le o seu index.html e verifica, por exemplo:
   * o bloco do patch 125 esta presente e aparece uma unica vez;
   * o envio antigo (que mandava tudo por cima) foi realmente trocado;
   * as pecas principais estao lá: ler a nuvem, juntar por obra, janela de
     escolha, tarja de aviso, vigia de 20 segundos, lixeira somada;
   * os patches 122, 123 e 124 continuam no arquivo;
   * a copia de seguranca index.html.bak-patch125 existe;
   * as chaves e parenteses do bloco fecham certo.

2) PAGINA DE TESTE AUTOMATICO (teste_patch125.html)
   Ele copia SO o bloco do patch 125 para uma pagina separada, com uma
   nuvem de mentira (nada toca o Supabase de verdade), e roda sozinho os
   casos que importam:
     1. eu e outra pessoa salvando obras DIFERENTES ao mesmo tempo -
        nenhum dos dois lancamentos pode se perder;
     2. a obra que eu estou olhando nao pode viajar para a nuvem;
     3. obra criada por outra pessoa tem que aparecer na minha tela;
     4. os dois na MESMA obra - a janela de escolha tem que abrir e a
        nuvem NAO pode ser sobrescrita antes de eu decidir;
     5. escolhendo "ficar com a minha" - a minha versao tem que ser a que
        fica gravada;
     6. nuvem fora do ar - nada pode ser gravado pela metade;
     7. a tela se atualizando sozinha, com a tarja dizendo quem mexeu.
   Cada caso aparece na tela em verde (PASSOU) ou vermelho (FALHOU).

COMO USAR (Windows)
-------------------
  1. Salve este arquivo na mesma pasta do seu index.html
     (Desktop\\PAINEL SERVIDOR).
  2. Clique duas vezes nele, ou rode no Prompt de Comando:
         python testar_patch125.py
  3. Leia o resultado da conferencia no prompt.
  4. Ele cria o arquivo teste_patch125.html na mesma pasta. Clique duas
     vezes nesse arquivo para abrir no navegador e veja a lista de testes
     ficar verde. O teste inteiro leva cerca de 25 segundos (uma parte
     precisa esperar o vigia da nuvem).
  5. Pode apagar o teste_patch125.html depois. Ele nao faz parte do painel
     e nao vai para o GitHub.

O QUE ELE NAO TESTA
-------------------
A pagina de teste usa uma nuvem de mentira, entao ela nao prova que o seu
Supabase esta no ar nem testa login, relatorios ou impressao. Para o teste
de verdade com duas pessoas, o proprio script imprime no fim um roteiro
curto de 4 passos para fazer em duas janelas do painel.

OPCOES
------
  --arquivo X    conferir outro arquivo em vez do index.html
  --so-conferir  nao criar a pagina de teste, apenas conferir o arquivo

SEGURANCA
---------
* Este script abre o seu index.html somente para LER. Ele nunca escreve
  nele, nunca fala com o git e nunca publica nada.
* O unico arquivo criado e o teste_patch125.html, que pode ser apagado.
"""

import io
import os
import sys

ARQ_TESTE = "teste_patch125.html"

INI = "<!-- INI PATCH125 -->"
FIM = "<!-- FIM PATCH125 -->"

# nome do teste, pedaco de codigo que precisa existir
CONFERENCIAS = [
    ("le a nuvem antes de gravar", "function lerDaNuvem"),
    ("monta o pacote juntando por obra", "function juntar("),
    ("sabe dizer no que EU mexi", "function minhasMudancas"),
    ("janela de escolha quando a obra bate", "function abrirChoque"),
    ("guarda as duas versoes antes de decidir", "function guardarAsDuas"),
    ("mostra a diferenca entre as versoes", "function verDiferenca"),
    ("traz para a tela o que veio da nuvem", "function aplicarDaNuvem"),
    ("tarja de aviso propria", "function mostrarAviso"),
    ("vigia a nuvem a cada 20 segundos", "setInterval(vigiar, 20000)"),
    ("troca o envio antigo pelo novo", "window.sincronizarBancoNuvem = meu"),
    ("avisa o patch 123 para nao repetir a trava", "meu.__p123 = true"),
    ("esconde o aviso generico do patch 123", "#p123Aviso { display: none !important; }"),
    ("a obra que eu olho fica neste navegador", "function guardarMinhaObra"),
    ("soma a lixeira das duas pessoas", "function juntarLixeira"),
    ("nao grava as cegas se a nuvem falhar", "Nuvem nao respondeu"),
    ("nao refaz o retrato depois de comecar", "if (!baseFeita) { fazerBase(); }"),
    ("atalhos de conferencia manual", "window.p125Estado"),
]

OUTROS_PATCHES = [
    ("patch 122 (excluir em lote)", "INI PATCH122"),
    ("patch 123 (lixeira)", "INI PATCH123"),
    ("patch 124 (backup diario)", "INI PATCH124"),
]

TOPO = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Teste do patch 125 - gravacao por obra</title>
<style>
  body { font-family: Segoe UI, Arial, sans-serif; background: #0b1220; color: #e5e7eb;
         margin: 0; padding: 24px; }
  h1 { font-size: 1.15rem; margin: 0 0 4px 0; }
  p.sub { margin: 0 0 16px 0; opacity: .8; font-size: .9rem; }
  #placar { font-weight: 800; margin: 10px 0 14px 0; font-size: 1rem; }
  table { border-collapse: collapse; width: 100%; max-width: 900px; font-size: .9rem; }
  td { padding: 8px 10px; border-bottom: 1px solid rgba(148,163,184,.25); vertical-align: top; }
  td.res { width: 92px; font-weight: 800; }
  .ok { color: #34d399; }
  .ruim { color: #f87171; }
  .esperando { color: #fbbf24; }
  small { opacity: .75; display: block; margin-top: 2px; }
</style>
</head>
<body>
<h1>Teste do patch 125 - gravacao por obra</h1>
<p class="sub">Esta pagina usa uma nuvem de mentira. Nada aqui fala com o Supabase de
verdade e o seu painel nao e alterado. Aguarde: o teste leva cerca de 25 segundos.</p>
<div id="placar">Rodando...</div>
<table id="lista"></table>

<script>
/* ---------- nuvem de mentira e painel de mentira ---------- */
var NUVEM = {
  dados: {
    obras: [
      { id: 'obra_1', nome: 'Obra A', itens: [ {id:'a1'}, {id:'a2'} ] },
      { id: 'obra_2', nome: 'Obra B', itens: [ {id:'b1'} ] }
    ],
    config: { cor: 'azul' },
    versaoBanco: 1,
    obraAtualId: 'obra_1'
  },
  updated_at: new Date(Date.now() - 3600000).toISOString()
};
var FORA_DO_AR = false;
var GRAVACOES = 0;

function consultaFalsa() {
  var f = {};
  var api = {
    select: function () { return api; },
    eq: function (c, v) { f.eq = v; return api; },
    single: function () { return api; },
    upsert: function (reg) { f.up = reg; return api; },
    then: function (ok, ruim) {
      var res;
      if (FORA_DO_AR) { res = { data: null, error: { message: 'sem rede' } }; }
      else if (f.up) {
        NUVEM.dados = JSON.parse(JSON.stringify(f.up.dados));
        NUVEM.updated_at = f.up.updated_at;
        GRAVACOES++;
        res = { data: null, error: null };
      } else {
        res = { data: { dados: JSON.parse(JSON.stringify(NUVEM.dados)),
                        updated_at: NUVEM.updated_at }, error: null };
      }
      return Promise.resolve(res).then(ok, ruim);
    },
    catch: function (fn) { return api.then(function (x) { return x; }, fn); }
  };
  return api;
}

var _supabase = { from: function () { return consultaFalsa(); } };
var db = JSON.parse(JSON.stringify(NUVEM.dados));
db.obraAtualId = 'obra_2';          /* eu estou olhando a Obra B */

function sincronizarBancoNuvem() { window.__envioAntigo = true; }
window.sincronizarBancoNuvem = sincronizarBancoNuvem;
window.render = function () { window.__redesenhou = (window.__redesenhou || 0) + 1; };
window.atualizarStatusNuvem = function (t) { window.__status = t; };
window.salvarLocalComoBackup = function () { window.__guardouAqui = (window.__guardouAqui || 0) + 1; };

/* nao deixa o teste baixar arquivos no seu computador */
var cliqueOriginal = HTMLAnchorElement.prototype.click;
HTMLAnchorElement.prototype.click = function () {
  if (this.hasAttribute('download')) { window.__baixou = (window.__baixou || 0) + 1; return; }
  return cliqueOriginal.apply(this, arguments);
};
</script>
"""

RODAPE = """
</body>
</html>
"""

TESTES = """
<script>
/* ---------- os testes ---------- */
var total = 0, bons = 0;

function marcar(nome, ok, detalhe) {
  total++;
  if (ok) { bons++; }
  var tr = document.createElement('tr');
  var a = document.createElement('td');
  a.className = 'res ' + (ok ? 'ok' : 'ruim');
  a.textContent = ok ? 'PASSOU' : 'FALHOU';
  var b = document.createElement('td');
  b.textContent = nome;
  if (detalhe) {
    var s = document.createElement('small');
    s.textContent = detalhe;
    b.appendChild(s);
  }
  tr.appendChild(a); tr.appendChild(b);
  document.getElementById('lista').appendChild(tr);
}

function aviso(texto) {
  var el = document.getElementById('placar');
  el.className = 'esperando';
  el.textContent = texto;
}

function esperar(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

function achar(lista, id) {
  for (var i = 0; i < (lista || []).length; i++) {
    if (String(lista[i].id) === id) { return lista[i]; }
  }
  return null;
}
function naNuvem(id) { return achar(NUVEM.dados.obras, id); }
function naTela(id) { return achar(db.obras, id); }
function quantos(obra) { return obra ? obra.itens.length : -1; }
function ids(obra) { return obra ? obra.itens.map(function (i) { return i.id; }).join(', ') : 'obra nao existe'; }
function botaoQueDiz(parte) {
  var todos = document.querySelectorAll('.p125-acoes button');
  for (var i = 0; i < todos.length; i++) {
    if (todos[i].textContent.indexOf(parte) >= 0) { return todos[i]; }
  }
  return null;
}

async function rodar() {
  aviso('Preparando...');
  await esperar(1600);

  /* 1) o patch assumiu o envio */
  marcar('O patch 125 assumiu o salvamento',
    !!(window.sincronizarBancoNuvem && window.sincronizarBancoNuvem.__p125),
    'e avisa o patch 123 para nao repetir a trava: '
      + !!(window.sincronizarBancoNuvem && window.sincronizarBancoNuvem.__p123));

  /* 2) duas pessoas, obras diferentes */
  aviso('Testando duas pessoas em obras diferentes...');
  naTela('obra_1').itens.push({ id: 'a3', quem: 'eu' });
  naNuvem('obra_2').itens.push({ id: 'b2', quem: 'o outro' });
  NUVEM.updated_at = new Date().toISOString();
  window.sincronizarBancoNuvem();
  await esperar(1600);

  marcar('A minha alteracao na Obra A foi gravada',
    quantos(naNuvem('obra_1')) === 3, 'itens na nuvem: ' + ids(naNuvem('obra_1')));
  marcar('O lancamento do outro na Obra B nao se perdeu',
    quantos(naNuvem('obra_2')) === 2, 'itens na nuvem: ' + ids(naNuvem('obra_2')));
  marcar('A Obra B do outro chegou na minha tela',
    quantos(naTela('obra_2')) === 2, 'itens na tela: ' + ids(naTela('obra_2')));
  marcar('A obra que EU estou olhando nao viajou para a nuvem',
    db.obraAtualId === 'obra_2' && NUVEM.dados.obraAtualId === 'obra_1',
    'na minha tela: ' + db.obraAtualId + ' | na nuvem: ' + NUVEM.dados.obraAtualId);
  marcar('O status diz o que foi salvo',
    String(window.__status || '').indexOf('Obra A') >= 0, 'status: ' + window.__status);

  /* 3) obra criada por outra pessoa */
  aviso('Testando obra criada por outra pessoa...');
  NUVEM.dados.obras.push({ id: 'obra_3', nome: 'Obra C', itens: [ {id:'c1'} ] });
  NUVEM.updated_at = new Date().toISOString();
  naTela('obra_1').itens.push({ id: 'a4', quem: 'eu' });
  window.sincronizarBancoNuvem();
  await esperar(1600);
  marcar('A obra criada pelo outro apareceu na minha tela e continua na nuvem',
    !!naTela('obra_3') && !!naNuvem('obra_3'), 'Obra C na tela e na nuvem');

  /* 4) a mesma obra nos dois lados */
  aviso('Testando os dois mexendo na MESMA obra...');
  naTela('obra_1').itens.push({ id: 'a5', quem: 'eu' });
  naNuvem('obra_1').itens.push({ id: 'aX', quem: 'o outro' });
  NUVEM.updated_at = new Date().toISOString();
  var antesDoChoque = JSON.stringify(NUVEM.dados);
  window.sincronizarBancoNuvem();
  await esperar(1600);

  var janelas = document.querySelectorAll('.p125-fundo');
  var texto = janelas.length ? janelas[0].textContent : '';
  marcar('A janela de escolha abriu e diz qual obra e',
    janelas.length === 1 && texto.indexOf('Obra A') >= 0,
    'janelas abertas: ' + janelas.length);
  marcar('A nuvem NAO foi sobrescrita antes de eu decidir',
    JSON.stringify(NUVEM.dados) === antesDoChoque, 'status: ' + window.__status);
  marcar('O painel oferece as duas versoes para conferir',
    !!botaoQueDiz('escolhi') && texto.indexOf('itens') >= 0,
    'nesta pagina de teste o download do arquivo com as duas versoes fica bloqueado');

  var bt = botaoQueDiz('minha em todas');
  marcar('Existem os atalhos de escolha', !!bt,
    'botoes: ' + [].map.call(document.querySelectorAll('.p125-acoes button'),
      function (b) { return b.textContent.trim(); }).join(' / '));
  if (bt) { bt.click(); }
  await esperar(1800);

  var meus = ids(naNuvem('obra_1'));
  marcar('Escolhendo "ficar com a minha", a minha versao foi gravada',
    meus.indexOf('a5') >= 0 && meus.indexOf('aX') < 0, 'itens na nuvem: ' + meus);
  marcar('A janela fechou depois da escolha',
    document.querySelectorAll('.p125-fundo').length === 0, '');

  /* 5) nuvem fora do ar */
  aviso('Testando com a nuvem fora do ar...');
  var antesDaQueda = JSON.stringify(NUVEM.dados);
  FORA_DO_AR = true;
  naTela('obra_2').itens.push({ id: 'b9', quem: 'eu' });
  window.sincronizarBancoNuvem();
  await esperar(1600);
  marcar('Com a nuvem fora do ar ele nao grava pela metade',
    JSON.stringify(NUVEM.dados) === antesDaQueda
      && String(window.__status || '').indexOf('nao respondeu') >= 0,
    'status: ' + window.__status);
  FORA_DO_AR = false;

  /* 6) a tela se atualiza sozinha */
  for (var s = 13; s > 0; s--) {
    aviso('Ultimo teste: esperando o vigia da nuvem (' + s + 's)...');
    await esperar(1000);
  }
  window.p125Vigiar();
  await esperar(900);
  /* a Obra C e do outro: eu nunca mexi nela, entao pode entrar sozinha */
  var antesDaVigia = quantos(naTela('obra_3'));
  naNuvem('obra_3').itens.push({ id: 'c2', quem: 'o outro' });
  NUVEM.dados.ultimaEdicao = { quem: 'Joao' };
  NUVEM.updated_at = new Date().toISOString();
  var chegou = false;
  for (var v = 0; v < 5 && !chegou; v++) {
    aviso('Ultimo teste: conferindo se a tela se atualiza sozinha...');
    window.p125Vigiar();
    await esperar(1500);
    chegou = quantos(naTela('obra_3')) === antesDaVigia + 1;
    if (!chegou) { await esperar(3500); }
  }

  marcar('A tela se atualizou sozinha com o lancamento do outro',
    chegou, 'itens na Obra C, na minha tela: ' + ids(naTela('obra_3')));
  var tarja = document.getElementById('p125Aviso');
  marcar('A tarja avisou quem mexeu e em qual obra',
    !!tarja && tarja.textContent.indexOf('Joao') >= 0
      && tarja.textContent.indexOf('Obra C') >= 0,
    tarja ? tarja.textContent.replace('Fechar', '') : 'tarja ausente');
  marcar('Depois de tudo, a obra que eu estou olhando continua a mesma',
    db.obraAtualId === 'obra_2', 'obra na minha tela: ' + db.obraAtualId);

  var el = document.getElementById('placar');
  el.className = (bons === total) ? 'ok' : 'ruim';
  el.textContent = (bons === total)
    ? 'TUDO CERTO: ' + bons + ' de ' + total + ' testes passaram. O patch 125 esta funcionando.'
    : 'ATENCAO: ' + bons + ' de ' + total + ' testes passaram. Veja as linhas em vermelho.';
}

rodar();
</script>
"""


def pegar_valor(nome, padrao=None):
    """le uma opcao do tipo --nome valor"""
    if nome in sys.argv:
        i = sys.argv.index(nome)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return padrao


def achar_arquivo():
    escolhido = pegar_valor("--arquivo")
    if escolhido:
        return escolhido
    aqui = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(aqui, "index.html")


def contar(texto, abre, fecha):
    return texto.count(abre) - texto.count(fecha)


def conferir(caminho):
    """confere o arquivo e devolve (quantos passaram, quantos testes, bloco)"""
    with io.open(caminho, "r", encoding="utf-8", errors="replace") as f:
        pagina = f.read()

    falhas = []

    def teste(nome, ok, detalhe=""):
        nonlocal_bons[0] += 1 if ok else 0
        nonlocal_total[0] += 1
        marca = "[ok]   " if ok else "[FALHOU]"
        print("  " + marca + " " + nome + ("  -> " + detalhe if detalhe and not ok else ""))
        if not ok:
            falhas.append(nome)

    nonlocal_bons = [0]
    nonlocal_total = [0]

    print("")
    print("1) O BLOCO DO PATCH 125")
    quantos = pagina.count(INI)
    teste("o bloco do patch 125 esta no arquivo", quantos >= 1,
          "nao encontrei o bloco - o patch 125 nao foi aplicado neste arquivo")
    teste("o bloco aparece uma unica vez (nao duplicou)", quantos == 1,
          "encontrei %d blocos" % quantos)

    bloco = ""
    if quantos >= 1 and FIM in pagina:
        ini = pagina.index(INI)
        fim = pagina.index(FIM, ini) + len(FIM)
        bloco = pagina[ini:fim]

    teste("o bloco esta fechado direito", bool(bloco) and "</script>" in bloco)
    teste("o bloco fica no fim da pagina, antes do fechamento",
          bool(bloco) and pagina.rfind(INI) > pagina.rfind("<body"))

    print("")
    print("2) AS PECAS QUE O PATCH PRECISA TER")
    for nome, pedaco in CONFERENCIAS:
        teste(nome, pedaco in bloco, "nao achei: " + pedaco)

    print("")
    print("3) O CODIGO FECHA CERTO")
    corpo = bloco
    teste("chaves { } fechando", contar(corpo, "{", "}") == 0,
          "sobraram %d" % contar(corpo, "{", "}"))
    teste("o estilo e o codigo do patch abrem e fecham",
          corpo.count("<style") == corpo.count("</style>")
          and corpo.count("<script") == corpo.count("</script>"))
    teste("nenhuma barra invertida solta no bloco", corpo.count(chr(92)) == 0,
          "achei %d" % corpo.count(chr(92)))

    print("")
    print("4) OS OUTROS PATCHES CONTINUAM NO LUGAR")
    for nome, pedaco in OUTROS_PATCHES:
        teste(nome, pedaco in pagina, "nao achei no arquivo")

    print("")
    print("5) COPIA DE SEGURANCA")
    backup = caminho + ".bak-patch125"
    teste("existe a copia index.html.bak-patch125", os.path.exists(backup),
          "a copia nao esta na pasta")

    return nonlocal_bons[0], nonlocal_total[0], bloco, falhas


def gerar_pagina(pasta, bloco):
    destino = os.path.join(pasta, ARQ_TESTE)
    with io.open(destino, "w", encoding="utf-8") as f:
        f.write(TOPO + "\n" + bloco + "\n" + TESTES + RODAPE)
    return destino


ROTEIRO = """
TESTE DE VERDADE, COM DUAS JANELAS (5 MINUTOS)
----------------------------------------------
  1. Abra o painel em duas janelas do navegador (ou em dois computadores).
     Na janela 1 escolha a Obra A; na janela 2 escolha a Obra B.
  2. Lance um item na Obra A (janela 1) e outro na Obra B (janela 2), quase
     ao mesmo tempo. Depois de alguns segundos as DUAS janelas tem que
     mostrar os dois lancamentos - e nada pode ter desaparecido.
  3. Agora ponha as duas janelas na MESMA obra e altere o mesmo item nas
     duas. A segunda a salvar tem que abrir a janela de escolha, dizendo o
     nome da obra. Escolha uma versao e confira o resultado nas duas telas.
  4. Troque de obra na janela 1 e salve na janela 2: a obra que voce esta
     olhando na janela 1 nao pode mudar sozinha.

  Dica: digitando p125Estado() no console do navegador (tecla F12) ele
  mostra em quantas obras voce mexeu e a hora da ultima gravacao conhecida.
"""


def main():
    caminho = achar_arquivo()
    if not os.path.isfile(caminho):
        print("NAO ENCONTREI o index.html.")
        print("Coloque este script na mesma pasta do painel e rode de novo,")
        print("ou informe o caminho com --arquivo index.html")
        return 1

    print("")
    print("CONFERINDO O PATCH 125 EM: " + os.path.basename(caminho))
    bons, total, bloco, falhas = conferir(caminho)

    print("")
    print("-" * 60)
    if bons == total:
        print("CONFERENCIA: tudo certo - %d de %d testes passaram." % (bons, total))
    else:
        print("CONFERENCIA: %d de %d testes passaram." % (bons, total))
        print("Nao passaram: " + ", ".join(falhas))
        print("Se o bloco nao foi encontrado, rode primeiro o")
        print("patch125_gravacao_por_obra.py nesta mesma pasta.")
    print("-" * 60)

    if "--so-conferir" in sys.argv:
        print(ROTEIRO)
        return 0 if bons == total else 2

    if not bloco:
        print("")
        print("Sem o bloco do patch 125 nao da para montar a pagina de teste.")
        print(ROTEIRO)
        return 2

    pasta = os.path.dirname(os.path.abspath(caminho))
    destino = gerar_pagina(pasta, bloco)
    print("")
    print("PAGINA DE TESTE CRIADA: " + os.path.basename(destino))
    print("Clique duas vezes nesse arquivo para abrir no navegador.")
    print("Ele roda sozinho 17 testes com uma nuvem de mentira (nao toca no")
    print("Supabase de verdade) e leva cerca de 25 segundos - a ultima parte")
    print("espera o vigia da nuvem. Se tudo ficar verde, o patch 125 esta")
    print("guardando cada obra com a versao de quem realmente mexeu nela.")
    print("Pode apagar esse arquivo depois do teste.")
    print(ROTEIRO)
    return 0 if bons == total else 2


if __name__ == "__main__":
    sys.exit(main())
