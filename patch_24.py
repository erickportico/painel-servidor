"""
Patch 24 — Feature 4: Botão de imprimir no Resumo de Pagamento

Problema:
  O painel de Resumo de Pagamento (panelPgtoResumo) não tem
  opção de impressão.

Solução (3 partes):

  A) Botão "🖨️ Imprimir" após os botões de navegação de mês.
  B) CSS print-pgto-resumo-mode para ocultar nav/tabs e
     exibir #panelPgtoResumo.
  C) Função JS imprimirPaginaPgtoResumo() seguindo o padrão
     de imprimirPaginaResumoLote.

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
    # A) Botão Imprimir no HTML do panelPgtoResumo
    # ==========================================

    old_nav = '''      <button onclick="mudarMesPgto(-1)">◀</button>
      <span id="pgtoMesAnoLabelResumo">Jan/2026</span>
      <button onclick="mudarMesPgto(1)">▶</button>
    </div>'''

    new_nav = '''      <button onclick="mudarMesPgto(-1)">◀</button>
      <span id="pgtoMesAnoLabelResumo">Jan/2026</span>
      <button onclick="mudarMesPgto(1)">▶</button>
      <button onclick="imprimirPaginaPgtoResumo()" style="margin-left:10px;padding:4px 12px;border:1px solid #cbd5e1;border-radius:6px;background:#1e3a5f;color:#fff;cursor:pointer;font-size:0.82rem;">🖨️ Imprimir</button>
    </div>'''

    if old_nav in text:
        text = text.replace(old_nav, new_nav, 1)
        changes.append('HTML: Botão Imprimir adicionado no panelPgtoResumo ✅')
    else:
        changes.append('❌ HTML: Não encontrou navegação de mês no panelPgtoResumo')

    # ==========================================
    # B) CSS print-pgto-resumo-mode
    # Inserir antes do fechamento </style>
    # ==========================================

    old_css_end = '''        body.print-resumo-mode #resumoLoteContainer { display: block !important; }
        body.print-resumo-mode #resumoLotePrintHeader { display: block !important; }
    </style>'''

    new_css_end = '''        body.print-resumo-mode #resumoLoteContainer { display: block !important; }
        body.print-resumo-mode #resumoLotePrintHeader { display: block !important; }
        body.print-pgto-resumo-mode .top-bar,
        body.print-pgto-resumo-mode nav,
        body.print-pgto-resumo-mode .settings-menu,
        body.print-pgto-resumo-mode #statusNuvem,
        body.print-pgto-resumo-mode .sub-tabs,
        body.print-pgto-resumo-mode #tab-itens,
        body.print-pgto-resumo-mode #tab-liberacao,
        body.print-pgto-resumo-mode #tab-medicoes,
        body.print-pgto-resumo-mode #tab-graficos,
        body.print-pgto-resumo-mode #tab-recebimento,
        body.print-pgto-resumo-mode #tab-cronograma,
        body.print-pgto-resumo-mode #tab-ctm,
        body.print-pgto-resumo-mode #tab-custo,
        body.print-pgto-resumo-mode #panelPgtoLancamentos { display: none !important; }
        body.print-pgto-resumo-mode #tab-pagamento { display: block !important; }
        body.print-pgto-resumo-mode #panelPgtoResumo { display: block !important; }
    </style>'''

    if old_css_end in text:
        text = text.replace(old_css_end, new_css_end, 1)
        changes.append('CSS: Regras print-pgto-resumo-mode adicionadas ✅')
    else:
        changes.append('❌ CSS: Não encontrou ponto de inserção para print-pgto-resumo-mode')

    # ==========================================
    # C) Função JS imprimirPaginaPgtoResumo()
    # ==========================================

    old_fechar = '''function fecharModalLancamento() {
  document.getElementById('modalLancamentoPgto').style.display = 'none';
}'''

    new_fechar = '''function fecharModalLancamento() {
  document.getElementById('modalLancamentoPgto').style.display = 'none';
}

function imprimirPaginaPgtoResumo() {
  document.body.classList.add('print-pgto-resumo-mode');
  imprimirPagina();
  document.body.classList.remove('print-pgto-resumo-mode');
}'''

    if old_fechar in text:
        text = text.replace(old_fechar, new_fechar, 1)
        changes.append('JS: Função imprimirPaginaPgtoResumo() criada ✅')
    else:
        changes.append('❌ JS: Não encontrou fecharModalLancamento para ponto de inserção')

    # ==========================================
    # Validação
    # ==========================================
    if text == original:
        print('⚠️ NENHUMA mudança foi aplicada!')
        return

    write_file(FILE, text)

    lf_text = text.replace('\r\n', '\n')
    has_print_btn = 'imprimirPaginaPgtoResumo()' in lf_text and '🖨️ Imprimir' in lf_text
    has_print_css = 'body.print-pgto-resumo-mode' in lf_text
    has_print_func = 'function imprimirPaginaPgtoResumo()' in lf_text

    print('=== PATCH 24 APLICADO ===')
    print(f'Arquivo: {FILE}')
    print(f'Mudanças aplicadas ({len(changes)}):')
    for i, c in enumerate(changes, 1):
        print(f'  {i}. {c}')
    print()
    print('Verificação pós-patch:')
    print(f'  Botão Imprimir no HTML: {"✅" if has_print_btn else "❌"}')
    print(f'  CSS print-pgto-resumo-mode: {"✅" if has_print_css else "❌"}')
    print(f'  Função imprimirPaginaPgtoResumo(): {"✅" if has_print_func else "❌"}')

if __name__ == '__main__':
    apply_patch()