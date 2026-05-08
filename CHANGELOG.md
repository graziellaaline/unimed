# CHANGELOG — Auditoria Unimed

## Regras de versionamento

| Campo   | Quando incrementar                                   |
|---------|------------------------------------------------------|
| `major` | Mudança estrutural incompatível (banco, arquitetura) |
| `minor` | Novo recurso ou funcionalidade adicionada            |
| `patch` | Correção de bug (sem novo recurso)                   |

---

## Histórico

### V1.5.03 — 2026-05-08
**Regras de elegibilidade ao plano de saúde por modalidade contratual + divergência quando inelegível tem cobrança**
- `app/processamento.py` — `ler_contratos`: substituída lista fixa `_CONTRATOS_INELEGIVEIS` por lógica baseada em palavras-chave:
  1. Qualquer contrato com `DETERMINADO` no nome → sem direito (regra geral).
  2. Exceção prioritária: `TERCEIRIZ*` (determinado ou indeterminado) + departamento contém `PLANALTINA` ou `298` → sempre elegível.
  3. Demais modalidades → segue valor da planilha de contratos (`vlr_contrato > 0`).
- `app/regras.py` — `aplicar_regras`: funcionário inelegível **sem** cobrança → `OK`; inelegível **com** cobrança na fatura e/ou na compra → `Inconsistente` com descrição "Sem elegibilidade ao plano de saúde conforme regras contratuais/departamento — [cobrança indevida]" e ação "Verificar e solicitar exclusão do plano".

### V1.5.02 — 2026-05-08
**Dependentes da fatura Unimed não aparecem mais como linhas na auditoria**
- `app/processamento.py` — `ler_fatura_csv`: reordenada prioridade da detecção de colunas — coluna "Titular" (nome do funcionário) agora tem precedência sobre coluna "Beneficiário" (nome individual); quando a fatura tem ambas as colunas, todos os lançamentos (titular e dependentes) são agrupados pelo nome do titular automaticamente.
- `app/processamento.py` — `ler_fatura_csv`: adicionado fallback por ordem de arquivo — quando a coluna detectada é "Beneficiário" e o dependente tem nome diferente do titular, o valor é acumulado no último titular visto; dependente nunca vira linha autônoma na auditoria.
- Ambas as estratégias se complementam: Fix 1 cobre faturas com coluna "Titular" separada; Fix 2 cobre faturas com coluna única de nomes.

### V1.5.01 — 2026-05-08
**Dependentes da planilha de compra não aparecem mais como linhas na auditoria**
- `app/processamento.py` — `ler_compra`: detecta coluna de tipo (Tipo/Categoria/Vínculo/Grau/Tp. Beneficiário) na planilha de compra; linhas de dependente são acumuladas no titular correspondente (por cod_func ou por ordem no arquivo) e nunca viram linhas autônomas; apenas titulares aparecem na tabela de auditoria.
- `COMPRA_HEADER_GROUPS` — adicionado grupo de detecção da coluna de tipo beneficiário.

### V1.5.00 — 2026-05-08
**Aprovação como tabela + Dt. Admissão/Demissão + correção de valor com texto**
- `pages/5_Aprovação.py` — interface completamente redesenhada: tabela interativa (`st.data_editor`) substitui os cards expansíveis; coluna `☑` para seleção de linhas; coluna `Justificativa` editável inline; botão **Salvar edições da tabela**; bloco **Justificar em lote** aplica justificativa a todos os selecionados; opção de gravar para meses futuros mantida.
- `pages/5_Aprovação.py` — colunas `Dt. Admissão` e `Dt. Demissão` adicionadas à tabela de pendências.
- `pages/2_Auditoria.py` — colunas `Dt. Admissão` e `Dt. Demissão` adicionadas à tabela de auditoria (antes só `Dt. Admissão` estava presente).
- `app/processamento.py` — `_parse_brl`: usa regex para extrair o primeiro bloco numérico, corrigindo células com texto junto ao valor (ex: `"403,20 titular"` retornava 0 e o funcionário aparecia como sem direito).

### V1.4.22 — 2026-05-06
**Aprovação sem dependentes isolados + app recarregado**
- `app/processamento.py` — componentes da fatura (`mensalidade`, `dependente`, `coparticipação`) passaram a ser carregados também no resultado da auditoria para apoiar regras de aprovação.
- `pages/5_Aprovação.py` — dependentes na fatura não entram mais na aprovação por si só; só permanecem quando houver divergência real entre compra e fatura.
- Aplicação local reiniciada para garantir que a interface use o código atualizado.

### V1.4.20 — 2026-05-06
**Correção de falso positivo no match por nome da fatura**
- `app/processamento.py` — o match por similaridade entre contrato e fatura foi endurecido para evitar casar pessoas diferentes apenas por sobrenome parecido.
- Corrige o caso de `LEANDRO DE MELO PEREIRA`, que estava sendo associado indevidamente à fatura de `ALEXSANDRE DA SILVA PEREIRA`.
- Após a correção, `LEANDRO DE MELO PEREIRA` passa a ficar corretamente como `não consta na fatura`.

### V1.4.19 — 2026-05-06
**Correção de falso desvio fora da comparação válida**
- `app/regras.py` — `Dif. Fatura x Compra` agora só é calculada quando o funcionário está simultaneamente na fatura e na compra.
- Corrige casos como `LEANDRO DE MELO PEREIRA`, em que a pendência correta era apenas `Consta na fatura mas não há lançamento de compra`, mas a tela também mostrava desvio indevido.
- Revisão na auditoria atual eliminou essa mesma natureza de falso desvio nas demais linhas equivalentes.

### V1.4.18 — 2026-05-06
**Filtro de inconsistência em Aprovação corrigido**
- `pages/5_Aprovação.py` — o seletor `Mesma inconsistência para lote` agora filtra de fato a lista de pendências exibidas na tela.
- `Salvar em lote` segue aplicando a justificativa a todas as pendências com a inconsistência selecionada.

### V1.4.17 — 2026-05-06
**Leitura ajustada com base nos arquivos reais da auditoria FIOTI**
- `app/processamento.py` — correlação de nomes refinada com base nos arquivos reais em `G:\Drives compartilhados\#9 - DP\SETRATA\AUDITORIAS\FIOTI\04.2026\SETRATA\FOLHA`.
- `Contratos` validados com cabeçalhos como `Cód. Empresa`, `Cód. Funcionário`, `Funcionário`, `Contrato Adm.`, `Departamento`, `Valor Plano de Saúde` e `Dt. Admissão`.
- `Compra` validada com cabeçalhos como `Cód. Emp.`, `Cód. Func.`, `Funcionário`, `Despartamento`, `Valor. Empresa` e `Valor. Beneficário`.
- `Fatura` validada com CSVs contendo `Beneficiário`, `Titular`, `Categoria`, `Data Inclusão`, `Descrição do item` e `Valor`.
- Ajuste garante alimentação real de `Valor Fatura` e `Valor Compra`, em vez de apenas `Valor Contrato`.

### V1.4.16 — 2026-05-06
**Aprovação em lote e justificativas reaproveitáveis**
- `app/db.py` — criada persistência de justificativas modelo reutilizáveis por `cliente + funcionário + inconsistência`.
- `pages/5_Aprovação.py` — nova opção de salvar justificativa em lote para todas as pendências com a mesma inconsistência.
- `pages/5_Aprovação.py` — nova opção para gravar a justificativa para meses futuros quando `Funcionário + Inconsistência` forem exatamente iguais.
- `pages/5_Aprovação.py` — no mês seguinte, pendências com correspondência exata já entram justificadas automaticamente, mas continuam como pendências até a aprovação final da auditoria.

### V1.4.15 — 2026-05-06
**Prioridade correta para nome e código da empresa**
- `app/processamento.py` — leitura do campo de `Funcionário` em `Contratos`, `Compra` e `Titular` na `Fatura` passou a priorizar cabeçalhos claramente de nome, evitando cair em colunas de matrícula/código quando houver ambiguidades.
- `app/processamento.py` — adicionado campo opcional `Empresa` por nomenclatura para exibição curta por código.
- `pages/1_Importação.py` — prévia da importação alinhada com a mesma prioridade de escolha da coluna de nome.
- `pages/2_Auditoria.py` e `pages/3_Inclusões.py` — filtro e coluna `Empresa` adicionados para exibir apenas o código na tela.

### V1.4.14 — 2026-05-06
**Consistência visual na aba de Inclusões**
- `pages/3_Inclusões.py` — validado o layout responsivo dos filtros em duas colunas para `Departamento` e `Contrato Adm.`, mantendo consistência com o restante da aplicação.

### V1.4.13 — 2026-05-06
**Filtros da auditoria mais responsivos**
- `pages/2_Auditoria.py` — filtros reorganizados em duas linhas para manter o campo `Funcionário` visível e melhorar a responsividade da área de filtros.
- Mantida a regra de gráficos acima dos filtros, reagindo ao conjunto filtrado.

### V1.4.12 — 2026-05-06
**Detecção compartilhada entre prévia e processamento**
- `app/processamento.py` — grupos de nomes esperados para `Contratos`, `Compra` e `Fatura` foram centralizados e reutilizados na escolha do melhor cabeçalho.
- `pages/1_Importação.py` — a pré-visualização de colunas agora usa o mesmo score de cabeçalho do processamento real para cada tipo de arquivo, reduzindo casos em que a tela mostrava `não encontrado` por escolher uma linha errada como cabeçalho.

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
