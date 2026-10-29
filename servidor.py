# -*- coding: utf-8 -*-
"""Arranque da Auditoria Unimed em Dash (serviço NSSM): `python servidor.py`.
Porta em UNIMED_PORTA (padrão 8055)."""
from web.app import principal

if __name__ == "__main__":
    principal()
