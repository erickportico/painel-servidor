"""
Patch 22 — Bug 3: Conteúdo da sub-tab de pagamento não atualiza ao trocar

Problema:
  trocarSubTabPgtoNovo() alterna a exibição (display) dos painéis
  panelPgtoLancamentos e panelPgtoResumo, mas NÃO chama
  renderPagamento(). Isso significa que ao clicar nas sub-tabs
  "Lançamentos" ou "Resumo", o conteúdo exibido fica vazio ou
  desatualizado — só é renderizado na primeira vez ou após
  outras ações que disparem renderPagamento().

Solução:
  Adicionar chamada renderPagamento() ao final de
  trocarSubTabPgtoNovo(), logo após a linha que alterna o
  display do panelPgtoResumo (linha 7955). Como
  renderPagamento() (linha 8427) já verifica pgtoSubTab
  para decidir se renderiza lancamentos ou resumo,
  isso garante que o conteúdo certo seja desenhado.

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

    # ==========================================
    # FIX: Adicionar renderPagamento() ao final de trocarSubTabPgtoNovo
    # A função atual termina com:
    #   document.getElementById('panelPgtoResumo').style.display = tab === 'resumo' ? '' : 'none';
    #   }
    # Inserir a chamada ANTES do fechamento }
    # ==========================================

    old_block = """  document.getElementById('panelPgtoResumo').style.display = tab === 'resumo' ? '' : 'none';
}"""

    new_block = """  document.getElementById('panelPgtoResumo').style.display = tab === 'resumo' ? '' : 'none';
  renderPagamento();
}"""

    if old_block in text:
        text = text.replace(old_block, new_block, 1)
        print('✅ renderPagamento() adicionado ao final de trocarSubTabPgtoNovo')
    else:
        # Fallback: buscar pela linha individual
        target_line = "  document.getElementById('panelPgtoResumo').style.display = tab === 'resumo' ? '' : 'none';"
        if target_line in text:
            pos = text.find(target_line)
            # Encontrar o } que fecha a função (próxima linha)
            after = text[pos + len(target_line):]
            after_stripped = after.lstrip('\n')
            if after_stripped.startswith('}'):
                nl_count = len(after) - len(after.lstrip('\n'))
                insert_pos = pos + len(target_line) + nl_count
                text = text[:insert_pos] + '  renderPagamento();\n' + text[insert_pos:]
                print('✅ renderPagamento() adicionado (fallback) ao final de trocarSubTabPgtoNovo')
            else:
                print('❌ Não encontrou o fechamento } da função')
                return
        else:
            print('❌ Não encontrou o bloco alvo em trocarSubTabPgtoNovo')
            return

    if text == original:
        print('⚠️ NENHUMA mudança foi aplicada!')
        return

    write_file(FILE, text)

    # Verificação
    lines = text.replace('\r\n', '\n').split('\n')
    found_render = False
    for i, line in enumerate(lines):
        if 'function trocarSubTabPgtoNovo' in line:
            # Verificar as próximas linhas
            for j in range(i, min(i + 12, len(lines))):
                if 'renderPagamento()' in lines[j] and '}' in lines[j+1] if j+1 < len(lines) else False:
                    found_render = True
                    break
            break

    print('=== PATCH 22 APLICADO ===')
    print(f'Arquivo: {FILE}')
    print(f'  renderPagamento() presente antes do fechamento: {"✅" if found_render else "⚠️ verificar manualmente"}')

if __name__ == '__main__':
    apply_patch()