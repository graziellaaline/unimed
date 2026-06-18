# CHANGELOG — Auditoria Unimed

## Regras de versionamento

| Campo   | Quando incrementar                                   |
|---------|------------------------------------------------------|
| `major` | Mudança estrutural incompatível (banco, arquitetura) |
| `minor` | Novo recurso ou funcionalidade adicionada            |
| `patch` | Correção de bug (sem novo recurso)                   |

---

## Histórico

### V1.13.0 — 2026-06-18
- Mudança: gráficos de Custo e Desvio removidos da aba **5 · Auditoria** (que fica só com filtros + tabela) e centralizados na aba **8 · Análises**.
- Novo: gráfico de Custo também por Contrato Adm. (além de Departamento e Empresa).
- Novo: cards de total de desvio (Contrato x Compra / Fatura x Compra) e tabela de detalhe com os registros individuais de maior desvio — para localizar rapidamente a origem de uma diferença, sem precisar pedir análise manual.
- Correção de robustez: página recalcula `Tipo Inconsistência`/colunas de desvio automaticamente se a auditoria em sessão tiver sido carregada por código antigo, e normaliza valores de Status/Departamento/Empresa antes de agrupar — evita gráficos aparecerem vazios por sessão desatualizada.
- Correção: gráfico "Evolução entre períodos" agora ordena por data real (mês/ano) em vez de ordem alfabética do texto do período.

### V1.12.0 — 2026-06-18
- Novo: tela **8 · Análises**, painel dedicado de gráficos para análise gerencial — custos por Departamento/Empresa, desvios por Departamento/Contrato Adm., inconsistências por Departamento/Tipo/Empresa/Contrato Adm., e evolução de Total Fatura x Total Compra e quantidade de inconsistências entre períodos já processados.

### V1.11.1 — 2026-06-18
- Novo: na aba Aprovação, a coluna "Sit." agora é uma caixa de marcação editável — desmarcar um item justificado o reverte para Pendente (remove a justificativa salva no banco), sem precisar apagar o texto manualmente.

### V1.11.0 — 2026-06-18
- Novo: filtro "Tipo de Inconsistência" na tela de Auditoria, com categorias estáveis (ex.: "Direito sem fatura", "Desligado na fatura", "Valor empresa ≠ contrato") independentes dos valores numéricos do texto — permite isolar um tipo específico de inconsistência mesmo quando um registro acumula vários motivos.

### V1.10.5 — 2026-06-17
- Ajuste: removido da tela de Importação o aviso "X desligado(s) sem correspondência na base ativa" — a planilha de inativos acumula desligados de qualquer período, então é normal ter centenas sem relação com o mês atual; não era uma inconsistência acionável e só gerava ruído (a pedido da usuária).

### V1.10.4 — 2026-06-17
- Ajuste: na aba Exclusões, Valor Fatura/Mensalidade/Dependentes/Coparticipação agora são exibidos zerados — esses valores vinham da fatura do mês ANTERIOR (quando a pessoa ainda constava), e por definição ninguém da lista de exclusões tem cobrança na fatura atual. A pedido da usuária, para não dar impressão de cobrança vigente.

### V1.10.3 — 2026-06-17
- Novo: botão "📥 Exportar Excel (Exclusões)" na página de Exclusões, com a mesma quebra (Mensalidade/Dependentes/Coparticipação/Composição da Cobrança) exibida na tela.

### V1.10.2 — 2026-06-17
- Novo: tabela de Exclusões agora mostra a quebra do valor cobrado (Mensalidade / Dependentes / Coparticipação) e uma coluna "Composição da Cobrança", para saber se a cobrança de um desligado é mensalidade recorrente, coparticipação por uso já ocorrido, ou ambos — relevante para decidir se cabe exclusão retroativa.

### V1.10.1 — 2026-06-17
- Ajuste: texto de Inclusões/Exclusões para colar na Descrição agora é agrupado por Departamento, com contagem total no rodapé (TOTAL DE INCLUSÕES/EXCLUSÕES) para confirmar que todos entraram no arquivo.

### V1.10.0 — 2026-06-17
- Novo: botão "📋 Texto para copiar e colar (Descrição)" nas páginas de Inclusões e Exclusões — gera um bloco de texto por funcionário (FUNCIONARIO / INCLUSÃO ou EXCLUSÃO / VALOR) no formato usado para colar na Descrição de outro sistema, com opção de baixar .txt.

### V1.9.4 — 2026-06-17
- Fix: ao mesclar dados de desligados, "Tem Direito" e "Valor Contrato" ficavam com valor de fallback ("—" / R$ 0,00) mesmo quando o desligado tinha contrato real (ex: Temporário) com direito definido. Agora esses dois campos também são preenchidos a partir do registro encontrado na planilha de inativos.

### V1.9.3 — 2026-06-17
- Fix: instalado pacote `xlrd` (faltava no venv), corrigindo erro "Não foi possível encontrar o cabeçalho" ao importar planilhas de contratos/desligados em formato `.xls` (Excel 97-2003).

### V1.9.2 — 2026-05-14
**Aprovação: remove UI de ordem de colunas + Exclusões: correção de erro ValueError**
- `pages/6_Aprovação.py` — removido expander "📋 Ordem das colunas" e botão "💾 Salvar esta ordem". O sistema carrega automaticamente a última ordem gravada (JSON) sem interação do usuário.
- `pages/3_Exclusões.py` — corrigido `ValueError: truth value of a Series is ambiguous` no lookup do dict de inativos: substituído `or` entre Series por dois `get()` separados com verificação de None explícita.

### V1.9.1 — 2026-05-14
**Exclusões: upload da planilha de inativos diretamente na página**
- `pages/3_Exclusões.py` — quando o arquivo de inativos não está salvo no banco (ou ainda há exclusões sem dados), exibe widget de upload da planilha de inativos diretamente na página. Permite enriquecer Empresa/Departamento/Contrato dos excluídos sem precisar reprocessar toda a importação.

### V1.9.0 — 2026-05-14
**Exclusões: enriquecimento de dados via planilha de inativos**
- `pages/3_Exclusões.py` — após identificar os excluídos do período anterior, busca os dados faltantes (Empresa, Departamento, Contrato Adm., Dt. Admissão, Dt. Demissão) no arquivo de inativos salvo para o período atual. Corrige casos como ALAN GABRIEL APARECIDO DE SOUZA DA SILVA que aparecem sem informações por serem _sem_contrato no período anterior.

### V1.8.9 — 2026-05-14
**Reordenação do menu + Exclusões Indevidas: matching matrícula+nome e status "Excluído — com cobrança"**
- Páginas renomeadas na nova ordem: 1·Importação, 2·Inclusões, 3·Exclusões, 4·Auditoria Exclusões Indevidas, 5·Auditoria, 6·Aprovação, 7·Histórico. `main.py` atualizado.
- `pages/4_Auditoria_Exclusões_Indevidas.py` — fat_lookup agora usa chave dupla (cod_func + _norm) idêntica à regra de mesclar_desligados; valida que demissão > admissão do contrato atual antes de incluir o caso (corrige GUSTAVO). Novo status "🔶 EXCLUÍDO — COM COBRANÇA MÉDICA" quando apenas Conta médica está sendo cobrada (mensalidade = R$ 0,00).

### V1.8.8 — 2026-05-14
**Exclusões Indevidas: nova coluna "O que está sendo cobrado"**
- `pages/6_Auditoria_Exclusões_Indevidas.py` — coluna "O que está sendo cobrado" adicionada à tabela, usando os campos `_vlr_mensalidade_fat`, `_vlr_dependente_fat` e `_vlr_copart_fat` do df_audit para mostrar "Mensalidade/Contribuição Saúde", "Dependente", "Conta médica" (ou combinações). A coluna aparece também na exportação Excel.

### V1.8.7 — 2026-05-14
**Correção: "None" nas datas + sem_contrato sem matrícula voltam a ser preenchidos**
- `app/processamento.py` — `mesclar_desligados`: funcionários _sem_contrato (sem matrícula no ativo, ex: aparecem só na fatura) continuam sendo localizados por nome na planilha de inativos para preenchimento de empresa/dept/admissão/demissão. A regra estrita mat+nome só se aplica a quem tem matrícula no ativo.
- `pages/5_Aprovação.py` — conversão de datas limpa explicitamente strings "None"/"nan"/"NaT" antes de `pd.to_datetime`, garantindo que células vazias apareçam em branco (não "None").

### V1.8.6 — 2026-05-14
**Correção: demissão ignorada quando data é anterior à admissão do contrato atual + remoção do CPF**
- `app/processamento.py` — `mesclar_desligados`: após encontrar par matrícula+nome, valida que a data de demissão é POSTERIOR à data de admissão do contrato ativo. Se a demissão for anterior, ignora (é contrato anterior encerrado — pessoa foi recontratada). Corrige casos como GUSTAVO FERREIRA MARTINS.
- `app/processamento.py` — remove completamente o campo CPF: não é lido de contratos, não é propagado no cruzamento, não é usado em nenhum matching. Matching é exclusivamente por matrícula+nome.

### V1.8.5 — 2026-05-14
**Regra de desligamento: vínculo exige matrícula+nome idênticos (sem fallback por nome)**
- `app/processamento.py` — `mesclar_desligados` remove o fallback por nome. A data de demissão só é preenchida quando matrícula E nome forem exatamente iguais nas duas planilhas. Nome igual com matrícula diferente = novo contrato, não preenche demissão. Relatório remove "via_nome" (não há mais vínculos por nome apenas).
- `pages/1_Importação.py` — `_mostrar_relatorio_desligados` atualizada para refletir nova semântica do relatório.

### V1.8.4 — 2026-05-14
**Aba Inclusões: recalculo imediato + critério duplo (Data Inclusão + novos vs período anterior)**
- `pages/3_Inclusões.py` — auto-carrega auditoria do banco (não dependia de sessão prévia); sempre recalcula a partir do df_audit atual (elimina stale de sessão). Dois critérios combinados: (1) titulares cuja "Data Inclusão" da fatura coincide com o mês/ano da auditoria; (2) titulares presentes na fatura atual que não estavam na fatura do período anterior — cobre inclusões retroativas. Coluna "Origem" explica de qual critério o registro veio. KPIs separados por critério.

### V1.8.3 — 2026-05-14
**Correção: desligados lidos com ler_contratos + preenchimento completo de campos ausentes**
- `app/processamento.py` — `mesclar_desligados` reescrita para aceitar a saída de `ler_contratos` (planilha de inativos com mesma estrutura da de ativos). Além de Dt. Demissão e _desligado, preenche Empresa, Departamento, Contrato Adm., Dt. Admissão e Cod. Funcionário para funcionários que apareciam só na fatura (_sem_contrato=True). Matching por cod_func+_norm_func (principal) e _norm_func apenas (fallback).
- `pages/1_Importação.py` — usa `ler_contratos` (não mais `ler_desligados`) para ler a planilha de inativos, garantindo que a coluna Dt. Demissão seja lida com a mesma lógica de parsing dos contratos ativos.
- `pages/6_Auditoria_Exclusões_Indevidas.py` — detecta automaticamente se df_desligados está em formato df_cont ou legado; mescla com mesclar_desligados usando o formato correto.

### V1.8.2 — 2026-05-14
**Correção: critério de matching de desligados alterado para Matrícula+Nome**
- `app/processamento.py` — `mesclar_desligados` usa agora **matrícula + nome** (ambos devem coincidir) como critério principal de vínculo entre a planilha de desligados e a base de contratos. Fallback para nome-apenas quando matrícula não está disponível em algum dos lados. Remove matching isolado por CPF ou matrícula que causava falsos positivos.

### V1.8.1 — 2026-05-14
**Correções pós-V1.8.0: datas futuras, "None" e mesclagem retroativa**
- `app/processamento.py` — `mesclar_desligados` recebe `periodo` e só marca `_desligado=True` quando a demissão ocorreu até o último dia do mês auditado; demissões futuras preenchem `Dt. Demissão` para visualização mas não geram alerta.
- `pages/5_Aprovação.py` — colunas de data mantidas como `pd.Timestamp` (sem `.dt.date`) para que células vazias apareçam em branco em vez de "None".
- `pages/6_Auditoria_Exclusões_Indevidas.py` — ao carregar a planilha de desligados (por upload manual, sessão ou banco), o sistema chama `mesclar_desligados` no `df_audit` da sessão e atualiza as regras; garante que `Dt. Demissão` apareça imediatamente nas abas Auditoria, Aprovação e Exclusões sem reprocessamento completo.

### V1.8.0 — 2026-05-14
**Novo: upload centralizado da planilha de desligados na Importação**
- `pages/1_Importação.py` — quarto uploader "🚫 Funcionários Desligados" (opcional). Ao processar, a planilha é mesclada com a auditoria antes das regras, atualizando `Dt. Demissão` e `_desligado` de cada funcionário. Relatório de inconsistências exibido após a importação (não encontrados, vínculos por nome, sem data, pendências).
- `app/processamento.py` — novo helper `_limpar_cpf()`, CPF lido opcionalmente da planilha de contratos e propagado no cruzamento; nova função `mesclar_desligados(df_audit, df_desl)` que faz o vínculo por CPF → matrícula (Cod. Funcionário) → nome normalizado e retorna relatório de inconsistências.
- `app/db.py` — `carregar_arquivos_auditoria` inicializa chave `"desligados"` no dict de retorno.
- `pages/6_Auditoria_Exclusões_Indevidas.py` — auto-carrega desligados da sessão (importados em 1 · Importação) ou do arquivo salvo no banco; upload manual continua disponível como substituição. Todas as abas (2, 3, 5, 6) usam `Dt. Demissão` já consolidada sem novo upload.
- CPF é campo interno de matching — não exibido em nenhuma tabela ou exportação.

### V1.7.3 — 2026-05-14
**Correção: falsa coparticipação atribuída ao titular anterior + duplicata no contratos + datas na Aprovação**
- `app/processamento.py` — `ler_fatura_csv`: quando a coluna detectada é "Titular" (nome igual em todas as linhas da família), não faz mais fallback para o último titular visto. Corrige caso onde coparticipação de um funcionário (MAURICIO ALEXANDRE CRUZ) era somada incorretamente ao titular anterior (MATHEWS OLIVEIRA MOTA).
- `app/processamento.py` — `ler_contratos`: remove cadastro duplicado do mesmo funcionário (mesmo cod_func + mesmo nome normalizado), mantendo apenas a primeira ocorrência. Corrige alerta falso "Tem direito mas não consta na fatura" para funcionários com linha duplicada na planilha (ex: DIESSICA PEREIRA DE SOUZA).
- `pages/5_Aprovação.py` — colunas `Dt. Admissão`, `Dt. Demissão` e `Dt. Elegibilidade` convertidas de string para `datetime.date` e configuradas como `DateColumn` no data_editor, permitindo ordenação correta por data.

### V1.6.0 — 2026-05-12
**Nova página: 3 · Exclusões do Mês**
- `pages/3_Exclusões.py` — compara os titulares na fatura do período atual com os de um período anterior selecionável. Lista quem saiu do plano (estava antes, não está agora). Inclui KPIs (titulares antes × depois × exclusões), filtros por empresa/departamento/contrato e tabela com dados do período anterior.
- `main.py` — tabela de navegação atualizada.

### V1.5.27 — 2026-05-12
**Auditoria: card "⏳ Pendentes" nos KPIs**
- `pages/2_Auditoria.py` — adicionado card "⏳ Pendentes" ao lado de "⚠️ Inconsist.", mostrando quantas inconsistências ainda não têm justificativa. Delta exibe quantas já foram justificadas.

### V1.5.26 — 2026-05-12
**Aprovação: ordem de colunas persistida + correção de erro no Histórico**
- `pages/5_Aprovação.py` — expander "📋 Ordem das colunas" com botões ↑↓ para reposicionar; ordem salva automaticamente em `dados/col_config_aprovacao.json` e aplicada via `column_order` no data_editor.
- `pages/4_Histórico.py` — corrigido ValueError: `df_hist.columns` tinha 4 nomes mas o DataFrame tinha 5 colunas (incluindo `id`). Substituído por construção explícita do dict.

### V1.5.25 — 2026-05-12
**Aprovação: filtro de situação (Pendentes / Justificados / Todos)**
- `pages/5_Aprovação.py` — adicionado selectbox "Situação" com contadores dinâmicos: `Todas (N)`, `⏳ Pendentes (N)`, `✅ Justificados (N)`. Permite focar rapidamente nas pendências ainda sem justificativa ou revisar as já aprovadas.

### V1.5.24 — 2026-05-12
**Justificativas: cópia automática para meses futuros como comportamento padrão**
- `pages/5_Aprovação.py` — checkboxes "Gravar justificativas para meses futuros" (individual e lote) agora iniciam marcados por padrão. Toda justificativa salva é automaticamente gravada no banco de modelos; desmarcar é a exceção.
- `app/db.py` — `migrar_justificativas` expandida: ao processar um mês novo (sem histórico do mesmo período), pré-popula automaticamente a partir dos modelos salvos de meses anteriores, filtrando por cliente. O usuário só precisa validar o que já vem preenchido.

### V1.5.23 — 2026-05-12
**Correção crítica: _classificar_plano ignorava valor numérico quando havia "NÃO" no texto**
- `app/processamento.py` — teste numérico (`_parse_brl > 0`) movido para ANTES do teste `"NAO" in s`. Campos como "450,00 - Auxiliar Agrícola II - Pesquisa NÃO tem plano" eram incorretamente classificados como sem direito porque "NAO" aparecia no texto descritivo do cargo/categoria. Agora o valor 450 é lido primeiro e prevalece.

### V1.5.22 — 2026-05-12
**Correção: TERCEIRIZAÇÃO INDETERMINADO respeita planilha de contratos**
- `app/processamento.py` — restaurada condição `and tem_direito`: contrato TERCEIRIZAÇÃO + INDETERMINADO só concede direito ao plano se a planilha de contratos tiver "Sim" na coluna de plano de saúde. Sem "Sim" → sem direito. Com "Sim" → elegível desde a admissão (sem carência).

### V1.5.21 — 2026-05-12
**Elegibilidade: TERCEIRIZAÇÃO INDETERMINADO → regra absoluta, sem dependência da planilha**
- `app/processamento.py` — removida condição `and tem_direito` do branch TERCEIRIZAÇÃO + INDETERMINADO. Agora qualquer contrato com essas palavras no campo "Contrato ADM" garante `tem_direito = True` e `copart_apos_exp = False` (elegível desde a admissão), independente do que estiver preenchido na coluna de plano de saúde da planilha de contratos.

### V1.5.20 — 2026-05-12
**Elegibilidade: regras de carência por tipo contratual**
- `app/processamento.py` — TERCEIRIZAÇÃO + INDETERMINADO com direito na planilha → `copart_apos_exp = False` (elegível desde a admissão, sem carência).
- `app/processamento.py` — INDETERMINADO puro (sem TERCEIRIZAÇÃO) com direito na planilha → `copart_apos_exp = True` (elegível após 90 dias da admissão), independente do que estiver escrito na planilha.

### V1.5.18 — 2026-05-08
**Contratos especiais 134 e 119: elegibilidade corrigida**
- `app/processamento.py` — `_CONTRATO_134` substituído por `_CONTRATOS_ESPECIAIS = {"134", "119"}`; a regra "contrato especial + INDETERMINADO → tem direito imediato" agora cobre 134 e 119; `copart_apos_exp` é zerado para esses contratos (direito imediato, sem espera de 90 dias).

### V1.5.17 — 2026-05-08
**Auditoria: coluna Justificado, filtro e cor azul para linhas já justificadas**
- `pages/2_Auditoria.py` — carrega justificativas do banco (por `auditoria_id` ou fallback por período) e adiciona coluna `Justificado` (Sim/Não) a cada linha.
- Filtro `Justificado` adicionado à seção de filtros para isolar apenas pendências já justificadas ou ainda abertas.
- Coloração: Inconsistente **justificado** → 🔵 azul (`#cce5ff`); Inconsistente **pendente** → 🔴 vermelho; OK → 🟢 verde.

### V1.5.16 — 2026-05-08
**Correção crítica: justificativas não apareciam por diferença de case no nome do cliente**
- `app/db.py` — `listar_periodos()`: adicionado `MAX(processado_em) DESC` como ordenação secundária; antes retornava o grupo `"SETRATA"` (ID 21, sem justificativas) antes de `"Setrata"` (ID 22, com 19 justificativas), pois ambos são grupos distintos no GROUP BY.
- `pages/5_Aprovação.py` — `_carregar_justificativas_ativas()`: fallback por período usa `cliente=""` em vez do cliente da sessão — cobre variações de case (`"Setrata"` vs `"SETRATA"`).

### V1.5.15 — 2026-05-08
**Auto-carregamento: Auditoria e Aprovação carregam do banco automaticamente ao abrir**
- `pages/2_Auditoria.py` e `pages/5_Aprovação.py` — ao abrir qualquer uma das abas com sessão vazia (após reinício do app), o sistema busca automaticamente a última auditoria do banco e popula a sessão sem exigir passagem pela Importação.
- Elimina a mensagem "Nenhuma auditoria carregada" após reinícios do app.

### V1.5.14 — 2026-05-08
**Aprovação: recuperação automática de justificativas mesmo com sessão resetada**
- `app/db.py` — nova função `carregar_justificativas_por_periodo()`: busca as justificativas do audit mais recente do período que tenha dados salvos — fallback quando `auditoria_id` da sessão aponta para audit sem justificativas.
- `pages/5_Aprovação.py` — ao abrir a aba, se `auditoria_id` está sem justificativas ou ausente, o sistema localiza e migra automaticamente as justificativas do período sem precisar de ação do usuário.

### V1.5.13 — 2026-05-08
**Justificativas nunca são perdidas ao reprocessar**
- `app/db.py` — nova função `migrar_justificativas(novo_id, periodo, cliente)`: copia automaticamente todas as justificativas da auditoria anterior mais recente do mesmo período para o novo audit_id; só copia registros ainda não existentes no novo ID.
- `pages/1_Importação.py` — `_processar_auditoria` chama `migrar_justificativas` logo após criar o novo audit, garantindo que reprocessamentos herdem as aprovações já feitas.

### V1.5.12 — 2026-05-08
**Aprovação: todos os Inconsistentes agora aparecem (IVANDO e outros corrigidos)**
- `pages/5_Aprovação.py` — removido o filtro de "dependente isolado" (`_sem_contrato & _na_fatura & mens_fat=0 & dif_fat=0`) que ocultava funcionários com contrato mas com falha de match de nome (ex: IVANDO JOSE TEODORO). Todo registro com `Status = Inconsistente` agora aparece na aba de Aprovação. Justificativas existentes no banco não são afetadas.

### V1.5.11 — 2026-05-08
**Correção de datas invertidas + reprocessamento**
- `app/processamento.py` — `_fmt_data`: removido fallback sem `dayfirst` (causava inversão de dia/mês em datas ambíguas); agora testa formatos explícitos em ordem: DD/MM/YYYY (BR), ISO YYYY-MM-DD, variantes; último recurso usa `dayfirst=True` exclusivamente.
- `pages/1_Importação.py` — botão "Reprocessar" (bloco arquivos salvos): corrigido `IndexError` quando compra é lista vazia; usa período da sessão como fallback se formulário vazio; salva arquivos no novo `auditoria_id` e recarrega caminhos antes de atualizar a sessão.
- `pages/1_Importação.py` — botão "Reprocessar" (tela inicial sem sessão): mesmo fix de `IndexError` e recarga de caminhos pós-processamento.

### V1.5.10 — 2026-05-08
**Botão "Reprocessar com regras atuais" sempre visível na aba de importação**
- `app/db.py` — `listar_periodos()` passa a retornar o campo `id` do registro mais recente de cada período, eliminando a necessidade de consulta extra para carregar arquivos.
- `pages/1_Importação.py` — auto-carrega `arquivos_fontes` do banco quando a sessão reinicia e o campo não está presente; tela inicial (sem sessão) exibe dois botões lado a lado: **Carregar resultado salvo** e **Reprocessar com regras atuais** (desabilitado se não houver arquivos salvos para o período).

### V1.5.09 — 2026-05-08
**Padronização da interpretação do campo "Plano de Saúde" da planilha de contratos**
- `app/processamento.py` — nova função `_classificar_plano(vlr_raw) -> (tem_direito, copart_apos_exp)` substitui `_tem_direito_plano` e os sets `_AFIRMATIVOS_PLANO`/`_NEGATIVOS_PLANO`; interpreta por ordem de prioridade:
  1. `"Sim com coparticipação após experiência"` → elegível após 90 dias da admissão (`copart_apos_exp = True`)
  2. `"Sim com coparticipação imediato"` → elegível desde a admissão
  3. `"Não"` / vazio / zero → sem direito
  4. Valor numérico > 0 → elegível (plano com valor definido)
  5. `"Sim"` / `"S"` / `"X"` genéricos → elegível
- `ler_contratos` usa `_classificar_plano` em substituição à lógica anterior; `copart_apos_exp` segue alimentando a regra dos 90 dias em `cruzar()`.

### V1.5.08 — 2026-05-08
**Correção crítica: INDETERMINADO era detectado como DETERMINADO**
- `app/processamento.py` — `"DETERMINADO" in "INDETERMINADO"` é `True` em Python (substring); todos os funcionários com contrato INDETERMINADO eram marcados como inelegíveis. Correção: `eh_determinado = "DETERMINADO" in norm and "INDETERMINADO" not in norm`. JEANE FONTINELE RIBEIRO DE SOUSA e demais casos com INDETERMINADO corrigidos.

### V1.5.07 — 2026-05-08
**Correção: funcionários com "Sim"/"X"/"S" na célula de plano apareciam como sem direito**
- `app/processamento.py` — nova função `_tem_direito_plano()`: reconhece valor numérico > 0 OU indicadores textuais afirmativos ("Sim", "S", "X", "Possui", "Tem", "Ativo", "Incluso") como indicação de que o funcionário possui o plano; palavras negativas ("Não", "N", "0") e células vazias retornam False.
- `ler_contratos` passou a usar `_tem_direito_plano()` em vez de `vlr > 0`, corrigindo casos como JEANE FONTINELE RIBEIRO DE SOUSA e outros com célula textual.

### V1.5.06 — 2026-05-08
**Regra específica do contrato 134**
- `app/processamento.py` — elegibilidade: contrato 134 + INDETERMINADO → `tem_direito = True` (forçado, independente do valor na planilha); contrato 134 + DETERMINADO → cai na regra geral DETERMINADO → `tem_direito = False`.
- Auditoria: 134 INDETERMINADO sem plano → Inconsistente via R1/R2; 134 DETERMINADO com cobrança → Inconsistente via bloco `_inelegivel_contrato`.

### V1.5.05 — 2026-05-08
**Regra dos 90 dias ("Sim com coparticipação após experiência")**
- `app/processamento.py` — `ler_contratos`: quando o campo de plano de saúde contiver o texto "experiência" (ex: "Sim com coparticipação após experiência"), o funcionário é marcado com `copart_apos_exp = True`; o `vlr_contrato` permanece 0 mas `tem_direito = True` (condicional).
- `app/processamento.py` — `cruzar()`: calcula a data de elegibilidade (admissão + 90 dias corridos) e compara com o primeiro dia do mês de referência da auditoria; se ainda em experiência, `Tem Direito` é sobrescrito para "Não" e `_aguarda_elegibilidade = True`; campo `Dt. Elegibilidade` exibido nas abas.
- `app/regras.py` — nova regra: `_aguarda_elegibilidade = True` → se há cobrança → Inconsistente "Em período de experiência, elegível em [data]"; se sem cobrança → OK.
- `pages/2_Auditoria.py` e `pages/5_Aprovação.py` — coluna `Dt. Elegibilidade` adicionada.

### V1.5.04 — 2026-05-08
**Regras de exceção TMG e lógica especial ANATACHA**
- `app/processamento.py` — elegibilidade: contratos com `TMG` no nome → sem direito ao plano; exceção: `MAURO ALVES DA SILVA` tem direito mesmo em contrato TMG.
- `app/processamento.py` — `cruzar()`: campo `_anatacha_especial` propagado em todos os resultados para identificar `ANATACHA CARDOSO ARAUJO`.
- `app/regras.py` — R5 reformulado: para ANATACHA, compara `empresa (compra)` vs `mensalidade titular + dependentes (fatura)` e `funcionária (compra)` vs `coparticipações (fatura)`; para os demais mantém comparação empresa vs contrato.

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
