# CHANGELOG — Auditoria Unimed

## Regras de versionamento

| Campo   | Quando incrementar                                   |
|---------|------------------------------------------------------|
| `major` | Mudança estrutural incompatível (banco, arquitetura) |
| `minor` | Novo recurso ou funcionalidade adicionada            |
| `patch` | Correção de bug (sem novo recurso)                   |

---

## Histórico

### V1.29.2 - 2026-10-21
- Correção: **LILIAN APARECIDA DE MORAES** (matrícula 60, empresa 4) aparecia com demissão em 19/08/2026, que era do MARCO ANTONIO RODRIGUES DE SOUZA (matrícula 60, **empresa 3**, admitido no mesmo dia). A regra que reconhece troca de nome (mesma matrícula + mesma admissão) não olhava a empresa. Agora exige também a mesma empresa e o mesmo primeiro nome. A troca de nome legítima continua valendo (LETICIA BARBON VITORINI → ...VITORINI HUHN). 10/2026 reprocessado.

### V1.29.1 - 2026-10-21
- **Justificativas recorrentes voltam a ser reaproveitadas.** Em 10/2026 só 2 de 81 vieram preenchidas: o mês entrou como "SETRATA" e o histórico estava como "Setrata", e a comparação exigia o texto idêntico, com os R$ dentro. Agora: cliente sem diferença de maiúsculas, e casa a mesma pessoa com a mesma inconsistência, ignorando os valores que mudam todo mês. Em 10/2026: 53 de 81 já vêm justificadas.
- Justificativa que só vale para o mês dela ("Admissão/Rescisão na referência da fatura") não é herdada para o mês seguinte.

### V1.29.0 - 2026-10-21
- **Filtros que conversam entre si (como no Excel).** O funil de cada coluna agora lista só os valores das linhas que sobraram pelos filtros das outras colunas. Ex.: filtrando Justificado = Não, o funil de Tipo Inconsistência não mostra mais "desligado na fatura" se todos esses já foram justificados. Vale para todas as tabelas do sistema.
- Tipo de inconsistência "Direito sem fatura" passa a se chamar **"Tem direito, fora da fatura"** (a pessoa tem direito ao plano mas não consta na fatura). Auditorias antigas mostram o nome novo sem serem reprocessadas.

### V1.28.2 - 2026-10-21
- Correção: o toast de progresso do processamento (e os avisos do kit) voltou a aparecer. A folha de estilo do kit DP Setrata não estava carregando, e o aviso ficava sem estilo, fora da tela.

### V1.28.1 - 2026-10-05
- Fundo: o mesmo azul do Portal (8080) atrás de todas as telas, com o conteúdo em cards e painéis brancos por cima.

### V1.28.0 - 2026-09-28
- **Barra de progresso no processamento.** Processar e reprocessar a auditoria agora mostram a barra do kit DP Setrata com a etapa em andamento, "3 de 8", porcentagem e tempo (lendo contratos, faturas, compra, cruzando, desligados, regras, salvando, justificativas) — no lugar do "Processando…" parado.
- Ao terminar aparece "concluído em Ns"; se der erro, o aviso vermelho com o motivo. Componente `Progresso` em `app/ui.py`.

### V1.27.0 - 2026-09-28
- **Aviso de versão nova.** Quando o sistema é atualizado, a tela aberta mostra a faixa "Nova versão disponível — Atualizar", igual aos outros sistemas do DP.
- **Novidades.** Depois de atualizar, aparece o que mudou na versão (tirado deste CHANGELOG).
- **Avisos no padrão dos outros sistemas.** Componentes do kit DP Setrata instalados em `static/` pelo `instalar_componentes.py`; aviso do sistema passa a ser o `DP.toast` do kit (`aviso()` em `app/ui.py`). O serviço agora sobe por `servico.py`, que grava `static/_versao-app.json` na subida (NSSM: `servico.py --server.port 8055 ...`).

### V1.26.0 - 2026-09-28
- **Logo Setrata no menu** e ícone Setrata na aba do navegador (antes: emoji 🏥). Logo e ícone lidos direto do kit `C:\Projetos\_identidade`; cópia de reserva em `app/marca/`.
- **Menu na casca do kit:** azul Setrata com brilho azul-claro e grade sutil, igual ao portal.
- **Indicadores (números do topo) no quadro do kit:** fundo azul bem claro, número grande escuro em negrito.
- **Botões:** principal em verde (ação); secundário contornado em azul. Blocos abertos/fechados como card branco.
- **Tabelas:** cabeçalho azul Setrata com letra branca; cores do filtro e da seleção passam para o azul do kit.

### V1.25.0 - 2026-09-28
- **Nova identidade visual DP Setrata.** Menu, botões, números e links no azul Setrata; Calibri Light em todo o sistema, inclusive títulos e números.
- **Gráficos no padrão dos relatórios.** Série única em azul Setrata; duas séries (ex.: Fatura × Compra) em azul + azul-claro; vermelho só para alerta. Tema Altair `dp_setrata` em `app/ui.py` (cores copiadas do kit `C:\Projetos\_identidade`, que usa Plotly).
- Avisos (`st.toast`) com a faixa azul do kit. Originais guardados em `_antigos/`.

### V1.24.2 - 2026-09-22
- **Correcao: a regra dos contratos especiais (119, 134) procurava o codigo no lugar errado.** Ela olhava o **tipo de contrato** ("Terceirizacao Indeterminado"), mas o codigo mora no **departamento** (`MONS- LAB UDI_119 TERC`, `INNOVATIVE_134 TERC`) — em nenhuma das 544 linhas de 09/2026 o codigo aparece no tipo de contrato, ou seja, a regra **nunca disparava**.
- Quem esta na planilha de ATIVOS nao sentia o erro: o direito vinha da coluna "Plano de Saude" (os 22 do `_119` estao todos como "Sim com coparticipacao imediato", R$ 425,78). Mas a planilha de **DESLIGADOS nao tem coluna de plano de saude nenhuma** — nela so existem cadastro, admissao e demissao. Resultado: ao ser desligada, a pessoa do `_119` perdia o direito e passava a ser acusada de **"Sem valor previsto no contrato mas consta na fatura"**, cobranca indevida que nao existe.
  - Corrigidos `GUSTAVO ALEXANDRE NEVES RODRIGUES` e `FELIPE RICARDO ROCHA`, os dois do `MONS- LAB UDI_119 TERC`: continuam apontados como **"Desligado na fatura"** (que e o problema real e procede), sem a acusacao falsa de cobranca sem direito.
  - Teste A/B sobre as 544 linhas: **exatamente 2** mudaram, as duas do `_119`. Nenhuma pessoa da planilha de ativos foi afetada — inclusive o `INNOVATIVE_134`, que segue sem direito nos contratos determinados. Totais inalterados: 461 OK, 83 inconsistentes, R$ 135.211,67.
- **Ainda em aberto:** outras **5** pessoas vindas da planilha de desligados continuam marcadas como "sem direito" so porque a planilha nao informa plano — `ADRIELE FERNANDES DA SILVA`, `ANA CRISTINA APARECIDA TORRES DOS SANTOS`, `EZEQUIAS DE SOUSA NOGUEIRA`, `GABRIELA DE PAULA LUZ` e `JEAN LUCAS DA ROCHA`, de departamentos sem regra propria. Depende de confirmar quais desses departamentos dao direito ao plano.
- **Dados: 09/2026 reprocessado.** Backup em `backups/historico_antes_reproc_09-2026_v7.db`.

### V1.24.1 - 2026-09-22
- **Correcao: quem foi temporario e depois efetivado vinha com o contrato ERRADO.** Quando a mesma pessoa tem duas linhas na planilha de desligados (contrato antigo + contrato atual) e a fatura nao traz a matricula da empresa — a Unimed so manda a carteirinha —, o sistema casava pelo nome e ficava com a **ultima linha do arquivo**, que podia ser o contrato velho. Agora vence o **contrato mais recente** (demissao, depois admissao).
  - Caso real: `GUSTAVO ALEXANDRE NEVES RODRIGUES` aparecia como desligado em **23/02/2023**, empresa 6, BAYER - LAB TEMP_120, matricula 320 — o contrato temporario dele, encerrado ha mais de tres anos. O contrato de verdade e o de matricula **1169**, empresa 2, MONS- LAB UDI_119 TERC, admitido em 24/02/2023 (dia seguinte a saida do temporario) e desligado em **15/09/2026**. Mesmo CPF (***.149.486-**), mesma pessoa, dois contratos.
  - A inconsistencia em si estava certa: ele foi desligado dentro do periodo e continua na fatura (R$ 343,99, fatura 03 NACIONAL) e na compra — a exclusao junto a Unimed procede. O que estava errado era a **data, a empresa, o departamento e a matricula** mostrados, que faziam parecer cobranca arrastada desde 2023.
  - Conferido linha a linha contra a auditoria anterior: das **544** linhas de 09/2026, **so a dele** mudou.
- **Dados: 09/2026 reprocessado.** Backup em `backups/historico_antes_reproc_09-2026_v6.db`.

### V1.24.0 - 2026-09-11
- **Correcao (leitura da planilha): a coluna "Plano de Saude" nunca era lida.** A elegibilidade saia so da coluna **"Valor Plano de Saude"**, onde o marcador vinha grudado no numero (`"468,00  - Imediato"`). Corrigir a coluna de texto — que e onde a informacao deveria estar — nao surtia efeito nenhum. Agora o **texto manda**, e o valor continua valendo quando a coluna de texto nao existe ou nada diz (planilhas antigas, outros clientes). Na planilha de 09/2026 as duas colunas discordavam em **63 linhas**: o texto dizia "apos experiencia" e o valor, nada.
- **Correcao: o padrao do departamento sobrepunha a planilha.** A regra "INDETERMINADO + depto MONS/BREED → adesao imediata" zerava a carencia mesmo quando a planilha dizia "apos experiencia" na linha da pessoa. O que esta escrito na linha dela agora vale mais que o padrao do departamento; os outros 5 do MONS/BREED, que nao pedem experiencia, seguem com adesao imediata.
  - Efeito conjunto: **4 pessoas** deixaram de ser apontadas como inconsistencia — `ANGELICA BARBOSA LOPES DOS SANTOS` (admissao 01/07, elegivel em **29/09**), `ANTONIO FIORI NETO`, `IAN CARVALHO DE OLIVEIRA` e `RODRIGO FREIRE DE SOUZA`. Todas em periodo de experiencia e corretamente fora da fatura — eram alarmes falsos. OK subiu de 200 para 204.
- **Correcao: "Dif. Fatura x Contrato" passa a comparar a MENSALIDADE DO TITULAR** com o contrato, e nao o total da fatura. O total soma dependentes e conta medica, entao todo mundo com dependente parecia cobranca a maior: `GERMANO FONSECA GALVAO` aparecia **+R$ 1.228,78** quando a mensalidade dele esta **R$ 23,79 abaixo** do contrato. A leitura ficou limpa: de 106 "acima do contrato" para **36** (265 abaixo, 3 exatos).
- **Dados: 09/2026 reprocessado** (versao `id=73`) com a planilha de contratos atualizada. Total faturado inalterado: R$ 135.211,67. Backup em `backups/historico_antes_reproc_09-2026_v5.db`.

### V1.23.1 - 2026-09-11
- **Correcao: a coluna "Justificado" nao virava "Sim" depois de salvar.** A justificativa era gravada no banco corretamente, mas a tabela na tela continuava mostrando "Nao". Causa: o componente da grade trabalha na estrategia `client_wins` — assim que **qualquer celula e editada**, ele passa a **ignorar todo dado novo** vindo do Python (o proprio componente registra no console do navegador: *"Data was edited on Grid. Ignoring further"*). Como a Justificativa e editada na propria grade, a trava ligava e a tela congelava nos valores antigos.
  - Agora, depois de gravar (salvar edicoes, justificar em lote ou reaplicar modelos), a grade e **remontada** — o unico jeito de soltar essa trava sem perder o que voce digita enquanto edita. Filtro e ordenacao sao preservados na remontagem.

### V1.23.0 - 2026-09-11
- **Elegibilidade: contrato DETERMINADO deixa de ser "sem direito" para todo mundo.** Alguns contratos determinados tem plano, outros nao — a regra geral ignorava isso e marcava cobranca indevida em quem tinha direito. Agora os departamentos **345**, **363** e os da **BAYER** (via de regra) mantem o direito mesmo com contrato determinado, somando-se aos ja existentes PLANALTINA e 298. O **134** (INNOVATIVE_134) continua **sem** direito, como deve ser.
- **Novo: excecao individual por cargo.** `MAURO ALVES DA SILVA` e o unico do contrato 292 (TMG) com plano, e e pelo cargo — a planilha diz "Nao" para ele, mas o direito existe. Criada a lista `_EXCECOES_POR_CARGO` (nome + trecho do departamento, para homonimo de outro contrato nao herdar a excecao), avaliada acima de todas as outras regras.
  - Conferido com teste A/B contra o codigo anterior, sobre as 535 pessoas da planilha: **exatamente 4** mudaram — `CAMILA AQUINO ANDRADE` (345), `MARIA EDUARDA TANAKA LIMA DA SILVA` (363), `ANA LAURA VIEIRA MINATEL` (Bayer 123) e `MAURO ALVES DA SILVA` (292). Nenhuma outra pessoa foi afetada; os 26 da Bayer com contrato "Temporario" continuam seguindo a planilha.
  - Efeito: as cobrancas de Camila, Maria Eduarda e Mauro deixam de ser apontadas como indevidas. **Ana Laura passou a aparecer como inconsistencia nova** — ela tem direito ao plano mas **nao consta na fatura**, ou seja, pode nao ter sido incluida. Vale conferir.
- **Novo: coluna "Dif. Fatura x Contrato"** na tela 5 e na exportacao Excel — quanto a Unimed cobra a mais (positivo) ou a menos (negativo) do que o contrato preve. Quem nao esta na fatura fica zerado. Calculada no carregamento, entao vale tambem para auditorias ja salvas, sem reprocessar.
- **Ordem das colunas fixa.** A ordem arrumada foi promovida para o codigo, entao nao depende mais do arquivo de estado. Arrastar continua funcionando e a nova posicao e gravada; apagar `dados/ordem_colunas_grade_auditoria.json` volta exatamente para a ordem definida.
- **Dados: 09/2026 reprocessado** (versao `id=72`) para aplicar as regras novas. Total faturado inalterado: R$ 135.211,67. Backup em `backups/historico_antes_reproc_09-2026_v4.db`.

### V1.22.0 - 2026-09-11
- **Correcao: a ordem das colunas voltou a ser sua.** Na unificacao das telas 5 e 6 a ordem arrumada na antiga tela de Aprovacao (`dados/col_config_aprovacao.json` — Empresa, Departamento, Contrato Adm. ANTES do Funcionario) foi perdida, e por cima disso o arrastar de cabecalho tinha sido travado. Agora: ordem inicial igual a que estava arrumada, **arrastar liberado** de novo, e a posicao escolhida **gravada em disco** (`dados/ordem_colunas_<tela>.json`) — sobrevive a recarregar a pagina e a reiniciar o servico. Coluna nova, que nao existia quando voce arrumou, entra no fim em vez de bagunçar o resto.
- **Novo: um controle so marca e desmarca todos.** O tique no cabecalho da coluna de selecao marca todas as linhas e, clicado de novo, desmarca todas. Respeita o filtro: "todos" alcanca so o que esta a vista, nunca linha fora da tela.
- Mudanca: **Status** passa a ficar ao lado de **Empresa**, no comeco da tabela.

### V1.21.0 - 2026-09-10
- **Removido o aviso de "Sistema atualizado"** (introduzido no V1.19.0). Saiu o pop-up, o botao "Novidades desta versao" na chapa do menu e o arquivo de estado `dados/versao_vista.json`. A versao continua visivel no rodape do menu. Aguardando nova especificacao para refazer.

### V1.20.2 - 2026-09-10
- **Correcao: o texto de Descricao (Inclusoes) saia com o valor inflado.** O bloco usava `Valor Fatura`, que e o **total** da linha — soma dependentes e conta medica junto com a mensalidade. O que o outro sistema espera e so a **mensalidade do titular**. Em meses sem dependente os dois numeros coincidiam, por isso o erro passou despercebido ate agora. Em 09/2026 afetava 3 das 22 inclusoes:
  - `WANDERSON PATRICIO TEIXEIRA` — saia R$ 896,41, correto **R$ 353,09** (dependente de R$ 543,32)
  - `EMANOELLY RIBEIRO` — saia R$ 534,22, correto **R$ 343,99** (dependente de R$ 190,23)
  - `PATRICK LUAN PEREIRA MACEDO` — saia R$ 534,22, correto **R$ 343,99** (dependente de R$ 190,23)
  - A busca do valor cobre os dois formatos de tabela: `_vlr_mensalidade_fat` (auditoria) e `Mensalidade` (tela de Exclusoes); `Valor Fatura` fica so como ultimo recurso. O texto de **Exclusoes** usa a mesma funcao, mas na pratica nao muda: quem tinha so conta medica ja sai num bloco separado antes da lista.

### V1.20.1 - 2026-09-10
- Correcao: o aviso de "Sistema atualizado" reaparecia toda vez que a pagina era recarregada. O "ja vi" ficava so na sessao do navegador, entao qualquer F5 ou aba nova trazia o pop-up de volta mesmo sem versao nova. Agora fica gravado em disco (`dados/versao_vista.json`): abre **uma unica vez** por versao e so volta quando sair outra. O botao "Novidades desta versao" continua reabrindo quando voce quiser.

### V1.20.0 - 2026-09-10
- **Correcao: quem ja esta desligado nao e inclusao.** Aparecia na aba **2 - Inclusoes** como "novo titular" so por nao constar na fatura do mes anterior. Nao e inclusao: e cobranca de quem saiu, e o lugar disso e a aba **4 - Auditoria Exclusoes Indevidas**. Agora esses casos saem da lista e a tela avisa quem foi retirado, por nome. Caso real em 09/2026: `ADRIELE FERNANDES DA SILVA` (mat. 900523), demitida em **01/07/2026** e cobrada em setembro.
- **Correcao: mudanca de nome deixava a demissao para tras.** Quem aparece so na fatura nao traz matricula, e a mesclagem com a planilha de inativos exigia nome identico. Entao quem casou e mudou de nome nunca recebia a Dt. Demissao: ficava eternamente como "nova titular" todo mes, em vez de ir para a tela de cobranca indevida. Caso real: a fatura traz `LETICIA BARBON VITORINI` e a planilha de inativos, `LETICIA BARBON VITORINI HUHN` (mat. 2, demitida **08/09/2026**, cobrada R$ 543,32 em 09/2026).
  - O casamento novo e deliberadamente restrito, para nao repetir o estrago do V1.16.0 de juntar pessoas diferentes: um nome tem de ser o **comeco exato** do outro (sobrenome acrescentado, nunca trocado — `GABRIEL OLIVEIRA RIBEIRO` e `GABRIEL DE OLIVEIRA REIS` continuam separados); o nome mais curto precisa de ao menos **3 partes**; e tem de haver **um unico** candidato, senao nao casa. Conferido em 09/2026: a regra produz **exatamente 1** casamento em toda a base — o da Leticia. Nenhum outro registro mudou.
- **Dados: 09/2026 reprocessado** (versao `id=71`). Nenhum valor mudou: 543 linhas, 342 inconsistencias, R$ 135.211,67. Backup em `backups/historico_antes_reproc_09-2026_v3.db`.

### V1.19.0 - 2026-09-10
- **Novo: pop-up de "Sistema atualizado".** Quando o servico sobe com uma versao diferente da ultima que voce deu OK, abre um aviso na tela com o que mudou. O texto sai do proprio CHANGELOG.md — escrever ali ja publica o aviso, sem segunda lista para manter. Ha tambem o botao **"Novidades desta versao"** na chapa do menu para reabrir quando quiser.

### V1.18.5 - 2026-09-10
- **Correcao (leitura da planilha de desligados).** A `Dt. Admissao` de quatro pessoas vinha como texto — `"IN - Indeterminado"`, `"TI - Terceirizacao Indeterminado"` — em vez de data. O codigo assumia que a planilha de inativos tinha a mesma estrutura da de ativos, e nao tem: na de ativos a data se chama `Dt. Admissao` e o tipo de contrato `Contrato Adm.`; na de inativos a data se chama `Admissao` e o tipo `Contrato Admissao`. Como a busca era por trecho do nome, `Contrato Admissao` casava com "admissao" e o tipo de contrato caia dentro do campo de data. Agora a busca prefere nome exato e recusa colunas com "contrato". Casos reais: `GABRIELA DE PAULA LUZ` (admissao real 17/11/2011), `ADRIELE FERNANDES DA SILVA`, `ANA CRISTINA APARECIDA TORRES DOS SANTOS` e `LORENA DE SOUZA CECELOTTI`. Depois da correcao: 2.140 linhas de desligados, **zero** com texto no lugar da data; planilha de ativos intacta.
- **Correcao (atraso medido contra data futura).** Auditar um mes ainda em curso fabricava atraso: a referencia era sempre o **fim da competencia**, entao quem fosse demitido naquele mes ja nascia "EXCLUSAO FORA DO PRAZO" contra uma data que ainda nem chegou. Em 09/2026, auditado em 10/09, `GABRIELA DE PAULA LUZ` (demissao 11/09, prazo 21/09) aparecia com 9 dias de atraso e `LORENA DE SOUZA CECELOTTI` (demissao 02/09, prazo 12/09) com 18. Agora a referencia e `min(fim da competencia, hoje)` — as duas passam a 0 dia de atraso.
- **Dados: 09/2026 reprocessado** (nova versao `id=70`; a anterior `id=68` preservada) para aplicar a correcao de leitura. Nenhum valor mudou: 543 linhas, 342 inconsistencias, R$ 135.211,67 — identicos. Backup em `backups/historico_antes_reproc_09-2026_v2.db`.

### V1.18.4 — 2026-09-10
- Correção: os filtros ficaram **instáveis** depois do V1.18.1 — piscavam e se perdiam ao clicar. A causa foi a própria persistência: o estado vivo do filtro era reinjetado nas opções da grade a cada rerun e o `streamlit-aggrid` remonta o iframe sempre que as opções mudam, então cada clique num filtro derrubava e reconstruía a tabela. Agora o que vai nas opções é congelado na primeira vez que a grade aparece: as opções não mudam mais, não há remontagem, e o filtro continua vivo no navegador.
- Dados: removido o arquivo de fatura repetido de 09/2026 (`temp_com_trabalho_temporario_ltda_20260910023216.csv`, registrado duas vezes). **Não havia distorção de valor** — a leitura já consolidava linhas idênticas em vez de somar; conferido, a diferença era R$ 0,00 e zero pessoas afetadas. A remoção é organização, não correção de número, e por isso não exigiu reprocessar o mês.

### V1.18.3 — 2026-09-10
- **Dados: 08/2026 reprocessado** (nova versão `id=69`; a anterior, `id=65`, foi preservada no histórico). Backup do banco em `backups/historico_antes_reproc_08-2026.db`.
  - **Por quê:** a auditoria de 08/2026 foi salva em 12/08/2026 às **16:56**; a correção do casamento por semelhança de nome (V1.16.0) foi escrita às **17:12** do mesmo dia — 16 minutos depois. A correção conserta o cálculo, mas não reescreve auditorias já gravadas, então aquele mês ficou congelado com o código antigo. Comparar 09 (correto) contra 08 (antigo) produzia fantasmas.
  - **O que estava errado:** a única linha de fatura da família (matrícula de fatura 1661, R$ 302,09 de mensalidade + R$ 50 de conta médica = R$ 352,09) era atribuída a `MARIA EDUARDA AMARAL OLIVEIRA` (mat. 211) em vez de `MARIA EDUARDA VIEIRA DE OLIVEIRA` (mat. 900268). Resultado: a AMARAL virava **exclusão** falsa em 09 e a VIEIRA virava **inclusão** falsa. `GABRIEL OLIVEIRA RIBEIRO` (mat. 206) tinha o mesmo problema em 07/2026.
  - **Efeito nos números:** nenhum valor financeiro mudou — total na fatura segue **286** e total faturado segue **R$ 122.671,81**. Só a atribuição andou entre duas pessoas, o que moveu uma linha de Inconsistente para OK (334 → 333). As justificativas foram migradas para a nova versão.
  - **Pendente:** 07/2026 continua com a atribuição antiga (3 pessoas divergem). Reprocessar aquele mês corrige o quadro de inclusões/exclusões de 08.

### V1.18.2 — 2026-09-10
- Correção: não dava para copiar o texto de uma célula (o nome do funcionário, por exemplo). Faltava o `ensureDomOrder` — sem ele o AG Grid desenha as linhas fora de ordem no HTML e a seleção do navegador não pega nada.
- Novo: **duplo clique numa célula copia o conteúdo**, com a célula piscando para confirmar. Arrastar para selecionar o texto também passou a funcionar, mas em coluna estreita vira briga com a barra de rolagem — o duplo clique é o caminho garantido. Colunas editáveis ficam de fora, porque nelas o clique abre a edição.

### V1.18.1 — 2026-09-10
- Correção: o filtro continuava se perdendo. Duas causas. (1) Nas telas sem edição a grade avisava o Python só quando o **filtro** mudava, nunca quando a **ordenação** mudava — não havia o que guardar. Agora todas as telas devolvem filtro, ordenação, seleção e edição. (2) A restauração dependia do `initialState` do AG Grid, que é lido antes das colunas existirem, quando o filtro customizado ainda nem foi criado. Agora filtro e ordenação são reaplicados assim que a grade termina de desenhar.

### V1.18.0 — 2026-09-10
- **Novo: bolinha azul no funil da coluna filtrada.** Dá para ver de relance onde a tabela está filtrada, sem abrir painel por painel; o nome da coluna também fica em negrito.
- **Correção: os filtros não eram gravados.** A cada rerun do Streamlit (salvar uma justificativa, clicar num botão, voltar para a aba) a grade era remontada do zero e o filtro se perdia. Filtro e ordenação agora sobrevivem ao rerun, guardados por tela. A **seleção** de linhas é de propósito a única coisa que não sobrevive — ressuscitar tiquezinhos depois de um rerun faria a justificativa em lote atingir quem o usuário já tinha desmarcado.

### V1.17.0 — 2026-09-10
- **Novo: filtro estilo Excel no cabeçalho de cada coluna.** Sai a fileira de `selectbox` acima das tabelas; entra um funil em cada cabeçalho, com ordenar A→Z / Z→A, campo de busca, "Selecionar tudo", lista de checkboxes e botões Limpar / OK. Filtro e ordenação rodam no navegador — a página não recarrega mais a cada seleção.
  - O painel é um componente customizado escrito em `app/grade.py`. A lista de checkboxes do AG Grid ("Set Filter") é recurso **Enterprise/pago**; a edição Community, que é a instalada, só traz filtro de texto ("contém", "igual a"). Por isso o painel foi implementado à mão, sem licença.
  - Aplicado em **2 · Inclusões**, **3 · Exclusões**, **4 · Exclusões Indevidas**, **5 · Auditoria e Aprovação**, **6 · Histórico** e **7 · Análises**.
- **Mudança estrutural: uma tela a menos.** As antigas **5 · Auditoria** (resultado) e **6 · Aprovação** (justificativa + fechamento) viraram **5 · Auditoria e Aprovação**. O trabalho era o mesmo — olhar a pendência e justificar ali —, e alternar entre as duas custava tempo. Agora a tabela é única: a coluna **Justificativa** é editável na própria grade, dá para marcar linhas e justificar em lote, e o botão de aprovar fica no rodapé. O filtro de cabeçalho substitui o antigo seletor "Situação: Pendentes / Justificados".
  - **Histórico** passou de 7 para **6** e **Análises** de 8 para **7**.
- **Novo: identidade visual do "Controle de EPIs e Uniformes" (Setrata).** Mesma regra da casa — toda cor sai de um token, superfícies claras e sólidas, separação por LINHA em vez de sombra, chapa azul-marinho no menu com item ativo em verde, e uma cor de destaque só (o azul-marinho da marca) reservada para ação, foco e seleção. Verde, âmbar e vermelho aparecem como ESTADO, nunca como enfeite. Tema claro e escuro definidos em `.streamlit/config.toml`; fonte **Calibri Light**.
- Correção: colunas de data sem valor mostravam **`NaT`** na grade — o `NaT` do pandas chega ao navegador como texto e não era reconhecido como célula vazia. Agora `NaT`, `NaN`, `None` e vazio exibem `—`, nas colunas de data, de valor e de texto.
- Correção: valores em reais nas tabelas deixaram de ser convertidos para texto antes de exibir. Eram formatados em `R$ 1.234,56` no Python, o que fazia a ordenação por valor sair alfabética; agora vão numéricos e a formatação acontece na exibição.
- Correção (justificativa em lote): a justificativa era aplicada a **todo o conjunto filtrado**, e não só às linhas com o tiquezinho marcado. A tela lia a seleção pelo acessor errado da grade (`selected_rows`, que não existe na versão 1.2 — o correto é `selected_data`), e sem seleção o lote caía sobre tudo o que o filtro deixava à vista. Filtrar não seleciona mais ninguém; só o tiquezinho da linha seleciona. O "marcar tudo" do cabeçalho foi removido pelo mesmo motivo, e a tela agora mostra por nome quem será afetado antes de aplicar.
- Mudança: a **ordem das colunas é fixa** — a definida na página. Não dá mais para arrastar cabeçalho, nenhuma coluna some ao soltar fora da grade, e a ordem se mantém quando os dados são recarregados.
- Nova dependência: `streamlit-aggrid>=1.2.1` (edição Community). Rode `instalar.bat` ou `pip install -r requirements.txt` antes de subir esta versão.

### V1.16.0 — 2026-08-12
- **Correção (identidade do funcionário).** O cruzamento fatura × contratos casava por **semelhança de nome** (≥72%), juntando pessoas diferentes na mesma linha: `GABRIEL OLIVEIRA RIBEIRO` (mat. 206) recebeu a conta médica de `GABRIEL DE OLIVEIRA REIS` (mat. 1540); `JADIELSON DA SILVA SANTOS` (mat. 207) recebeu a mensalidade de `DANILO DA SILVA SANTOS`; `MARIA EDUARDA AMARAL OLIVEIRA` (mat. 211) recebeu a de `MARIA EDUARDA VIEIRA DE OLIVEIRA` (mat. 900268). Como consequência, no mês seguinte essas pessoas apareciam como "exclusão". Agora o sistema lê a coluna **Matrícula da fatura** e:
  - casa primeiro quem tem **nome idêntico** (e a matrícula desempata homônimos);
  - só depois tenta nome parecido, **recusando** quando os dois lados têm matrícula e elas divergem — foi assim que os 4 casos acima foram separados, sem quebrar os casamentos legítimos por nome parecido (`DAIANE DUTRA RIBEIRO` ↔ `DAIANE DUTRA RIBEIRO GALDINO`), onde a fatura não traz matrícula.
  - A matrícula **nunca** casa sozinha: a numeração da fatura não é a mesma do RH (85 pessoas de nome idêntico têm matrículas diferentes nos dois arquivos).
- Correção: funcionário que aparece só na fatura passa a carregar a **matrícula da fatura**, que é o que liga a linha ao cadastro certo na planilha de inativos. `MATEUS DOS SANTOS RODRIGUES` vinha com a demissão de **13/06/2024** — do homônimo de matrícula 1009; o correto é a matrícula 900419, demitido em **22/07/2026**.
- Correção: quem **muda de nome** (casamento, correção de cadastro) virava exclusão em um mês e "novo titular" no outro, todo mês. As abas **2 · Inclusões** e **3 · Exclusões** passam a comparar por matrícula, confirmada por nome ou data de admissão; a aba 3 lista à parte quem trocou de nome. Caso real: `YANDRA MYLENNA DE LIMA LIBORIO` → `YANDRA MYLENNA LIBORIO FERRAZ` (mat. 900295, admissão 20/09/2022).
- Correção: a mesclagem da planilha de inativos exigia matrícula **e** nome idênticos, então quem mudava de nome e depois era demitido ficava sem Dt. Demissão. Agora aceita a mesma matrícula com nome diferente quando a **data de admissão** confirma.
- Mudança: na aba **3 · Exclusões**, quem constava na fatura anterior **só com coparticipação** (conta médica, sem mensalidade) sai da contagem de exclusões e passa a um bloco próprio. Não era titular ativo do plano naquele mês — é cobrança de atendimento já ocorrido, comum em quem já estava desligado, e não sair no mês seguinte é o esperado. O Excel e o texto de descrição levam só as exclusões de fato.
- **Atenção:** auditorias já salvas mantêm os dados antigos. Reprocesse os meses em **1 · Importação → "Reprocessar com arquivos salvos"** para aplicar as correções.

### V1.15.0 — 2026-08-12
- Correção: células vazias apareciam com o texto cinza **"None"** em todas as tabelas (mais visível na coluna Dt. Demissão da aba **3 · Exclusões**). É como o Streamlit desenha valor ausente; agora todas as tabelas do sistema usam o helper `app.ui.tabela` / `tabela_editavel`, que troca esse texto por **"—"**.
- Correção: na aba **3 · Exclusões** os valores (Mensalidade, Dependentes, Coparticipação, Valor Fatura) eram zerados antes de exibir — a tabela inteira ficava em R$ 0,00, a coluna **Composição da Cobrança** sempre "—" e o texto de descrição saía com "VALOR: R$ 0,00". Agora mostram o que estava sendo cobrado na fatura do mês comparado, com o mês no cabeçalho da coluna e um aviso de que não há cobrança no mês atual.
- Correção: na aba **4 · Auditoria de Exclusões Indevidas**, quem tinha data de demissão e **zero dia de cobrança indevida no período** (ex.: demitido dia 03 com cobertura até o fim do mês) entrava no prejuízo estimado com a **fatura cheia** — o valor cheio só faz sentido quando não há data de demissão para ratear. O KPI de Prejuízo Estimado estava inflado.
- Correção: na aba **4**, subir uma planilha de desligados manualmente quando já havia uma carregada na sessão quebrava a página (`ValueError: The truth value of a DataFrame is ambiguous`). A mesclagem também passa a usar sempre a mesma planilha que gerou a lista exibida.
- Correção: `listar_periodos` ordenava por texto (`MM/AAAA`), então **12/2025 vinha antes de 08/2026** — as telas que abrem "a auditoria mais recente" podiam carregar o mês errado. A ordenação passou a ser cronológica de verdade.
- Correção: no gráfico **Por Contrato Adm.** da aba **8 · Análises** todas as barras viravam uma só, rotulada `undefined` — o Vega-Lite lê o ponto de "Contrato Adm." como campo aninhado.
- Correção: a aba **3 · Exclusões** era a única que não carregava a última auditoria sozinha — exigia passar pela **1 · Importação** a cada reinício.
- Correção: numeração das abas nos títulos das telas (Inclusões aparecia como "3", Exclusões Indevidas como "6", Aprovação como "5", Histórico como "4"), link "Navegue para 2 · Auditoria" no Histórico (é a 5) e a aba **8 · Análises**, que faltava na tabela da tela inicial.
- Correção: caracteres corrompidos na aba **1 · Importação** (`⚠️` e `🔍` apareciam como `�?`).
- Correção: exportação Excel gravava `nan` em células vazias e o texto de descrição saía com "EXCLUSÃO: nan" quando não havia data.

### V1.14.2 — 2026-07-24
- Correção: a ordenação por data ao clicar no cabeçalho das tabelas não funcionava nas abas **2 · Inclusões**, **3 · Exclusões** e **5 · Auditoria**. As colunas de data estavam como texto (`"31/07/2025"`), então o Streamlit ordenava alfabeticamente (comparando o dia primeiro) — `"02/07/2026"` vinha antes de `"31/07/2025"`. Agora as colunas de data são convertidas para data real e exibidas com `DateColumn` (dd/mm/aaaa), ordenando cronologicamente. A exportação Excel dessas abas continua igual. (As abas 4 e 6 já ordenavam certo.)

### V1.14.1 — 2026-07-24
- Correção: na aba **6 · Auditoria de Exclusões Indevidas**, a tabela era ordenada pelo texto do Status — como cada status começa com um emoji, a ordenação saía pela ordem dos emojis e jogava a **🚨 COBRANÇA INDEVIDA** (o caso mais grave) para o rodapé. Agora a ordem é por gravidade explícita: 🚨 Cobrança Indevida → ⚠️ Exclusão Fora do Prazo → 🔶 Excluído com cobrança médica; dentro de cada grupo, do maior prejuízo para o menor.

### V1.14.0 — 2026-06-18
- Mudança: todos os gráficos de barra/linha da aba **8 · Análises** agora usam Altair em vez do gráfico nativo simples do Streamlit, com o **valor escrito em cada barra/ponto** — antes só dava para ver a altura da barra, sem o número.
- Correção: gráficos de Custo/Desvio/Inconsistência por Departamento e Contrato Adm. limitam a exibição aos 15 maiores (esses grupos têm 50+ categorias; com todas juntas as barras ficavam finas demais e pareciam vazias) — o restante continua disponível na tabela de detalhe.

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
