# 🏥 Auditoria Unimed

Sistema de auditoria de plano de saúde Unimed, desenvolvido para o setor de Departamento Pessoal.  
Cruza três fontes de dados e aponta automaticamente as inconsistências.

---

## O que o sistema faz

Compara três planilhas mensais e gera um relatório completo de auditoria:

| Fonte | O que representa |
|-------|-----------------|
| **Funcionários por Contrato** | Quem tem direito ao plano e qual o valor previsto |
| **Fatura Unimed (CSV)** | O que a Unimed cobrou no mês |
| **Compra / Lançamento** | O que foi lançado para pagamento no sistema |

---

## Regras de auditoria

- ✅ Tem direito e está na fatura com valor correto → **OK**
- ⚠️ Tem direito mas não consta na fatura → inconsistente
- ⚠️ Consta na fatura mas não tem lançamento de compra → inconsistente
- ⚠️ Sem direito ao plano mas consta na fatura → inconsistente
- ⚠️ Lançado na compra mas não consta na fatura → inconsistente
- ⚠️ Valor empresa (compra) diferente do valor do contrato → inconsistente
- ⚠️ Total compra (titular + dependentes) diferente do total da fatura → inconsistente
- ⚠️ Funcionário desligado sendo cobrado → inconsistente
- ⚠️ Consta na fatura sem vínculo identificado no contrato → inconsistente

---

## Telas do sistema

| Tela | Função |
|------|--------|
| **1 · Importação** | Recebe os arquivos, mostra as colunas encontradas e processa (com barra de andamento) |
| **2 · Inclusões** | Incluídos no mês e titulares novos em relação ao mês anterior, com o texto para colar |
| **3 · Exclusões** | Quem saiu da fatura em relação a um mês escolhido |
| **4 · Exclusões indevidas** | Desligados ainda cobrados e o prejuízo estimado |
| **5 · Auditoria e Aprovação** | Tabela completa, justificativa na própria célula, lote e fechamento do mês |
| **6 · Histórico** | Abre qualquer auditoria guardada sem importar de novo |
| **7 · Análises** | Custos, desvios, inconsistências e a evolução entre os meses |
| **Gestão de usuários** | Só administrador: quem tem acesso, papel, e-mail de acesso |
| **Meu tema** | Vidro ou Relevo, claro ou escuro, cor de destaque |

O seletor no topo troca a auditoria aberta em todas as telas.

---

## Instalação

1. Python 3.10+ e acesso à rede da Setrata (o pacote da casa vem da CentralFeedback).
2. `instalar.bat` (ou `python -m venv venv` + `venv\Scripts\pip install -r requirements.txt`).
3. `iniciar.bat` (ou `python servidor.py`) — abre em `http://localhost:8055`.

---

## Como roda (V2 — Dash, padrão da casa)

- `servidor.py` sobe o app (Flask + Dash, servido pelo waitress) na porta `UNIMED_PORTA` (padrão 8055).
- **Camada da casa** (`setrata-casa`, instalado pela CentralFeedback): login (Google da equipe +
  `admin@` local), porta de manutenção, feedback com triagem, e-mail de acesso, PWA. As rotas ficam
  em `/_casa/...`. O app só escreve `casa/adaptador.py` (como guarda gente e abre sessão) e
  `casa/instalar.py` (a ligação). **Mudanças nesses dois passam pelo TI.**
- **Modo restrito**: só entra quem o administrador cadastrou em Gestão de usuários.
- Segredos em `secrets/` (fora do git): `config.env` (`GOOGLE_CLIENT_ID/SECRET`, `UNIMED_SECRET_KEY`,
  `UNIMED_PUBLIC_URL`, `CENTRAL_URL`, `CENTRAL_CODIGO_TOKEN`) e `admin-local.txt` (senha do `admin@`,
  12+ caracteres). Sem `config.env` o app sobe só com o `admin@` local.
- Cálculo e regras continuam em `app/` (processamento, regras, db, exportação, exclusões indevidas),
  sem mudança. As telas estão em `web/telas/`; o trabalho de cada tela, em `web/servico*.py`.
- Testes: `python -m pytest` — inclui a suíte de contrato da casa (`tests/test_casa_contrato.py`).

---

## Estrutura das planilhas

### Funcionários por Contrato
| Coluna | Campo |
|--------|-------|
| D | Nome do Funcionário |
| G | Departamento |
| H | Data de Admissão |
| L | Valor do Plano de Saúde |

### Compra / Lançamento
| Coluna | Campo |
|--------|-------|
| F | Nome do Funcionário |
| K | Valor Empresa (comparado com o contrato) |
| L | Valor Funcionário |

> A planilha de compra pode ter múltiplas linhas por funcionário (titular + dependentes). O sistema agrupa automaticamente e soma todos os valores antes de comparar com a fatura.

### Fatura Unimed (CSV)
O sistema considera apenas as linhas com descrição:
- `Mensalidade/Contribuição Saúde`
- `Conta médica`

---

## Tecnologias

- **Dash** (Flask) + **dash-ag-grid** — interface web
- **setrata-casa** — login, feedback e camada da casa
- **Pandas** — cruzamento de dados
- **Openpyxl** — exportação para Excel
- **SQLite** — histórico de auditorias

---

## Versão atual

Veja o arquivo `CHANGELOG.md` para o histórico completo de versões.
