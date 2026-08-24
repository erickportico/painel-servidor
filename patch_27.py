#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PATCH 27 — PAINEL SERVIDOR
  A) Adicionar botao 📋 Duplicar Item ao lado de "Adicionar Item" (line ~2520)
  B) Adicionar funcao duplicarItem() apos exportarMateriaisConsolidados (ends ~5706)
  C) Adicionar botao 📋 Duplicar na tabela de itens (actions-cell, ao lado de excluirItem)
  D) Adicionar funcao duplicarItemFromTable() apos excluirItem (ends ~6933)

Idempotente: segura para re-executar. Se alteracoes ja presentes, pula.
CRLF → LF na leitura; LF → CRLF na escrita.
Target: C:/Users/OBRAS 8/Desktop/PAINEL SERVIDOR/index.html
"""

import os, re, sys

FILE = r'C:/Users/OBRAS 8/Desktop/PAINEL SERVIDOR/index.html'

# ─── Helpers ───────────────────────────────────────────────────────

def read_file(path):
    with open(path, 'rb') as f:
        raw = f.read()
    text = raw.decode('utf-8-sig', errors='replace')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    if not text.endswith('\n'):
        text += '\n'
    return text

def write_file(path, text):
    text = text.replace('\n', '\r\n')
    with open(path, 'wb') as f:
        f.write(text.encode('utf-8', errors='replace'))

def find_function_end(lines, start_idx, max_lines=80):
    """Brace-counting: find closing brace of function starting at start_idx."""
    brace = 0
    for j in range(start_idx, min(start_idx + max_lines, len(lines))):
        brace += lines[j].count('{') - lines[j].count('}')
        if brace <= 0 and j > start_idx:
            return j
    return None

# ─── Main ───────────────────────────────────────────────────────────

def apply_patch():
    if not os.path.exists(FILE):
        print(f"ERRO: Arquivo nao encontrado: {FILE}")
        return

    text = read_file(FILE)
    lines = text.split('\n')
    changes = []

    # ──────────────────────────────────────────────────────────────
    # IDEMPOTENCY CHECK — skip entire patch if all markers found
    # ──────────────────────────────────────────────────────────────
    body = text
    has_dup_item_btn_top  = 'duplicarItem()' in body and '📋 Duplicar Item' in body
    has_dup_item_func     = 'function duplicarItem()' in body or 'window.duplicarItem' in body
    has_dup_item_btn_row  = 'duplicarItemFromTable(' in body and '📋' in body
    has_dup_item_tbl_func = 'function duplicarItemFromTable(' in body or 'window.duplicarItemFromTable' in body

    if has_dup_item_btn_top and has_dup_item_func and has_dup_item_btn_row and has_dup_item_tbl_func:
        print("=== PATCH 27: Ja aplicado (idempotente) ===")
        print("Todas as alteracoes ja estao presentes. Nada a fazer.")
        return

    # ──────────────────────────────────────────────────────────────
    # SECTION A — Add 📋 Duplicar Item button next to Adicionar Item
    # ──────────────────────────────────────────────────────────────
    # Find the "Adicionar Item" button line, insert duplicar button after it

    btn_top_inserted = False

    # Strategy 1: find line with abrirModalItem and Adicionar Item
    for i, line in enumerate(lines):
        if 'abrirModalItem()' in line and 'Adicionar Item' in line and 'onclick' in line:
            if 'duplicarItem()' in line:
                btn_top_inserted = True
                changes.append("Botao 📋 Duplicar Item (topo): ja presente")
                break
            # Extract indentation
            indent = len(line) - len(line.lstrip())
            spaces = ' ' * indent
            # Get the Adicionar Item button HTML
            # Find the <button start
            btn_start = line.find('<button')
            if btn_start == -1:
                continue
            btn_end = line.find('</button>', btn_start)
            if btn_end == -1:
                continue
            btn_end += len('</button>')
            add_btn_html = line[btn_start:btn_end]
            # Create Duplicar Item button
            dup_btn_html = add_btn_html.replace('abrirModalItem()', 'duplicarItem()').replace('Adicionar Item', '📋 Duplicar Item').replace('success', 'secondary')
            # Insert the new button after the Adicionar Item button
            new_line = line[:btn_end] + '\n' + spaces + dup_btn_html + line[btn_end:]
            lines[i] = new_line
            btn_top_inserted = True
            changes.append("Botao 📋 Duplicar Item (topo): inserido")
            break

    if not btn_top_inserted:
        # Fallback: regex search for the button
        for i, line in enumerate(lines):
            if 'Adicionar Item' in line and 'button' in line.lower():
                if 'duplicarItem()' not in line:
                    indent = len(line) - len(line.lstrip())
                    spaces = ' ' * indent
                    btn_match = re.search(r'<button[^>]*onclick="abrirModalItem\(\)"[^>]*>Adicionar Item</button>', line)
                    if btn_match:
                        dup_html = btn_match.group(0).replace('abrirModalItem()', 'duplicarItem()').replace('Adicionar Item', '\U0001f4cb Duplicar Item').replace('success', 'secondary')
                        lines[i] = line[:btn_match.end()] + '\n' + spaces + dup_html + line[btn_match.end():]
                        btn_top_inserted = True
                        changes.append("Botao 📋 Duplicar Item (topo): inserido (fallback)")
                        break

    if not btn_top_inserted:
        changes.append("[FALHA] Botao 📋 Duplicar Item (topo): nao encontrado")

    # Re-read lines after section A (since we may have inserted a newline)
    # Actually the newline is embedded in the same line index, so let's split properly
    text = '\n'.join(lines)
    lines = text.split('\n')

    # ──────────────────────────────────────────────────────────────
    # SECTION B — Add duplicarItem() function after exportarMateriaisConsolidados
    # ──────────────────────────────────────────────────────────────
    # This function opens the modal pre-filled with a copy of the
    # currently selected item, so the user can adjust before saving.

    func_dup_inserted = False

    body_check = '\n'.join(lines)
    if 'function duplicarItem()' in body_check or 'window.duplicarItem' in body_check:
        func_dup_inserted = True
        changes.append("Funcao duplicarItem(): ja presente")
    else:
        # Find exportarMateriaisConsolidados function end
        export_start = None
        for i, line in enumerate(lines):
            if 'function exportarMateriaisConsolidados' in line or 'exportarMateriaisConsolidados = function' in line:
                export_start = i
                break

        if export_start is not None:
            export_end = find_function_end(lines, export_start, max_lines=60)
            if export_end is not None:
                closing_line = lines[export_end]
                indent = len(closing_line) - len(closing_line.lstrip())
                base_indent = ' ' * indent
                inner_indent = base_indent + '    '
                inner2 = base_indent + '        '

                dup_func = [
                    '',
                    base_indent + 'function duplicarItem() {',
                    inner_indent + 'const obra = getObraAtual();',
                    inner_indent + 'if (!obra.itens || !obra.itens.length) {',
                    inner2 + 'alert("Nenhum item para duplicar.");',
                    inner2 + 'return;',
                    inner_indent + '}',
                    inner_indent + '// Find last selected/edited item, or prompt user',
                    inner_indent + 'const tbody = document.querySelector("#tabelaItens tbody");',
                    inner_indent + 'if (!tbody) { alert("Tabela de itens nao encontrada."); return; }',
                    inner_indent + '// Get selected item from active row or first item',
                    inner_indent + 'const activeRow = tbody.querySelector("tr.selected, tr.highlighted, tr.active");',
                    inner_indent + 'let itemId = null;',
                    inner_indent + 'if (activeRow) {',
                    inner2 + 'const inp = activeRow.querySelector("input[onchange*=editarItem]");',
                    inner2 + 'if (inp) {',
                    inner2 + '  const m = inp.getAttribute("onchange").match(/editarItem\\((\\d[^,]*)/);',
                    inner2 + '  if (m) itemId = Number(m[1]);',
                    inner2 + '}',
                    inner_indent + '}',
                    inner_indent + 'if (!itemId && obra.itens.length > 0) {',
                    inner2 + 'if (!confirm("Nenhum item selecionado. Duplicar o ultimo item da lista?")) return;',
                    inner2 + 'itemId = obra.itens[obra.itens.length - 1].id;',
                    inner_indent + '}',
                    inner_indent + 'const item = obra.itens.find(i => i.id === itemId);',
                    inner_indent + 'if (!item) { alert("Item nao encontrado."); return; }',
                    inner_indent + '// Pre-fill modal with item data',
                    inner_indent + 'document.getElementById("itemRef").value = item.ref || "";',
                    inner_indent + 'document.getElementById("itemTipo").value = item.tipo || "";',
                    inner_indent + 'document.getElementById("itemLoc").value = item.loc || "";',
                    inner_indent + 'document.getElementById("itemVidro").value = item.vidro || "";',
                    inner_indent + 'document.getElementById("itemQtd").value = item.qtd || 1;',
                    inner_indent + 'document.getElementById("itemLarg").value = item.larg || 1.0;',
                    inner_indent + 'document.getElementById("itemAlt").value = item.alt || 1.0;',
                    inner_indent + 'document.getElementById("modalItem").style.display = "flex";',
                    base_indent + '}',
                ]

                for offset, new_line in enumerate(dup_func):
                    lines.insert(export_end + 1 + offset, new_line)

                func_dup_inserted = True
                changes.append("Funcao duplicarItem(): inserida apos exportarMateriaisConsolidados")
            else:
                changes.append("[FALHA] Funcao duplicarItem(): nao encontrado fim de exportarMateriaisConsolidados")
        else:
            changes.append("[FALHA] Funcao duplicarItem(): funcao exportarMateriaisConsolidados nao encontrada")

    # Re-join and re-split after insertions
    text = '\n'.join(lines)
    lines = text.split('\n')

    # ──────────────────────────────────────────────────────────────
    # SECTION C — Add 📋 Duplicar button in item table row (actions-cell)
    # ──────────────────────────────────────────────────────────────
    # Find the line with excluirItem button in actions-cell,
    # insert a duplicar button before the excluir button.

    btn_row_inserted = False

    for i, line in enumerate(lines):
        if 'excluirItem(' in line and 'actions-cell' in line and 'danger' in line:
            if 'duplicarItemFromTable' in line:
                btn_row_inserted = True
                changes.append("Botao 📋 Duplicar (tabela itens): ja presente")
                break
            # Find the excluirItem button
            excl_pos = line.find('excluirItem(')
            if excl_pos == -1:
                continue
            btn_tag_start = line.rfind('<button', 0, excl_pos)
            if btn_tag_start == -1:
                continue
            btn_end = line.find('</button>', excl_pos)
            if btn_end == -1:
                continue
            btn_end += len('</button>')
            excl_btn_html = line[btn_tag_start:btn_end]
            # Create duplicar button
            dup_btn_html = excl_btn_html.replace('excluirItem(', 'duplicarItemFromTable(').replace('danger', 'warning').replace('\u274c', '\U0001f4cb').replace('Excluir', 'Duplicar')
            # Insert before excluirItem button
            new_line = line[:btn_tag_start] + dup_btn_html + excl_btn_html + line[btn_end:]
            lines[i] = new_line
            btn_row_inserted = True
            changes.append("Botao 📋 Duplicar (tabela itens): inserido")
            break

    if not btn_row_inserted:
        # Fallback: regex for excluirItem in action cell
        for i, line in enumerate(lines):
            if 'excluirItem(' in line and 'button' in line.lower() and 'onclick' in line:
                if 'duplicarItemFromTable' not in line:
                    excl_match = re.search(r'<button[^>]*onclick="excluirItem\([^)]+\)"[^>]*>[^<]*</button>', line)
                    if excl_match:
                        dup_html = excl_match.group(0).replace('excluirItem(', 'duplicarItemFromTable(').replace('danger', 'warning').replace('\u274c', '\U0001f4cb')
                        lines[i] = line[:excl_match.start()] + dup_html + excl_match.group(0) + line[excl_match.end():]
                        btn_row_inserted = True
                        changes.append("Botao 📋 Duplicar (tabela itens): inserido (fallback)")
                        break

    if not btn_row_inserted:
        changes.append("[FALHA] Botao 📋 Duplicar (tabela itens): nao encontrado")

    # Re-join/re-split after section C
    text = '\n'.join(lines)
    lines = text.split('\n')

    # ──────────────────────────────────────────────────────────────
    # SECTION D — Add duplicarItemFromTable() function after excluirItem
    # ──────────────────────────────────────────────────────────────

    func_tbl_inserted = False

    body_check = '\n'.join(lines)
    if 'function duplicarItemFromTable(' in body_check or 'window.duplicarItemFromTable' in body_check:
        func_tbl_inserted = True
        changes.append("Funcao duplicarItemFromTable(): ja presente")
    else:
        # Find excluirItem function
        excluir_item_start = None
        for i, line in enumerate(lines):
            if 'function excluirItem(' in line or 'window.excluirItem' in line:
                excluir_item_start = i
                break

        if excluir_item_start is not None:
            excluir_item_end = find_function_end(lines, excluir_item_start, max_lines=40)
            if excluir_item_end is not None:
                closing_line = lines[excluir_item_end]
                indent = len(closing_line) - len(closing_line.lstrip())
                base_indent = ' ' * indent
                inner_indent = base_indent + '    '
                inner2 = base_indent + '        '

                dup_tbl_func = [
                    '',
                    base_indent + 'function duplicarItemFromTable(id) {',
                    inner_indent + 'const obra = getObraAtual();',
                    inner_indent + 'if (!obra.itens) obra.itens = [];',
                    inner_indent + 'const item = obra.itens.find(i => i.id === id);',
                    inner_indent + 'if (!item) { alert("Item nao encontrado."); return; }',
                    inner_indent + 'if (!confirm("Duplicar este item?")) return;',
                    inner_indent + 'const clone = {',
                    inner2 + 'id: Date.now() + Math.random(),',
                    inner2 + 'ref: item.ref || "",',
                    inner2 + 'tipo: item.tipo || "",',
                    inner2 + 'loc: item.loc || "",',
                    inner2 + 'vidro: item.vidro || "",',
                    inner2 + 'qtd: item.qtd || 1,',
                    inner2 + 'larg: item.larg || 1.0,',
                    inner2 + 'alt: item.alt || 1.0,',
                    inner2 + 'fem: 0,',
                    inner2 + 'fabricado: 0,',
                    inner2 + 'instalado: 0,',
                    inner2 + 'dataInstalacao: null,',
                    inner2 + 'historicoMedicoes: {},',
                    inner2 + 'hasBottom: item.hasBottom !== undefined ? item.hasBottom : true,',
                    inner2 + 'ctmProfile: item.ctmProfile || "largo"',
                    inner_indent + '};',
                    inner_indent + 'obra.itens.push(clone);',
                    inner_indent + 'salvarDB();',
                    inner_indent + '// Re-render the active tab',
                    inner_indent + 'const obraAtual = getObraAtual();',
                    inner_indent + 'renderTabelaLiberacao(obraAtual);',
                    inner_indent + 'renderTabelaFabricacao(obraAtual);',
                    inner_indent + 'renderTabelaInstalacao(obraAtual);',
                    base_indent + '}',
                ]

                for offset, new_line in enumerate(dup_tbl_func):
                    lines.insert(excluir_item_end + 1 + offset, new_line)

                func_tbl_inserted = True
                changes.append("Funcao duplicarItemFromTable(): inserida apos excluirItem")
            else:
                changes.append("[FALHA] Funcao duplicarItemFromTable(): nao encontrado fim de excluirItem")
        else:
            changes.append("[FALHA] Funcao duplicarItemFromTable(): funcao excluirItem nao encontrada")

    # ──────────────────────────────────────────────────────────────
    # RECONSTRUCT & WRITE
    # ──────────────────────────────────────────────────────────────
    text = '\n'.join(lines)
    if text.endswith('\n\n'):
        text = text.rstrip('\n') + '\n'

    write_file(FILE, text)

    # ──────────────────────────────────────────────────────────────
    # VERIFICATION
    # ──────────────────────────────────────────────────────────────
    print("=== PATCH 27 APLICADO ===")
    print(f"Arquivo: {FILE}")
    print(f"Mudancas aplicadas ({len(changes)}):")
    for idx, c in enumerate(changes, 1):
        print(f"  {idx}. {c}")

    verify = read_file(FILE)
    vlines = verify.split('\n')
    checks = []

    has_dup_top = any('duplicarItem()' in l and 'Duplicar Item' in l for l in vlines)
    checks.append(("Botao 📋 Duplicar Item (topo)", "OK" if has_dup_top else "FALHA"))

    has_dup_func = 'function duplicarItem()' in verify
    checks.append(("Funcao duplicarItem()", "OK" if has_dup_func else "FALHA"))

    has_dup_row_btn = any('duplicarItemFromTable(' in l for l in vlines)
    checks.append(("Botao 📋 Duplicar (tabela)", "OK" if has_dup_row_btn else "FALHA"))

    has_dup_tbl_func = 'function duplicarItemFromTable(' in verify
    checks.append(("Funcao duplicarItemFromTable()", "OK" if has_dup_tbl_func else "FALHA"))

    has_excluir_item = any('excluirItem(' in l and 'danger' in l for l in vlines)
    checks.append(("Botao excluirItem preservado", "OK" if has_excluir_item else "FALHA"))

    print("\nVerificacao pos-patch:")
    for label, status in checks:
        print(f"  {label}: {status}")


if __name__ == '__main__':
    apply_patch()
