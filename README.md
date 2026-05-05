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
| **1 · Importação** | Carrega os arquivos, detecta as colunas automaticamente e processa |
| **2 · Auditoria** | Tabela completa com filtros, KPIs e exportação para Excel |
| **3 · Inclusões do Mês** | Funcionários incluídos no plano no período de referência |
| **4 · Histórico** | Recarrega qualquer auditoria anterior sem precisar reimportar |
| **5 · Aprovação** | Justificativa obrigatória para cada pendência antes de fechar o mês |

---

## Instalação

### Pré-requisito
- Python 3.10 ou superior instalado

### Passos

1. Baixe ou clone este repositório
2. Abra a pasta `auditoria-unimed`
3. Dê dois cliques em **`instalar.bat`** — instala tudo automaticamente
4. Após a instalação, dê dois cliques em **`iniciar.bat`** para abrir o sistema

O sistema abre no navegador em `http://localhost:8055`.

> O atalho de inicialização é criado automaticamente na pasta Startup do Windows — o sistema inicia junto com o computador.

---

## Como usar

### 1. Importe os arquivos
Na tela **1 · Importação**:
- Preencha o **mês de referência** (ex: `04/2026`)
- Carregue a planilha de **Funcionários por Contrato**
- Carregue as **faturas Unimed** em CSV (pode selecionar várias de uma vez)
- Carregue a planilha de **Compra / Lançamento**
- Clique em **▶ Processar Auditoria**

### 2. Analise o resultado
Na tela **2 · Auditoria**:
- Veja os KPIs: total, OK, inconsistências
- Filtre por status, departamento ou nome
- Exporte para Excel com um clique

### 3. Recarregue sem reimportar
Nas próximas vezes que abrir o sistema, clique em **"Carregar auditoria de MM/AAAA"** — os dados são recuperados do histórico automaticamente.

### 4. Aprove as pendências
Na tela **5 · Aprovação**, justifique cada inconsistência antes de fechar o mês.

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

- **Streamlit** — interface web
- **Pandas** — cruzamento de dados
- **Openpyxl** — exportação para Excel
- **SQLite** — histórico de auditorias

---

## Versão atual

Veja o arquivo `CHANGELOG.md` para o histórico completo de versões.
