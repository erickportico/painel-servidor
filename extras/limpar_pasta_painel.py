# -*- coding: utf-8 -*-
"""
Limpeza da pasta do Painel Portico.

O que faz: organiza a pasta sem APAGAR nada. Tudo que sai do lugar vai para
subpastas, entao da sempre para voltar atras:

  backups/antigos/      copias antigas do painel (fica com as 5 mais novas na pasta)
  patches/aplicados/    scripts de patch que ja foram usados
  temporarios/          lixo do Python e do Windows (__pycache__, .tmp, .log, ...)

NUNCA toca em: index.html, .git, arquivos .sql e .js, INICIAR_SERVIDOR.bat,
servidor_painel.py, deploy_painel.py, o patch mais recente e este proprio script.

Uso:
    python limpar_pasta_painel.py              (mostra o plano e pergunta antes)
    python limpar_pasta_painel.py --so-listar   (so mostra, nao mexe em nada)
    python limpar_pasta_painel.py --sim         (faz sem perguntar)
    python limpar_pasta_painel.py --manter 3    (quantas copias recentes deixar)
"""

from __future__ import print_function

import io
import os
import re
import shutil
import sys
import time

MANTER_PADRAO = 5

PASTA_BACKUPS = os.path.join("backups", "antigos")
PASTA_PATCHES = os.path.join("patches", "aplicados")
PASTA_TEMP = "temporarios"

# nomes que nunca sao movidos
INTOCAVEIS = set([
    "index.html",
    "iniciar_servidor.bat",
    "servidor_painel.py",
    "deploy_painel.py",
    "deploy_painel.cfg",
    "limpar_pasta_painel.py",
    "relatorio_admin.py",
])

PASTAS_INTOCAVEIS = set([".git", "git", "backups", "patches", "temporarios",
                         "painel-servidor", "node_modules"])

# copias de seguranca do painel
RE_BACKUP = re.compile(r"^index\.html\.(bak|antes)[^/\\]*$", re.I)
RE_BACKUP2 = re.compile(r"^index.*\.(bak|old|backup)\d*$", re.I)

# scripts de patch
RE_PATCH = re.compile(r"^patch[_-]?\d*.*\.py$", re.I)

# temporarios
EXT_TEMP = (".tmp", ".temp", ".log", ".pyc", ".pyo", ".bak~")
NOMES_TEMP = ("__pycache__", ".ds_store", "thumbs.db", "desktop.ini")


def titulo(txt):
    print("")
    print("=" * 62)
    print("  " + txt)
    print("=" * 62)


def tamanho_legivel(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024.0:
            return "%.1f %s" % (n, u)
        n = n / 1024.0
    return "%.1f TB" % n


def tamanho_de(caminho):
    if os.path.isfile(caminho):
        try:
            return os.path.getsize(caminho)
        except Exception:
            return 0
    total = 0
    for raiz, _dirs, arqs in os.walk(caminho):
        for a in arqs:
            try:
                total += os.path.getsize(os.path.join(raiz, a))
            except Exception:
                pass
    return total


def data_de(caminho):
    try:
        return os.path.getmtime(caminho)
    except Exception:
        return 0


def eh_temp(nome, caminho):
    baixo = nome.lower()
    if baixo in NOMES_TEMP:
        return True
    for e in EXT_TEMP:
        if baixo.endswith(e):
            return True
    return False


def levantar(manter):
    """Monta o plano: lista de (origem, pasta_destino, motivo)."""
    plano = []
    backups = []

    for nome in sorted(os.listdir(".")):
        caminho = os.path.join(".", nome)
        baixo = nome.lower()

        if baixo in INTOCAVEIS:
            continue
        if os.path.isdir(caminho) and baixo in PASTAS_INTOCAVEIS:
            continue

        if eh_temp(nome, caminho):
            plano.append((nome, PASTA_TEMP, "arquivo temporario"))
            continue

        if RE_BACKUP.match(nome) or RE_BACKUP2.match(nome):
            backups.append(nome)
            continue

        if os.path.isfile(caminho) and RE_PATCH.match(nome):
            plano.append((nome, PASTA_PATCHES, "patch ja aplicado"))
            continue

    # das copias de seguranca, guarda as mais recentes na pasta principal
    backups.sort(key=lambda n: data_de(n), reverse=True)
    ficam = backups[:manter]
    vao = backups[manter:]
    for nome in vao:
        plano.append((nome, PASTA_BACKUPS, "copia antiga do painel"))

    # o patch mais recente fica a mao
    patches = [p for p in plano if p[1] == PASTA_PATCHES]
    if patches:
        patches.sort(key=lambda p: data_de(p[0]), reverse=True)
        recente = patches[0][0]
        plano = [p for p in plano if p[0] != recente]

    return plano, ficam


def mover(nome, destino):
    if not os.path.isdir(destino):
        os.makedirs(destino)
    alvo = os.path.join(destino, nome)
    if os.path.exists(alvo):
        base, ext = os.path.splitext(nome)
        alvo = os.path.join(destino, base + "_" + time.strftime("%H%M%S") + ext)
    shutil.move(nome, alvo)
    return alvo


def escrever_leia_me():
    texto = (
        u"Organizacao da pasta do Painel Portico\n"
        u"======================================\n\n"
        u"Nada foi apagado. Os arquivos foram apenas guardados aqui:\n\n"
        u"  backups/antigos/    copias antigas do painel (index.html.bak_...)\n"
        u"  patches/aplicados/  scripts de patch que ja foram usados\n"
        u"  temporarios/        lixo do Python e do Windows\n\n"
        u"Se precisar de algum de volta, e so arrastar para a pasta principal.\n"
        u"Quando tiver certeza de que nao precisa mais, pode apagar estas\n"
        u"pastas a mao, sem risco para o painel.\n\n"
        u"Na pasta principal ficam sempre:\n"
        u"  index.html            o painel\n"
        u"  INICIAR_SERVIDOR.bat  liga o painel no seu computador\n"
        u"  servidor_painel.py    o servidor local\n"
        u"  deploy_painel.py      publica no GitHub e no Render\n"
        u"  arquivos .sql e .js   usados pelo Supabase\n"
        u"  o patch mais recente\n"
    )
    with io.open("LEIA-ME_organizacao.txt", "w", encoding="utf-8") as f:
        f.write(texto)


def main():
    argv = sys.argv[1:]
    so_listar = "--so-listar" in argv
    sem_perguntar = "--sim" in argv
    manter = MANTER_PADRAO
    if "--manter" in argv:
        try:
            manter = max(0, int(argv[argv.index("--manter") + 1]))
        except Exception:
            print("Valor invalido em --manter; vou usar %d." % MANTER_PADRAO)

    titulo("LIMPEZA DA PASTA DO PAINEL")

    if not os.path.isfile("index.html"):
        print("Nao achei o index.html nesta pasta.")
        print("Coloque este script na pasta do painel e rode de novo.")
        return 1

    plano, ficam = levantar(manter)

    if not plano:
        print("A pasta ja esta organizada. Nada para mover.")
        return 0

    grupos = {}
    for nome, destino, motivo in plano:
        grupos.setdefault(destino, []).append((nome, motivo))

    total = 0
    for destino in sorted(grupos.keys()):
        print("")
        print("Vao para " + destino.replace(os.sep, "/") + ":")
        for nome, motivo in grupos[destino]:
            t = tamanho_de(nome)
            total += t
            print("  - %-46s %10s  (%s)" % (nome[:46], tamanho_legivel(t), motivo))

    print("")
    print("Total que sai da pasta principal: " + tamanho_legivel(total))
    if ficam:
        print("Copias de seguranca que continuam a mao (%d mais novas):" % len(ficam))
        for n in ficam:
            print("  - " + n)
    print("")
    print("Importante: NADA sera apagado. Tudo vai para subpastas.")

    if so_listar:
        print("")
        print("Foi so uma previa (--so-listar). Nada foi movido.")
        return 0

    if not sem_perguntar:
        try:
            entrada = raw_input("Pode organizar assim? [s/n] ")  # noqa
        except NameError:
            entrada = input("Pode organizar assim? [s/n] ")
        if entrada.strip().lower() not in ("s", "sim", "y", "yes"):
            print("Cancelado. Nada foi movido.")
            return 1

    titulo("ORGANIZANDO")
    movidos = 0
    for nome, destino, _motivo in plano:
        try:
            alvo = mover(nome, destino)
            movidos += 1
            print("  ok: " + nome + "  ->  " + alvo.replace(os.sep, "/"))
        except Exception as e:
            print("  nao consegui mover " + nome + ": " + str(e))

    escrever_leia_me()

    titulo("PRONTO")
    print("%d itens guardados. Liberou %s da pasta principal." %
          (movidos, tamanho_legivel(total)))
    print("Criei o arquivo LEIA-ME_organizacao.txt explicando onde ficou cada coisa.")
    print("")
    print("O painel continua funcionando igual: index.html nao foi tocado.")
    print("Para conferir: python deploy_painel.py --so-checar")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("")
        print("Cancelado. Nada foi movido.")
        sys.exit(1)
