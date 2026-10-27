/* CÓPIA do kit DP Setrata — NÃO EDITE AQUI. Fonte: C:\Projetos\_identidade\componentes. Atualize com instalar_componentes.py. */
/* ===========================================================================
   DP Setrata — componentes de comportamento (V1.0.0, 28/09/2026)

   FONTE ÚNICA. Pedido dela: "padronize essas ferramentas que são úteis em todos
   os sistemas, como barra de progresso, aviso de versão". Cada sistema recebe
   uma CÓPIA deste arquivo pelo instalar_componentes.py — NÃO edite a cópia,
   edite aqui e rode o instalador.

   JavaScript puro, de propósito: não depende do Dash nem do servidor. Continua
   funcionando quando o callback está ocupado (processamento longo) ou quando o
   servidor reiniciou e a tela ficou órfã — que é exatamente quando precisa.

   O que oferece (window.DP):
     DP.toast(msg, tipo, prender)   tipo: ok | err | aviso | info | progress
                                    (fecha com clique no aviso ou Esc, menos a barra andando)
     Ponte Dash: <div class="dp-aviso" data-tipo data-msg …> na página vira toast
     DP.fase(texto)                 texto da etapa dentro da barra
     DP.fechar()                    esconde o aviso agora (fim de trabalho longo)
     DP.porcentagem(n | null)       barra com % real (null = indeterminada)
     DP.acompanhar(url, fechaSozinho)
         pergunta ao servidor a cada 0,7s: {rodando, porcentagem, fase, feitos,
         total, decorrido_s, erro} e anima a barra ("3 de 10 — 30% · 12s")
     DP.confirmar(pergunta, {sim, nao, perigo}) -> Promise<boolean>
     DP.avisar(mensagem, {ok}) -> Promise   aviso com um botão só ("OK")
         pergunta Sim/Não antes de ação que apaga/substitui (regra da casa)
     Filtro de coluna (A→Z com caixa seletora): automático em <table class="dp-filtravel">
         cada cabeçalho ganha ▾ -> A→Z / Z→A, busca, "Selecionar tudo" e a lista de
         valores com caixinha. Ordena número, % e hh:mm como número. DP.filtrarTabelas()
         refaz na hora (a vigia já faz sozinha quando a tabela aparece).
     Feedback (usuário -> desenvolvedor): automático onde o servidor tiver as rotas do
         feedback_web.py (/_feedback/eu). Chip "Feedback" no canto com badge das respostas
         não lidas; abas Enviar / Meus / Gerenciar (admin). window.DP_FEEDBACK = false desliga.
     Aviso de versão: automático. Lê window.DP_VERSAO_URL (padrão "/_versao-app")
         a cada 15s: {versao, boot, novidades?}. Se o servidor reiniciou, mostra
         a faixa "Nova versão … — Atualizar" e, havendo novidades, o botão
         "Novidades" com o CHANGELOG.

   Compatibilidade: window.toast / window.toastFase continuam existindo (a API
   da receita SetForge que o Fioti já usa), a menos que o sistema já tenha um
   `toast` próprio — aí só DP.toast.
   =========================================================================== */
(function () {
  if (window.DP && window.DP.__versao) return;           // carregado duas vezes

  // ------------------------------------------------------------------ toast
  var _timer = null;

  function caixa() {
    var t = document.getElementById("dp-toast");
    if (!t) {
      t = document.createElement("div");
      t.id = "dp-toast";
      t.className = "dp-toast";
      t.setAttribute("role", "status");
      t.setAttribute("aria-live", "polite");
      t.innerHTML = '<button type="button" class="dp-toast-x" aria-label="Fechar" ' +
        'title="Fechar">×</button><div class="dp-toast-texto"></div>' +
        '<div class="dp-toast-prog"><div class="dp-toast-trilho"><span></span></div>' +
        '<div class="dp-toast-fase"></div></div>';
      // Fecha com um clique ou Esc (22/10/2026: o aviso de erro fica preso para dar
      // tempo de ler e não tinha como tirar da tela). Barra andando não fecha.
      t.addEventListener("click", function () { fecharAviso(); });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") fecharAviso();
      });
      document.body.appendChild(t);
    }
    return t;
  }

  function fecharAviso() {
    var t = document.getElementById("dp-toast");
    if (!t || t.className.indexOf("mostra") < 0 || t.className.indexOf("dp-t-progress") >= 0) return;
    if (_timer) { clearTimeout(_timer); _timer = null; }
    t.className = "dp-toast";
  }

  var TIPOS = { ok: "ok", sucesso: "ok", err: "err", erro: "err",
                progress: "progress", progresso: "progress", andando: "progress",
                info: "info", aviso: "aviso", atencao: "aviso" };

  function toast(msg, tipo, prender) {
    tipo = TIPOS[tipo] || "ok";
    var t = caixa();
    t.querySelector(".dp-toast-texto").textContent = msg;
    // Classe com prefixo: "progress" é classe do Bootstrap (altura de 1rem e
    // overflow escondido) e cortava o toast no Fioti.
    t.className = "dp-toast mostra dp-t-" + tipo;
    if (tipo !== "progress") {
      pararAcompanhamento();
      fase("");
    }
    if (_timer) { clearTimeout(_timer); _timer = null; }
    if (!prender) {
      _timer = setTimeout(function () { t.className = "dp-toast"; }, 6000);
    }
  }

  function fase(texto) {
    var f = caixa().querySelector(".dp-toast-fase");
    f.textContent = texto || "";
  }

  function porcentagem(valor) {
    var t = caixa();
    var span = t.querySelector(".dp-toast-trilho > span");
    if (valor === null || valor === undefined) {
      t.classList.remove("determinada");
      span.style.width = "";
      return;
    }
    t.classList.add("determinada");
    span.style.width = Math.max(0, Math.min(100, valor)) + "%";
  }

  // ------------------------------------------------------------------ acompanhar
  var _poll = null;

  function pararAcompanhamento() {
    if (_poll) { clearInterval(_poll); _poll = null; }
    var t = document.getElementById("dp-toast");
    if (t) { t.classList.remove("determinada"); }
  }

  function acompanhar(url, fechaSozinho) {
    pararAcompanhamento();
    var viuRodando = false;
    var inicio = Date.now();
    porcentagem(0);
    fase("Enviando para o servidor… 0%");
    _poll = setInterval(function () {
      fetch(url, { credentials: "same-origin", cache: "no-store" })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (p) {
          if (!_poll || !p) return;
          if (!p.rodando && !viuRodando) {
            // Recusado antes de começar (falta arquivo, sem permissão): a tela
            // explica; a barra não fica girando para sempre.
            if (fechaSozinho && Date.now() - inicio > 8000) {
              pararAcompanhamento();
              caixa().className = "dp-toast";
            }
            return;
          }
          if (p.rodando) viuRodando = true;
          if (!p.rodando && fechaSozinho) {
            var seg = p.decorrido_s ? " em " + Math.round(p.decorrido_s) + "s" : "";
            if (p.erro) toast("Falha no processamento: " + p.erro, "err", false);
            else toast("Processamento concluído" + seg + ".", "ok", false);
            return;
          }
          var pct = p.rodando ? (p.porcentagem || 0) : 100;
          porcentagem(pct);
          var txt = p.fase || "Processando…";
          if (p.rodando && p.total) txt += " (" + p.feitos + " de " + p.total + ")";
          if (!p.rodando) txt = "Finalizando…";
          fase(txt + " — " + pct + "%" +
               (p.decorrido_s ? " · " + Math.round(p.decorrido_s) + "s" : ""));
        })
        .catch(function () { /* servidor ocupado: tenta no próximo ciclo */ });
    }, 700);
  }

  // ------------------------------------------------------------------ confirmar
  function confirmar(pergunta, opcoes) {
    opcoes = opcoes || {};
    return new Promise(function (resolver) {
      var fundo = document.createElement("div");
      fundo.className = "dp-confirma-fundo";
      fundo.innerHTML =
        '<div class="dp-confirma" role="alertdialog" aria-modal="true">' +
          '<p class="dp-confirma-texto"></p>' +
          '<div class="dp-confirma-acoes">' +
            '<button type="button" class="dp-btn dp-btn-2" data-r="0"></button>' +
            '<button type="button" class="dp-btn ' + (opcoes.perigo === false ? "" : "dp-btn-perigo") +
              '" data-r="1"></button>' +
          "</div></div>";
      fundo.querySelector(".dp-confirma-texto").textContent = pergunta;
      fundo.querySelector('[data-r="0"]').textContent = opcoes.nao || "Não";
      fundo.querySelector('[data-r="1"]').textContent = opcoes.sim || "Sim";
      function fechar(r) {
        document.removeEventListener("keydown", tecla);
        fundo.remove();
        resolver(r);
      }
      function tecla(e) { if (e.key === "Escape") fechar(false); }
      fundo.addEventListener("click", function (e) {
        var b = e.target.closest("[data-r]");
        if (b) fechar(b.getAttribute("data-r") === "1");
        else if (e.target === fundo) fechar(false);
      });
      document.addEventListener("keydown", tecla);
      document.body.appendChild(fundo);
      fundo.querySelector('[data-r="0"]').focus();        // o padrão seguro é o "Não"
    });
  }

  // Aviso que pede só "OK" (05/10/2026): para avisar algo que a pessoa precisa
  // ler antes de seguir, sem escolha a fazer. Mesmo visual da pergunta Sim/Não.
  function avisar(mensagem, opcoes) {
    opcoes = opcoes || {};
    return new Promise(function (resolver) {
      var fundo = document.createElement("div");
      fundo.className = "dp-confirma-fundo";
      fundo.innerHTML =
        '<div class="dp-confirma" role="alertdialog" aria-modal="true">' +
          '<p class="dp-confirma-texto"></p>' +
          '<div class="dp-confirma-acoes">' +
            '<button type="button" class="dp-btn" data-r="1"></button>' +
          "</div></div>";
      fundo.querySelector(".dp-confirma-texto").textContent = mensagem;
      fundo.querySelector('[data-r="1"]').textContent = opcoes.ok || "OK";
      function fechar() {
        document.removeEventListener("keydown", tecla);
        fundo.remove();
        resolver(true);
      }
      function tecla(e) { if (e.key === "Escape" || e.key === "Enter") fechar(); }
      fundo.querySelector('[data-r="1"]').addEventListener("click", fechar);
      document.addEventListener("keydown", tecla);
      document.body.appendChild(fundo);
      fundo.querySelector('[data-r="1"]').focus();
    });
  }

  // ------------------------------------------------------------------ aviso de versão
  var _boot = null, _versaoAberta = null, _avisado = false, _conferiuNovidades = false;
  var CHAVE_VISTA = "dp-novidades-vista:" + location.host;   // uma por sistema (porta)

  function mostrarNovidades(novidades, versaoAtual, aoFechar) {
    var fundo = document.createElement("div");
    fundo.className = "dp-confirma-fundo";
    var html = '<div class="dp-novidades" role="dialog" aria-modal="true">' +
      '<h2>Novidades</h2>' +
      (versaoAtual ? '<p class="dp-novidades-nota">Você está na versão <b>' + esc(versaoAtual) + "</b>.</p>" : "") +
      '<div class="dp-novidades-lista">';
    (novidades || []).forEach(function (n) {
      html += '<section><h3>' + esc(n.versao) + (n.data ? ' <small>' + esc(n.data) + '</small>' : '') +
              '</h3><ul>' + (n.itens || []).map(function (i) { return "<li>" + esc(i) + "</li>"; }).join("") +
              "</ul></section>";
    });
    html += '</div><div class="dp-confirma-acoes"><button type="button" class="dp-btn">Entendi</button></div></div>';
    fundo.innerHTML = html;
    fundo.addEventListener("click", function (e) {
      if (e.target === fundo || e.target.closest(".dp-btn")) {
        fundo.remove();
        if (aoFechar) aoFechar();           // marca como VISTO ao fechar, nunca ao abrir
      }
    });
    document.body.appendChild(fundo);
  }

  function esc(t) {
    var d = document.createElement("div");
    d.textContent = t == null ? "" : String(t);
    return d.innerHTML;
  }

  function avisarVersao(dados) {
    if (_avisado) return;
    _avisado = true;
    var faixa = document.createElement("div");
    faixa.className = "dp-versao";
    faixa.setAttribute("role", "alert");
    faixa.innerHTML = '<span><b>Nova versão disponível' +
      (dados.versao ? " (" + esc(dados.versao) + ")" : "") +
      '.</b> Atualize a tela para continuar — os botões desta página podem não responder.</span>' +
      (dados.novidades && dados.novidades.length
        ? '<button type="button" class="dp-versao-btn dp-versao-novidades">Novidades</button>' : "") +
      '<button type="button" class="dp-versao-btn dp-versao-ok">Atualizar</button>' +
      '<button type="button" class="dp-versao-btn dp-versao-adiar">Agora não</button>';
    faixa.querySelector(".dp-versao-ok").onclick = function () { window.location.reload(); };
    // "Agora não" (pedido dela no BI, 17/09/2026): some e volta na próxima
    // consulta — dá para terminar o que estava fazendo. Nunca recarrega sozinho.
    faixa.querySelector(".dp-versao-adiar").onclick = function () {
      faixa.remove();
      document.body.classList.remove("dp-com-aviso-versao");
      _avisado = false;
    };
    var nov = faixa.querySelector(".dp-versao-novidades");
    if (nov) nov.onclick = function () { mostrarNovidades(dados.novidades); };
    document.body.appendChild(faixa);
    document.body.classList.add("dp-com-aviso-versao");
  }

  // Novidades automáticas: na primeira vez que a pessoa abre uma versão nova,
  // uma vez só (por sistema). Marca como vista ao FECHAR.
  function novidadesDaVersao(d) {
    if (_conferiuNovidades || !d.versao || !d.novidades || !d.novidades.length) return;
    _conferiuNovidades = true;
    var vista = null;
    try { vista = localStorage.getItem(CHAVE_VISTA); } catch (e) { return; }
    if (vista === String(d.versao)) return;
    mostrarNovidades(d.novidades, d.versao, function () {
      try { localStorage.setItem(CHAVE_VISTA, String(d.versao)); } catch (e) { /* sem memória: tudo bem */ }
    });
  }

  function checarVersao() {
    var url = window.DP_VERSAO_URL || "/_versao-app";
    fetch(url, { cache: "no-store", credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) {
        if (!d || !d.boot) return;
        if (_boot === null) {
          _boot = d.boot; _versaoAberta = d.versao;
          novidadesDaVersao(d);
          return;
        }
        // Reinício OU versão nova: mudança só de visual (CSS, layout) não mexe
        // no mapa de callbacks, mas a tela aberta fica velha do mesmo jeito.
        if (d.boot !== _boot || d.versao !== _versaoAberta) avisarVersao(d);
      })
      .catch(function () { /* fora do ar: silêncio, tenta de novo */ });
  }

  function iniciar() {
    if (window.DP_VERSAO_URL === false) return;          // sistema que não quer o aviso
    checarVersao();
    setInterval(checarVersao, 15000);
  }

  // ------------------------------------------------------------------ ponte para o Dash
  // Telas em Dash avisam pelo SERVIDOR (o callback devolve o aviso). Contrato:
  // qualquer elemento  <div class="dp-aviso" data-tipo data-msg data-prender
  // data-pct data-fase data-quando>  que aparecer na página vira DP.toast. O
  // data-quando muda a cada aviso, então o mesmo texto duas vezes também aparece.
  function lerAviso(el) {
    var tipo = el.getAttribute("data-tipo") || "info";
    toast(el.getAttribute("data-msg") || el.textContent || "", tipo,
          el.getAttribute("data-prender") === "1");
    if (TIPOS[tipo] === "progress") {
      var pct = el.getAttribute("data-pct");
      porcentagem(pct === null || pct === "" ? null : Number(pct));
      fase(el.getAttribute("data-fase") || "");
    }
  }

  function vigiarAvisos() {
    new MutationObserver(function (mudancas) {
      mudancas.forEach(function (m) {
        if (m.type === "attributes") {
          if (m.target.classList && m.target.classList.contains("dp-aviso")) lerAviso(m.target);
          return;
        }
        m.addedNodes.forEach(function (n) {
          if (n.nodeType !== 1) return;
          if (n.classList.contains("dp-aviso")) lerAviso(n);
          if (n.querySelectorAll) n.querySelectorAll(".dp-aviso").forEach(lerAviso);
        });
      });
    }).observe(document.documentElement,
               { childList: true, subtree: true, attributes: true, attributeFilter: ["data-quando"] });
  }

  // ------------------------------------------------------------------ filtro de coluna
  // Pedido dela (30/09/2026): "filtro de AZ com caixa seletora" nas tabelas, no kit,
  // igual ao que o Ponto Setrata faz — mas em JavaScript puro, para servir a qualquer
  // sistema (Dash, HTML próprio, relatório exportado). Basta a classe dp-filtravel.
  // Em Dash, a tabela deve vir como HTML "solto" (dcc.Markdown com
  // dangerously_allow_html): o React não pode ser dono dos <th> que ganham o botão.
  var painelFiltro = null;

  function semAcento(s) {
    return String(s).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  }
  function textoCelula(td) {
    if (!td) return "";
    var v = td.getAttribute("data-v");
    return (v != null ? v : td.textContent).replace(/\s+/g, " ").trim();
  }
  // "1.234" "12,5%" "12:30" "-3:05" "8,2 h" "R$ 1.234,56" e "25/03/2024" viram
  // número (a data como aaaammdd, para ordenar no tempo); o resto é texto.
  function comoNumero(t) {
    var d = String(t).trim().match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
    if (d) return Number(d[3] + d[2] + d[1]);
    var s = String(t).replace(/\s|%|h$|R\$/gi, "");
    var m = s.match(/^(-)?(\d+):(\d{2})$/);
    if (m) return (m[1] ? -1 : 1) * (Number(m[2]) * 60 + Number(m[3]));
    if (/^-?\d{1,3}(\.\d{3})*(,\d+)?$/.test(s) || /^-?\d+(,\d+)?$/.test(s))
      return parseFloat(s.replace(/\./g, "").replace(",", "."));
    return null;
  }
  function comparar(a, b) {
    var x = comoNumero(a), y = comoNumero(b);
    if (x !== null && y !== null) return x - y;
    return String(a).localeCompare(String(b), "pt-BR", { numeric: true, sensitivity: "base" });
  }
  function linhasDe(tab) {
    return Array.prototype.filter.call(tab.querySelectorAll("tr"),
      function (tr) { return tr.querySelector("td"); });
  }
  function cabecalhosDe(tab) {
    var th = tab.querySelectorAll("thead th");
    return th.length ? th : tab.querySelectorAll("tr:first-child th");
  }
  function aplicarFiltro(tab) {
    var st = tab.__dpFiltro, vis = 0;
    linhasDe(tab).forEach(function (tr) {
      var ok = true;
      for (var c in st.filtros) {
        if (!st.filtros[c].has(textoCelula(tr.children[c]))) { ok = false; break; }
      }
      tr.style.display = ok ? "" : "none";
      tr.classList.toggle("dp-zebra", ok && (vis++ % 2 === 1));
    });
    cabecalhosDe(tab).forEach(function (th, i) {
      var b = th.querySelector(".dp-filtro-bt");
      if (b) b.classList.toggle("ativo", !!st.filtros[i]);
    });
  }
  function ordenarPor(tab, i, dir) {
    var ls = linhasDe(tab);
    if (!ls.length) return;
    var pai = ls[0].parentNode;
    ls.sort(function (a, b) {
      return dir * comparar(textoCelula(a.children[i]), textoCelula(b.children[i]));
    }).forEach(function (tr) { pai.appendChild(tr); });
    aplicarFiltro(tab);
  }
  function fecharFiltro() {
    if (painelFiltro) { painelFiltro.remove(); painelFiltro = null; }
  }
  function abrirFiltro(tab, i, botao) {
    fecharFiltro();
    var st = tab.__dpFiltro, vals = {};
    linhasDe(tab).forEach(function (tr) { vals[textoCelula(tr.children[i])] = 1; });
    var lista = Object.keys(vals).sort(comparar);
    var marcados = st.filtros[i] || new Set(lista);
    var p = document.createElement("div");
    p.className = "dp-filtro-painel";
    p.innerHTML =
      '<div class="dp-filtro-ordem"><button type="button" data-o="1">A → Z</button>' +
      '<button type="button" data-o="-1">Z → A</button></div>' +
      '<input class="dp-filtro-busca" placeholder="buscar…" autocomplete="off">' +
      '<label class="dp-filtro-todos"><input type="checkbox"> Selecionar tudo</label>' +
      '<div class="dp-filtro-lista">' + lista.map(function (v) {
        return '<label><input type="checkbox" value="' + esc(v).replace(/"/g, "&quot;") + '"' +
          (marcados.has(v) ? " checked" : "") + "> " + (v === "" ? "(vazio)" : esc(v)) + "</label>";
      }).join("") + "</div>" +
      '<div class="dp-filtro-acoes"><button type="button" class="dp-btn dp-btn-2" data-a="limpar">' +
      'Limpar</button><button type="button" class="dp-btn" data-a="ok">OK</button></div>';
    document.body.appendChild(p);
    painelFiltro = p;
    var r = botao.getBoundingClientRect();
    var largura = Math.min(300, document.documentElement.clientWidth - 16);
    p.style.top = (window.scrollY + r.bottom + 4) + "px";
    p.style.left = Math.max(window.scrollX + 8, Math.min(window.scrollX + r.right - largura,
      window.scrollX + document.documentElement.clientWidth - largura - 8)) + "px";
    var caixas = p.querySelectorAll(".dp-filtro-lista input");
    var todos = p.querySelector(".dp-filtro-todos input");
    var visiveis = function () {
      return Array.prototype.filter.call(caixas, function (c) { return c.parentNode.style.display !== "none"; });
    };
    var acertarTodos = function () {
      var v = visiveis();
      todos.checked = v.length > 0 && v.every(function (c) { return c.checked; });
    };
    acertarTodos();
    todos.addEventListener("change", function () {
      visiveis().forEach(function (c) { c.checked = todos.checked; });
    });
    caixas.forEach(function (c) { c.addEventListener("change", acertarTodos); });
    var busca = p.querySelector(".dp-filtro-busca");
    busca.addEventListener("input", function () {
      var t = semAcento(busca.value.trim());
      caixas.forEach(function (c) {
        c.parentNode.style.display = !t || semAcento(c.value).indexOf(t) >= 0 ? "" : "none";
      });
      acertarTodos();
    });
    busca.addEventListener("keydown", function (e) {      // Enter = OK só no que a busca achou
      if (e.key !== "Enter") return;
      caixas.forEach(function (c) { c.checked = c.parentNode.style.display !== "none"; });
      p.querySelector('[data-a="ok"]').click();
    });
    busca.focus();
    p.querySelectorAll("[data-o]").forEach(function (b) {
      b.addEventListener("click", function () { ordenarPor(tab, i, Number(b.getAttribute("data-o"))); fecharFiltro(); });
    });
    p.querySelector('[data-a="limpar"]').addEventListener("click", function () {
      delete st.filtros[i]; aplicarFiltro(tab); fecharFiltro();
    });
    p.querySelector('[data-a="ok"]').addEventListener("click", function () {
      var sel = new Set();
      caixas.forEach(function (c) { if (c.checked) sel.add(c.value); });
      if (sel.size === lista.length) delete st.filtros[i]; else st.filtros[i] = sel;
      aplicarFiltro(tab); fecharFiltro();
    });
    p.addEventListener("click", function (e) { e.stopPropagation(); });
  }
  function prepararTabela(tab) {
    if (!tab.__dpFiltro) tab.__dpFiltro = { filtros: {} };
    cabecalhosDe(tab).forEach(function (th, i) {
      if (th.querySelector(".dp-filtro-bt")) return;
      var b = document.createElement("button");
      b.type = "button"; b.className = "dp-filtro-bt"; b.textContent = "▾";
      b.title = "Ordenar e filtrar"; b.setAttribute("aria-label", "Ordenar e filtrar esta coluna");
      b.addEventListener("click", function (e) { e.stopPropagation(); abrirFiltro(tab, i, b); });
      th.classList.add("dp-filtro-th");
      th.appendChild(b);
    });
  }
  function filtrarTabelas() {
    document.querySelectorAll("table.dp-filtravel").forEach(prepararTabela);
  }
  function vigiarTabelas() {
    filtrarTabelas();
    var agendado = false;
    new MutationObserver(function () {
      if (agendado) return;
      agendado = true;
      setTimeout(function () { agendado = false; filtrarTabelas(); }, 60);
    }).observe(document.documentElement, { childList: true, subtree: true });
    document.addEventListener("click", fecharFiltro);
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") fecharFiltro(); });
  }

  // ------------------------------------------------------------------ feedback
  // Receita mecanismo-feedback.md, padronizada no kit (pedido dela, 30/09/2026).
  // O servidor é o feedback_web.py do kit; aqui é só a tela.
  var fbEu = null, fbJanela = null, fbPrint = null;

  function fbApi(caminho, corpo) {
    var base = window.DP_FEEDBACK_URL || "/_feedback";
    var op = corpo ? { method: "POST", credentials: "same-origin",
                       headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) }
                   : { credentials: "same-origin", cache: "no-store" };
    return fetch(base + caminho, op).then(function (r) {
      var tipo = r.headers.get("content-type") || "";
      if (tipo.indexOf("json") < 0) return { ok: false, status: r.status, dados: {} };
      return r.json().then(function (d) { return { ok: r.ok, status: r.status, dados: d }; });
    });
  }
  function fbTela() {
    if (typeof window.DP_FEEDBACK_TELA === "function") {
      try { return String(window.DP_FEEDBACK_TELA()); } catch (e) { /* segue */ }
    }
    var aba = document.querySelector(".aba.ativa, .nav-link.active, [aria-selected='true']");
    return location.pathname + location.search + (aba ? " · " + aba.textContent.trim() : "") +
      " · " + document.title;
  }
  function fbBadge() {
    var chip = document.getElementById("dp-fb-chip");
    if (!chip || !fbEu) return;
    var n = (fbEu.nao_vistos || 0) + (fbEu.admin ? (fbEu.abertos || 0) : 0);
    var b = chip.querySelector(".dp-fb-badge");
    b.textContent = n > 99 ? "99+" : String(n);
    b.style.display = n ? "" : "none";
    chip.title = fbEu.admin ? (fbEu.abertos || 0) + " feedback(s) em aberto" : "Enviar feedback";
  }
  function fbAtualizar() {
    if (window.DP_FEEDBACK === false) return;
    fbApi("/eu").then(function (r) {
      if (!r.ok) { fbEu = null; var c = document.getElementById("dp-fb-chip"); if (c) c.remove(); return; }
      fbEu = r.dados;
      if (!document.getElementById("dp-fb-chip")) {
        var chip = document.createElement("button");
        chip.id = "dp-fb-chip"; chip.type = "button"; chip.className = "dp-fb-chip";
        chip.innerHTML = 'Feedback<span class="dp-fb-badge" style="display:none"></span>';
        chip.addEventListener("click", fbAbrir);
        document.body.appendChild(chip);
      }
      fbBadge();
    }).catch(function () { /* sistema sem feedback ou fora do ar: sem chip */ });
  }
  function fbFechar() { if (fbJanela) { fbJanela.remove(); fbJanela = null; } fbPrint = null; }
  function fbAbrir() {
    fbFechar();
    var abas = '<button type="button" data-aba="enviar" class="ativa">Enviar</button>' +
      '<button type="button" data-aba="meus">Meus feedbacks</button>' +
      (fbEu && fbEu.admin ? '<button type="button" data-aba="gerenciar">Gerenciar' +
        (fbEu.abertos ? ' <span class="dp-fb-conta">' + fbEu.abertos + "</span>" : "") + "</button>" : "");
    var fundo = document.createElement("div");
    fundo.className = "dp-confirma-fundo";
    fundo.innerHTML = '<div class="dp-fb-janela" role="dialog" aria-modal="true">' +
      '<div class="dp-fb-topo"><h2>Feedback</h2><button type="button" class="dp-fb-x" aria-label="Fechar">×</button></div>' +
      '<div class="dp-fb-abas">' + abas + '</div><div class="dp-fb-corpo"></div></div>';
    document.body.appendChild(fundo);
    fbJanela = fundo;
    fundo.addEventListener("click", function (e) { if (e.target === fundo) fbFechar(); });
    fundo.querySelector(".dp-fb-x").addEventListener("click", fbFechar);
    fundo.querySelectorAll("[data-aba]").forEach(function (b) {
      b.addEventListener("click", function () { fbMostrar(b.getAttribute("data-aba")); });
    });
    fbMostrar("enviar");
  }
  function fbMostrar(aba) {
    if (!fbJanela) return;
    fbJanela.querySelectorAll("[data-aba]").forEach(function (b) {
      b.classList.toggle("ativa", b.getAttribute("data-aba") === aba);
    });
    var corpo = fbJanela.querySelector(".dp-fb-corpo");
    if (aba === "enviar") return fbFormEnviar(corpo);
    corpo.innerHTML = '<p class="dp-fb-nota">Carregando…</p>';
    if (aba === "meus") fbApi("/meus").then(function (r) { fbListar(corpo, r.dados.itens || [], false); fbAtualizar(); });
    else fbApi("/todos").then(function (r) { fbListar(corpo, r.dados.itens || [], true, r.dados.head); });
  }
  function fbFormEnviar(corpo) {
    corpo.innerHTML =
      '<div class="dp-fb-tipos"><label><input type="radio" name="dp-fb-tipo" value="bug" checked> Algo não funciona (bug)</label>' +
      '<label><input type="radio" name="dp-fb-tipo" value="melhoria"> Ideia de melhoria</label></div>' +
      '<textarea class="dp-fb-texto" maxlength="5000" placeholder="Conte o que aconteceu ou o que você gostaria…"></textarea>' +
      '<div class="dp-fb-print" tabindex="0">Print (opcional): <b>cole aqui com Ctrl+V</b> ou ' +
      '<label class="dp-fb-arquivo">escolha um arquivo<input type="file" accept="image/*" hidden></label>' +
      '<div class="dp-fb-previa"></div></div>' +
      '<p class="dp-fb-nota">A tela onde você está vai junto, para achar o problema mais rápido.</p>' +
      '<div class="dp-confirma-acoes"><button type="button" class="dp-btn" data-a="enviar">Enviar</button></div>';
    var zona = corpo.querySelector(".dp-fb-print"), previa = corpo.querySelector(".dp-fb-previa");
    function usar(arquivo) {
      if (!arquivo || arquivo.type.indexOf("image/") !== 0) { toast("O print precisa ser uma imagem.", "aviso"); return; }
      if (arquivo.size > 8 * 1024 * 1024) { toast("O print passou de 8 MB.", "aviso"); return; }
      var leitor = new FileReader();
      leitor.onload = function () {
        fbPrint = { b64: leitor.result, nome: arquivo.name || "print.png" };
        previa.innerHTML = '<img alt="print" src="' + leitor.result + '"> <button type="button" class="dp-btn dp-btn-2">tirar</button>';
        previa.querySelector("button").addEventListener("click", function () { fbPrint = null; previa.innerHTML = ""; });
      };
      leitor.readAsDataURL(arquivo);
    }
    corpo.querySelector("input[type=file]").addEventListener("change", function (e) { usar(e.target.files[0]); });
    fbJanela.addEventListener("paste", function (e) {
      var itens = (e.clipboardData || {}).items || [];
      for (var i = 0; i < itens.length; i++) {
        if (itens[i].type.indexOf("image/") === 0) { usar(itens[i].getAsFile()); e.preventDefault(); return; }
      }
    });
    corpo.querySelector('[data-a="enviar"]').addEventListener("click", function () {
      var texto = corpo.querySelector(".dp-fb-texto").value.trim();
      if (!texto) { toast("Escreva o que aconteceu ou o que você quer melhorar.", "aviso"); return; }
      var tipo = corpo.querySelector("input[name=dp-fb-tipo]:checked").value;
      fbApi("/enviar", { tipo: tipo, descricao: texto, pagina: fbTela(),
                         print_b64: fbPrint ? fbPrint.b64 : "", print_nome: fbPrint ? fbPrint.nome : "" })
        .then(function (r) {
          if (!r.ok) { toast(r.dados.erro || "Não consegui enviar.", "err", true); return; }
          toast("Feedback enviado. Obrigada! A resposta aparece aqui no botão.", "ok");
          fbAtualizar(); fbMostrar("meus");
        }).catch(function () { toast("Não consegui enviar — o sistema está fora do ar?", "err", true); });
    });
    corpo.querySelector(".dp-fb-texto").focus();
  }
  function fbListar(corpo, itens, admin, head) {
    if (!itens.length) { corpo.innerHTML = '<p class="dp-fb-nota">Nenhum feedback ainda.</p>'; return; }
    var st = (fbEu && fbEu.status) || {}, tp = (fbEu && fbEu.tipos) || {};
    corpo.innerHTML = itens.map(function (f) {
      var html = '<div class="dp-fb-item dp-fb-' + esc(f.status) + '">' +
        '<div class="dp-fb-cab"><b>#' + f.id + " · " + esc(tp[f.tipo] || f.tipo) + '</b><span class="dp-fb-st">' +
        esc(st[f.status] || f.status) + "</span></div>" +
        '<div class="dp-fb-nota">' + esc(f.criado_em) + (admin ? " · " + esc(f.nome || f.login) : "") +
        " · " + esc(f.pagina) + "</div>" +
        '<div class="dp-fb-desc">' + esc(f.descricao) + "</div>" +
        (f.print ? '<a target="_blank" rel="noopener" href="' + (window.DP_FEEDBACK_URL || "/_feedback") +
          "/print/" + encodeURIComponent(f.print) + '"><img class="dp-fb-mini" alt="print" src="' +
          (window.DP_FEEDBACK_URL || "/_feedback") + "/print/" + encodeURIComponent(f.print) + '"></a>' : "") +
        (f.resposta ? '<div class="dp-fb-resp"><b>Resposta' + (f.respondido_por ? " de " + esc(f.respondido_por) : "") +
          ":</b> " + esc(f.resposta) + (f.commit ? ' <span class="dp-fb-nota">(versão ' + esc(f.commit) + ")</span>" : "") + "</div>" : "");
      if (admin) {
        html += '<details><summary>Responder / atualizar</summary>' +
          '<textarea class="dp-fb-texto" data-r="resposta" placeholder="O que foi feito e como ver o resultado">' + esc(f.resposta || "") + "</textarea>" +
          '<div class="dp-fb-linha"><select data-r="status">' + Object.keys(st).map(function (k) {
            return '<option value="' + k + '"' + (k === f.status ? " selected" : "") + ">" + esc(st[k]) + "</option>";
          }).join("") + '</select><input data-r="commit" placeholder="commit" value="' + esc(f.commit || head || "") + '">' +
          '<button type="button" class="dp-btn" data-salvar="' + f.id + '">Salvar</button></div></details>';
      }
      return html + "</div>";
    }).join("");
    corpo.querySelectorAll("[data-salvar]").forEach(function (b) {
      b.addEventListener("click", function () {
        var caixa = b.closest("details");
        fbApi("/responder", { id: Number(b.getAttribute("data-salvar")),
          resposta: caixa.querySelector('[data-r="resposta"]').value,
          status: caixa.querySelector('[data-r="status"]').value,
          commit: caixa.querySelector('[data-r="commit"]').value }).then(function (r) {
          if (!r.ok) { toast(r.dados.erro || "Não consegui salvar.", "err", true); return; }
          toast("Resposta salva. Quem enviou vê no botão Feedback.", "ok");
          fbAtualizar(); fbMostrar("gerenciar");
        });
      });
    });
  }
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && fbJanela) fbFechar(); });

  // ------------------------------------------------------------------ exporta
  window.DP = {
    __versao: "1.0.0",
    toast: toast, fase: fase, porcentagem: porcentagem,
    acompanhar: acompanhar, parar: pararAcompanhamento,
    fechar: function () { pararAcompanhamento(); caixa().className = "dp-toast"; },
    confirmar: confirmar, avisar: avisar, novidades: mostrarNovidades,
    filtrarTabelas: filtrarTabelas,
    feedback: function () { if (fbEu) fbAbrir(); }
  };
  if (typeof window.toast !== "function") window.toast = toast;
  if (typeof window.toastFase !== "function") window.toastFase = fase;

  vigiarAvisos();
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", vigiarTabelas);
  else vigiarTabelas();
  var fbComecar = function () { fbAtualizar(); setInterval(fbAtualizar, 60000); };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fbComecar);
  else fbComecar();
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
