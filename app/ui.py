# -*- coding: utf-8 -*-
"""
Componentes de interface compartilhados entre todas as páginas.

Identidade visual DP Setrata (28/09/2026, kit em C:\Projetos\_identidade):
azul Setrata no destaque e no menu, Calibri Light em tudo. Base herdada do
"Controle de EPIs e Uniformes":
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

# Logo e ícone vêm do kit DP Setrata — trocou lá, troca aqui. A cópia em
# app/marca só entra se o kit não estiver acessível.
_KIT = Path(r"C:\Projetos\_identidade")
_MARCA_LOCAL = Path(__file__).resolve().parent / "marca"


def _marca(nome: str) -> str:
    kit = _KIT / nome
    return str(kit if kit.exists() else _MARCA_LOCAL / nome)


LOGO = _marca("logo_setrata_transparente.png")   # branco — só sobre o azul do menu
ICONE = _marca("icone_setrata.png")              # aba do navegador e menu recolhido


# ── Componentes de comportamento do kit (aviso de versão, Novidades, avisos) ──
# Cópia instalada em static/ pelo `instalar_componentes.py auditoria-unimed` —
# não editar lá. O arquivo de versão é gravado pelo servico.py na subida;
# gravar de novo aqui cobre quem roda pelo `streamlit run` direto.
from app.versao_app import URL as _VERSAO_URL, gravar as _gravar_versao_app

_STATIC = Path(__file__).resolve().parent.parent / "static"
_BOOT_VERSAO = str(int(__import__("time").time()))   # quebra o cache dos componentes a cada subida
_gravar_versao_app()


def _componentes_html() -> str:
    # Por endereço, não embutido: o st.html descarta <script> grande inline.
    if not (_STATIC / "dp-componentes.js").exists():
        return ""
    v = _BOOT_VERSAO
    return (f'<link rel="stylesheet" href="/app/static/dp-componentes.css?v={v}">'
            f"<script>window.DP_VERSAO_URL = {_VERSAO_URL!r};</script>"
            f'<script src="/app/static/dp-componentes.js?v={v}"></script>')


def aviso(msg: str, tipo: str = "ok", prender: bool = False):
    """Aviso do kit (DP.toast) — ok · err · aviso · info. Nada de toast próprio."""
    import html as _h
    import time
    st.markdown(
        f'<div class="dp-aviso" style="display:none" data-tipo="{_h.escape(tipo)}" '
        f'data-msg="{_h.escape(msg)}" data-prender="{1 if prender else 0}" '
        f'data-quando="{time.time()}"></div>',
        unsafe_allow_html=True,
    )

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
  --bg-deep: #013A68; --bg-dark: #005584; --royal: #1D6A93;
  --bright: #005584;  --accent: #529E2B;  --accent-rgb: 82, 158, 43;
  --sup-1: #FFFFFF; --sup-2: #F1F4F8; --sup-3: #E7ECF2;
  --linha: #E3E8EE; --linha-forte: #CBD5E1;
  --tinta: #1E2A3A; --tinta-2: #5B6675; --tinta-3: #8A95A5;
  --marca: var(--bg-dark);
  --bom: #2E7D32; --atencao: #B45309; --risco: #D03B3B; --info: #005584;
  --bom-fraco: #ECF5ED; --atencao-fraco: #FDF3E7;
  --risco-fraco: #FBEDED; --info-fraco: #EAF2FB; --marca-fraco: #EDF1F6;
  --fonte: "Calibri Light", Calibri, Carlito, "Segoe UI", system-ui, -apple-system, sans-serif;
  --r-2: 8px; --r-3: 12px; --r-pill: 999px;
  --e-1: 0 1px 2px rgba(15, 23, 42, .04);
  --fs-xs: 12px; --fs-sm: 13px; --fs-md: 16px;
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

/* ── Casca do menu (.dp-casca do kit): azul Setrata com brilho e grade ─────── */
section[data-testid="stSidebar"], section[data-testid="stSidebar"] > div:first-child {
  background-color: #013A68;
  background-image:
    radial-gradient(600px 400px at 90% 0%, rgba(167, 198, 213, 0.30), transparent 60%),
    radial-gradient(500px 400px at 0% 100%, rgba(1, 32, 77, 0.45), transparent 65%),
    linear-gradient(rgba(255, 255, 255, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.055) 1px, transparent 1px),
    linear-gradient(180deg, #005584 0%, #013A68 75%);
  background-size: auto, auto, 44px 44px, 44px 44px, auto;
}
/* Logo Setrata no topo do menu — o st.logo nasce com 24px, pequeno demais
   para ler "Gestão Estratégica de Pessoas". */
[data-testid="stSidebarHeader"] { height: auto; padding-top: 20px; padding-bottom: 4px; }
img[data-testid="stSidebarLogo"] { height: 64px !important; max-height: none !important; max-width: 100%; }
img[data-testid="stHeaderLogo"]  { height: 32px !important; max-height: none !important; }

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
[data-testid="stSidebarNavItems"]::before {
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
  background: rgba(255, 255, 255, .16);
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

/* ── Números (st.metric) = quadro de indicador (.dp-kpi do kit) ──────────── */
[data-testid="stMetric"] {
  background: #F2F6F9;
  border-radius: 10px;
  padding: 12px 14px;
}
[data-testid="stMetricValue"] {
  color: var(--tinta); font-weight: 700; line-height: 1.1;
  font-variant-numeric: tabular-nums;
}
[data-testid="stMetricLabel"] p { color: var(--tinta-2); font-size: var(--fs-md); }
[data-testid="stMetricDelta"] { font-weight: 700; }

/* ── Cabeçalho da página: título escuro à esquerda ───────────────────────── */
h1, h2, h3 { font-weight: 700; color: var(--tinta); }
[data-testid="stHeadingWithActionElements"] { margin-bottom: 2px; }

/* Blocos abertos/fechados = card branco do kit (.dp-card). */
[data-testid="stExpander"] details {
  border: 1px solid var(--linha);
  border-radius: 14px;
  background: var(--sup-1);
  box-shadow: 0 1px 3px rgba(16, 24, 40, .06), 0 1px 2px rgba(16, 24, 40, .04);
}

/* ── Botões do kit: principal verde (ação), secundário contornado em azul ─── */
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  background: #529E2B; border-color: #529E2B; color: #fff; font-weight: 700;
  border-radius: 10px;
}
[data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover {
  background: #3F7A21; border-color: #3F7A21; color: #fff;
}
.stMain [data-testid="stBaseButton-secondary"], .stMain [data-testid="stBaseButton-secondaryFormSubmit"] {
  background: transparent; color: #005584; border: 1px solid #A7C6D5;
  font-weight: 700; border-radius: 10px;
}
.stMain [data-testid="stBaseButton-secondary"]:hover,
.stMain [data-testid="stBaseButton-secondaryFormSubmit"]:hover {
  background: #E6EEF3; color: #005584; border-color: #005584;
}
hr { border-color: var(--linha); }

/* Calibri Light também nos títulos e números (destaque pelo tamanho). */
h1, h2, h3, h4, [data-testid="stMetricValue"], [data-testid="stSidebarNav"] a,
[data-testid="stToast"], button { font-family: var(--fonte) !important; }


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


# ── Gráficos (Altair) na identidade DP Setrata ─────────────────────────────
# Cores copiadas do kit (C:\Projetos\_identidade\graficos.py) — o kit usa
# Plotly, que este sistema não tem. Regra: série única = azul Setrata; duas
# séries = azul + azul-claro; três = + azul médio; vermelho/laranja só alerta.
AZUL = "#005584"
AZUL_CLARO = "#A7C6D5"
TEXTO = "#1E2A3A"
TEXTO_2 = "#5B6675"
GRADE = "#E8EDF2"
FONTE = "Calibri Light, Calibri, Carlito, Segoe UI, sans-serif"
SERIES = [AZUL, AZUL_CLARO, "#4586AE"]   # ordem fixa, nunca repete


def _tema_altair():
    import altair as alt

    def tema():
        return {"config": {
            "font": FONTE,
            "background": "transparent",
            "view": {"stroke": None},
            "range": {"category": SERIES},
            "bar": {"color": AZUL, "cornerRadiusEnd": 4},
            "line": {"color": AZUL, "strokeWidth": 2},
            "point": {"color": AZUL, "size": 64, "filled": True},
            "text": {"color": TEXTO, "font": FONTE, "fontSize": 12},
            "axis": {"labelFont": FONTE, "titleFont": FONTE, "labelColor": TEXTO_2,
                     "titleColor": TEXTO_2, "labelFontSize": 12, "gridColor": GRADE,
                     "gridDash": [2, 3], "domainColor": GRADE, "tickColor": GRADE},
            "legend": {"labelFont": FONTE, "titleFont": FONTE, "labelColor": TEXTO,
                       "labelFontSize": 12, "orient": "top"},
            "title": {"font": FONTE, "color": TEXTO, "fontSize": 16, "fontWeight": "normal"},
        }}

    try:
        alt.theme.register("dp_setrata", enable=True)(tema)
    except AttributeError:  # Altair < 5.5
        alt.themes.register("dp_setrata", tema)
        alt.themes.enable("dp_setrata")


def barra_lateral():
    """Aplica a identidade visual e desenha o rodapé de versão na chapa."""
    from version import __version__

    st.logo(LOGO, icon_image=ICONE, size="large")
    st.markdown(_ESTILO, unsafe_allow_html=True)
    comp = _componentes_html()
    if comp:
        st.sidebar.html(comp, unsafe_allow_javascript=True)
    _tema_altair()
    st.sidebar.markdown(
        f'<div class="rodape-versao"><div class="faixa"></div>{__version__}</div>',
        unsafe_allow_html=True,
    )


def selo(texto: str, tom: str = "marca") -> str:
    """Devolve o HTML de um selo de estado (`marca`, `bom`, `atencao`, `risco`, `info`)."""
    return f'<span class="selo {tom}">{texto}</span>'


class Progresso:
    """Barra de progresso do kit (DP.toast "progress") para trabalho por etapas.

        with Progresso("Processando auditoria de 09/2026", total=8) as prog:
            prog.etapa("Lendo contratos")
            ...

    Cada etapa manda um <div class="dp-aviso"> novo para a tela; o
    dp-componentes.js transforma em barra com porcentagem, "3 de 8" e tempo.
    O Streamlit entrega esses pedaços enquanto o código ainda está rodando.
    """

    def __init__(self, titulo: str, total: int):
        import time
        self.titulo, self.total, self.feitos = titulo, max(int(total), 1), 0
        self._inicio = time.time()
        self._lugar = st.sidebar.empty()

    def _enviar(self, tipo: str, msg: str, pct=None, fase: str = "", prender: bool = False):
        import html as _h
        import time
        self._lugar.markdown(
            f'<div class="dp-aviso" style="display:none" data-tipo="{tipo}" '
            f'data-msg="{_h.escape(msg)}" data-prender="{1 if prender else 0}" '
            f'data-pct="{"" if pct is None else pct}" data-fase="{_h.escape(fase)}" '
            f'data-quando="{time.time()}"></div>',
            unsafe_allow_html=True,
        )

    def etapa(self, fase: str):
        """Marca o começo de uma etapa (a barra mostra quantas já terminaram)."""
        import time
        seg = int(time.time() - self._inicio)
        pct = round(100 * self.feitos / self.total)
        self._enviar("progress", self.titulo, pct,
                     f"{fase} — {self.feitos} de {self.total} · {pct}% · {seg}s", prender=True)
        self.feitos += 1

    def __enter__(self):
        self._enviar("progress", self.titulo, 0, "Começando…", prender=True)
        return self

    def __exit__(self, tipo, erro, _tb):
        import time
        seg = int(time.time() - self._inicio)
        if erro is None:
            self._enviar("ok", f"{self.titulo} — concluído em {seg}s.")
        else:
            self._enviar("err", f"Falha: {erro}")
        return False
