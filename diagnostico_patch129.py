# -*- coding: utf-8 -*-
# =====================================================================
# DIAGNOSTICO DO PATCH 129
#   Confere, no seu proprio arquivo, se o PATCH 129 esta aplicado e
#   inteiro, e se as pecas do painel que ele usa continuam no lugar.
# =====================================================================
#
# O QUE MUDA
#   Nada. Este script SO LE o seu index.html e escreve um relatorio.
#   Ele nunca altera, apaga ou move o seu arquivo.
#
# COMO USAR
#   1. Deixe este arquivo na mesma pasta do seu index.html.
#   2. Rode:  python diagnostico_patch129.py
#   3. Leia a lista na tela. Cada linha vem com OK, ATENCAO ou FALHA.
#
# O QUE OLHAR DEPOIS
#   * Se tudo der OK, siga a lista de conferencia no navegador que o
#     script imprime no final (leva menos de dois minutos).
#   * Se aparecer FALHA de "patch nao encontrado", rode o
#     patch129_nao_interromper.py antes.
#   * Fica um relatorio salvo em diagnostico_patch129.txt na mesma pasta.
#
# SEGURANCA
#   * Somente leitura: nao mexe no painel nem nos seus dados.
#   * Nao envia nada para a internet.
# =====================================================================

import io
import os
import sys

ALVO = 'index.html'
MARCA = 'PATCH129_NAO_INTERROMPER'

linhas = []
contas = {'ok': 0, 'atencao': 0, 'falha': 0}


def nota(estado, texto, detalhe=''):
    contas[estado] = contas[estado] + 1
    rotulo = {'ok': 'OK     ', 'atencao': 'ATENCAO', 'falha': 'FALHA  '}[estado]
    linha = rotulo + ' | ' + texto
    if detalhe:
        linha = linha + '\n        ' + detalhe
    linhas.append(linha)
    print(linha)


def achar_arquivo():
    aqui = os.path.dirname(os.path.abspath(__file__))
    for pasta in [aqui, os.getcwd()]:
        caminho = os.path.join(pasta, ALVO)
        if os.path.isfile(caminho):
            return caminho
    return None


def equilibrado(trecho):
    """Confere se chaves, parenteses e colchetes fecham, ignorando texto
    entre aspas e comentarios."""
    pares = {'}': '{', ')': '(', ']': '['}
    pilha = []
    i = 0
    tam = len(trecho)
    while i < tam:
        c = trecho[i]
        prox = trecho[i + 1] if i + 1 < tam else ''
        if c == '/' and prox == '*':
            fim = trecho.find('*/', i + 2)
            i = tam if fim < 0 else fim + 2
            continue
        if c == '/' and prox == '/':
            fim = trecho.find('\n', i)
            i = tam if fim < 0 else fim + 1
            continue
        if c in ('"', "'", '`'):
            i = i + 1
            while i < tam and trecho[i] != c:
                i = i + 2 if trecho[i] == '\\' else i + 1
            i = i + 1
            continue
        if c in '{([':
            pilha.append(c)
        elif c in pares:
            if not pilha or pilha.pop() != pares[c]:
                return False
        i = i + 1
    return not pilha


PECAS_PATCH = [
    ('selo de aviso "atualizacao em espera"', "'p129Selo'"),
    ('botao de destravar a tela', "'p129Solta'"),
    ('botao de ver todos os meses no Centro de Custos', "'p129Mes'"),
    ('fila que segura a atualizacao automatica', 'function agendar'),
    ('protecao das funcoes de desenho da tela', 'function proteger'),
    ('teste de verdade contra o servidor', 'function testarServidor'),
    ('limpeza de tela travada', 'function overlayPreso'),
    ('liberacao da rolagem', 'function soltar'),
    ('mes vigente no Centro de Custos', 'function mesVigente'),
    ('ajuste automatico do campo de mes', 'function ajustarMesCusto'),
    ('comando de conferencia no console', 'window.P129'),
]

ANCORAS = [
    ('campo de mes do Centro de Custos', 'custoFilterMes'),
    ('aba do Centro de Custos', 'tab-custo'),
    ('troca de menu do painel', 'function trocarAba'),
    ('desenho do Centro de Custos', 'renderCustoDashboard'),
    ('aviso de internet do patch 117', 'p117Net'),
]

OPCIONAIS = [
    ('vigia da nuvem do patch 125', 'p125Vigiar'),
    ('tabela sem pisca do patch 126', 'PATCH126'),
    ('login no servidor do patch 128', 'PATCH128'),
]


def main():
    caminho = achar_arquivo()
    if not caminho:
        print('FALHA   | Nao achei o arquivo ' + ALVO + ' nesta pasta.')
        print('          Coloque este script na mesma pasta do painel e rode de novo.')
        return 2

    with io.open(caminho, 'r', encoding='utf-8', errors='ignore') as f:
        texto = f.read()

    print('')
    print('DIAGNOSTICO DO PATCH 129 - ' + os.path.basename(caminho))
    print('tamanho do arquivo: ' + str(len(texto)) + ' caracteres')
    print('-' * 66)

    # 1. o patch esta aplicado?
    vezes = texto.count(MARCA)
    if vezes == 0:
        nota('falha', 'PATCH 129 nao esta aplicado neste arquivo.',
             'Rode o patch129_nao_interromper.py nesta pasta e repita o diagnostico.')
        resumo()
        return 1
    if vezes > 2:
        nota('atencao', 'A marca do PATCH 129 aparece ' + str(vezes) + ' vezes.',
             'Pode ter sido aplicado duas vezes. Volte a copia de seguranca mais antiga.')
    else:
        nota('ok', 'PATCH 129 aplicado uma vez, sem duplicar.')

    inicio = texto.find(MARCA)
    fim_body = texto.rfind('</body>')
    if fim_body > 0 and inicio < fim_body:
        nota('ok', 'O bloco do patch esta antes do fim da pagina.')
    else:
        nota('falha', 'O bloco do patch esta fora do lugar (depois do fim da pagina).',
             'Volte a copia de seguranca e aplique o patch novamente.')

    bloco = texto[inicio:fim_body if fim_body > inicio else len(texto)]

    # 2. o bloco esta inteiro?
    if bloco.count('<script') == bloco.count('</script>') and bloco.count('<script') >= 1:
        nota('ok', 'O bloco de codigo abre e fecha corretamente.')
    else:
        nota('falha', 'O bloco de codigo do patch parece cortado.',
             'abre=' + str(bloco.count('<script')) + ' fecha=' + str(bloco.count('</script>')))

    if equilibrado(bloco):
        nota('ok', 'Chaves e parenteses do patch estao fechando.')
    else:
        nota('atencao', 'A contagem de chaves/parenteses nao fechou.',
             'Pode ser so um sinal de divisao no codigo. Confira o console do navegador.')

    if '\\' in bloco.replace('\\n', '') and '\\/' in bloco:
        nota('atencao', 'Achei barras invertidas no bloco.',
             'Elas costumam quebrar o codigo quando o arquivo e reescrito.')
    else:
        nota('ok', 'Nenhuma barra invertida estranha no bloco.')

    # 3. as pecas do patch estao todas la?
    faltando = []
    for nome, chave in PECAS_PATCH:
        if chave in bloco:
            nota('ok', 'Peca presente: ' + nome + '.')
        else:
            faltando.append(nome)
            nota('falha', 'Peca faltando: ' + nome + '.')

    # 4. as pecas do painel que o patch usa continuam no lugar?
    for nome, chave in ANCORAS:
        antes = texto[:inicio]
        if chave in antes:
            nota('ok', 'O painel ainda tem: ' + nome + '.')
        elif chave in texto:
            nota('atencao', 'Achei ' + nome + ' apenas dentro do proprio patch.',
                 'Confira se voce nao renomeou essa parte do painel.')
        else:
            nota('falha', 'Nao achei no painel: ' + nome + '.',
                 'O patch 129 depende disso para funcionar por completo.')

    for nome, chave in OPCIONAIS:
        if chave in texto:
            nota('ok', 'Conversa com o ' + nome + ' esta possivel.')
        else:
            nota('atencao', 'Nao achei o ' + nome + ' (nao impede o patch 129 de rodar).')

    # 5. o patch entrou depois dos outros?
    posteriores = []
    for chave in ['PATCH125', 'PATCH126', 'PATCH127', 'PATCH128']:
        pos = texto.rfind(chave)
        if pos > inicio:
            posteriores.append(chave)
    if posteriores:
        nota('atencao', 'Ha patch mais antigo escrito depois do 129: ' + ', '.join(posteriores) + '.',
             'O 129 deve ser o ultimo para proteger as funcoes dos anteriores.')
    else:
        nota('ok', 'O PATCH 129 e o ultimo bloco da pagina.')

    # 6. copia de seguranca
    pasta = os.path.dirname(os.path.abspath(caminho))
    copias = [n for n in os.listdir(pasta) if n.startswith('index.html.antes_patch129_')]
    if copias:
        nota('ok', 'Existe copia de seguranca de antes do patch (' + str(len(copias)) + ').',
             'mais recente: ' + sorted(copias)[-1])
    else:
        nota('atencao', 'Nao achei copia de seguranca de antes do patch 129 nesta pasta.')

    resumo()
    conferencia_no_navegador()
    salvar(pasta)
    return 1 if contas['falha'] else 0


def resumo():
    print('-' * 66)
    fim = ('RESULTADO: ' + str(contas['ok']) + ' ok, ' + str(contas['atencao'])
           + ' atencao, ' + str(contas['falha']) + ' falha(s)')
    print(fim)
    linhas.append('')
    linhas.append(fim)
    if contas['falha']:
        print('Ha falhas: aplique o patch novamente ou volte a copia de seguranca.')
    elif contas['atencao']:
        print('Sem falhas. Veja os pontos de atencao acima.')
    else:
        print('Tudo em ordem no arquivo. Agora confira no navegador.')


TESTES_NO_NAVEGADOR = [
    ('Cadastro nao e interrompido',
     'Abra um cadastro, escreva algo em um campo e fique parado 1 minuto.',
     'O texto continua no campo e aparece o selo "Atualizacao em espera" no canto.'),
    ('A atualizacao acontece depois',
     'Clique fora do campo e espere alguns segundos.',
     'O selo desaparece e a lista/tela se atualiza sozinha.'),
    ('Suas acoes valem na hora',
     'Com um campo em foco, mude um filtro ou clique em um botao.',
     'A tela responde imediatamente, sem esperar.'),
    ('Centro de Custos no mes atual',
     'Entre no Centro de Custos.',
     'O campo MES ja vem com o mes de hoje e os numeros aparecem preenchidos.'),
    ('Ver todos os meses',
     'Clique no botao "Ver todos os meses" e depois no "Voltar ao mes atual".',
     'O filtro limpa e volta, sem recarregar a pagina.'),
    ('Aviso de internet',
     'Com internet funcionando, olhe o canto da tela por 30 segundos.',
     'O aviso vermelho de sem internet nao aparece (ou desaparece sozinho).'),
    ('Aviso de internet ao cair',
     'Desligue o wi-fi por 1 minuto.',
     'O aviso aparece; ao religar, ele sai sozinho em pouco tempo.'),
    ('Trocar de menu nao trava',
     'Troque de menu 10 vezes seguidas, rapido.',
     'A tela continua respondendo e a pagina rola normalmente.'),
    ('Destravar na mao',
     'Se algo travar, aperte Esc ou use o botao "Destravar tela".',
     'A tela volta a responder sem precisar recarregar.'),
]


def conferencia_no_navegador():
    bloco = []
    bloco.append('')
    bloco.append('CONFERENCIA NO NAVEGADOR (abra o painel e faca na ordem)')
    bloco.append('Antes de comecar, aperte Ctrl+F5 para carregar a versao nova.')
    bloco.append('')
    n = 0
    for titulo, faca, esperado in TESTES_NO_NAVEGADOR:
        n = n + 1
        bloco.append(str(n) + '. ' + titulo)
        bloco.append('   faca:    ' + faca)
        bloco.append('   esperado: ' + esperado)
        bloco.append('   [ ] passou   [ ] nao passou')
    bloco.append('')
    bloco.append('COMANDO DE CONFERENCIA (console do navegador, tecla F12)')
    bloco.append('   P129.conferir()')
    bloco.append('   Ele mostra: se o painel entende que voce esta no meio de um')
    bloco.append('   cadastro, o que esta na fila de atualizacao, se o servidor')
    bloco.append('   respondeu no ultimo teste, se a tela esta travada e qual mes')
    bloco.append('   o Centro de Custos esta usando.')
    bloco.append('')
    bloco.append('   P129.testarServidor()   testa a nuvem agora e ajusta o aviso')
    bloco.append('   P129.soltar()           destrava a tela na hora')
    bloco.append('')
    bloco.append('Se "P129 is not defined" aparecer no console, o patch nao esta')
    bloco.append('carregando: verifique se ha erro em vermelho antes dele.')
    for l in bloco:
        print(l)
        linhas.append(l)


def salvar(pasta):
    destino = os.path.join(pasta, 'diagnostico_patch129.txt')
    try:
        with io.open(destino, 'w', encoding='utf-8') as f:
            f.write('DIAGNOSTICO DO PATCH 129\n')
            f.write('\n'.join(linhas))
            f.write('\n')
        print('')
        print('Relatorio salvo em ' + os.path.basename(destino))
    except Exception as e:
        print('')
        print('Nao consegui salvar o relatorio: ' + str(e))


if __name__ == '__main__':
    sys.exit(main())
