# CHANGELOG — Auditoria Unimed

## Regras de versionamento

| Campo   | Quando incrementar                                   |
|---------|------------------------------------------------------|
| `major` | Mudança estrutural incompatível (banco, arquitetura) |
| `minor` | Novo recurso ou funcionalidade adicionada            |
| `patch` | Correção de bug (sem novo recurso)                   |

---

## Histórico

### V1.4.11 — 2026-05-05
**Pré-visualização de colunas alinhada ao processamento real**
- `pages/1_Importação.py` — o painel de colunas detectadas agora usa a mesma lógica de detecção de cabeçalho do processamento real para Excel e CSV, reduzindo falsos `não encontrado` na importação.
- Mantida a correlação por nomenclatura ampliada para `Contratos` e `Compra`, sem dependência de coluna fixa.

### V1.4.10 — 2026-05-05
**Correlação ampliada por nomenclatura + gráficos analíticos**
- `app/processamento.py` — ampliada a lista de nomes correlatos para leitura de `Contratos` e `Compra`, cobrindo variações como `Funcionária`, `Matrícula`, `Setor`, `Unidade`, `Valor Mensal`, `Mensalidade Titular`, `Patronal`, `Custo Empresa`, `Desconto Funcionário` e similares, sem voltar a usar posição fixa.
- `pages/1_Importação.py` — painel de colunas detectadas alinhado com os novos nomes correlatos para facilitar a conferência do mapeamento.
- `pages/2_Auditoria.py` — adicionados gráficos de gastos por `Departamento` e `Contrato Adm.` e gráficos de desvio por essas mesmas categorias.

### V1.4.09 — 2026-05-05
**Remoção de duplicatas idênticas na consolidação da fatura**
- `app/processamento.py` — `ler_faturas_csv`: antes de consolidar por titular, agora remove duplicatas exatas do mesmo conjunto de valores para evitar dobrar o `Valor Fatura` quando o mesmo conteúdo é enviado mais de uma vez.
- Corrige casos como o de `JEANE FONTINELE RIBEIRO DE SOUSA`, em que o total da fatura estava sendo somado em dobro.

### V1.4.08 — 2026-05-05
**Mapeamento 100% por nomenclatura das colunas**
- `app/processamento.py` — removidos os fallbacks por posição nas leituras de `Contratos` e `Compra`; a identificação dos campos agora depende apenas do nome das colunas.
- `pages/1_Importação.py` — painel de colunas detectadas atualizado para refletir apenas detecção por nomenclatura, sem referências a colunas fixas.

### V1.4.07 — 2026-05-05
**Correção de fallback da coluna Contrato Adm.**
- `app/processamento.py` — `Contrato Adm.` nos contratos agora usa fallback fixo na coluna `F` (índice 5) quando a detecção por nome não encontrar o campo.

### V1.4.06 — 2026-05-05
**Filtros sempre visíveis + recálculo ao carregar histórico**
- `pages/2_Auditoria.py` e `pages/3_Inclusões.py` — filtros de `Departamento` e `Contrato Adm.` agora aparecem sempre, mesmo quando a auditoria carregada não tem valores disponíveis para esses campos.
- `app/regras.py` — `Dif. Contrato x Compra` é recalculada na aplicação das regras para nunca exibir valor negativo; quando o contrato é maior que a compra empresa, a diferença fica `0,00`.
- `pages/1_Importação.py` e `pages/4_Histórico.py` — auditorias carregadas do banco agora são recalculadas com as regras atuais, evitando continuar exibindo divergências antigas já corrigidas.

### V1.4.05 — 2026-05-05
**Contrato Adm. em telas/exports + divergência positiva no contrato**
- `app/processamento.py` — `ler_contratos`: suporte opcional à coluna `Contrato Adm.` por detecção de nome.
- `app/processamento.py` — `cruzar`: campo `Contrato Adm.` adicionado ao resultado da auditoria e às inclusões; `Dif. Contrato x Compra` agora só mostra valor positivo quando a compra empresa excede o contrato.
- `app/regras.py` — regra R5 ajustada para sinalizar apenas quando `Valor Empresa (Compra)` é maior que `Valor Contrato`.
- `pages/1_Importação.py` — painel de colunas detectadas passa a mostrar `Contrato Adm.` quando existir no arquivo de contratos.
- `pages/2_Auditoria.py` — novo filtro por `Contrato Adm.` e coluna exibida na tabela da auditoria.
- `pages/3_Inclusões.py` — coluna `Contrato Adm.` adicionada na aba de inclusões, com filtros de `Departamento` e `Contrato Adm.`.
- `app/exportacao.py` — `Contrato Adm.` incluído nas abas `Auditoria` e `Inclusões do Mês` do Excel.

### V1.4.04 — 2026-05-05
**Correções de leitura da fatura + inclusões por período de referência**
- `app/processamento.py` — `_ler_planilha`: CSV agora também detecta automaticamente a linha correta de cabeçalho, evitando faturas lidas com cabeçalho errado e totais zerados.
- `app/processamento.py` — `ler_fatura_csv`: valida colunas obrigatórias da fatura e falha com erro explícito quando não encontra linhas válidas de `Conta médica` ou `Mensalidade/Contribuição Saúde`.
- `app/processamento.py` — normalização de texto ajustada para reconhecer descrições com encoding quebrado, como `Conta mÃ©dica` e `Mensalidade/ContribuiÃ§Ã£o SaÃºde`.
- `app/processamento.py` — `Data Inclusão` passa a considerar apenas linhas de titular.
- `app/regras.py` — filtro de inclusões do mês agora aceita período manual em `MM/AA` ou `MM/AAAA` e compara datas como `05/04/26` corretamente.
- `pages/1_Importação.py` — campo de período atualizado para aceitar `04/26` e `04/2026`.

### V1.4.03 — 2026-05-05
**Correção crítica: filtro de descrição da fatura era parcial, somava linhas erradas**
- `app/processamento.py` — `ler_fatura_csv`: substituído filtro por substring (muito amplo) por
  correspondência EXATA:
  - `"Conta médica"` → aceito se desc_norm == "CONTA MEDICA"
  - `"Mensalidade/Contribuição Saúde"` → aceito se contém "MENSALIDADE" E "CONTRIBUICAO"
  - Qualquer outra linha (odonto, previdência, taxas, duplicatas, etc.) é ignorada
- Corrige total incorreto de ALINE FRANCELINO (sistema mostrava R$ 652,86 ou R$ 452,86;
  correto é R$ 293,79 + R$ 150,00 = R$ 443,79).

### V1.4.02 — 2026-05-05
**Correção: recarregar auditoria retornava vazio (pandas 3.x)**
- `app/db.py` — `carregar_auditoria`: `pd.read_json(df_json)` substituído por `pd.read_json(io.StringIO(df_json))`. No pandas 3.x passar string diretamente retorna DataFrame vazio silenciosamente; `io.StringIO` é obrigatório.
- Correção de cálculo: `vlr_fatura` na fatura CSV agora inclui coparticipação ("Conta médica") além da mensalidade — total correto (ex: ALINE FRANCELINO: 293,79 + 150,00 = 443,79).

### V1.4.01 — 2026-05-05
**Correção: botão "Recarregar auditoria" não funcionava**
- Removido `st.rerun()` que cancelava a exibição do resultado antes de o usuário ver.
- Adicionado feedback de erro quando o banco não tem dados para carregar.
- Botão agora é `type="primary"` e ocupa a largura toda para ser mais visível.
- Se auditoria já está na sessão, mostra resumo de status em vez do botão.

### V1.4.0 — 2026-05-05
**Fallback por posição de coluna + filtro de descrição na fatura CSV**
- `app/processamento.py` — `ler_contratos` e `ler_compra`: quando a detecção por keyword falha, usa a posição da coluna informada pela Graziella (contratos: D=3, G=6, H=7, L=11; compra: F=5, K=10, L=11). Keyword ainda é o método primário; posição é fallback garantido.
- `app/processamento.py` — `ler_fatura_csv`: passa a filtrar apenas linhas com descrição "Conta médica" ou "Mensalidade/Contribuição Saúde". Demais linhas são ignoradas para evitar duplicação.
- `pages/1_Importação.py`: painel de diagnóstico agora mostra TODAS as colunas reais encontradas no arquivo, facilitando identificação de problemas de mapeamento.

### V1.3.0 — 2026-05-05
**Correção crítica de leitura + regras de auditoria por estrutura real das planilhas**
- `app/processamento.py` — `_ler_planilha`: detecta automaticamente em qual linha está o cabeçalho (testa até a 8ª linha), resolvendo falha em planilhas com títulos antes dos dados.
- `app/processamento.py` — `ler_contratos`: remove dependência de "Tipo de Contrato" (campo não existe); elegibilidade agora = tem valor previsto no plano. Keywords de detecção de colunas expandidas.
- `app/processamento.py` — `ler_compra`: agrupa TODAS as linhas por funcionário (titular + dependentes) antes de comparar. `vlr_empresa` = parcela empresa (coluna K, compara com contrato); `vlr_compra_total` = soma de todas as linhas (compara com fatura).
- `app/regras.py`: regras R5 e R6 separadas — R5 compara empresa vs contrato; R6 compara total compra vs fatura.
- Colunas renomeadas: "Valor Empresa (Compra)", "Valor Compra Total", "Dif. Contrato x Compra", "Dif. Fatura x Compra".
- Exportação Excel e tela de auditoria atualizadas com as novas colunas.

### V1.2.0 — 2026-05-05
**UX: remoção do mapeamento de colunas + auto-recarregamento da última auditoria**
- `pages/1_Importação.py`: seção de "Mapeamento de Colunas" removida da interface — detecção de colunas agora é 100% automática e silenciosa. Exibe apenas um painel colapsado "Colunas detectadas" para conferência opcional.
- Bug corrigido: leitura de colunas dos CSVs agora usa `nrows=3` em vez de `nrows=0`, permitindo que o sniffer de separador funcione corretamente.
- Período e arquivos obrigatórios agora têm avisos claros que explicam por que o botão está desabilitado.
- Novo bloco "Recarregar última auditoria" no topo da página: ao abrir o sistema, oferece recarregar a última auditoria salva com um clique — sem precisar fazer upload dos arquivos novamente.
- `version.py`: bump para V1.2.0.

### V1.1.0 — 2026-05-05
**Upload de múltiplas faturas Unimed**
- `pages/1_Importação.py`: upload da fatura alterado para `accept_multiple_files=True`; legenda mostra quantos arquivos foram carregados.
- `app/processamento.py`: nova função `ler_faturas_csv(paths, col_map)` — lê cada arquivo separadamente com o mesmo mapeamento e consolida em um único DataFrame (soma valores por titular, mantém primeira data de inclusão).

### V1.0.0 — 2026-05-05
**Lançamento inicial**
- Sistema completo de auditoria Unimed em Streamlit (porta 8055).
- Cruzamento de 3 bases: Funcionários por Contrato × Fatura CSV Unimed × Planilha de Compra.
- Mapeamento flexível de colunas com autodetecção por keyword e persistência por cliente.
- 8 regras de auditoria: direito vs. fatura, compra vs. fatura, desligado, sem vínculo, valores divergentes, etc.
- Tela de Inclusões do Mês: detecta Data Inclusão do CSV e filtra pelo período de referência.
- Histórico em SQLite com recarregamento sem reprocessar.
- Aprovação com justificativa obrigatória por pendência.
- Exportação Excel com 3 abas: Auditoria, Inclusões, Justificativas.
- Inicialização automática com o Windows via atalho na pasta Startup.
