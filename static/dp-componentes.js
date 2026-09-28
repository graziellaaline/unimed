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
     Ponte Dash: <div class="dp-aviso" data-tipo data-msg …> na página vira toast
     DP.fase(texto)                 texto da etapa dentro da barra
     DP.fechar()                    esconde o aviso agora (fim de trabalho longo)
     DP.porcentagem(n | null)       barra com % real (null = indeterminada)
     DP.acompanhar(url, fechaSozinho)
         pergunta ao servidor a cada 0,7s: {rodando, porcentagem, fase, feitos,
         total, decorrido_s, erro} e anima a barra ("3 de 10 — 30% · 12s")
     DP.confirmar(pergunta, {sim, nao, perigo}) -> Promise<boolean>
         pergunta Sim/Não antes de ação que apaga/substitui (regra da casa)
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
      t.innerHTML = '<div class="dp-toast-texto"></div>' +
        '<div class="dp-toast-prog"><div class="dp-toast-trilho"><span></span></div>' +
        '<div class="dp-toast-fase"></div></div>';
      document.body.appendChild(t);
    }
    return t;
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

  // ------------------------------------------------------------------ exporta
  window.DP = {
    __versao: "1.0.0",
    toast: toast, fase: fase, porcentagem: porcentagem,
    acompanhar: acompanhar, parar: pararAcompanhamento,
    fechar: function () { pararAcompanhamento(); caixa().className = "dp-toast"; },
    confirmar: confirmar, novidades: mostrarNovidades
  };
  if (typeof window.toast !== "function") window.toast = toast;
  if (typeof window.toastFase !== "function") window.toastFase = fase;

  vigiarAvisos();
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
