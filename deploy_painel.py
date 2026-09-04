# -*- coding: utf-8 -*-
"""
DEPLOY DO PAINEL PORTICO - publica o index.html no Render depois do patch

O que ele faz, na ordem:
  1. acha o index.html na pasta
  2. confere se o Patch 104 esta dentro dele e se o arquivo esta sadio
  3. guarda uma copia de seguranca com data e hora
  4. envia para o GitHub (git add / commit / push) - pede confirmacao antes
  5. se voce configurar o gancho do Render, manda o deploy comecar na hora
  6. acorda o site e confere se a versao publicada ja tem o patch

Como usar (na pasta onde esta o index.html):
    python deploy_painel.py

Opcoes:
    --so-checar     apenas confere o arquivo, nao publica nada
    --sim           nao pergunta nada, faz tudo direto
    --sem-git       pula o envio para o GitHub (usa so o gancho do Render)
    --sem-esperar   nao fica esperando o site subir
    --arquivo X     usa outro arquivo em vez de index.html
    --mensagem X    texto do commit
    --site X        endereco do painel publicado
    --hook X        endereco do gancho de deploy do Render
    --config        so grava/atualiza as configuracoes e sai

Na primeira vez ele cria o arquivo deploy_painel.cfg com o endereco do site
e o gancho do Render, para voce nao precisar digitar de novo.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
import datetime

try:
    from urllib.request import urlopen, Request
    from urllib.error import URLError, HTTPError
except ImportError:  # python 2
    from urllib2 import urlopen, Request, URLError, HTTPError

ARQ_CONFIG = 'deploy_painel.cfg'
SITE_PADRAO = 'https://painel-obras-supabase-realtime.onrender.com'
MARCA_INI = '<!-- PATCH104_INI -->'
MARCA_FIM = '<!-- PATCH104_FIM -->'


def msg(txt):
    try:
        print(txt)
    except Exception:
        print(txt.encode('ascii', 'replace').decode('ascii'))
    sys.stdout.flush()


def titulo(txt):
    msg('')
    msg('=' * 62)
    msg('  ' + txt)
    msg('=' * 62)


def perguntar(txt, automatico):
    if automatico:
        return True
    try:
        entrada = raw_input(txt + ' [s/n] ')  # noqa: F821  (python 2)
    except NameError:
        entrada = input(txt + ' [s/n] ')
    except Exception:
        return False
    return str(entrada).strip().lower() in ('s', 'si', 'sim', 'y', 'yes')


def agora_texto():
    return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')


# ---------------------------------------------------------------- #
# configuracoes gravadas no arquivo deploy_painel.cfg
# ---------------------------------------------------------------- #
def ler_config(pasta):
    caminho = os.path.join(pasta, ARQ_CONFIG)
    dados = {}
    if os.path.exists(caminho):
        try:
            f = open(caminho, 'r')
            dados = json.load(f)
            f.close()
        except Exception:
            dados = {}
    return dados


def gravar_config(pasta, dados):
    caminho = os.path.join(pasta, ARQ_CONFIG)
    try:
        f = open(caminho, 'w')
        json.dump(dados, f, indent=2)
        f.close()
        msg('Configuracoes guardadas em ' + ARQ_CONFIG)
    except Exception as e:
        msg('AVISO: nao consegui guardar as configuracoes (' + str(e) + ')')


def pedir_texto(pergunta, valor_atual):
    sufixo = ''
    if valor_atual:
        sufixo = ' [enter mantem: ' + valor_atual + ']'
    try:
        try:
            r = raw_input(pergunta + sufixo + ': ')  # noqa: F821
        except NameError:
            r = input(pergunta + sufixo + ': ')
    except Exception:
        return valor_atual
    r = str(r).strip()
    return r if r else valor_atual


def configurar(pasta):
    titulo('CONFIGURACAO')
    cfg = ler_config(pasta)
    msg('O endereco do painel publicado (o do Render).')
    cfg['site'] = pedir_texto('Endereco do site', cfg.get('site') or SITE_PADRAO)
    msg('')
    msg('O gancho de deploy do Render e opcional. Para pegar:')
    msg('  Render > seu servico > Settings > Deploy Hook > Copy.')
    msg('Deixe vazio se voce prefere que o Render deploie sozinho apos o push.')
    cfg['hook'] = pedir_texto('Gancho de deploy', cfg.get('hook') or '')
    msg('')
    msg('O ramo do GitHub pode ficar vazio: nesse caso uso o ramo em que voce esta.')
    cfg['branch'] = pedir_texto('Ramo do GitHub', cfg.get('branch') or '')
    gravar_config(pasta, cfg)
    return cfg


# ---------------------------------------------------------------- #
# achar o index.html
# ---------------------------------------------------------------- #
def achar_arquivo(nome_pedido):
    if nome_pedido:
        if os.path.exists(nome_pedido):
            return os.path.abspath(nome_pedido)
        msg('ERRO: nao encontrei o arquivo ' + nome_pedido)
        return None

    aqui = os.getcwd()
    tentativas = [
        os.path.join(aqui, 'index.html'),
        os.path.join(aqui, 'public', 'index.html'),
        os.path.join(aqui, 'static', 'index.html'),
        os.path.join(aqui, 'dist', 'index.html'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'index.html'),
    ]
    for t in tentativas:
        if os.path.exists(t):
            return os.path.abspath(t)

    # ultima tentativa: o maior index.html ate 2 niveis abaixo
    achados = []
    for raiz, pastas, arquivos in os.walk(aqui):
        if raiz.count(os.sep) - aqui.count(os.sep) > 2:
            continue
        pastas[:] = [p for p in pastas if p not in ('.git', 'node_modules', '__pycache__')]
        for a in arquivos:
            if a.lower() == 'index.html':
                cheio = os.path.join(raiz, a)
                try:
                    achados.append((os.path.getsize(cheio), cheio))
                except Exception:
                    pass
    if achados:
        achados.sort()
        return os.path.abspath(achados[-1][1])

    msg('ERRO: nao encontrei nenhum index.html nesta pasta.')
    msg('Rode o script na mesma pasta do painel, ou use: --arquivo caminho/index.html')
    return None


# ---------------------------------------------------------------- #
# conferir se o arquivo esta bom para publicar
# ---------------------------------------------------------------- #
def conferir_arquivo(caminho):
    msg('Conferindo o arquivo antes de publicar...')
    problemas = []
    avisos = []

    try:
        f = open(caminho, 'r', encoding='utf-8', errors='replace')
    except TypeError:  # python 2
        import codecs
        f = codecs.open(caminho, 'r', 'utf-8', 'replace')
    texto = f.read()
    f.close()

    tamanho = len(texto)
    msg('  tamanho: ' + str(round(tamanho / 1024.0, 1)) + ' KB')
    if tamanho < 5000:
        problemas.append('o arquivo esta muito pequeno; parece incompleto')

    if '</html>' not in texto.lower():
        problemas.append('falta o fechamento </html>; o arquivo pode estar cortado')
    if '</body>' not in texto.lower():
        problemas.append('falta o fechamento </body>')

    abre = len(re.findall(r'<script\b', texto, re.I))
    fecha = len(re.findall(r'</script\s*>', texto, re.I))
    msg('  blocos de script: ' + str(abre) + ' abertos / ' + str(fecha) + ' fechados')
    if abre != fecha:
        problemas.append('sobrou um bloco de script sem fechar (' + str(abre) + ' x ' + str(fecha) + ')')

    tem_ini = MARCA_INI in texto
    tem_fim = MARCA_FIM in texto
    if tem_ini and tem_fim:
        msg('  Patch 104 (nuvem): presente')
    elif tem_ini or tem_fim:
        problemas.append('o bloco do Patch 104 esta pela metade no arquivo')
    else:
        avisos.append('o Patch 104 nao esta neste arquivo; rode o patch104.py antes se quiser a nuvem')

    if 'PATCH104_INI' in texto and texto.count(MARCA_INI) > 1:
        problemas.append('o bloco do Patch 104 aparece mais de uma vez')

    if 'supabase' not in texto.lower():
        avisos.append('nao vi nenhuma referencia ao Supabase no arquivo')

    for a in avisos:
        msg('  AVISO: ' + a)
    for p in problemas:
        msg('  PROBLEMA: ' + p)

    if problemas:
        msg('')
        msg('Nao vou publicar um arquivo com problema. Corrija e rode de novo.')
        return False, texto
    msg('  arquivo aprovado.')
    return True, texto


# ---------------------------------------------------------------- #
# copia de seguranca
# ---------------------------------------------------------------- #
def guardar_copia(caminho):
    destino = caminho + '.antes_deploy_' + agora_texto()
    try:
        shutil.copy2(caminho, destino)
        msg('Copia de seguranca: ' + os.path.basename(destino))
        return destino
    except Exception as e:
        msg('AVISO: nao consegui fazer a copia (' + str(e) + ')')
        return None


def limpar_copias_antigas(caminho, manter=5):
    pasta = os.path.dirname(caminho) or '.'
    base = os.path.basename(caminho) + '.antes_deploy_'
    achados = []
    try:
        for a in os.listdir(pasta):
            if a.startswith(base):
                achados.append(a)
    except Exception:
        return
    achados.sort()
    for a in achados[:-manter]:
        try:
            os.remove(os.path.join(pasta, a))
        except Exception:
            pass


# ---------------------------------------------------------------- #
# git
# ---------------------------------------------------------------- #
def rodar(comando, pasta):
    try:
        p = subprocess.Popen(comando, cwd=pasta, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
        saida = p.communicate()[0]
        try:
            saida = saida.decode('utf-8', 'replace')
        except Exception:
            saida = str(saida)
        return p.returncode, saida.strip()
    except Exception as e:
        return 1, str(e)


def tem_git(pasta):
    codigo, _ = rodar(['git', 'rev-parse', '--is-inside-work-tree'], pasta)
    return codigo == 0


def proteger_copias(pasta):
    """evita que as copias de seguranca e o cfg va para o GitHub"""
    linhas_novas = ['*.antes_deploy_*', '*.bak_patch*', ARQ_CONFIG]
    caminho = os.path.join(pasta, '.gitignore')
    atual = ''
    if os.path.exists(caminho):
        try:
            f = open(caminho, 'r')
            atual = f.read()
            f.close()
        except Exception:
            atual = ''
    faltam = [l for l in linhas_novas if l not in atual]
    if not faltam:
        return
    try:
        f = open(caminho, 'a')
        if atual and not atual.endswith('\n'):
            f.write('\n')
        f.write('\n# copias de seguranca do painel (nao publicar)\n')
        for l in faltam:
            f.write(l + '\n')
        f.close()
        msg('Ajustei o .gitignore para nao publicar as copias de seguranca.')
    except Exception:
        pass


def enviar_para_github(pasta, arquivos, mensagem, branch, automatico):
    titulo('ENVIANDO PARA O GITHUB')

    codigo, saida = rodar(['git', 'status', '--porcelain'], pasta)
    if codigo != 0:
        msg('ERRO ao falar com o git: ' + saida)
        return False
    if not saida:
        msg('Nada mudou desde o ultimo envio. Nao ha o que publicar.')
        return None

    msg('Arquivos que mudaram:')
    for linha in saida.split('\n')[:20]:
        msg('  ' + linha)

    _, ramo_atual = rodar(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], pasta)
    if ramo_atual:
        msg('Ramo atual: ' + ramo_atual)
    if not branch:
        branch = ramo_atual or 'main'
    elif ramo_atual and branch != ramo_atual:
        msg('AVISO: o ramo configurado e "' + branch + '", mas voce esta em "' +
            ramo_atual + '". Vou usar o ramo em que voce esta.')
        branch = ramo_atual

    if not perguntar('Enviar essas mudancas para o GitHub?', automatico):
        msg('Envio cancelado. Nada foi publicado.')
        return False

    for a in arquivos:
        codigo, saida = rodar(['git', 'add', '--', a], pasta)
        if codigo != 0:
            msg('ERRO ao preparar ' + a + ': ' + saida)
            return False

    codigo, saida = rodar(['git', 'commit', '-m', mensagem], pasta)
    if codigo != 0:
        if 'nothing to commit' in saida.lower():
            msg('Nada novo para registrar.')
        else:
            msg('ERRO ao registrar as mudancas: ' + saida)
            return False
    else:
        msg('Mudancas registradas: ' + mensagem)

    codigo, saida = rodar(['git', 'push', 'origin', branch], pasta)
    if codigo != 0:
        msg('ERRO ao enviar: ' + saida)
        msg('Dica: se pedir senha, configure um token ou chave SSH no GitHub.')
        return False
    msg('Enviado para o GitHub (ramo ' + branch + ').')
    return True


# ---------------------------------------------------------------- #
# render
# ---------------------------------------------------------------- #
def chamar_hook(hook):
    titulo('AVISANDO O RENDER')
    if not hook:
        msg('Sem gancho configurado. O Render deve deploiar sozinho apos o push.')
        msg('Se quiser disparar na hora, rode: python deploy_painel.py --config')
        return None
    try:
        req = Request(hook, data=b'', headers={'User-Agent': 'deploy-painel'})
        resp = urlopen(req, timeout=30)
        codigo = resp.getcode()
        resp.read()
        if 200 <= codigo < 300:
            msg('Deploy iniciado no Render.')
            return True
        msg('O Render respondeu ' + str(codigo) + '.')
        return False
    except HTTPError as e:
        msg('O Render respondeu com erro ' + str(e.code) + '.')
        return False
    except URLError as e:
        msg('Nao consegui falar com o Render: ' + str(getattr(e, 'reason', e)))
        return False
    except Exception as e:
        msg('Nao consegui falar com o Render: ' + str(e))
        return False


def baixar(url, tempo=45):
    req = Request(url, headers={'User-Agent': 'deploy-painel',
                                'Cache-Control': 'no-cache'})
    resp = urlopen(req, timeout=tempo)
    dados = resp.read()
    try:
        dados = dados.decode('utf-8', 'replace')
    except Exception:
        dados = str(dados)
    return resp.getcode(), dados


def conferir_site(site, esperar_patch, minutos=8):
    titulo('CONFERINDO O SITE PUBLICADO')
    if not site:
        msg('Sem endereco de site configurado.')
        return False

    msg('O plano gratuito do Render hiberna e leva de 30 a 60 segundos')
    msg('para acordar. Vou tentar por ate ' + str(minutos) + ' minutos.')
    limite = time.time() + minutos * 60
    tentativa = 0

    while time.time() < limite:
        tentativa += 1
        try:
            codigo, texto = baixar(site)
            if codigo == 200:
                if not esperar_patch:
                    msg('Site no ar (tentativa ' + str(tentativa) + ').')
                    return True
                if MARCA_INI in texto and MARCA_FIM in texto:
                    msg('Site no ar e com a versao nova do patch. Tudo certo.')
                    return True
                msg('  tentativa ' + str(tentativa) + ': site no ar, mas ainda')
                msg('  servindo a versao antiga; o deploy deve estar em andamento.')
            else:
                msg('  tentativa ' + str(tentativa) + ': resposta ' + str(codigo))
        except HTTPError as e:
            msg('  tentativa ' + str(tentativa) + ': erro ' + str(e.code) +
                ' (503 costuma ser o servico acordando)')
        except Exception as e:
            msg('  tentativa ' + str(tentativa) + ': ' + str(e)[:70])
        time.sleep(20)

    msg('')
    msg('Passou o tempo e o site ainda nao respondeu como esperado.')
    msg('Abra o painel do Render e veja o registro do ultimo deploy.')
    return False


# ---------------------------------------------------------------- #
# programa
# ---------------------------------------------------------------- #
def pegar_valor(nome, padrao=None):
    args = sys.argv
    if nome in args:
        i = args.index(nome)
        if i + 1 < len(args):
            return args[i + 1]
    return padrao


def main():
    titulo('DEPLOY DO PAINEL PORTICO')

    so_checar = '--so-checar' in sys.argv
    automatico = '--sim' in sys.argv
    sem_git = '--sem-git' in sys.argv
    sem_esperar = '--sem-esperar' in sys.argv

    arquivo = achar_arquivo(pegar_valor('--arquivo'))
    if not arquivo:
        return 1
    pasta = os.path.dirname(arquivo) or os.getcwd()
    msg('Painel: ' + os.path.basename(arquivo))

    cfg = ler_config(pasta)
    if '--config' in sys.argv:
        configurar(pasta)
        return 0
    if not cfg and not so_checar and not automatico:
        msg('')
        msg('Primeira vez por aqui. Vou pedir duas informacoes rapidas.')
        cfg = configurar(pasta)

    site = pegar_valor('--site', cfg.get('site') or SITE_PADRAO)
    hook = pegar_valor('--hook', cfg.get('hook') or '')
    branch = pegar_valor('--branch', cfg.get('branch') or '')
    mensagem = pegar_valor('--mensagem',
                           'Painel: publica versao com sincronizacao na nuvem (' +
                           datetime.datetime.now().strftime('%d/%m/%Y %H:%M') + ')')

    ok, texto = conferir_arquivo(arquivo)
    if not ok:
        return 1
    tem_patch = MARCA_INI in texto and MARCA_FIM in texto

    if so_checar:
        msg('')
        msg('Conferencia terminada. Nada foi publicado (--so-checar).')
        return 0

    guardar_copia(arquivo)
    limpar_copias_antigas(arquivo)

    enviou = None
    if sem_git:
        msg('')
        msg('Pulando o GitHub (--sem-git).')
    elif not tem_git(pasta):
        msg('')
        msg('Esta pasta nao e um repositorio git, entao nao ha o que enviar.')
        msg('Se o Render publica a partir do GitHub, coloque o painel no repositorio.')
    else:
        extras = [os.path.basename(arquivo)]
        proteger_copias(pasta)
        for a in ('painel_nuvem_v104.sql', 'patch104.py', '.gitignore'):
            if os.path.exists(os.path.join(pasta, a)):
                extras.append(a)
        enviou = enviar_para_github(pasta, extras, mensagem, branch, automatico)
        if enviou is False:
            return 1

    if enviou is None and not hook and not sem_git:
        msg('')
        msg('Nada novo foi enviado, entao nao vou disparar deploy.')
        if not perguntar('Quer conferir o site do jeito que esta?', automatico):
            return 0
    else:
        chamar_hook(hook)

    if sem_esperar:
        msg('')
        msg('Pronto. Nao vou esperar o site subir (--sem-esperar).')
        return 0

    bom = conferir_site(site, tem_patch)

    titulo('RESUMO')
    msg('Arquivo conferido e com copia de seguranca guardada.')
    if enviou:
        msg('Mudancas enviadas para o GitHub.')
    if hook:
        msg('Deploy disparado no Render.')
    if bom:
        msg('Site publicado e respondendo com a versao nova.')
        msg('')
        msg('Use o painel por: ' + site)
        if tem_patch:
            msg('Confira o aviso "Nuvem: salvo hh:mm" no canto de baixo a esquerda.')
    else:
        msg('O site ainda nao confirmou a versao nova; veja o Render.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        msg('')
        msg('Cancelado por voce.')
        sys.exit(1)
