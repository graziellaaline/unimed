# -*- coding: utf-8 -*-
"""
Grade (tabela) com filtro estilo Excel no cabeçalho de cada coluna.

Substitui os `selectbox`/`multiselect` que ficavam acima das tabelas. O filtro
é um componente customizado do AG Grid — a edição Community não traz o
"Set Filter" (lista de checkboxes) porque ele é recurso Enterprise/pago, então
o painel é implementado aqui em JavaScript: ordenar A→Z / Z→A, buscar,
"Selecionar tudo", lista de checkboxes e botões Limpar / OK.

Filtro e ordenação rodam no navegador — a página não recarrega a cada clique.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode, JsCode

# ── Filtro customizado ───────────────────────────────────────────────────────
# Atenção ao editar: o `JsCode` do st_aggrid remove comentários e junta tudo em
# UMA linha antes de mandar pro navegador. Por isso: nada de comentário JS, e
# todo comando precisa terminar em ";" (não dá pra confiar no ASI).
_FILTRO_JS = JsCode("""
class {
    init(p) {
        this.p = p;
        this.aplicado = null;
        this.pend = new Set();
        this.valores = [];
        this.visiveis = [];
        this.busca = '';
        this.hidePopup = null;
        this.eGui = document.createElement('div');
        this.eGui.className = 'uni-filtro';
        this.eGui.innerHTML = '<div class="uni-ordem"><button type="button" data-act="asc">&#9650; A&rarr;Z</button><button type="button" data-act="desc">&#9660; Z&rarr;A</button></div>'
            + '<input class="uni-busca" type="text" placeholder="Buscar...">'
            + '<label class="uni-todos"><input type="checkbox" class="uni-chk-todos"><span>Selecionar tudo</span></label>'
            + '<div class="uni-lista"></div>'
            + '<div class="uni-acoes"><button type="button" data-act="limpar">Limpar</button><button type="button" class="uni-ok" data-act="ok">OK</button></div>';
        this.eLista = this.eGui.querySelector('.uni-lista');
        this.eBusca = this.eGui.querySelector('.uni-busca');
        this.eTodos = this.eGui.querySelector('.uni-chk-todos');
        this.eBusca.addEventListener('input', (e) => { this.busca = e.target.value.toLowerCase(); this.render(); });
        this.eTodos.addEventListener('change', (e) => { this.marcarVisiveis(e.target.checked); this.render(); });
        this.eGui.addEventListener('keydown', (e) => { if (e.key === 'Enter') { this.aplicar(); } });
        this.eGui.addEventListener('click', (e) => {
            const b = e.target.closest('button');
            if (!b) { return; }
            const a = b.getAttribute('data-act');
            if (a === 'asc' || a === 'desc') { this.ordenar(a); }
            else if (a === 'limpar') { this.limpar(); }
            else if (a === 'ok') { this.aplicar(); }
        });
    }

    texto(v) {
        if (v === null || v === undefined) { return ''; }
        return String(v);
    }

    escapar(s) {
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    carregarValores() {
        const vistos = new Set();
        this.p.api.forEachLeafNode((n) => { vistos.add(this.texto(this.p.getValue(n))); });
        this.valores = Array.from(vistos).sort((a, b) => a.localeCompare(b, 'pt-BR', { numeric: true, sensitivity: 'base' }));
        this.pend = this.aplicado === null ? new Set(this.valores) : new Set(this.aplicado);
    }

    render() {
        const termo = this.busca;
        this.visiveis = termo ? this.valores.filter((v) => v.toLowerCase().indexOf(termo) >= 0) : this.valores.slice();
        let html = '';
        this.visiveis.forEach((v, i) => {
            const marcado = this.pend.has(v) ? ' checked' : '';
            const rotulo = v === '' ? '<i>(vazio)</i>' : this.escapar(v);
            html += '<label class="uni-item" title="' + this.escapar(v) + '"><input type="checkbox" data-i="' + i + '"' + marcado + '><span>' + rotulo + '</span></label>';
        });
        this.eLista.innerHTML = html || '<div class="uni-vazio">Nenhum valor encontrado</div>';
        this.eLista.querySelectorAll('input[type=checkbox]').forEach((el) => {
            el.addEventListener('change', (ev) => {
                const v = this.visiveis[parseInt(ev.target.getAttribute('data-i'), 10)];
                if (ev.target.checked) { this.pend.add(v); } else { this.pend.delete(v); }
                this.sincTodos();
            });
        });
        this.sincTodos();
    }

    sincTodos() {
        const marcados = this.visiveis.filter((v) => this.pend.has(v)).length;
        this.eTodos.checked = this.visiveis.length > 0 && marcados === this.visiveis.length;
        this.eTodos.indeterminate = marcados > 0 && marcados < this.visiveis.length;
    }

    marcarVisiveis(ligar) {
        this.visiveis.forEach((v) => { if (ligar) { this.pend.add(v); } else { this.pend.delete(v); } });
    }

    ordenar(dir) {
        this.p.api.applyColumnState({ state: [{ colId: this.p.column.getColId(), sort: dir }], defaultState: { sort: null } });
        this.fechar();
    }

    limpar() {
        this.aplicado = null;
        this.busca = '';
        this.eBusca.value = '';
        this.carregarValores();
        this.render();
        this.p.filterChangedCallback();
        this.fechar();
    }

    aplicar() {
        this.aplicado = this.pend.size === this.valores.length ? null : new Set(this.pend);
        this.p.filterChangedCallback();
        this.fechar();
    }

    fechar() {
        if (this.hidePopup) { this.hidePopup(); }
    }

    getGui() { return this.eGui; }

    isFilterActive() { return this.aplicado !== null; }

    doesFilterPass(pr) { return this.aplicado.has(this.texto(this.p.getValue(pr.node))); }

    getModel() { return this.aplicado === null ? null : { valores: Array.from(this.aplicado) }; }

    setModel(m) { this.aplicado = m && m.valores ? new Set(m.valores) : null; }

    afterGuiAttached(pr) {
        this.hidePopup = pr && pr.hidePopup ? pr.hidePopup : null;
        this.busca = '';
        this.eBusca.value = '';
        this.carregarValores();
        this.render();
        setTimeout(() => { this.eBusca.focus(); }, 10);
    }
}
""")

# Tokens do "Controle de EPIs e Uniformes" (Setrata) — a grade roda dentro de
# um iframe, então as variáveis CSS da página não chegam aqui: a paleta é
# resolvida no Python e injetada já concreta.
_PALETA = {
    "light": {
        "sup_1": "#FFFFFF", "sup_2": "#F1F4F8",
        "linha": "#E3E8EE", "linha_forte": "#CBD5E1",
        "tinta": "#1E2A3A", "tinta_3": "#8A95A5",
        "marca": "#005584", "marca_2": "#013A68", "marca_fraco": "#E6EEF3",
        "azul": "#005584",
        "foco": "0 0 0 3px rgba(0, 85, 132, .14)",
    },
    "dark": {
        "sup_1": "#1A1F27", "sup_2": "#222833",
        "linha": "#2C3644", "linha_forte": "#3D4959",
        "tinta": "#E7EDF4", "tinta_3": "#8592A6",
        "marca": "#6FA8DC", "marca_2": "#8FBEE8", "marca_fraco": "rgba(111, 168, 220, .12)",
        "azul": "#6FA8DC",
        "foco": "0 0 0 3px rgba(111, 168, 220, .20)",
    },
}


# Reaplica filtro e ordenação assim que a grade termina de desenhar. Não dá
# para depender do `initialState`: ele é lido antes de as colunas existirem e o
# filtro customizado ainda não foi instanciado.
_RESTAURAR_JS = JsCode("""
function (p) {
    const e = p.context ? p.context.estadoSalvo : null;
    if (!e) { return; }
    if (e.filtro && Object.keys(e.filtro).length) { p.api.setFilterModel(e.filtro); }
    if (e.ordem && e.ordem.length) { p.api.applyColumnState({ state: e.ordem, defaultState: { sort: null } }); }
}
""")

# Duplo clique numa célula copia o conteúdo. Arrastar para selecionar o texto
# funciona, mas em célula estreita é briga com a barra de rolagem — o duplo
# clique é o caminho garantido. Colunas editáveis ficam de fora: nelas o clique
# abre a edição. `execCommand` em vez de `navigator.clipboard` porque a grade
# roda em iframe, onde a API nova costuma vir bloqueada.
_COPIAR_JS = JsCode("""
function (e) {
    if (!e.colDef || e.colDef.editable) { return; }
    const v = e.value === null || e.value === undefined ? '' : String(e.value);
    if (!v) { return; }
    const ta = document.createElement('textarea');
    ta.value = v;
    ta.style.position = 'fixed';
    ta.style.top = '-1000px';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); } catch (err) { }
    document.body.removeChild(ta);
    try { e.api.flashCells({ rowNodes: [e.node], columns: [e.column.getColId()] }); } catch (err) { }
}
""")

# Onde o filtro/ordenação de cada grade fica guardado entre reruns.
_CHAVE_ESTADO = "_estado_grade_%s"

# Quantas vezes a grade já foi remontada — entra na chave do componente.
_CHAVE_GERACAO = "_geracao_grade_%s"

# A ordem das colunas é escolha do usuário: ele arrasta o cabeçalho e a posição
# tem de continuar lá amanhã. Por isso vai para disco, não para a sessão.
_DIR_ORDEM = Path(__file__).resolve().parent.parent / "dados"


def _arquivo_ordem(key: str) -> Path:
    return _DIR_ORDEM / f"ordem_colunas_{key}.json"


def _ordem_salva(key: str) -> list:
    try:
        return list(json.loads(_arquivo_ordem(key).read_text(encoding="utf-8")))
    except Exception:
        return []


def _gravar_ordem(key: str, colunas: list):
    try:
        _DIR_ORDEM.mkdir(parents=True, exist_ok=True)
        _arquivo_ordem(key).write_text(
            json.dumps(colunas, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass                                  # não pode derrubar a tela

# A grade roda em iframe: a fonte do tema do Streamlit não chega sozinha.
_FONTE = '"Calibri Light", Calibri, Carlito, "Segoe UI", system-ui, -apple-system, sans-serif'


def _css_filtro(tema: str) -> dict:
    """Visual do painel de filtro — papel e tinta, separação por linha."""
    c = _PALETA.get(tema, _PALETA["light"])
    botao = {
        "padding": "6px 10px",
        "border": f"1px solid {c['linha_forte']}",
        "border-radius": "8px",
        "background": c["sup_1"],
        "color": c["tinta"],
        "cursor": "pointer",
        "font-size": "12px",
        "font-family": _FONTE,
    }
    # Coluna com filtro ativo ganha uma bolinha azul no funil do cabeçalho — dá
    # para ver de relance onde a tabela está filtrada. O AG Grid marca a célula
    # com `ag-header-cell-filtered` e o ícone com `ag-filter-active`; cobrimos
    # os dois porque o nome mudou entre versões.
    ponto = {
        "content": "''",
        "position": "absolute",
        "top": "2px",
        "right": "1px",
        "width": "7px",
        "height": "7px",
        "border-radius": "999px",
        "background": "#A7C6D5",
        "box-shadow": "0 0 0 1.5px #005584",
        "pointer-events": "none",
    }
    return {
        ".ag-root-wrapper, .ag-theme-streamlit": {"font-family": _FONTE},
        # Cabeçalho no padrão da tabela do kit DP Setrata: azul com letra branca.
        ".ag-header, .ag-header-row, .ag-header-cell, .ag-header-group-cell": {
            "background-color": "#005584",
            "color": "#FFFFFF",
        },
        ".ag-header-cell-text": {"color": "#FFFFFF", "font-weight": "700"},
        ".ag-header .ag-icon, .ag-header-cell-menu-button, .ag-header-cell-filter-button": {
            "color": "rgba(255, 255, 255, .85)",
        },
        ".ag-header .ag-checkbox-input-wrapper": {"background-color": "#FFFFFF"},
        ".ag-header-cell-resize::after": {"background-color": "rgba(255, 255, 255, .25)"},
        ".ag-header-cell-filtered .ag-header-cell-filter-button": {
            "position": "relative",
            "color": "#FFFFFF",
            "opacity": "1",
        },
        ".ag-header-cell-filtered .ag-header-cell-filter-button::after": ponto,
        ".ag-header-icon.ag-filter-active": {"position": "relative", "color": "#FFFFFF"},
        ".ag-header-icon.ag-filter-active::after": ponto,
        ".ag-header-cell-filtered .ag-header-cell-text": {"font-weight": "600"},
        ".uni-filtro": {
            "font-family": _FONTE,
            "width": "286px",
            "padding": "12px",
            "background": c["sup_1"],
            "color": c["tinta"],
            "font-size": "13.5px",
            "display": "flex",
            "flex-direction": "column",
            "gap": "9px",
            "accent-color": c["marca"],
        },
        ".uni-filtro .uni-ordem": {"display": "flex", "gap": "6px"},
        ".uni-filtro .uni-ordem button": {**botao, "flex": "1"},
        ".uni-filtro .uni-ordem button:hover": {
            "background": c["sup_2"],
            "border-color": c["marca"],
        },
        ".uni-filtro .uni-busca": {
            "width": "100%",
            "padding": "8px 10px",
            "border": f"1px solid {c['linha_forte']}",
            "border-radius": "8px",
            "background": c["sup_1"],
            "color": c["tinta"],
            "outline": "none",
            "font-size": "13.5px",
            "font-family": _FONTE,
        },
        ".uni-filtro .uni-busca:focus": {"border-color": c["marca"], "box-shadow": c["foco"]},
        ".uni-filtro .uni-todos": {
            "display": "flex",
            "align-items": "center",
            "gap": "8px",
            "font-weight": "600",
            "padding": "5px 2px",
            "border-bottom": f"1px solid {c['linha']}",
            "cursor": "pointer",
        },
        ".uni-filtro .uni-lista": {
            "max-height": "232px",
            "overflow-y": "auto",
            "display": "flex",
            "flex-direction": "column",
        },
        ".uni-filtro .uni-item": {
            "display": "flex",
            "align-items": "center",
            "gap": "8px",
            "padding": "4px 2px",
            "cursor": "pointer",
            "white-space": "nowrap",
            "overflow": "hidden",
            "text-overflow": "ellipsis",
        },
        ".uni-filtro .uni-item:hover": {"background": c["marca_fraco"]},
        ".uni-filtro .uni-vazio": {
            "padding": "12px 2px",
            "color": c["tinta_3"],
            "font-style": "italic",
        },
        ".uni-filtro .uni-acoes": {
            "display": "flex",
            "justify-content": "flex-end",
            "gap": "6px",
            "padding-top": "8px",
            "border-top": f"1px solid {c['linha']}",
        },
        ".uni-filtro .uni-acoes button": botao,
        # Uma cor de destaque só: a marca fica reservada para a ação.
        ".uni-filtro .uni-acoes .uni-ok": {
            **botao,
            "background": c["marca"],
            "border-color": c["marca"],
            "color": "#fff" if tema == "light" else "#0F172A",
            "font-weight": "600",
            "padding": "6px 16px",
        },
        ".uni-filtro .uni-acoes .uni-ok:hover": {
            "background": c["marca_2"],
            "border-color": c["marca_2"],
        },
    }


def _tema_atual() -> str:
    """"light" ou "dark", seguindo o tema que o usuário está vendo."""
    try:
        return "dark" if st.context.theme.type == "dark" else "light"
    except Exception:
        return "light"

# Moeda e data são formatadas no navegador para o valor continuar numérico /
# temporal por trás — assim a ordenação da coluna sai certa.
# Célula ausente chega aqui como texto: o pandas serializa NaT/NaN e o AG Grid
# mostraria "NaT" cru na coluna de data. Todo formatador passa por este teste.
_VAZIOS_JS = """
    const v = p.value;
    if (v === null || v === undefined) { return '—'; }
    const s = String(v).trim();
    if (['', 'NAT', 'NAN', 'NONE', 'NULL', 'NONE.'].indexOf(s.toUpperCase()) >= 0) { return '—'; }
"""

_FMT_BRL = JsCode("""
function (p) {
""" + _VAZIOS_JS + """
    const n = Number(s);
    if (isNaN(n)) { return s; }
    return 'R$ ' + n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
""")

_FMT_DATA = JsCode("""
function (p) {
""" + _VAZIOS_JS + """
    const d = new Date(s);
    if (isNaN(d.getTime())) { return s; }
    return String(d.getUTCDate()).padStart(2, '0') + '/' + String(d.getUTCMonth() + 1).padStart(2, '0') + '/' + d.getUTCFullYear();
}
""")

_FMT_VAZIO = JsCode("""
function (p) {
""" + _VAZIOS_JS + """
    return v;
}
""")


def grade(
    df: pd.DataFrame,
    key: str,
    *,
    height: int = 430,
    colunas_moeda: tuple = (),
    colunas_data: tuple = (),
    colunas_editaveis: tuple = (),
    colunas_checkbox: tuple = (),
    larguras: dict | None = None,
    cor_linha: JsCode | None = None,
    selecao: bool = False,
):
    """
    Desenha a tabela com filtro estilo Excel no cabeçalho de cada coluna.

    Devolve a resposta do AgGrid — `["data"]` traz o DataFrame como está na
    tela (filtrado e ordenado) e `["selected_rows"]` as linhas marcadas.
    """
    if df is None or df.empty:
        st.info("Nenhum registro para exibir.")
        return None

    # Ordem das colunas: a que o usuário deixou da última vez que arrastou.
    # Coluna nova (que ainda não existia quando ele arrumou) entra no fim, em
    # vez de bagunçar o que ele montou.
    ordem = _ordem_salva(key)
    if ordem:
        arrumadas = [c for c in ordem if c in df.columns]
        novas = [c for c in df.columns if c not in arrumadas]
        df = df[arrumadas + novas]

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        filter=_FILTRO_JS,
        sortable=True,
        resizable=True,
        editable=False,
        suppressHeaderMenuButton=True,      # deixa só o funil no cabeçalho
        suppressHeaderFilterButton=False,
        valueFormatter=_FMT_VAZIO,
        minWidth=110,
        flex=1,
    )

    larguras = larguras or {}
    editavel = bool(colunas_editaveis)
    for col in df.columns:
        cfg: dict = {}
        if col in colunas_moeda:
            cfg.update(valueFormatter=_FMT_BRL, type="numericColumn", minWidth=140, flex=0)
        elif col in colunas_data:
            cfg.update(valueFormatter=_FMT_DATA, minWidth=125, flex=0)
        if col in colunas_checkbox:
            cfg.update(
                cellRenderer="agCheckboxCellRenderer",
                cellEditor="agCheckboxCellEditor",
                minWidth=70,
                maxWidth=90,
                flex=0,
            )
        if col in colunas_editaveis:
            cfg.update(editable=True, singleClickEdit=True)
        if col in larguras:
            cfg.update(width=larguras[col], flex=0)
        if cfg:
            gb.configure_column(col, **cfg)

    if selecao:
        # Um controle só no cabeçalho da coluna de tique, que faz as duas
        # funções: marca todas as linhas e, clicado de novo, desmarca todas.
        # `filtered_only` limita ao que o filtro deixou à vista — marcar "todos"
        # nunca alcança linha que não está na tela.
        gb.configure_selection("multiple", use_checkbox=True,
                               header_checkbox=True, header_checkbox_filtered_only=True)

    opcoes = gb.build()
    opcoes["suppressMenuHide"] = True       # funil sempre visível, não só no hover
    opcoes["animateRows"] = True
    # Para selecionar o texto de uma célula com o mouse os dois andam juntos:
    # sem `ensureDomOrder` o AG Grid desenha as linhas fora de ordem no HTML e
    # a seleção do navegador não pega nada.
    opcoes["enableCellTextSelection"] = True
    opcoes["ensureDomOrder"] = True
    opcoes["onCellDoubleClicked"] = _COPIAR_JS
    # Arrastar cabeçalho é permitido — a ordem é escolha do usuário e fica
    # gravada em disco (ver `_ordem_salva`). `suppressDragLeaveHidesColumns`
    # impede que uma coluna suma ao ser solta fora da grade, e
    # `maintainColumnOrder` evita que a ordem se embaralhe ao recarregar dados.
    opcoes["suppressMovableColumns"] = False
    opcoes["suppressDragLeaveHidesColumns"] = True
    opcoes["maintainColumnOrder"] = True
    if cor_linha is not None:
        opcoes["getRowStyle"] = cor_linha

    # Filtro e ordenação sobrevivem ao rerun do Streamlit. A cada interação o
    # script roda de novo e a grade é remontada do zero — sem isso, salvar uma
    # justificativa ou trocar de aba jogava fora tudo o que estava filtrado.
    # `initialState` só é lido na criação da grade, então não briga com o que o
    # usuário está fazendo na tela.
    # `MODEL_CHANGED` é o apelido de VALUE|SELECTION|FILTERING|SORTING: sem ele
    # a ordenação não voltava do navegador e não havia o que guardar.
    #
    # O que vai em `gridOptions` fica CONGELADO na primeira vez que a grade
    # aparece na sessão. Antes o estado vivo era reinjetado a cada rerun: como
    # o st_aggrid remonta o iframe sempre que as opções mudam, cada clique num
    # filtro derrubava e reconstruía a grade — era isso que fazia os filtros
    # "piscarem" e parecerem instáveis. Congelado, as opções não mudam mais e o
    # filtro simplesmente continua vivo no navegador, sem remontagem.
    inicial = f"_estado_inicial_grade_{key}"
    if inicial not in st.session_state:
        st.session_state[inicial] = st.session_state.get(_CHAVE_ESTADO % key) or {}
    opcoes["context"] = {"estadoSalvo": st.session_state[inicial]}
    opcoes["onFirstDataRendered"] = _RESTAURAR_JS

    # Assim que uma célula é editada, o componente passa a IGNORAR todo dado
    # novo vindo do Python — é a estratégia "client_wins" dele, e o próprio
    # componente avisa no console: "Data was edited on Grid. Ignoring further".
    # Resultado: você salvava a justificativa e a coluna "Justificado" continuava
    # "Não" na tela, mesmo já gravada no banco. A saída é remontar a grade (ver
    # `recarregar`), que é o único jeito de limpar essa trava sem perder o que o
    # usuário digitou enquanto edita.
    chave_componente = f"{key}__g{st.session_state.get(_CHAVE_GERACAO % key, 0)}"

    resposta = AgGrid(
        df,
        gridOptions=opcoes,
        height=height,
        theme="streamlit",
        key=chave_componente,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=False,    # só Community — sem licença paga
        custom_css=_css_filtro(_tema_atual()),
        update_mode=GridUpdateMode.MODEL_CHANGED,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        show_toolbar=False,
        show_search=False,
        show_download_button=False,
    )

    # Guarda só filtro e ordenação. A seleção fica de fora de propósito:
    # ressuscitar tiquezinhos depois de um rerun faria uma ação em lote atingir
    # gente que o usuário já tinha desmarcado.
    try:
        bruto = resposta.grid_state or {}
    except Exception:
        bruto = {}
    if bruto:
        st.session_state[_CHAVE_ESTADO % key] = {
            "filtro": (bruto.get("filter") or {}).get("filterModel") or {},
            "ordem":  (bruto.get("sort") or {}).get("sortModel") or [],
        }

    # Arrastou uma coluna? Grava a nova ordem para ela estar lá amanhã.
    try:
        estado_cols = resposta.columns_state or []
    except Exception:
        estado_cols = []
    atual = [c.get("colId") for c in estado_cols if isinstance(c, dict) and c.get("colId")]
    atual = [c for c in atual if c in df.columns]
    if atual and atual != list(df.columns):
        _gravar_ordem(key, atual)

    return resposta


def recarregar(key: str):
    """
    Faz a grade aceitar os dados novos do Python na próxima exibição.

    Chame depois de gravar algo que muda a tabela (uma justificativa, por
    exemplo). Sem isso o componente ignora o dado novo assim que qualquer
    célula tiver sido editada. O filtro e a ordenação são preservados: o estado
    vivo vira o estado inicial da grade remontada.
    """
    st.session_state[_CHAVE_GERACAO % key] = st.session_state.get(_CHAVE_GERACAO % key, 0) + 1
    st.session_state[f"_estado_inicial_grade_{key}"] = st.session_state.get(_CHAVE_ESTADO % key) or {}


def limpar_estado(key: str):
    """Descarta filtro e ordenação guardados de uma grade."""
    st.session_state.pop(_CHAVE_ESTADO % key, None)
    st.session_state.pop(f"_estado_inicial_grade_{key}", None)


def cor_por_status() -> JsCode:
    """
    Cor de fundo das linhas da auditoria — estado, não enfeite:
    risco (vermelho fraco) = pendente, info (azul fraco) = já justificado.
    """
    escuro = _tema_atual() == "dark"
    risco = "rgba(233, 112, 112, .13)" if escuro else "#FBEDED"
    info  = "rgba(111, 168, 220, .13)" if escuro else "#EAF2FB"
    return JsCode("""
    function (p) {
        if (!p.data) { return null; }
        if (p.data['Status'] !== 'Inconsistente') { return null; }
        if (p.data['Justificado'] === 'Sim') { return { background: '""" + info + """' }; }
        return { background: '""" + risco + """' };
    }
    """)
