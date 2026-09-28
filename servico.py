# -*- coding: utf-8 -*-
"""Arranque do serviço AuditoriaUnimed (NSSM).

Grava a versão para o aviso "Nova versão" do kit DP Setrata e sobe o Streamlit
exatamente como antes: `servico.py <argumentos>` = `streamlit run main.py <argumentos>`.
"""
import sys

from app.versao_app import gravar

gravar()

from streamlit.web import cli  # noqa: E402

sys.argv = ["streamlit", "run", "main.py", *sys.argv[1:]]
sys.exit(cli.main())
