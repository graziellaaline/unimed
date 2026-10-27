# -*- coding: utf-8 -*-
"""Regras da auditoria Unimed: fatura × folha × contrato.

Gente fictícia montada em memória. Nada aqui abre o dados/historico.db.
"""
import pandas as pd
import pytest

from app import db
from app.processamento import (_classificar_plano, _parse_brl, cod_func_chave,
                               mesclar_desligados)
from app.regras import aplicar_regras, calcular_stats, identificar_incluidos_mes


def auditar(**campos):
    linha = {"Funcionário": "FULANA TESTE", "Tem Direito": "Sim", "_na_fatura": True,
             "_na_compra": True, "_desligado": False, "_sem_contrato": False,
             "Valor Fatura": 0.0, "Valor Empresa (Compra)": 0.0, "Valor Compra Total": 0.0,
             "Valor Contrato": 0.0, "_vlr_mensalidade_fat": 0.0}
    linha.update(campos)
    return aplicar_regras(pd.DataFrame([linha])).iloc[0]


def tipos(resultado):
    return set(filter(None, resultado["Tipo Inconsistência"].split(" | ")))


# --------------------------------------------------------------------------- #
def test_tudo_batendo_fica_ok():
    r = auditar(**{"Valor Fatura": 450.0, "Valor Compra Total": 450.0,
                   "Valor Empresa (Compra)": 450.0, "Valor Contrato": 450.0})
    assert r["Status"] == "OK" and not tipos(r)


def test_r1_tem_direito_e_nao_esta_na_fatura():
    assert "Tem direito, fora da fatura" in tipos(auditar(_na_fatura=False, _na_compra=False))


def test_r1_nao_vale_para_desligado():
    r = auditar(_na_fatura=False, _na_compra=False, _desligado=True)
    assert "Tem direito, fora da fatura" not in tipos(r)


def test_r2_fatura_sem_compra():
    assert "Fatura sem compra" in tipos(auditar(_na_compra=False))


def test_r3_sem_direito_mas_na_fatura():
    assert "Sem direito mas na fatura" in tipos(auditar(**{"Tem Direito": "Não"}))


def test_r4_compra_sem_fatura():
    assert "Compra sem fatura" in tipos(auditar(_na_fatura=False))


def test_r5_valor_empresa_acima_do_contrato_com_tolerancia_de_10_centavos():
    dentro = auditar(**{"Valor Empresa (Compra)": 450.05, "Valor Contrato": 450.0})
    fora = auditar(**{"Valor Empresa (Compra)": 451.0, "Valor Contrato": 450.0})
    assert "Valor empresa ≠ contrato" not in tipos(dentro)
    assert "Valor empresa ≠ contrato" in tipos(fora)


def test_r6_total_da_compra_diferente_da_fatura():
    r = auditar(**{"Valor Fatura": 900.0, "Valor Compra Total": 450.0})
    assert "Total compra ≠ fatura" in tipos(r)


def test_r7_desligado_na_fatura():
    assert "Desligado na fatura" in tipos(auditar(_desligado=True))


def test_r8_na_fatura_sem_contrato():
    assert "Sem correspondência no contrato" in tipos(auditar(_sem_contrato=True))


def test_inelegivel_sem_cobranca_e_ok_e_com_cobranca_e_inconsistente():
    sem = auditar(_inelegivel_contrato=True, _na_fatura=False, _na_compra=False)
    com = auditar(_inelegivel_contrato=True)
    assert sem["Status"] == "OK"
    assert com["Tipo Inconsistência"] == "Sem elegibilidade (contrato/departamento)"


def test_periodo_de_experiencia_com_cobranca_e_inconsistente():
    r = auditar(_aguarda_elegibilidade=True, **{"Dt. Elegibilidade": "01/10/2026"})
    assert r["Tipo Inconsistência"] == "Período de experiência"
    assert "01/10/2026" in r["Inconsistência"]


def test_diferenca_fatura_x_contrato_usa_a_mensalidade_do_titular():
    # Total da fatura inclui dependente; a comparação com o contrato é pela mensalidade
    r = auditar(**{"Valor Fatura": 1500.0, "_vlr_mensalidade_fat": 426.21,
                   "Valor Contrato": 450.0})
    assert r["Dif. Fatura x Contrato"] == pytest.approx(-23.79)


def test_estatisticas_contam_ok_e_inconsistentes():
    df = aplicar_regras(pd.DataFrame([
        {"Tem Direito": "Sim", "_na_fatura": True, "_na_compra": True},
        {"Tem Direito": "Sim", "_na_fatura": False, "_na_compra": False},
    ]))
    stats = calcular_stats(df)
    assert (stats["total"], stats["ok"], stats["inconsistente"]) == (2, 1, 1)


def test_incluidos_no_mes_le_data_brasileira():
    df = pd.DataFrame({"Data Inclusão": ["07/10/2026", "10/07/2026", ""]})
    assert len(identificar_incluidos_mes(df, "10/2026")) == 1


# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("texto_plano, valor, esperado", [
    ("Sim com coparticipação após experiência", "", (True, True)),
    ("Sim com coparticipação imediato", "", (True, False)),
    ("Não", "450,00", (False, False)),
    ("", "450,00 - Auxiliar Agrícola II - Pesquisa NÃO tem plano", (True, False)),
    ("", "Não", (False, False)),
    ("", "", (False, False)),
    ("", "Sim", (True, False)),
])
def test_classificar_plano(texto_plano, valor, esperado):
    assert _classificar_plano(valor, texto_plano) == esperado


@pytest.mark.parametrize("bruto, esperado", [
    ("R$ 1.234,56", 1234.56), ("403,20 titular", 403.20), ("1,234.56", 1234.56),
    ("", 0.0), ("-", 0.0), (None, 0.0),
])
def test_parse_brl(bruto, esperado):
    assert _parse_brl(bruto) == pytest.approx(esperado)


def test_matricula_comparavel():
    assert cod_func_chave("900295.0") == cod_func_chave(" 0900295 ") == "900295"


# --------------------------------------------------------------------------- #
def test_justificativa_reaproveitada_ignora_os_valores_do_mes():
    a = db.chave_inconsistencia("Valor empresa (R$ 739.24) difere do contrato (R$ 450.00)")
    b = db.chave_inconsistencia("Valor empresa (R$ 812.10) difere do contrato (R$ 450.00)")
    assert a == b


def test_justificativa_so_do_mes_nao_passa_para_o_seguinte():
    assert db.justificativa_herdavel("Cliente autorizou a cobrança")
    assert not db.justificativa_herdavel("Admissão na referência da fatura")
    assert not db.justificativa_herdavel("")


# --------------------------------------------------------------------------- #
def _inativo(cod, nome, empresa, admissao, demissao):
    return {"cod_func": cod, "_norm_func": nome, "funcionario": nome, "empresa": empresa,
            "admissao": admissao, "demissao": demissao}


def _ativo(cod, nome, empresa, admissao):
    return {"Cod. Funcionário": cod, "Funcionário": nome, "Empresa": empresa,
            "Dt. Admissão": admissao, "Dt. Demissão": "", "_desligado": False,
            "_sem_contrato": False}


def test_mesma_matricula_de_outra_empresa_nao_herda_a_demissao():
    # Caso de 21/10/2026: matrícula 60 existe na empresa 3 e na 4, mesma admissão.
    # Mesmo primeiro nome de propósito: aqui só a EMPRESA pode separar as duas.
    ativos = pd.DataFrame([_ativo("60", "MARIA TESTE UM", "4", "05/03/2024")])
    inativos = pd.DataFrame([_inativo("60", "MARIA TESTE DOIS", "3", "05/03/2024",
                                      "19/08/2026")])

    saida, _ = mesclar_desligados(ativos, inativos, "10/2026")

    assert not saida.iloc[0]["_desligado"]
    assert saida.iloc[0]["Dt. Demissão"] == ""


def test_mesma_matricula_e_empresa_com_outro_primeiro_nome_nao_herda_a_demissao():
    # Mesma empresa de propósito: aqui só o PRIMEIRO NOME pode separar as duas
    ativos = pd.DataFrame([_ativo("60", "FULANA DE TAL", "4", "05/03/2024")])
    inativos = pd.DataFrame([_inativo("60", "BELTRANO DA SILVA", "4", "05/03/2024",
                                      "19/08/2026")])

    saida, _ = mesclar_desligados(ativos, inativos, "10/2026")

    assert not saida.iloc[0]["_desligado"]
    assert saida.iloc[0]["Dt. Demissão"] == ""


def test_troca_de_sobrenome_na_mesma_empresa_continua_reconhecida():
    ativos = pd.DataFrame([_ativo("77", "LETICIA TESTE HUHN", "2", "01/02/2023")])
    inativos = pd.DataFrame([_inativo("77", "LETICIA TESTE", "2", "01/02/2023",
                                      "15/09/2026")])

    saida, _ = mesclar_desligados(ativos, inativos, "10/2026")

    assert saida.iloc[0]["_desligado"]
    assert saida.iloc[0]["Dt. Demissão"] == "15/09/2026"


def test_demissao_depois_do_periodo_preenche_a_data_mas_nao_desliga():
    ativos = pd.DataFrame([_ativo("88", "CICLANO TESTE", "1", "01/01/2025")])
    inativos = pd.DataFrame([_inativo("88", "CICLANO TESTE", "1", "01/01/2025",
                                      "05/11/2026")])

    saida, _ = mesclar_desligados(ativos, inativos, "10/2026")

    assert saida.iloc[0]["Dt. Demissão"] == "05/11/2026"
    assert not saida.iloc[0]["_desligado"]


def test_demissao_de_contrato_anterior_nao_desliga_o_atual():
    ativos = pd.DataFrame([_ativo("99", "RECONTRATADA TESTE", "1", "01/06/2026")])
    inativos = pd.DataFrame([_inativo("99", "RECONTRATADA TESTE", "1", "01/01/2025",
                                      "31/12/2025")])

    saida, _ = mesclar_desligados(ativos, inativos, "10/2026")

    assert not saida.iloc[0]["_desligado"]
