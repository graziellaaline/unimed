# -*- coding: utf-8 -*-
"""
Componentes de interface compartilhados entre todas as páginas.

A identidade visual é a mesma do "Controle de EPIs e Uniformes" (Setrata):
papel e tinta — superfícies claras e sólidas, separação por LINHA em vez de
sombra, chapa azul-marinho no menu, e uma cor de destaque só. Verde, âmbar e
vermelho aparecem como ESTADO, nunca como enfeite.

As cores vêm do tema (`.streamlit/config.toml`); aqui ficam só os ajustes que
o tema do Streamlit não alcança.
"""
import inspect
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Célula vazia (data/valor ausente) é desenhada pelo Streamlit com o texto
# "None" em cinza. O parâmetro `placeholder` troca esse texto — só existe a
# partir do Streamlit 1.51, por isso a checagem antes de repassar.
_CELULA_VAZIA = "—"
_DATAFRAME_TEM_PLACEHOLDER = "placeholder" in inspect.signature(st.dataframe).parameters
_EDITOR_TEM_PLACEHOLDER    = "placeholder" in inspect.signature(st.data_editor).parameters


def tabela(dados, **kwargs):
    """`st.dataframe` padrão do sistema — sem "None" nas células vazias."""
    if _DATAFRAME_TEM_PLACEHOLDER:
        kwargs.setdefault("placeholder", _CELULA_VAZIA)
    return st.dataframe(dados, **kwargs)


def tabela_editavel(dados, **kwargs):
    """`st.data_editor` padrão do sistema — sem "None" nas células vazias."""
    if _EDITOR_TEM_PLACEHOLDER:
        kwargs.setdefault("placeholder", _CELULA_VAZIA)
    return st.data_editor(dados, **kwargs)


_ESTILO = """
<style>
/* ── Tokens (espelham o style.css do Controle de EPIs) ───────────────────── */
:root {
  --bg-deep: #01204D; --bg-dark: #0A3161; --royal: #1A3A5C;
  --bright: #2E7DD1;  --accent: #529E2B;  --accent-rgb: 82, 158, 43;
  --sup-1: #FFFFFF; --sup-2: #F1F4F8; --sup-3: #E7ECF2;
  --linha: #E3E8EF; --linha-forte: #CBD5E1;
  --tinta: #0F172A; --tinta-2: #475569; --tinta-3: #8592A6;
  --marca: var(--bg-deep);
  --bom: #2E7D32; --atencao: #B45309; --risco: #C62828; --info: #2E7DD1;
  --bom-fraco: #ECF5ED; --atencao-fraco: #FDF3E7;
  --risco-fraco: #FBEDED; --info-fraco: #EAF2FB; --marca-fraco: #EDF1F6;
  --fonte: "Calibri Light", Calibri, "Segoe UI", system-ui, -apple-system, sans-serif;
  --r-2: 8px; --r-3: 12px; --r-pill: 999px;
  --e-1: 0 1px 2px rgba(15, 23, 42, .04);
  --fs-xs: 11px; --fs-sm: 12px; --fs-md: 15px;
}
[data-theme="dark"], .stApp[data-theme="dark"] {
  --sup-1: #1A1F27; --sup-2: #222833; --sup-3: #2C3441;
  --linha: #2C3644; --linha-forte: #3D4959;
  --tinta: #E7EDF4; --tinta-2: #B3BECC; --tinta-3: #8592A6;
  --marca: #6FA8DC;
  --bom: #6DBE73; --atencao: #E0A030; --risco: #E97070; --info: #6FA8DC;
  --bom-fraco: rgba(109, 190, 115, .13); --atencao-fraco: rgba(224, 160, 48, .13);
  --risco-fraco: rgba(233, 112, 112, .13); --info-fraco: rgba(111, 168, 220, .13);
  --marca-fraco: rgba(111, 168, 220, .12);
}

/* ── Chapa do menu ───────────────────────────────────────────────────────── */
/* Cabeçalho fixo acima da navegação — equivale ao "#menu .topo" do EPI. */
[data-testid="stSidebarNav"]::before {
  content: "Auditoria Unimed";
  display: block;
  font-size: var(--fs-md);
  font-weight: 600;
  color: #fff;
  padding: 18px 16px 2px;
}
[data-testid="stSidebarNav"]::after {
  content: "conferência de faturas e movimentação · Setrata";
  display: block;
  font-size: var(--fs-xs);
  color: rgba(255, 255, 255, .62);
  padding: 0 16px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, .12);
  margin-bottom: 10px;
}
[data-testid="stSidebarNav"] { border-top: none; padding-top: 0; }

/* Itens do menu: repouso apagado, ativo com chapa verde translúcida. */
[data-testid="stSidebarNav"] a {
  border-radius: var(--r-2);
  margin: 0 4px 2px;
  padding: 8px 11px;
  color: rgba(255, 255, 255, .8);
}
[data-testid="stSidebarNav"] a:hover { background: rgba(255, 255, 255, .09); color: #fff; }
[data-testid="stSidebarNav"] a[aria-current="page"] {
  background: rgba(var(--accent-rgb), .22);
  color: #fff;
  font-weight: 600;
}

/* Faixa verde da marca + versão, no rodapé da chapa. */
[data-testid="stSidebarUserContent"] .rodape-versao {
  margin-top: 8px; padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, .12);
  font-size: var(--fs-xs); color: rgba(255, 255, 255, .6);
}
[data-testid="stSidebarUserContent"] .rodape-versao .faixa {
  height: 4px; width: 46px; background: var(--accent);
  border-radius: var(--r-pill); margin-bottom: 10px;
}

/* ── Números (st.metric) — o ".numero" do EPI ────────────────────────────── */
[data-testid="stMetric"] {
  background: var(--sup-1);
  border: 1px solid var(--linha);
  border-radius: var(--r-3);
  box-shadow: var(--e-1);
  padding: 14px 16px;
}
[data-testid="stMetricValue"] { color: var(--marca); font-weight: 600; line-height: 1.1; }
[data-testid="stMetricLabel"] p { color: var(--tinta-2); font-size: var(--fs-sm); }

/* ── Cabeçalho da página ─────────────────────────────────────────────────── */
h1, h2, h3 { font-weight: 600; }
[data-testid="stHeadingWithActionElements"] { margin-bottom: 2px; }

/* Separação por linha, não por sombra. */
[data-testid="stExpander"] details {
  border: 1px solid var(--linha);
  border-radius: var(--r-3);
  background: var(--sup-1);
}
hr { border-color: var(--linha); }

/* ── Selos de estado ─────────────────────────────────────────────────────── */
.selo {
  display: inline-block; padding: 2px 9px; border-radius: var(--r-pill);
  font-size: var(--fs-xs); font-weight: 600; white-space: nowrap;
}
.selo.marca   { background: var(--marca-fraco);   color: var(--marca); }
.selo.bom     { background: var(--bom-fraco);     color: var(--bom); }
.selo.atencao { background: var(--atencao-fraco); color: var(--atencao); }
.selo.risco   { background: var(--risco-fraco);   color: var(--risco); }
.selo.info    { background: var(--info-fraco);    color: var(--info); }
</style>
"""


def barra_lateral():
    """Aplica a identidade visual e desenha o rodapé de versão na chapa."""
    from version import __version__

    st.markdown(_ESTILO, unsafe_allow_html=True)
    st.sidebar.markdown(
        f'<div class="rodape-versao"><div class="faixa"></div>{__version__}</div>',
        unsafe_allow_html=True,
    )


def selo(texto: str, tom: str = "marca") -> str:
    """Devolve o HTML de um selo de estado (`marca`, `bom`, `atencao`, `risco`, `info`)."""
    return f'<span class="selo {tom}">{texto}</span>'
