# -*- coding: utf-8 -*-
# =====================================================================
# GERENCIAR PAINEL - aplica os patches, limpa a bagunca e envia p/ Git
# =====================================================================
#
# PARA QUE SERVE
#   Em vez de rodar patch por patch na mao, este script faz tudo em fila:
#     1. descobre quais patches (patch1xx_*.py) ainda NAO foram aplicados
#        no seu index.html e aplica em ordem de numero;
#     2. arruma a bagunca: junta as copias de seguranca antigas, apaga
#        restos do Python e arquivos de teste solto;
#     3. grava no Git e envia para o servidor do repositorio.
#
# REGRA DE OURO DESTE SCRIPT
#   Sem nenhum comando, ele NAO MEXE EM NADA. So mostra o que faria.
#   Rode assim primeiro:
#       python gerenciar_painel.py
#   Depois, quando concordar com o que ele mostrou:
#       python gerenciar_painel.py aplicar     -> so aplica os patches
#       python gerenciar_painel.py limpar      -> so arruma os arquivos
#       python gerenciar_painel.py enviar      -> so grava e envia no Git
#       python gerenciar_painel.py tudo        -> os tres, em fila
#
#   Extras:
#       --sim            responde "sim" sem perguntar (use com cuidado)
#       --recado "texto" o recado que vai junto no Git
#       --so-gravar      grava no Git mas NAO envia para o servidor
#
# O QUE ELE NUNCA FAZ
#   * Nunca apaga os seus scripts de patch nem os arquivos .sql: eles sao
#     o seu historico.
#   * Nunca apaga o index.html.
#   * Nunca apaga a copia de seguranca mais nova (guarda as 3 ultimas).
#   * Nunca usa envio forcado no Git, nunca desfaz commit, nunca
#     descarta alteracao sua. Se o Git reclamar, ele para e conta o
#     motivo, em vez de insistir.
#
# O QUE OLHAR DEPOIS
#   * A lista final: quantos patches entraram, quantos arquivos foram
#     arrumados e se o envio foi aceito.
#   * Abra o painel com Ctrl+F5 e confira no console.
#
# SEGURANCA - LEIA UMA VEZ
#   * Antes de aplicar patch, ele faz uma copia do index.html (alem das
#     copias que cada patch ja faz por conta).
#   * Se o seu repositorio for publico, lembre que o index.html leva
#     dentro dele a chave de ligacao com o servidor. O script avisa
#     sobre isso. O certo e o repositorio ser privado.
#   * Guardar no Git nao substitui as regras do servidor: quem manda no
#     acesso aos dados continua sendo o servidor.
# =====================================================================

import io
import os
import re
import shutil
import subprocess
import sys
import time

ALVO = 'index.html'
GUARDA_COPIAS = 3
PASTA_COPIAS = 'copias_antigas'
PASTA_APLICADOS = 'patches_aplicados'


def fala(t=''):
    try:
        print(t)
    except Exception:
        print(t.encode('ascii', 'replace').decode('ascii'))


def titulo(t):
    fala('')
    fala('=' * 62)
    fala(t)
    fala('=' * 62)


def ler(caminho):
    with io.open(caminho, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def confirmar(pergunta, automatico):
    if automatico:
        fala('  > ' + pergunta + ' (respondido sim automaticamente)')
        return True
    try:
        r = raw_input(u'  > ' + pergunta + u' [s/N] ')  # noqa: F821
    except NameError:
        r = input(u'  > ' + pergunta + u' [s/N] ')
    except (EOFError, KeyboardInterrupt):
        fala('')
        return False
    return str(r).strip().lower() in ('s', 'si', 'sim', 'y', 'yes')


def rodar(partes, pasta='.'):
    """Roda um comando e devolve (codigo, texto). Nunca lanca excecao."""
    try:
        p = subprocess.Popen(partes, cwd=pasta, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        saida = p.communicate()[0]
        try:
            saida = saida.decode('utf-8', 'replace')
        except Exception:
            saida = str(saida)
        return p.returncode, saida.strip()
    except Exception as e:
        return 127, str(e)


# ---------------------------------------------------------------------
# 1) descobrir os patches e quais faltam
# ---------------------------------------------------------------------
def numero_do_nome(nome):
    m = re.match(r'^patch(\d+)', nome)
    return int(m.group(1)) if m else 999999


def marca_do_patch(caminho):
    """Le a marca que o patch grava no index.html, para saber se ja entrou."""
    try:
        texto = ler(caminho)
    except Exception:
        return ''
    m = re.search(r"^MARCA\s*=\s*['\"]([^'\"]+)['\"]", texto, re.M)
    if m:
        return m.group(1)
    m = re.search(r"<!--\s*INI\s+(PATCH[0-9A-Z_]+)", texto)
    return m.group(1) if m else ''


def listar_patches(pasta):
    achados = []
    for nome in os.listdir(pasta):
        if not nome.lower().endswith('.py'):
            continue
        if not nome.lower().startswith('patch'):
            continue
        if nome == os.path.basename(__file__):
            continue
        achados.append(nome)
    achados.sort(key=lambda n: (numero_do_nome(n), n))
    return achados


def separar(pasta, patches, html):
    faltando, dentro, sem_marca = [], [], []
    for nome in patches:
        marca = marca_do_patch(os.path.join(pasta, nome))
        if not marca:
            sem_marca.append(nome)
        elif marca in html:
            dentro.append(nome)
        else:
            faltando.append(nome)
    return faltando, dentro, sem_marca

# ---------------------------------------------------------------------
# 2) aplicar os que faltam
# ---------------------------------------------------------------------
def aplicar(pasta, faltando, automatico, de_verdade):
    titulo('PASSO 1 - APLICAR OS PATCHES QUE FALTAM')
    if not faltando:
        fala('  Nada a aplicar: o index.html ja tem todos os patches da pasta.')
        return True, []

    fala('  Vao entrar, nesta ordem:')
    for n in faltando:
        fala('    - ' + n)
    if not de_verdade:
        fala('')
        fala('  (mostrando so o que faria - use "aplicar" ou "tudo" para valer)')
        return True, []
    if not confirmar('Aplicar esses %d patch(es) no index.html?' % len(faltando),
                     automatico):
        fala('  Cancelado por voce. Nada foi alterado.')
        return False, []

    copia = ALVO + '.antes_da_fila_' + time.strftime('%Y%m%d_%H%M%S')
    try:
        shutil.copyfile(os.path.join(pasta, ALVO), os.path.join(pasta, copia))
        fala('  Copia de seguranca da fila: ' + copia)
    except Exception as e:
        fala('  Nao consegui fazer a copia de seguranca (' + str(e) + '). Parei aqui.')
        return False, []

    entraram = []
    for nome in faltando:
        codigo, saida = rodar([sys.executable, nome], pasta)
        primeira = (saida.splitlines() or [''])[0]
        if codigo == 0:
            fala('  ok  ' + nome + '  ->  ' + primeira)
            entraram.append(nome)
        else:
            fala('  ERRO em ' + nome + ':')
            for linha in saida.splitlines()[-8:]:
                fala('        ' + linha)
            fala('')
            fala('  Parei a fila neste ponto para nao empilhar problema.')
            fala('  Se quiser voltar ao ponto de partida, use o arquivo ' + copia)
            return False, entraram
    fala('')
    fala('  Entraram %d patch(es).' % len(entraram))
    return True, entraram


# ---------------------------------------------------------------------
# 3) limpar a bagunca (sem apagar nada importante)
# ---------------------------------------------------------------------
def alvos_de_limpeza(pasta):
    copias, restos, testes = [], [], []
    for nome in os.listdir(pasta):
        cheio = os.path.join(pasta, nome)
        if os.path.isdir(cheio):
            if nome == '__pycache__':
                restos.append(nome)
            continue
        baixo = nome.lower()
        if baixo.startswith(ALVO + '.backup') or baixo.startswith(ALVO + '.antes_da_fila'):
            copias.append(nome)
        elif baixo.endswith('.pyc') or baixo.endswith('.pyo') or baixo.endswith('~'):
            restos.append(nome)
        elif baixo.startswith('teste') and baixo.endswith('.js'):
            testes.append(nome)
        elif baixo in ('index.html.orig', 'index.html.rej', 'nul'):
            restos.append(nome)

    def idade(n):
        try:
            return os.path.getmtime(os.path.join(pasta, n))
        except Exception:
            return 0

    copias.sort(key=idade, reverse=True)
    guardar = copias[:GUARDA_COPIAS]
    mover = copias[GUARDA_COPIAS:]
    return guardar, mover, restos, testes


def limpar(pasta, automatico, de_verdade, guardar_patches):
    titulo('PASSO 2 - ARRUMAR OS ARQUIVOS DA PASTA')
    guardar, mover, restos, testes = alvos_de_limpeza(pasta)

    fala('  Copias de seguranca: %d no total.' % (len(guardar) + len(mover)))
    for n in guardar:
        fala('    fica aqui  ' + n)
    for n in mover:
        fala('    vai para a pasta ' + PASTA_COPIAS + '/  ' + n)
    if restos:
        fala('  Restos que serao apagados (nao servem para nada):')
        for n in restos:
            fala('    apaga  ' + n)
    if testes:
        fala('  Arquivos de teste soltos que serao apagados:')
        for n in testes:
            fala('    apaga  ' + n)
    if guardar_patches:
        fala('  Os patches ja aplicados vao para a pasta ' + PASTA_APLICADOS + '/')

    if not (mover or restos or testes or guardar_patches):
        fala('  A pasta ja esta limpa. Nada a fazer.')
        return True

    if not de_verdade:
        fala('')
        fala('  (mostrando so o que faria - use "limpar" ou "tudo" para valer)')
        return True
    if not confirmar('Pode arrumar? Seus patches, .sql e o index.html ficam intactos.',
                     automatico):
        fala('  Cancelado por voce. Nada foi alterado.')
        return False

    if mover:
        destino = os.path.join(pasta, PASTA_COPIAS)
        if not os.path.isdir(destino):
            os.makedirs(destino)
        for n in mover:
            try:
                shutil.move(os.path.join(pasta, n), os.path.join(destino, n))
            except Exception as e:
                fala('  nao consegui mover ' + n + ': ' + str(e))
    for n in restos + testes:
        cheio = os.path.join(pasta, n)
        try:
            if os.path.isdir(cheio):
                shutil.rmtree(cheio)
            else:
                os.remove(cheio)
        except Exception as e:
            fala('  nao consegui apagar ' + n + ': ' + str(e))
    fala('  Arrumado: %d copia(s) guardada(s) de lado, %d resto(s) apagado(s).'
         % (len(mover), len(restos) + len(testes)))
    return True


def arquivar_patches(pasta, aplicados, de_verdade):
    if not aplicados or not de_verdade:
        return
    destino = os.path.join(pasta, PASTA_APLICADOS)
    if not os.path.isdir(destino):
        os.makedirs(destino)
    for n in aplicados:
        try:
            shutil.move(os.path.join(pasta, n), os.path.join(destino, n))
        except Exception:
            pass
    fala('  %d patch(es) guardado(s) em ' % len(aplicados) + PASTA_APLICADOS + '/')

# ---------------------------------------------------------------------
# 4) gravar e enviar no Git
# ---------------------------------------------------------------------
def cuidar_do_gitignore(pasta, de_verdade):
    linhas = [
        '# arrumado pelo gerenciar_painel',
        'index.html.backup*',
        'index.html.antes_da_fila*',
        PASTA_COPIAS + '/',
        '__pycache__/',
        '*.pyc',
    ]
    caminho = os.path.join(pasta, '.gitignore')
    atual = ''
    if os.path.exists(caminho):
        atual = ler(caminho)
    faltam = [x for x in linhas if x not in atual]
    if not faltam:
        return False
    if not de_verdade:
        fala('  Vou pedir ao Git para ignorar as copias de seguranca.')
        return False
    with io.open(caminho, 'a', encoding='utf-8') as f:
        if atual and not atual.endswith('\n'):
            f.write(u'\n')
        f.write(u'\n'.join(faltam) + u'\n')
    fala('  Ajustei o .gitignore: as copias de seguranca nao vao mais para o Git.')
    return True


def ordem_primeira_gravacao(pasta):
    codigo, _ = rodar(['git', 'rev-parse', '--verify', 'HEAD'], pasta)
    return codigo != 0


def enviar(pasta, recado, automatico, de_verdade, so_gravar):
    titulo('PASSO 3 - GRAVAR NO GIT E ENVIAR')

    codigo, _ = rodar(['git', '--version'])
    if codigo != 0:
        fala('  O Git nao esta instalado neste computador (ou nao esta no caminho).')
        fala('  Os patches ja foram aplicados; so o envio nao aconteceu.')
        return False

    codigo, _ = rodar(['git', 'rev-parse', '--is-inside-work-tree'], pasta)
    if codigo != 0:
        fala('  Esta pasta nao e um repositorio Git ainda.')
        fala('  Se quiser versionar, crie o repositorio uma vez e rode de novo.')
        return False

    codigo, ramo = rodar(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], pasta)
    ramo = (ramo.splitlines() or [''])[0].strip() if codigo == 0 else ''
    if not ramo or ramo == 'HEAD':
        codigo2, ramo2 = rodar(['git', 'symbolic-ref', '--short', 'HEAD'], pasta)
        ramo = (ramo2.splitlines() or [''])[0].strip() if codigo2 == 0 else 'master'
    _, sujeira = rodar(['git', 'status', '--porcelain'], pasta)
    _, remotos = rodar(['git', 'remote'], pasta)
    tem_remoto = bool(remotos.strip())

    fala('  Ramo atual: ' + (ramo or '(nao sei)'))
    if ordem_primeira_gravacao(pasta):
        fala('  Este repositorio ainda nao tem nenhuma gravacao: esta sera a primeira.')
    if not sujeira.strip():
        fala('  Nao ha nada de novo para gravar. O Git ja esta em dia.')
        return True

    fala('  Alteracoes que serao gravadas:')
    for linha in sujeira.splitlines()[:40]:
        fala('    ' + linha)
    if len(sujeira.splitlines()) > 40:
        fala('    ... e mais %d arquivo(s)' % (len(sujeira.splitlines()) - 40))

    if not tem_remoto:
        fala('  Aviso: nao ha servidor de repositorio configurado. Vou apenas gravar aqui.')
    else:
        fala('  Lembrete de seguranca: o index.html leva dentro dele a chave de')
        fala('  ligacao com o servidor. Confirme que este repositorio e privado.')

    if not de_verdade:
        fala('')
        fala('  (mostrando so o que faria - use "enviar" ou "tudo" para valer)')
        return True
    if not confirmar('Gravar no Git' + ('' if so_gravar or not tem_remoto else ' e enviar') + '?',
                     automatico):
        fala('  Cancelado por voce. Nada foi gravado.')
        return False

    cuidar_do_gitignore(pasta, True)

    codigo, saida = rodar(['git', 'add', '-A'], pasta)
    if codigo != 0:
        fala('  O Git nao conseguiu separar os arquivos: ' + saida)
        return False

    if not recado:
        recado = 'Painel: patches aplicados e pasta arrumada (' + \
                 time.strftime('%d/%m/%Y %H:%M') + ')'
    codigo, saida = rodar(['git', 'commit', '-m', recado], pasta)
    if codigo != 0:
        if 'nothing to commit' in saida.lower():
            fala('  Nao havia nada novo para gravar.')
        else:
            fala('  O Git nao conseguiu gravar:')
            for linha in saida.splitlines()[-8:]:
                fala('    ' + linha)
            return False
    else:
        fala('  Gravado com o recado: ' + recado)

    if so_gravar:
        fala('  Voce pediu para nao enviar. Ficou gravado so no seu computador.')
        return True
    if not tem_remoto:
        fala('  Sem servidor de repositorio: ficou gravado so no seu computador.')
        return True

    codigo, saida = rodar(['git', 'push'], pasta)
    if codigo != 0 and 'no upstream' in saida.lower():
        codigo, saida = rodar(['git', 'push', '-u', 'origin', ramo], pasta)
    if codigo == 0:
        fala('  Enviado para o repositorio.')
        return True

    fala('  O envio nao foi aceito. O Git respondeu:')
    for linha in saida.splitlines()[-10:]:
        fala('    ' + linha)
    fala('')
    fala('  Seu trabalho esta gravado aqui, nada foi perdido. Em geral isso')
    fala('  acontece quando alguem enviou algo antes de voce: rode "git pull",')
    fala('  resolva o que ele apontar e envie de novo. Nao vou forcar o envio,')
    fala('  porque forcar pode apagar o trabalho da outra pessoa.')
    return False

# ---------------------------------------------------------------------
# 5) o maestro
# ---------------------------------------------------------------------
def ajuda():
    fala('Como usar:')
    fala('  python gerenciar_painel.py            mostra o que faria (nao mexe em nada)')
    fala('  python gerenciar_painel.py aplicar    aplica os patches que faltam')
    fala('  python gerenciar_painel.py limpar     arruma as copias e os restos')
    fala('  python gerenciar_painel.py enviar     grava no Git e envia')
    fala('  python gerenciar_painel.py tudo       os tres, em fila')
    fala('')
    fala('Extras: --sim (nao pergunta)  --so-gravar (nao envia)')
    fala('        --recado "texto"      recado que vai no Git')
    fala('        --guardar-patches     move os patches aplicados para uma pasta')


def main():
    argumentos = [a for a in sys.argv[1:]]
    automatico = '--sim' in argumentos
    so_gravar = '--so-gravar' in argumentos
    guardar_patches = '--guardar-patches' in argumentos
    recado = ''
    if '--recado' in argumentos:
        i = argumentos.index('--recado')
        if i + 1 < len(argumentos):
            recado = argumentos[i + 1]
            del argumentos[i:i + 2]
    palavras = [a for a in argumentos if not a.startswith('--')]
    ordem = (palavras[0].lower() if palavras else 'ver')

    if ordem in ('ajuda', 'help', '-h', '--help'):
        ajuda()
        return 0
    if ordem not in ('ver', 'aplicar', 'limpar', 'enviar', 'tudo'):
        fala('Nao entendi "' + ordem + '".')
        fala('')
        ajuda()
        return 1

    pasta = os.path.dirname(os.path.abspath(__file__)) or '.'
    if not os.path.exists(os.path.join(pasta, ALVO)):
        fala('Nao encontrei o ' + ALVO + ' nesta pasta.')
        fala('Coloque este script na mesma pasta do painel e rode de novo.')
        return 1

    html = ler(os.path.join(pasta, ALVO))
    patches = listar_patches(pasta)
    faltando, dentro, sem_marca = separar(pasta, patches, html)

    titulo('SITUACAO DE AGORA')
    fala('  Patches na pasta: %d' % len(patches))
    fala('  Ja aplicados:     %d' % len(dentro))
    fala('  Faltando aplicar: %d' % len(faltando))
    for n in faltando:
        fala('      - ' + n)
    if sem_marca:
        fala('  Nao consegui reconhecer (vou deixar de fora, rode na mao se precisar):')
        for n in sem_marca:
            fala('      - ' + n)
    if ordem == 'ver':
        fala('')
        fala('  Nada foi alterado. Este e so o retrato da pasta.')

    tudo_certo = True
    entraram = []

    if ordem in ('ver', 'aplicar', 'tudo'):
        ok, entraram = aplicar(pasta, faltando, automatico,
                               ordem in ('aplicar', 'tudo'))
        tudo_certo = tudo_certo and ok
        if not ok and ordem == 'tudo':
            fala('')
            fala('Parei antes de limpar e de enviar, porque um patch falhou.')
            return 1

    if ordem in ('ver', 'limpar', 'tudo'):
        ok = limpar(pasta, automatico, ordem in ('limpar', 'tudo'), guardar_patches)
        tudo_certo = tudo_certo and ok
        if guardar_patches:
            arquivar_patches(pasta, entraram or dentro, ordem in ('limpar', 'tudo'))

    if ordem in ('ver', 'enviar', 'tudo'):
        ok = enviar(pasta, recado, automatico, ordem in ('enviar', 'tudo'), so_gravar)
        tudo_certo = tudo_certo and ok

    titulo('RESUMO')
    if ordem == 'ver':
        fala('  Foi so um ensaio: nada mudou no seu computador.')
        fala('  Quando concordar com a lista acima, rode:')
        fala('      python gerenciar_painel.py tudo')
    elif tudo_certo:
        fala('  Tudo pronto.')
        if entraram:
            fala('  Patches aplicados: ' + str(len(entraram)))
        fala('  Agora abra o painel e pressione Ctrl+F5.')
    else:
        fala('  Terminou com pendencia. Leia as mensagens acima:')
        fala('  o passo que falhou foi contado, e nada foi apagado por conta.')
    return 0 if tudo_certo else 1


if __name__ == '__main__':
    sys.exit(main())
