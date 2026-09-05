# -*- coding: utf-8 -*-
# =====================================================================
# PUBLICAR PATCH - aplica o patch e manda para o Git (que atualiza o site)
# =====================================================================
#
# O QUE MUDA
#   Os patches mexem apenas no arquivo da sua maquina. Este script fecha
#   o caminho que faltava: aplica o patch (se voce indicar um), confere
#   se o arquivo ficou sadio, envia para o Git e o site se atualiza
#   sozinho a partir dai.
#
# COMO USAR
#   Deixe este arquivo na pasta do painel (a mesma do index.html) e rode:
#
#     python publicar_patch.py patch129_nao_interromper.py
#         aplica o patch 129 e publica em seguida
#
#     python publicar_patch.py
#         publica o arquivo como ele esta agora (sem aplicar patch)
#
#     python publicar_patch.py patch130.py patch131.py
#         aplica vários na ordem e publica uma vez so
#
#   Opcoes:
#     --so-conferir   confere e mostra o que faria, sem enviar nada
#     --sim           nao pergunta nada
#     --mensagem X    texto do commit (o padrao cita os patches aplicados)
#     --arquivo X     usa outro arquivo em vez de index.html
#     --tudo          envia tambem os .py e .sql desta pasta
#
# O QUE OLHAR DEPOIS
#   * No fim ele mostra o codigo do envio e o nome do ramo.
#   * Abra o painel publicado e aperte Ctrl+F5; o rodape/console deve
#     mostrar o patch novo.
#   * Se o envio for recusado por causa de alteracao de outra pessoa, ele
#     avisa em portugues e diz o comando para trazer o que falta.
#
# SEGURANCA
#   * Faz copia de seguranca antes de qualquer coisa.
#   * Envia somente o arquivo do painel (a menos que voce peca --tudo).
#   * Nao envia arquivos de senha, .env, chaves nem as copias .antes_*.
#   * Nao apaga nada e nao mexe na configuracao do seu Git.
#   * Nunca envia para o ramo principal sem avisar qual e o ramo.
# =====================================================================

import io
import os
import re
import shutil
import subprocess
import sys
import time

ALVO = 'index.html'
PROIBIDOS = ('.env', 'senha', 'secret', 'credenc', 'token', '.key', '.pem')


def fala(txt):
    try:
        print(txt)
    except Exception:
        print(txt.encode('ascii', 'replace').decode('ascii'))
    sys.stdout.flush()


def titulo(txt):
    fala('')
    fala('-' * 64)
    fala('  ' + txt)
    fala('-' * 64)


def perguntar(txt, automatico):
    if automatico:
        return True
    try:
        resp = raw_input(txt + ' [s/n] ')  # noqa: F821
    except NameError:
        resp = input(txt + ' [s/n] ')
    except Exception:
        return False
    return str(resp).strip().lower() in ('s', 'si', 'sim', 'y', 'yes')


def rodar(args, pasta):
    """Roda um comando e devolve (codigo, saida). Nunca levanta erro."""
    try:
        p = subprocess.Popen(args, cwd=pasta, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        saida = p.communicate()[0]
        try:
            saida = saida.decode('utf-8', 'replace')
        except Exception:
            saida = str(saida)
        return p.returncode, saida.strip()
    except Exception as e:
        return 127, str(e)


def patches_no_arquivo(texto):
    """Lista os numeros de patch que aparecem no arquivo, em ordem."""
    achados = []
    for m in re.finditer(r'PATCH[ _]?(\d{2,3})', texto):
        n = m.group(1)
        if n not in achados:
            achados.append(n)
    achados.sort(key=lambda v: int(v))
    return achados


def arquivo_sadio(texto):
    """Confere o basico: a pagina fecha, os blocos de codigo fecham."""
    problemas = []
    if len(texto) < 5000:
        problemas.append('o arquivo esta pequeno demais para ser o painel')
    if '</body>' not in texto or '</html>' not in texto:
        problemas.append('a pagina nao termina corretamente')
    if texto.count('<script') != texto.count('</script>'):
        problemas.append('ha bloco de codigo aberto e nao fechado')
    if '<<<<<<<' in texto or '>>>>>>>' in texto:
        problemas.append('o arquivo tem marcas de conflito do Git (<<<<<<<) para resolver')
    return problemas


def repositorio_em_ordem(pasta, raiz, ramo):
    """Confere se o repositorio nao esta no meio de uma juncao."""
    recados = []
    pasta_git = os.path.join(raiz, '.git')
    for nome, aviso in (('MERGE_HEAD', 'juncao (merge) pela metade'),
                        ('rebase-merge', 'reordenacao (rebase) pela metade'),
                        ('rebase-apply', 'reordenacao (rebase) pela metade'),
                        ('CHERRY_PICK_HEAD', 'aplicacao de commit pela metade')):
        if os.path.exists(os.path.join(pasta_git, nome)):
            recados.append('O repositorio esta com uma ' + aviso + '.')
            break
    if ramo in ('HEAD', '(desconhecido)', ''):
        recados.append('O repositorio nao esta em nenhum ramo (estado solto).')
    return recados


def aplicar(patch, pasta):
    """Roda um script de patch nesta pasta. Devolve True se deu certo."""
    fala('')
    fala('Aplicando ' + patch + ' ...')
    codigo, saida = rodar([sys.executable, patch], pasta)
    for linha in saida.splitlines():
        fala('   ' + linha)
    if codigo != 0:
        fala('   -> o patch terminou com erro (codigo ' + str(codigo) + ').')
        return False
    return True


def seguro_para_enviar(nome):
    baixo = nome.lower()
    if '.antes_' in baixo or baixo.endswith('.bak'):
        return False
    for ruim in PROIBIDOS:
        if ruim in baixo:
            return False
    return True


def main(argv):
    automatico = '--sim' in argv
    so_conferir = '--so-conferir' in argv
    tudo = '--tudo' in argv
    mensagem = ''
    arquivo = ALVO
    patches = []

    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--mensagem' and i + 1 < len(argv):
            mensagem = argv[i + 1]
            i = i + 2
            continue
        if a == '--arquivo' and i + 1 < len(argv):
            arquivo = argv[i + 1]
            i = i + 2
            continue
        if a.startswith('--'):
            i = i + 1
            continue
        patches.append(a)
        i = i + 1

    pasta = os.path.dirname(os.path.abspath(__file__)) or os.getcwd()
    caminho = os.path.join(pasta, arquivo)
    if not os.path.isfile(caminho):
        caminho = os.path.join(os.getcwd(), arquivo)
        pasta = os.getcwd()
    if not os.path.isfile(caminho):
        fala('Nao achei o arquivo ' + arquivo + ' nesta pasta.')
        fala('Coloque este script na mesma pasta do painel e rode de novo.')
        return 2

    titulo('PUBLICAR PATCH - ' + os.path.basename(caminho))

    # 1. copia de seguranca antes de tudo
    copia = caminho + '.antes_publicar_' + time.strftime('%Y%m%d_%H%M%S') + '.html'
    try:
        shutil.copyfile(caminho, copia)
        fala('Copia de seguranca: ' + os.path.basename(copia))
    except Exception as e:
        fala('Nao consegui fazer copia de seguranca: ' + str(e))
        return 2

    with io.open(caminho, 'r', encoding='utf-8', errors='ignore') as f:
        antes = f.read()
    patches_antes = patches_no_arquivo(antes)

    # 2. aplica os patches pedidos
    for p in patches:
        if not os.path.isfile(os.path.join(pasta, p)):
            fala('Nao achei o script ' + p + ' nesta pasta. Parei aqui.')
            return 2
        if not aplicar(p, pasta):
            fala('')
            fala('Nada foi publicado porque o patch nao terminou bem.')
            return 1

    with io.open(caminho, 'r', encoding='utf-8', errors='ignore') as f:
        depois = f.read()

    # 3. o arquivo esta sadio?
    titulo('CONFERINDO O ARQUIVO')
    problemas = arquivo_sadio(depois)
    if problemas:
        for pr in problemas:
            fala('FALHA: ' + pr)
        fala('')
        fala('Nao vou publicar um arquivo com problema.')
        fala('Para voltar atras, apague o painel e renomeie ' + os.path.basename(copia))
        return 1
    fala('OK: a pagina fecha e os blocos de codigo estao fechados.')

    novos = [n for n in patches_no_arquivo(depois) if n not in patches_antes]
    if novos:
        fala('OK: patch novo dentro do arquivo: ' + ', '.join(novos))
    elif patches:
        fala('ATENCAO: o patch nao acrescentou marca nova (talvez ja estivesse aplicado).')
    fala('Patches presentes: ' + ', '.join(patches_no_arquivo(depois)[-8:]))
    return publicar(pasta, caminho, mensagem, novos, automatico, so_conferir, tudo)


def publicar(pasta, caminho, mensagem, novos, automatico, so_conferir, tudo):
    titulo('ENVIANDO PARA O GIT')

    codigo, _ = rodar(['git', '--version'], pasta)
    if codigo != 0:
        fala('O Git nao esta instalado nesta maquina (ou nao esta no caminho).')
        fala('Instale o Git e rode este script de novo. O painel local ja esta atualizado.')
        return 1

    codigo, raiz = rodar(['git', 'rev-parse', '--show-toplevel'], pasta)
    if codigo != 0:
        fala('Esta pasta nao e um repositorio Git, entao nao ha para onde enviar.')
        fala('O painel local esta atualizado. Se o site publica a partir do Git,')
        fala('coloque o painel na pasta do repositorio e rode aqui.')
        return 1
    fala('Repositorio: ' + os.path.basename(raiz))

    codigo, ramo = rodar(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], pasta)
    ramo = ramo if codigo == 0 else '(desconhecido)'
    fala('Ramo atual: ' + ramo)

    recados = repositorio_em_ordem(pasta, raiz, ramo)
    if recados:
        fala('')
        for r in recados:
            fala('FALHA: ' + r)
        fala('')
        fala('Nao vou enviar assim, para nao misturar o trabalho de outra pessoa.')
        fala('Resolva primeiro no seu Git (concluir ou desfazer a juncao, e voltar')
        fala('para o ramo de publicacao) e rode este script novamente.')
        fala('O seu painel local continua atualizado e com copia de seguranca.')
        return 1

    codigo, remoto = rodar(['git', 'remote', 'get-url', 'origin'], pasta)
    if codigo != 0:
        fala('Este repositorio nao tem destino (origin) configurado.')
        fala('Sem destino, o site nao recebe a atualizacao. Configure o origin e repita.')
        return 1
    limpo = re.sub(r'//[^@/]+@', '//', remoto)
    fala('Destino: ' + limpo)

    # o que vai junto
    rel = os.path.relpath(caminho, raiz).replace(os.sep, '/')
    enviar = [rel]
    if tudo:
        for nome in sorted(os.listdir(pasta)):
            if not (nome.endswith('.py') or nome.endswith('.sql')):
                continue
            if not seguro_para_enviar(nome):
                fala('Deixei de fora por seguranca: ' + nome)
                continue
            alvo = os.path.relpath(os.path.join(pasta, nome), raiz).replace(os.sep, '/')
            if alvo not in enviar:
                enviar.append(alvo)
    fala('Vai enviar: ' + ', '.join(enviar))

    codigo, sujo = rodar(['git', 'status', '--porcelain'] + enviar, pasta)
    if codigo == 0 and not sujo:
        fala('')
        fala('O Git ja esta igual ao seu arquivo: nao ha nada novo para enviar.')
        fala('Se o site esta velho, o problema esta no site, nao no envio.')
        return 0

    if not mensagem:
        if novos:
            mensagem = 'PATCH ' + ', '.join(novos) + ' aplicado no painel'
        else:
            mensagem = 'Atualizacao do painel ' + time.strftime('%d/%m/%Y %H:%M')

    fala('Mensagem do commit: ' + mensagem)

    if so_conferir:
        fala('')
        fala('Modo so conferir: paro aqui, nada foi enviado.')
        return 0

    if ramo in ('main', 'master'):
        fala('Atencao: o envio vai direto para o ramo ' + ramo + ' (o que publica o site).')
    if not perguntar('Posso enviar agora?', automatico):
        fala('Cancelado. O painel local continua atualizado; nada foi enviado.')
        return 0

    codigo, saida = rodar(['git', 'add'] + enviar, pasta)
    if codigo != 0:
        fala('Nao consegui preparar os arquivos:')
        fala(saida)
        return 1

    codigo, saida = rodar(['git', 'commit', '-m', mensagem], pasta)
    fala(saida)
    if codigo != 0 and 'nothing to commit' not in saida.lower():
        fala('Nao consegui registrar a alteracao. Nada foi enviado.')
        return 1

    codigo, saida = rodar(['git', 'push', '-u', 'origin', ramo], pasta)
    fala(re.sub(r'//[^@/]+@', '//', saida))
    if codigo != 0:
        baixo = saida.lower()
        fala('')
        if 'rejected' in baixo or 'non-fast-forward' in baixo or 'fetch first' in baixo:
            fala('O envio foi recusado: alguem alterou o repositorio depois de voce.')
            fala('Traga o que falta e repita:')
            fala('   git pull --rebase origin ' + ramo)
            fala('   python ' + os.path.basename(__file__))
        elif 'authentication' in baixo or 'permission' in baixo or 'could not read' in baixo:
            fala('O Git nao conseguiu entrar na sua conta.')
            fala('Entre novamente na conta do Git (token/senha) e repita o envio.')
        elif 'could not resolve' in baixo or 'timed out' in baixo or 'network' in baixo:
            fala('Sem conexao com o servidor do Git. Tente de novo com internet.')
        else:
            fala('O envio falhou. A mensagem acima diz o motivo.')
        fala('O seu painel local continua atualizado e com copia de seguranca.')
        return 1

    codigo, ultimo = rodar(['git', 'log', '-1', '--pretty=%h %s'], pasta)
    titulo('PUBLICADO')
    fala('Enviado para ' + ramo + ': ' + (ultimo if codigo == 0 else mensagem))
    fala('')
    fala('O site que publica a partir deste ramo comeca a atualizar agora.')
    fala('Costuma levar de 1 a 3 minutos. Depois abra o painel e aperte Ctrl+F5.')
    fala('Se o site nao mudar, olhe o painel de deploy do servico: pode haver')
    fala('deploy automatico desligado ou falha no build.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
