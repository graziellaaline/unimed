# CHANGELOG — Auditoria Unimed

## Regras de versionamento

| Campo   | Quando incrementar                                   |
|---------|------------------------------------------------------|
| `major` | Mudança estrutural incompatível (banco, arquitetura) |
| `minor` | Novo recurso ou funcionalidade adicionada            |
| `patch` | Correção de bug (sem novo recurso)                   |

---

## Histórico

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
