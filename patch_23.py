"""
Patch 23 — Feature 2: Selects de Profissionais e Ajudantes no modal de edição de lançamento

Problema:
  O modal de edição (modalLancamentoPgto) só permite editar
  Instalação M², Material, Taxa Profissional e Taxa Ajudante.
  Não é possível alterar quais profissionais e ajudantes estão
  alocados no lançamento.

Solução (4 partes):

  A) Inserir 2 novos campos multi-select no HTML do modal
     (editLancProfissionais e editLancAjudantes) após a div
     editLancTaxaAjud, antes do fechamento do grid.

  B) Criar função popularSelectsEditLanc() após
     popularSelectsPgto().

  C) Atualizar editarLancamentoPgto() para chamar
     popularSelectsEditLanc() e pré-selecionar atuais.

  D) Atualizar salvarEdicaoLancamento() para ler
     selectedOptions dos 2 novos selects e recalcular
     numProf/numAjud.

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
    # A) Inserir selects multi-select no HTML do modal
    # Após a div editLancTaxaAjud, antes do fechamento do grid </div>
    # ==========================================

    old_html = '''      <div>
        <label style="font-size:0.82rem;font-weight:600;">Taxa Ajudante R$/m²</label>
        <input type="number" id="editLancTaxaAjud" step="0.01" min="0" style="width:100%;padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;box-sizing:border-box;">
      </div>
    </div>'''

    new_html = '''      <div>
        <label style="font-size:0.82rem;font-weight:600;">Taxa Ajudante R$/m²</label>
        <input type="number" id="editLancTaxaAjud" step="0.01" min="0" style="width:100%;padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;box-sizing:border-box;">
      </div>
      <div>
        <label style="font-size:0.82rem;font-weight:600;">Profissionais</label>
        <select id="editLancProfissionais" multiple style="width:100%;min-height:60px;padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:0.85rem;box-sizing:border-box;"></select>
      </div>
      <div>
        <label style="font-size:0.82rem;font-weight:600;">Ajudantes</label>
        <select id="editLancAjudantes" multiple style="width:100%;min-height:60px;padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:0.85rem;box-sizing:border-box;"></select>
      </div>
    </div>'''

    if old_html in text:
        text = text.replace(old_html, new_html, 1)
        changes.append('HTML: Selects editLancProfissionais e editLancAjudantes inseridos no modal ✅')
    else:
        changes.append('❌ HTML: Não encontrou bloco alvo no modal')

    # ==========================================
    # B) Criar função popularSelectsEditLanc() após popularSelectsPgto()
    # ==========================================

    insert_after = '  // Populate material select based on currently selected obra\n  popularMaterialPgto();\n}'

    new_func = '''  // Populate material select based on currently selected obra
  popularMaterialPgto();
}

function popularSelectsEditLanc() {
  const selProf = document.getElementById('editLancProfissionais');
  selProf.innerHTML = '';
  getProfissionaisAll().forEach(c => {
    selProf.innerHTML += `<option value="${escaparHTML(c.id)}">${escaparHTML(c.nome)}</option>`;
  });
  const selAjud = document.getElementById('editLancAjudantes');
  selAjud.innerHTML = '';
  getAjudantesAll().forEach(c => {
    selAjud.innerHTML += `<option value="${escaparHTML(c.id)}">${escaparHTML(c.nome)}</option>`;
  });
}'''

    if insert_after in text:
        text = text.replace(insert_after, new_func, 1)
        changes.append('JS: Função popularSelectsEditLanc() criada ✅')
    else:
        changes.append('❌ JS: Não encontrou ponto de inserção para popularSelectsEditLanc()')

    # ==========================================
    # C) Atualizar editarLancamentoPgto()
    # ==========================================

    old_edit_func = '''function editarLancamentoPgto(lancId, obraId) {
  const obra = db.obras.find(o => o.id === obraId);
  if (!obra) return;
  const lanc = (obra.lancamentosProducao || []).find(l => l.id === lancId);
  if (!lanc) return;
  document.getElementById('editLancId').value = lanc.id;
  document.getElementById('editLancObraId').value = obra.id;
  document.getElementById('editLancInstalacaoM2').value = lanc.instalacaoM2;
  document.getElementById('editLancMaterial').value = lanc.material;
  document.getElementById('editLancTaxaProf').value = lanc.taxaProf;
  document.getElementById('editLancTaxaAjud').value = lanc.taxaAjud;
  document.getElementById('modalLancamentoPgto').style.display = 'flex';
}'''

    new_edit_func = '''function editarLancamentoPgto(lancId, obraId) {
  const obra = db.obras.find(o => o.id === obraId);
  if (!obra) return;
  const lanc = (obra.lancamentosProducao || []).find(l => l.id === lancId);
  if (!lanc) return;
  document.getElementById('editLancId').value = lanc.id;
  document.getElementById('editLancObraId').value = obra.id;
  document.getElementById('editLancInstalacaoM2').value = lanc.instalacaoM2;
  document.getElementById('editLancMaterial').value = lanc.material;
  document.getElementById('editLancTaxaProf').value = lanc.taxaProf;
  document.getElementById('editLancTaxaAjud').value = lanc.taxaAjud;
  popularSelectsEditLanc();
  // Pré-selecionar profissionais
  const selProf = document.getElementById('editLancProfissionais');
  Array.from(selProf.options).forEach(opt => {
    opt.selected = (lanc.profissionais || []).includes(opt.value);
  });
  // Pré-selecionar ajudantes
  const selAjud = document.getElementById('editLancAjudantes');
  Array.from(selAjud.options).forEach(opt => {
    opt.selected = (lanc.ajudantes || []).includes(opt.value);
  });
  document.getElementById('modalLancamentoPgto').style.display = 'flex';
}'''

    if old_edit_func in text:
        text = text.replace(old_edit_func, new_edit_func, 1)
        changes.append('JS: editarLancamentoPgto() atualizado com popularSelectsEditLanc e pré-seleção ✅')
    else:
        changes.append('❌ JS: Não encontrou editarLancamentoPgto() para atualizar')

    # ==========================================
    # D) Atualizar salvarEdicaoLancamento()
    # ==========================================

    old_save_func = '''function salvarEdicaoLancamento() {
  const lancId = document.getElementById('editLancId').value;
  const obraId = document.getElementById('editLancObraId').value;
  const obra = db.obras.find(o => o.id === obraId);
  if (!obra) return;
  const lanc = (obra.lancamentosProducao || []).find(l => l.id === lancId);
  if (!lanc) return;
  lanc.instalacaoM2 = parseFloat(document.getElementById('editLancInstalacaoM2').value) || 0;
  lanc.material = document.getElementById('editLancMaterial').value.trim();
  lanc.taxaProf = parseFloat(document.getElementById('editLancTaxaProf').value) || 6;
  lanc.taxaAjud = parseFloat(document.getElementById('editLancTaxaAjud').value) || 4;
  const numProf = (lanc.profissionais || []).length || 1;
  const numAjud = (lanc.ajudantes || []).length || 1;
  lanc.valorProf = lanc.instalacaoM2 * lanc.taxaProf / numProf;
  lanc.valorAjud = lanc.instalacaoM2 * lanc.taxaAjud / numAjud;
  salvarDB();
  fecharModalLancamento();
  renderPagamento();
}'''

    new_save_func = '''function salvarEdicaoLancamento() {
  const lancId = document.getElementById('editLancId').value;
  const obraId = document.getElementById('editLancObraId').value;
  const obra = db.obras.find(o => o.id === obraId);
  if (!obra) return;
  const lanc = (obra.lancamentosProducao || []).find(l => l.id === lancId);
  if (!lanc) return;
  lanc.instalacaoM2 = parseFloat(document.getElementById('editLancInstalacaoM2').value) || 0;
  lanc.material = document.getElementById('editLancMaterial').value.trim();
  lanc.taxaProf = parseFloat(document.getElementById('editLancTaxaProf').value) || 6;
  lanc.taxaAjud = parseFloat(document.getElementById('editLancTaxaAjud').value) || 4;
  // Ler profissionais e ajudantes dos selects
  lanc.profissionais = Array.from(document.getElementById('editLancProfissionais').selectedOptions).map(o => o.value);
  lanc.ajudantes = Array.from(document.getElementById('editLancAjudantes').selectedOptions).map(o => o.value);
  const numProf = lanc.profissionais.length || 1;
  const numAjud = lanc.ajudantes.length || 1;
  lanc.valorProf = lanc.instalacaoM2 * lanc.taxaProf / numProf;
  lanc.valorAjud = lanc.instalacaoM2 * lanc.taxaAjud / numAjud;
  salvarDB();
  fecharModalLancamento();
  renderPagamento();
}'''

    if old_save_func in text:
        text = text.replace(old_save_func, new_save_func, 1)
        changes.append('JS: salvarEdicaoLancamento() atualizado para ler selects e recalcular ✅')
    else:
        changes.append('❌ JS: Não encontrou salvarEdicaoLancamento() para atualizar')

    # ==========================================
    # Validação
    # ==========================================
    if text == original:
        print('⚠️ NENHUMA mudança foi aplicada!')
        return

    write_file(FILE, text)

    lf_text = text.replace('\r\n', '\n')
    has_edit_prof = 'id="editLancProfissionais"' in lf_text
    has_edit_ajud = 'id="editLancAjudantes"' in lf_text
    has_popular_edit = 'function popularSelectsEditLanc' in lf_text
    has_preselect = 'opt.selected = (lanc.profissionais || []).includes(opt.value)' in lf_text
    has_read_selects = 'lanc.profissionais = Array.from(document.getElementById' in lf_text

    print('=== PATCH 23 APLICADO ===')
    print(f'Arquivo: {FILE}')
    print(f'Mudanças aplicadas ({len(changes)}):')
    for i, c in enumerate(changes, 1):
        print(f'  {i}. {c}')
    print()
    print('Verificação pós-patch:')
    print(f'  Select editLancProfissionais no HTML: {"✅" if has_edit_prof else "❌"}')
    print(f'  Select editLancAjudantes no HTML: {"✅" if has_edit_ajud else "❌"}')
    print(f'  Função popularSelectsEditLanc(): {"✅" if has_popular_edit else "❌"}')
    print(f'  Pré-seleção em editarLancamentoPgto: {"✅" if has_preselect else "❌"}')
    print(f'  Leitura de selects em salvarEdicaoLancamento: {"✅" if has_read_selects else "❌"}')

if __name__ == '__main__':
    apply_patch()