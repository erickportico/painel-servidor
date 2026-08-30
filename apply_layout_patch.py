#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Patch de atualizacao de layout/responsividade - Painel de Producao e Instalacao

Uso:
    python3 apply_layout_patch.py index.html

Por padrao sobrescreve o arquivo informado (cria um .bak antes).
Use --output SAIDA.html para gravar em outro arquivo sem mexer no original.
"""
import argparse
import shutil
import sys

REPLACEMENTS = [
    (
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>Painel de Acompanhamento de Produção e Instalação</title>\n    <!-- Bibliotecas de Gráficos (Chart.js) -->\n    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>\n',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>Painel de Acompanhamento de Produção e Instalação</title>\n    <!-- Tipografia -->\n    <link rel="preconnect" href="https://fonts.googleapis.com">\n    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">\n    <!-- Bibliotecas de Gráficos (Chart.js) -->\n    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>\n',
    ),
    (
        '        /* VARIÁVEIS - TEMA CLARO */\n        :root {\n            --bg: #f8fafc;\n            --card-bg: #ffffff;\n            --text: #1e293b;\n            --text-light: #64748b;\n            --border: #cbd5e1;\n            --primary: #0f172a;\n            --primary-accent: #2563eb;\n',
        '        /* VARIÁVEIS - TEMA CLARO */\n        :root {\n            --bg: #f4f6fa;\n            --card-bg: #ffffff;\n            --text: #1c2536;\n            --text-light: #66748f;\n            --border: #dde3ec;\n            --primary: #0f172a;\n            --primary-accent: #2563eb;\n',
    ),
    (
        '            --table-header-base: #e2e8f0;\n            --table-row-completed: #f0fdf4;\n            --card-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);\n        }\n\n        /* VARIÁVEIS - TEMA ESCURO (SLATE DARK / PREMIUM) */\n        body.dark-mode {\n            --bg: #0f172a;\n            --card-bg: #1e293b;\n            --text: #f8fafc;\n            --text-light: #94a3b8;\n            --border: #334155;\n            --primary: #020617;\n            --primary-accent: #3b82f6;\n',
        "            --table-header-base: #e2e8f0;\n            --table-row-completed: #f0fdf4;\n            --card-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.06);\n            --radius-lg: 14px;\n            --radius: 10px;\n            --radius-sm: 7px;\n            --font-sans: 'Inter', 'Segoe UI', system-ui, sans-serif;\n            --font-mono: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;\n        }\n\n        /* VARIÁVEIS - TEMA ESCURO (SLATE DARK / PREMIUM) */\n        body.dark-mode {\n            --bg: #0b1220;\n            --card-bg: #161f32;\n            --text: #f1f5f9;\n            --text-light: #94a3b8;\n            --border: #2b3852;\n            --primary: #020617;\n            --primary-accent: #3b82f6;\n",
    ),
    (
        '            --med-header-dark: #84cc16;\n            --input-bg: #0f172a;\n            --table-header-base: #334155;\n            --table-row-completed: #064e3b22;\n            --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -2px rgba(0, 0, 0, 0.3);\n',
        '            --med-header-dark: #84cc16;\n            --input-bg: #0f172a;\n            --table-header-base: #263248;\n            --table-row-completed: #064e3b22;\n            --card-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -2px rgba(0, 0, 0, 0.3);\n',
    ),
    (
        "            margin: 0;\n            padding: 0;\n            font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;\n            transition: background-color 0.2s, border-color 0.2s, color 0.2s;\n        }\n",
        '            margin: 0;\n            padding: 0;\n            font-family: var(--font-sans);\n            transition: background-color 0.2s, border-color 0.2s, color 0.2s;\n        }\n',
    ),
    (
        '            color: var(--text);\n            padding: 15px;\n            line-height: 1.4;\n            overflow: auto;\n        }\n\n',
        '            color: var(--text);\n            padding: 15px;\n            line-height: 1.45;\n            overflow: auto;\n            -webkit-font-smoothing: antialiased;\n            text-rendering: optimizeLegibility;\n        }\n\n',
    ),
    (
        '            background: var(--primary);\n            color: white;\n            padding: 16px 20px;\n            border-radius: 12px;\n            display: flex;\n            flex-direction: column;\n',
        '            background: var(--primary);\n            color: white;\n            padding: 18px 22px;\n            border-radius: var(--radius-lg);\n            display: flex;\n            flex-direction: column;\n',
    ),
    (
        '            align-items: center;\n            gap: 20px;\n        }\n\n        .header-title-info {\n            flex: 1 1 0;\n        }\n\n        .header-title-info h1 {\n            font-size: 1.5rem;\n            font-weight: 800;\n            line-height: 1.1;\n            letter-spacing: -0.5px;\n        }\n\n        .header-title-info p {\n            font-size: 0.85rem;\n            opacity: 0.8;\n        }\n\n',
        '            align-items: center;\n            gap: 20px;\n            flex-wrap: wrap;\n        }\n\n        .header-title-info {\n            flex: 1 1 0;\n            min-width: 200px;\n        }\n\n        .header-title-info h1 {\n            font-size: 1.5rem;\n            font-weight: 800;\n            line-height: 1.15;\n            letter-spacing: -0.5px;\n        }\n\n        .header-title-info p {\n            font-size: 0.85rem;\n            opacity: 0.75;\n            margin-top: 2px;\n        }\n\n',
    ),
    (
        '            align-items: center;\n            flex-shrink: 0;\n        }\n\n',
        '            align-items: center;\n            flex-shrink: 0;\n            flex-wrap: wrap;\n        }\n\n',
    ),
    (
        '        button,\n        textarea {\n            padding: 6px 10px;\n            border-radius: 6px;\n            border: 1px solid var(--border);\n            font-size: 0.85rem;\n            background: var(--input-bg);\n            color: var(--text);\n        }\n\n',
        '        button,\n        textarea {\n            padding: 7px 11px;\n            border-radius: var(--radius-sm);\n            border: 1px solid var(--border);\n            font-size: 0.85rem;\n            background: var(--input-bg);\n            color: var(--text);\n        }\n\n        select:focus,\n        input:focus,\n        textarea:focus {\n            outline: none;\n            border-color: var(--primary-accent);\n            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);\n        }\n\n',
    ),
    (
        '            font-weight: 600;\n            cursor: pointer;\n            transition: 0.2s;\n        }\n\n        button:hover {\n            opacity: 0.9;\n            transform: translateY(-1px);\n        }\n\n',
        '            font-weight: 600;\n            cursor: pointer;\n            transition: 0.15s ease;\n            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);\n        }\n\n        button:hover {\n            opacity: 0.92;\n            transform: translateY(-1px);\n            box-shadow: 0 4px 8px rgba(15, 23, 42, 0.15);\n        }\n\n        button:active {\n            transform: translateY(0);\n        }\n\n',
    ),
    (
        '            background: var(--card-bg);\n            padding: 16px;\n            border-radius: 10px;\n            border: 1px solid var(--border);\n            box-shadow: var(--card-shadow);\n        }\n\n        .kpi-card .label {\n            font-size: 0.75rem;\n            color: var(--text-light);\n            text-transform: uppercase;\n            font-weight: 700;\n            letter-spacing: 0.5px;\n        }\n\n',
        '            background: var(--card-bg);\n            padding: 16px;\n            border-radius: var(--radius);\n            border: 1px solid var(--border);\n            box-shadow: var(--card-shadow);\n            transition: box-shadow 0.2s, transform 0.2s;\n        }\n\n        .kpi-card:hover {\n            box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);\n            transform: translateY(-1px);\n        }\n\n        .kpi-card .label {\n            font-size: 0.72rem;\n            color: var(--text-light);\n            text-transform: uppercase;\n            font-weight: 700;\n            letter-spacing: 0.6px;\n        }\n\n',
    ),
    (
        '            margin: 4px 0;\n            color: var(--text);\n        }\n\n        .tabs {\n            display: flex;\n            gap: 8px;\n            border-bottom: 2px solid var(--border);\n            margin-bottom: 16px;\n            flex-wrap: wrap;\n        }\n\n        .tab-btn {\n            background: none;\n            border: none;\n            color: var(--text-light);\n            padding: 10px 18px;\n            font-weight: 600;\n            cursor: pointer;\n            border-bottom: 3px solid transparent;\n            border-radius: 0;\n        }\n\n',
        '            margin: 4px 0;\n            color: var(--text);\n            letter-spacing: -0.3px;\n        }\n\n        .tabs {\n            display: flex;\n            gap: 4px;\n            border-bottom: 2px solid var(--border);\n            margin-bottom: 16px;\n            flex-wrap: wrap;\n            overflow-x: auto;\n            scrollbar-width: thin;\n        }\n\n        .tab-btn {\n            background: none;\n            border: none;\n            box-shadow: none;\n            color: var(--text-light);\n            padding: 10px 16px;\n            font-weight: 600;\n            cursor: pointer;\n            border-bottom: 3px solid transparent;\n            border-radius: 0;\n            white-space: nowrap;\n        }\n\n        .tab-btn:hover {\n            color: var(--text);\n            transform: none;\n            box-shadow: none;\n        }\n\n',
    ),
    (
        '        .card {\n            background: var(--card-bg);\n            border-radius: 12px;\n            border: 1px solid var(--border);\n            padding: 18px;\n',
        '        .card {\n            background: var(--card-bg);\n            border-radius: var(--radius-lg);\n            border: 1px solid var(--border);\n            padding: 18px;\n',
    ),
    (
        '            font-size: 0.85rem;\n            display: none;\n        }\n\n',
        '            font-size: 0.85rem;\n            display: none;\n        }\n\n        /* ===== RESPONSIVIDADE GERAL (cabeçalho, KPIs, abas, cards) ===== */\n        @media (max-width: 860px) {\n            body { padding: 10px; }\n\n            header { padding: 14px 16px; }\n\n            .header-title-container { gap: 12px; }\n\n            .header-title-info h1 { font-size: 1.2rem; }\n\n            .header-title-info p { font-size: 0.78rem; }\n\n            .header-badges-right { width: 100%; justify-content: flex-start; }\n\n            .project-selector { width: 100%; }\n\n            .project-selector select { flex: 1 1 auto; min-width: 0; }\n\n            .kpi-grid, .recebimento-kpi-grid {\n                grid-template-columns: repeat(auto-fit, minmax(135px, 1fr));\n                gap: 8px;\n            }\n\n            .kpi-card { padding: 12px; }\n\n            .kpi-card .value { font-size: 1.2rem; }\n\n            .card { padding: 14px; border-radius: var(--radius); }\n\n            .card-header { gap: 8px; }\n\n            .card-title { font-size: 0.95rem; }\n\n            .tabs { gap: 2px; }\n\n            .tab-btn { padding: 9px 12px; font-size: 0.85rem; }\n\n            .search-box { min-width: 0; width: 100%; }\n\n            table { font-size: 0.75rem; }\n\n            .modal { padding: 16px; max-width: 100%; }\n        }\n\n        @media (max-width: 520px) {\n            .header-title-info h1 { font-size: 1.05rem; }\n\n            .kpi-grid, .recebimento-kpi-grid {\n                grid-template-columns: repeat(auto-fit, minmax(115px, 1fr));\n            }\n\n            .config-grid { grid-template-columns: 1fr; }\n        }\n\n',
    ),
]


def apply_patch(content: str) -> str:
    applied = 0
    for old, new in REPLACEMENTS:
        count = content.count(old)
        if count == 0:
            print(f"[AVISO] Trecho nao encontrado (pode ja ter sido aplicado antes):\n{old[:80]!r}...", file=sys.stderr)
            continue
        if count > 1:
            print(f"[AVISO] Trecho encontrado {count}x, aplicando apenas na primeira ocorrencia:\n{old[:80]!r}...", file=sys.stderr)
        content = content.replace(old, new, 1)
        applied += 1
    print(f"{applied}/{len(REPLACEMENTS)} blocos de mudanca aplicados.")
    return content


def main():
    parser = argparse.ArgumentParser(description="Aplica o patch de layout no index.html")
    parser.add_argument("arquivo", help="Caminho para o index.html original")
    parser.add_argument("--output", "-o", help="Arquivo de saida (padrao: sobrescreve o original, criando .bak)")
    args = parser.parse_args()

    with open(args.arquivo, encoding="utf-8", newline=None) as f:
        content = f.read()

    new_content = apply_patch(content)

    if args.output:
        destino = args.output
    else:
        destino = args.arquivo
        backup = args.arquivo + ".bak"
        shutil.copyfile(args.arquivo, backup)
        print(f"Backup salvo em: {backup}")

    with open(destino, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Arquivo atualizado gravado em: {destino}")


if __name__ == "__main__":
    main()