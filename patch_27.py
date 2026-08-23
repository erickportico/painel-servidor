"""
Patch 27 — Feature 7: Exportar Especificações dos Itens em CSV

Problema:
  Não há opção de exportar as especificações dos itens
  (vidro, tipo, loc, dimensões, etc.) da obra atual.

Solução (2 partes):

  A) Botão "📋 Exportar Especificações" na aba Itens,
     após o botão "Adicionar Item".

  B) Função JS exportarEspecificacoes() que gera CSV
     com BOM UTF-8, seguindo o padrão de
     exportarMateriaisConsolidados.

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
    # A) Adicionar botão "Exportar Especificações" na aba Itens
    # Após o botão "Adicionar Item" (class="success")
    # ==========================================

    old_btn_area = '''                <button class="success" onclick="abrirModalItem()">Adicionar Item</button>
            </div>'''

    new_btn_area = '''                <button class="success" onclick="abrirModalItem()">Adicionar Item</button>
                <button onclick="exportarEspecificacoes()" style="padding:6px 14px;border:1px solid #cbd5e1;border-radius:6px;background:#2563eb;color:#fff;cursor:pointer;font-size:0.85rem;">📋 Exportar Especificações</button>
            </div>'''

    if old_btn_area in text:
        text = text.replace(old_btn_area, new_btn_area, 1)
        changes.append('HTML: Botão Exportar Especificações adicionado ✅')
    else:
        changes.append('❌ HTML: Não encontrou área de botões do tab-itens')

    # ==========================================
    # B) Criar função exportarEspecificacoes()
    # Inserir após exportarMateriaisConsolidados
    # ==========================================

    func_marker = 'function exportarMateriaisConsolidados'
    if func_marker in text:
        pos_func = text.find(func_marker)
        # Encontrar o fechamento da função (contando chaves)
        brace_count = 0
        pos = pos_func
        found_open = False
        while pos < len(text):
            if text[pos] == '{':
                brace_count += 1
                found_open = True
            elif text[pos] == '}':
                brace_count -= 1
                if found_open and brace_count == 0:
                    insert_pos = pos + 1
                    new_func_text = '''

    function exportarEspecificacoes() {
        const obra = getObraAtual();
        if (!obra || !obra.itens || !obra.itens.length) {
            alert('Nenhum item encontrado na obra atual.');
            return;
        }
        const obraNome = (obra.nome || obra.cliente || 'obra').replace(/[^a-zA-Z0-9À-ÿ]/g, '_');
        const hoje = new Date().toISOString().slice(0, 10);
        const fileName = 'especificacoes_' + obraNome + '_' + hoje + '.csv';

        // Cabeçalho CSV
        const header = 'Ref;Tipo;Loc;Vidro;Qtd;Larg;Alt;HasBottom;CtmProfile';
        const rows = obra.itens.map(item => {
            const ref = String(item.ref || '').replace(/;/g, ',');
            const tipo = String(item.tipo || '').replace(/;/g, ',');
            const loc = String(item.loc || item.local || '').replace(/;/g, ',');
            const vidro = String(item.vidro || '').replace(/;/g, ',');
            const qtd = item.qtd || item.quantidade || 0;
            const larg = item.larg || item.largura || 0;
            const alt = item.alt || item.altura || 0;
            const hasBottom = item.hasBottom ? 'Sim' : 'Não';
            const ctmProfile = String(item.ctmProfile || '').replace(/;/g, ',');
            return [ref, tipo, loc, vidro, qtd, larg, alt, hasBottom, ctmProfile].join(';');
        });

        const csvContent = '\uFEFF' + header + '\n' + rows.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }'''
                    text = text[:insert_pos] + new_func_text + text[insert_pos:]
                    changes.append('JS: Função exportarEspecificacoes() criada ✅')
                    break
            pos += 1
        else:
            changes.append('❌ JS: Não encontrou fechamento de exportarMateriaisConsolidados')
    else:
        changes.append('❌ JS: Não encontrou exportarMateriaisConsolidados para ponto de inserção')

    # ==========================================
    # Validação
    # ==========================================
    if text == original:
        print('⚠️ NENHUMA mudança foi aplicada!')
        return

    write_file(FILE, text)

    lf_text = text.replace('\r\n', '\n')
    has_export_btn = 'exportarEspecificacoes()' in lf_text and '📋 Exportar Especificações' in lf_text
    has_export_func = 'function exportarEspecificacoes()' in lf_text
    has_bom = '\\uFEFF' in lf_text
    has_csv_cols = 'Ref;Tipo;Loc;Vidro;Qtd;Larg;Alt;HasBottom;CtmProfile' in lf_text

    print('=== PATCH 27 APLICADO ===')
    print(f'Arquivo: {FILE}')
    print(f'Mudanças aplicadas ({len(changes)}):')
    for i, c in enumerate(changes, 1):
        print(f'  {i}. {c}')
    print()
    print('Verificação pós-patch:')
    print(f'  Botão Exportar Especificações: {"✅" if has_export_btn else "❌"}')
    print(f'  Função exportarEspecificacoes(): {"✅" if has_export_func else "❌"}')
    print(f'  BOM UTF-8 no CSV: {"✅" if has_bom else "❌"}')
    print(f'  Colunas CSV completas: {"✅" if has_csv_cols else "❌"}')

if __name__ == '__main__':
    apply_patch()