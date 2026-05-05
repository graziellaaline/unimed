# -*- coding: utf-8 -*-
"""Componentes de interface compartilhados entre todas as páginas."""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def barra_lateral():
    """Injeta título + versão ACIMA do menu de navegação no sidebar."""
    from version import __version__

    st.markdown(f"""
    <style>
    /* Cabeçalho fixo acima da navegação */
    [data-testid="stSidebarNav"]::before {{
        content: "🏥  Auditoria Unimed";
        display: block;
        font-size: 17px;
        font-weight: 700;
        color: #1565c0;
        padding: 22px 16px 2px 16px;
        letter-spacing: 0.01em;
    }}
    [data-testid="stSidebarNav"]::after {{
        content: "{__version__}";
        display: block;
        font-size: 11px;
        font-weight: 600;
        color: #ffffff;
        background: #1565c0;
        border-radius: 4px;
        padding: 2px 8px;
        margin: 0 16px 14px 16px;
        width: fit-content;
    }}
    /* Linha separadora abaixo do badge de versão */
    [data-testid="stSidebarNav"] {{
        border-top: none;
        padding-top: 0;
    }}
    </style>
    """, unsafe_allow_html=True)
