from pathlib import Path

ALLOWED_ENTITIES = {"LINE", "TEXT"}

def pairs(text):
    values = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if values and values[-1] == "":
        values.pop()
    if len(values) % 2:
        raise ValueError(f"quantidade ímpar de linhas: {len(values)}")
    return list(zip(values[0::2], values[1::2]))

def validate(path):
    ps = pairs(Path(path).read_text(encoding="utf-8"))
    if not ps or ps[0] != ("0", "SECTION"):
        raise ValueError("DXF não começa com SECTION")
    if ("0", "EOF") != ps[-1]:
        raise ValueError("DXF não termina com EOF")
    sections = [value for code, value in ps if code == "2" and value in {"HEADER", "ENTITIES"}]
    if sections[:2] != ["HEADER", "ENTITIES"]:
        raise ValueError(f"seções inválidas: {sections}")
    entities = []
    in_entities = False
    for code, value in ps:
        if (code, value) == ("2", "ENTITIES"):
            in_entities = True
            continue
        if in_entities and code == "0" and value == "ENDSEC":
            in_entities = False
            continue
        if in_entities and code == "0":
            entities.append(value)
    invalid = sorted(set(entities) - ALLOWED_ENTITIES)
    if invalid:
        raise ValueError(f"entidades incompatíveis: {invalid}")
    if not entities:
        raise ValueError("nenhuma entidade gráfica encontrada")
    if any(code == "0" and value == "COMMENT" for code, value in ps):
        raise ValueError("entidade COMMENT encontrada")
    return len(ps), len(entities)

if __name__ == "__main__":
    import sys
    for filename in sys.argv[1:]:
        total, entities = validate(filename)
        print(f"OK {filename}: pares={total}, entidades={entities}")
    if len(sys.argv) == 1:
        print("Uso: python validar_dxf_r12_ctm.py arquivo.dxf [...]")
        raise SystemExit(2)

# O navegador gera o DXF; este script valida arquivos exportados pelo usuário.
