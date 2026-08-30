# -*- coding: utf-8 -*-
"""
PATCH 89 - corrige o travamento causado pelo PATCH 88

O que aconteceu:
  O patch 88 instalou um "vigia" (MutationObserver) que ficava olhando
  toda a pagina. Mas esse mesmo vigia escrevia na pagina (faixa verde
  "Quem esta acessando agora", etiquetas online / visto ha X minutos e o
  contador no botao do menu). Cada escrita acordava o vigia de novo, que
  escrevia outra vez, sem parar. Isso deixou o navegador ocupado 100% do
  tempo e apareceu a mensagem "Esta pagina nao esta respondendo".

O que este patch faz:
  1) Desliga o vigia do patch 88 (era ele que criava o ciclo infinito).
  2) Os tres recursos do patch 88 continuam funcionando normalmente,
     agora atualizados pela verificacao leve que roda a cada 3 segundos.
  3) A faixa verde e o contador do botao passam a ser reescritos somente
     quando o conteudo realmente mudou (antes eram reescritos sempre).
  4) A tela do historico ganha uma trava de seguranca para nunca se
     redesenhar dentro de si mesma.

O que NAO muda:
  - a caixa "Usuarios cadastrados" continua centralizada e menor;
  - a faixa "Quem esta acessando agora" continua aparecendo;
  - a tela "Historico de alteracoes" continua igual, com busca e CSV;
  - nada mais do painel e alterado.

Como usar:
  Coloque este arquivo na mesma pasta do index.html e execute:
      python patch89_corrigir_travamento.py
  Depois abra o painel e recarregue com Ctrl + F5.

Seguranca:
  - cria backup automatico do index.html antes de mexer
  - mexe apenas em 4 linhas do bloco do patch 88
  - pode rodar varias vezes (na segunda ele avisa e nao faz nada)
"""

import io
import os
import sys
import shutil
from datetime import datetime

MARCA = 'PATCH89_ANTITRAVA_OK'
MARCA88 = 'PATCH88_CENTRO_PRESENCA_HISTORICO_OK'


# ------------------------------------------------------------------ #
# trocas pontuais dentro do bloco do patch 88
# cada item: (apelido, texto_antigo, texto_novo, obrigatorio)
# a marca @@ representa a quebra de linha do proprio arquivo
# ------------------------------------------------------------------ #
TROCAS = [
    (
        'desligar o vigia que travava a pagina',
        "      ob.observe(document.body, { childList: true, subtree: true });",
        "      /* PATCH 89: vigia desligado - ele escrevia na pagina e se"
        "@@         acordava sozinho, criando um ciclo infinito. A atualizacao"
        "@@         agora e feita pela verificacao de 3 segundos logo acima. */"
        "@@      ob = null;",
        True,
    ),
    (
        'faixa verde reescrita so quando muda',
        "    bl.innerHTML = htmlPresenca();",
        "    var p89novo = htmlPresenca();"
        "@@    if (window.__p89faixa !== p89novo) {"
        "@@      window.__p89faixa = p89novo;"
        "@@      bl.innerHTML = p89novo;"
        "@@    }",
        False,
    ),
    (
        'contador do botao reescrito so quando muda',
        "    g.textContent = n + (n === 1 ? ' acessando' : ' acessando');",
        "    var p89txt = n + ' acessando';"
        "@@    if (g.textContent !== p89txt) { g.textContent = p89txt; }",
        False,
    ),
    (
        'trava de seguranca na tela do historico',
        "    if (f) { desenharHist(); }",
        "    if (f && !window.__p89hist) {"
        "@@      window.__p89hist = true;"
        "@@      try { desenharHist(); } finally { window.__p89hist = false; }"
        "@@    }",
        False,
    ),
]


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

    if MARCA88 not in html:
        print('AVISO: nao encontrei o bloco do PATCH 88 neste index.html.')
        print('Se o painel ja esta funcionando bem, nao precisa deste patch.')
        return 1

    quebra = '\r\n' if '\r\n' in html[:4000] else '\n'

    feitas = []
    faltando = []

    for apelido, antigo, novo, obrigatorio in TROCAS:
        quantas = html.count(antigo)
        if quantas != 1:
            if obrigatorio:
                print('ERRO: nao consegui localizar com seguranca: ' + apelido)
                print('      (ocorrencias encontradas: ' + str(quantas) + ')')
                print('Nada foi alterado no seu arquivo.')
                return 1
            faltando.append(apelido)
            continue
        html = html.replace(antigo, novo.replace('@@', quebra), 1)
        feitas.append(apelido)

    pos = html.rfind('</body>')
    if pos < 0:
        pos = html.rfind('</html>')
    if pos < 0:
        print('ERRO: nao encontrei o final da pagina (</body>).')
        return 1

    html = html[:pos] + '<!-- ' + MARCA + ' -->' + quebra + html[pos:]

    selo = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = alvo + '.bak_patch89_' + selo
    shutil.copyfile(alvo, backup)

    with io.open(alvo, 'w', encoding='utf-8', errors='surrogateescape', newline='') as f:
        f.write(html)

    print('PATCH 89 aplicado com sucesso.')
    for item in feitas:
        print('  - ' + item)
    for item in faltando:
        print('  - (nao encontrado, ignorado) ' + item)
    print('')
    print('O travamento vinha do vigia do patch 88, que se acordava sozinho.')
    print('Ele foi desligado. A faixa verde, as etiquetas online e o')
    print('historico de alteracoes continuam funcionando.')
    print('')
    print('Backup salvo em: ' + backup)
    print('')
    print('Agora feche a aba do painel, abra de novo e recarregue com Ctrl + F5.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
