"""
Patch 26 — Feature 6: Custos de Produção no Centro de Custos

Problema:
  O Centro de Custos só exibe custos cadastrados manualmente
  (centrosCusto). Os lançamentos de produção (lancamentosProducao)
  têm valores de prof/ajud que NÃO aparecem como custos.

Solução (2 partes):

  A) Modificar getCustosFiltered() para também iterar
     db.obras[].lancamentosProducao e criar entradas virtuais
     de custo com flag _producao:true.

  B) Modificar renderCustoTable() para NÃO exibir botões
     de editar/excluir em entradas com _producao === true.

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
    # A) Modificar getCustosFiltered() para incluir custos de produção
    # ==========================================

    old_get_custos = (
        'function getCustosFiltered(){\n'
        '  var obraId = document.getElementById("custoFilterObra").value;\n'
        '  var regiao = document.getElementById("custoFilterRegiao").value.trim().toLowerCase();\n'
        '  var mes = document.getElementById("custoFilterMes").value;\n'
        '  var result = [];\n'
        '  db.obras.forEach(function(o){\n'
        '    (o.centrosCusto || []).forEach(function(c){\n'
        '      if(obraId && c.obraId !== obraId) return;\n'
        '      if(regiao && (!c.regiao || c.regiao.toLowerCase().indexOf(regiao) === -1)) return;\n'
        '      if(mes){\n'
        '        var d = c.data || "";\n'
        '        var cMes = d.substring(0, 7);\n'
        '        if(cMes !== mes) return;\n'
        '      }\n'
        '      result.push(c);\n'
        '    });\n'
        '  });\n'
        '  return result;\n'
        '}'
    )

    new_get_custos = (
        'function getCustosFiltered(){\n'
        '  var obraId = document.getElementById("custoFilterObra").value;\n'
        '  var regiao = document.getElementById("custoFilterRegiao").value.trim().toLowerCase();\n'
        '  var mes = document.getElementById("custoFilterMes").value;\n'
        '  var result = [];\n'
        '  db.obras.forEach(function(o){\n'
        '    (o.centrosCusto || []).forEach(function(c){\n'
        '      if(obraId && c.obraId !== obraId) return;\n'
        '      if(regiao && (!c.regiao || c.regiao.toLowerCase().indexOf(regiao) === -1)) return;\n'
        '      if(mes){\n'
        '        var d = c.data || "";\n'
        '        var cMes = d.substring(0, 7);\n'
        '        if(cMes !== mes) return;\n'
        '      }\n'
        '      result.push(c);\n'
        '    });\n'
        '    // Custos virtuais de produção\n'
        '    (o.lancamentosProducao || []).forEach(function(lanc){\n'
        '      var obraNome = o.nome || o.cliente || "Obra s/n";\n'
        '      var cProd = {\n'
        '        id: "prod_" + lanc.id,\n'
        '        obraId: o.id,\n'
        '        data: lanc.data || new Date().toISOString().slice(0,10),\n'
        '        categoria: "Produção",\n'
        '        descricao: obraNome + " - " + (lanc.material || "Sem material"),\n'
        '        valor: (lanc.valorProf || 0) + (lanc.valorAjud || 0),\n'
        '        regiao: "Geral",\n'
        '        _producao: true\n'
        '      };\n'
        '      if(obraId && cProd.obraId !== obraId) return;\n'
        '      if(regiao && (!cProd.regiao || cProd.regiao.toLowerCase().indexOf(regiao) === -1)) return;\n'
        '      if(mes){\n'
        '        var d2 = cProd.data || "";\n'
        '        var cMes2 = d2.substring(0, 7);\n'
        '        if(cMes2 !== mes) return;\n'
        '      }\n'
        '      result.push(cProd);\n'
        '    });\n'
        '  });\n'
        '  return result;\n'
        '}'
    )

    if old_get_custos in text:
        text = text.replace(old_get_custos, new_get_custos, 1)
        changes.append('getCustosFiltered(): custos virtuais de produção adicionados')
    else:
        changes.append('getCustosFiltered(): NAO encontrou função para atualizar')

    # ==========================================
    # B) Modificar renderCustoTable() - ocultar botões editar/excluir
    #    para entradas de produção (_producao === true)
    #
    #    Busca a linha que contém editarCusto + excluirCusto + btn-icon-sm
    #    dentro de um html += com lanc-actions, e substitui por
    #    versão condicional que mostra "Produção" se c._producao
    # ==========================================

    lines = text.split('\n')
    replaced = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if (
            'html +=' in stripped
            and 'lanc-actions' in stripped
            and 'editarCusto' in stripped
            and 'excluirCusto' in stripped
            and 'btn-icon-sm' in stripped
            and 'c.id' in stripped
        ):
            indent = line[:len(line) - len(line.lstrip())]
            # Nova linha: se c._producao, mostrar label; senão botões normais
            # Usamos formato raw com chr(39) para aspas simples dentro de JS
            SQ = chr(39)   # single quote
            DQ = chr(34)   # double quote
            BS = chr(92)   # backslash
            # editarCusto(\' + c.id + \')  <- JS needs backslash before single-quote
            BTN_EDIT = f"'<button class={DQ}btn-icon-sm{DQ} onclick={DQ}editarCusto({BS}{SQ}' + c.id + '{BS}{SQ}){DQ} title={DQ}Editar{DQ}>✏️</button>'"
            BTN_DEL  = f"'<button class={DQ}btn-icon-sm{DQ} onclick={DQ}excluirCusto({BS}{SQ}' + c.id + '{BS}{SQ}){DQ} title={DQ}Excluir{DQ}>🗑️</button>'"
            PROD_LABEL = f"'<span style={DQ}font-size:0.75rem;color:#94a3b8;{DQ}>Produção</span>'"
            NEW_TD = f"'<td class={DQ}lanc-actions{DQ}>' + (c._producao ? {PROD_LABEL} : {BTN_EDIT} + {BTN_DEL}) + '</td></tr>'"
            new_line = indent + 'html += ' + NEW_TD + ';'
            lines[i] = new_line
            text = '\n'.join(lines)
            replaced = True
            changes.append(f'renderCustoTable(): botões ocultos para produção (linha {i+1})')
            break

    if not replaced:
        changes.append('renderCustoTable(): NAO encontrou botões editar/excluir')

    # ==========================================
    # Validação
    # ==========================================
    if text == original:
        print('NENHUMA mudança foi aplicada!')
        return

    write_file(FILE, text)

    lf_text = text.replace('\r\n', '\n')
    has_prod_custos = '_producao: true' in lf_text
    has_virtual_push = '"prod_" + lanc.id' in lf_text
    has_conditional_btns = 'c._producao' in lf_text

    print('=== PATCH 26 APLICADO ===')
    print(f'Arquivo: {FILE}')
    print(f'Mudanças aplicadas ({len(changes)}):')
    for i, c in enumerate(changes, 1):
        print(f'  {i}. {c}')
    print()
    print('Verificação pós-patch:')
    print(f'  Custos virtuais de produção em getCustosFiltered: {"OK" if has_prod_custos and has_virtual_push else "FALHOU"}')
    print(f'  Flag _producao: true criada: {"OK" if has_prod_custos else "FALHOU"}')
    print(f'  Botões editar/excluir condicionais: {"OK" if has_conditional_btns else "FALHOU"}')

if __name__ == '__main__':
    apply_patch()