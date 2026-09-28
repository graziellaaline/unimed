# -*- coding: utf-8 -*-
"""Resposta da rota /_versao-app do kit DP Setrata, gravada como arquivo.

O Streamlit não deixa pendurar rota própria (o `st.App` que deixaria ainda é
experimental), então o JSON que o `versao_web` do kit devolveria vai para
`static/_versao-app.json`, servido em /app/static. Precisa ser gravado NA
SUBIDA do serviço (servico.py): se esperar a primeira tela abrir, a tela que
já estava aberta nunca vê o `boot` novo e o aviso "Nova versão" não aparece.
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
KIT = Path(r"C:\Projetos\_identidade")
ARQUIVO = RAIZ / "static" / "_versao-app.json"
URL = "/app/static/_versao-app.json"


def gravar():
    try:
        sys.path.insert(0, str(RAIZ))
        sys.path.insert(0, str(KIT))
        from version import __version__
        import versao_web
        dados = versao_web.dados(__version__, changelog=str(RAIZ / "CHANGELOG.md"))
        ARQUIVO.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass                      # sem o aviso de versão o sistema segue normal
