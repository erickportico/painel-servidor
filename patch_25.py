"""
Patch 25 — Feature 5: Persistir obra selecionada ao recarregar a página

Problema:
  trocarObra() salva db.obraAtualId no DB mas NÃO salva no
  localStorage. Ao recarregar, a aba é restaurada mas a
  obra volta para outra.

Solução (2 partes):

  A) Em trocarObra(), adicionar localStorage.setItem("esq_activeObra", id)
  B) Em DOMContentLoaded, ler "esq_activeObra" e chamar trocarObra()

Arquivo: C:/Users/OBRAS 8/Desktop/PAINEL SERVIDOR/index.html
"""

import os

FILE = r'C:/Users/OBRAS 8/Desktop/PAINEL SERVIDOR/index.html'

def read_file(path):
    with open(path, 'rb') as f:
        raw = f.read()
    text = raw.decode('utf-8', errors='replace')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return text

def write_file(path, text):
    text = text.replace('\n', '\r\n')
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(text)

def apply_patch():
    text = read_file(FILE)
    original = text
    changes = []

    # ==========================================
    # A) Em trocarObra(), adicionar localStorage.setItem
    # ==========================================

    old_trocar_obra = '''    function trocarObra(id) {
        db.obraAtualId = id;
        cronogramaInitialized = false;
        salvarDB();
    }'''

    new_trocar_obra = '''    function trocarObra(id) {
        db.obraAtualId = id;
        localStorage.setItem("esq_activeObra", id);
        cronogramaInitialized = false;
        salvarDB();
    }'''

    if old_trocar_obra in text:
        text = text.replace(old_trocar_obra, new_trocar_obra, 1)
        changes.append('trocarObra(): localStorage.setItem adicionado ✅')
    else:
        changes.append('❌ trocarObra(): Não encontrou para atualizar')

    # ==========================================
    # B) Em DOMContentLoaded, restaurar obra antes da aba
    # ==========================================

    old_dom = '''    window.addEventListener('DOMContentLoaded', () => {
        carregarTemaPreferido();
        var savedTab = localStorage.getItem('esq_activeTab') || 'itens';
        trocarAba(savedTab);'''

    new_dom = '''    window.addEventListener('DOMContentLoaded', () => {
        carregarTemaPreferido();
        var savedObra = localStorage.getItem('esq_activeObra');
        if (savedObra) trocarObra(savedObra);
        var savedTab = localStorage.getItem('esq_activeTab') || 'itens';
        trocarAba(savedTab);'''

    if old_dom in text:
        text = text.replace(old_dom, new_dom, 1)
        changes.append('DOMContentLoaded: restauração de obra via localStorage adicionada ✅')
    else:
        changes.append('❌ DOMContentLoaded: Não encontrou para atualizar')

    # ==========================================
    # Validação
    # ==========================================
    if text == original:
        print('⚠️ NENHUMA mudança foi aplicada!')
        return

    write_file(FILE, text)

    lf_text = text.replace('\r\n', '\n')
    set_count = lf_text.count('localStorage.setItem("esq_activeObra"')
    get_count = lf_text.count("localStorage.getItem('esq_activeObra')")

    print('=== PATCH 25 APLICADO ===')
    print(f'Arquivo: {FILE}')
    print(f'Mudanças aplicadas ({len(changes)}):')
    for i, c in enumerate(changes, 1):
        print(f'  {i}. {c}')
    print()
    print('Verificação pós-patch:')
    print(f'  localStorage.setItem("esq_activeObra") em trocarObra: {"✅" if set_count >= 1 else "❌"} ({set_count} ocorrência(s))')
    print(f'  localStorage.getItem("esq_activeObra") em DOMContentLoaded: {"✅" if get_count >= 1 else "❌"} ({get_count} ocorrência(s))')

if __name__ == '__main__':
    apply_patch()