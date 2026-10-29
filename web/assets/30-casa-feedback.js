/* Chip de Feedback ligado à camada da casa (rotas /_casa/feedback, receita mecanismo-feedback).
   Abas: Enviar · Meus feedbacks · Triagem (admin) · Código do sistema (admin).
   A regra (nasce em triagem, recusa com motivo, aviso por e-mail) é do servidor; aqui é só a tela.
   O chip do kit (/_feedback) fica desligado neste app: window.DP_FEEDBACK = false. */
window.DP_FEEDBACK = false;
(function () {
  var EU = null, JANELA = null, PRINT = "";

  function esc(t) { return String(t == null ? "" : t).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function aviso(msg, tipo) { if (window.DP && DP.toast) DP.toast(msg, tipo || "info"); }
  function api(metodo, url, corpo) {
    var op = { method: metodo, credentials: "same-origin", headers: {} };
    if (corpo instanceof FormData) op.body = corpo;
    else if (corpo !== undefined) { op.headers["Content-Type"] = "application/json"; op.body = JSON.stringify(corpo); }
    return fetch(url, op).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (!r.ok) throw new Error(d.erro || d.detail || "Não deu certo. Tente de novo.");
        return d;
      });
    });
  }
  function quando(iso) {
    if (!iso) return "";
    var d = new Date(/Z|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + "Z");
    return isNaN(d) ? iso : d.toLocaleDateString("pt-BR") + " " + d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  }

  function chip() {
    var c = document.getElementById("casaFbChip");
    if (c) return c;
    c = document.createElement("button");
    c.type = "button"; c.id = "casaFbChip"; c.className = "casa-fb-chip";
    c.innerHTML = '💬 Feedback<span class="casa-fb-badge" hidden></span>';
    c.addEventListener("click", abrir);
    document.body.appendChild(c);
    return c;
  }
  function badge() {
    api("GET", "/_casa/feedback/badge").then(function (b) {
      var n = (b.nao_vistos || 0) + (EU && EU.admin ? b.triagem || 0 : 0);
      var el = chip().querySelector(".casa-fb-badge");
      el.hidden = !n; el.textContent = n > 99 ? "99+" : String(n);
      el.title = EU && EU.admin && b.triagem ? b.triagem + " na fila de triagem" : "respostas novas";
      EU.triagem = b.triagem || 0;
    }).catch(function () { /* sessão caiu: o chip some na próxima tela */ });
  }

  function fechar() { if (JANELA) { JANELA.remove(); JANELA = null; } PRINT = ""; }
  function abrir() {
    fechar();
    var abas = [["enviar", "Enviar"], ["meus", "Meus feedbacks"]];
    if (EU && EU.admin) abas.push(["triagem", "Triagem" + (EU.triagem ? " (" + EU.triagem + ")" : "")], ["codigo", "Código do sistema"]);
    JANELA = document.createElement("div");
    JANELA.className = "casa-fb-fundo";
    JANELA.innerHTML = '<div class="pn casa-fb" role="dialog" aria-modal="true" aria-label="Feedback">' +
      '<div class="cabeca"><h2 class="t">Feedback</h2><button type="button" class="btn ghost peq" data-fechar>✕ Fechar</button></div>' +
      '<div class="chips" role="tablist">' + abas.map(function (a, i) {
        return '<button type="button" role="tab" class="chip' + (i ? "" : " on") + '" data-aba="' + a[0] + '">' + esc(a[1]) + "</button>"; }).join("") +
      '</div><div class="casa-fb-corpo"></div></div>';
    document.body.appendChild(JANELA);
    JANELA.addEventListener("click", function (e) {
      if (e.target === JANELA || e.target.closest("[data-fechar]")) return fechar();
      var a = e.target.closest("[data-aba]");
      if (a) mostrar(a.getAttribute("data-aba"));
    });
    JANELA.addEventListener("keydown", function (e) { if (e.key === "Escape") fechar(); });
    mostrar("enviar");
  }
  function mostrar(aba) {
    JANELA.querySelectorAll("[data-aba]").forEach(function (b) { b.classList.toggle("on", b.getAttribute("data-aba") === aba); });
    var corpo = JANELA.querySelector(".casa-fb-corpo");
    ({ enviar: formEnviar, meus: meus, triagem: triagem, codigo: codigo })[aba](corpo);
  }

  function formEnviar(corpo) {
    corpo.innerHTML =
      '<div class="chips" role="radiogroup" aria-label="Tipo"><label class="marca"><input type="radio" name="fbtipo" value="bug" checked> Problema</label>' +
      '<label class="marca"><input type="radio" name="fbtipo" value="melhoria"> Melhoria</label></div>' +
      '<label class="campo">O que aconteceu ou o que você quer?<textarea class="inp" id="fbMsg" maxlength="5000" placeholder="Conte com suas palavras. A tela de onde você enviou vai junto."></textarea></label>' +
      '<label class="campo" style="margin-top:10px">Print da tela (opcional — também dá para colar com Ctrl+V)<input type="file" id="fbArq" accept="image/*"></label>' +
      '<div id="fbPrevia" class="cap"></div>' +
      '<div class="acts" style="margin-top:12px"><button type="button" class="btn azul" id="fbEnviar">Enviar</button></div>' +
      '<p class="cap">Seu feedback passa primeiro pela triagem do administrador da Auditoria Unimed e depois segue para o TI.</p>';
    function usar(arquivo) {
      if (!arquivo || !/^image\//.test(arquivo.type)) return;
      if (arquivo.size > 8 * 1024 * 1024) return aviso("O print passa de 8 MB. Envie uma imagem menor.", "err");
      var l = new FileReader();
      l.onload = function () { PRINT = l.result; corpo.querySelector("#fbPrevia").textContent = "Print anexado: " + (arquivo.name || "imagem colada"); };
      l.readAsDataURL(arquivo);
    }
    corpo.querySelector("#fbArq").addEventListener("change", function (e) { usar(e.target.files[0]); });
    JANELA.addEventListener("paste", function (e) {
      var it = Array.prototype.find.call(e.clipboardData.items || [], function (i) { return /^image\//.test(i.type); });
      if (it) usar(it.getAsFile());
    });
    corpo.querySelector("#fbEnviar").addEventListener("click", function () {
      var msg = corpo.querySelector("#fbMsg").value.trim();
      if (!msg) return aviso("Escreva o que aconteceu antes de enviar.", "err");
      var b = this; b.disabled = true;
      api("POST", "/_casa/feedback", { tipo: corpo.querySelector("[name=fbtipo]:checked").value, mensagem: msg,
        tela: location.pathname + location.search, print: PRINT })
        .then(function () { aviso("Feedback enviado. Você acompanha a resposta em Meus feedbacks.", "ok"); fechar(); badge(); })
        .catch(function (e) { aviso(e.message, "err"); b.disabled = false; });
    });
  }

  function cartao(f, admin) {
    var etiqueta = f.status === "em_triagem" ? "warn" : f.status === "rejeitado_triagem" || f.status === "rejeitado" ? "crit" : f.status === "resolvido" ? "ok" : "neu";
    return '<div class="pn casa-fb-item">' +
      '<div class="cabeca"><b>#' + f.id + " · " + esc(f.tipo_rotulo) + '</b><span class="tag ' + etiqueta + '">' + esc(f.status_rotulo) + "</span></div>" +
      '<div class="cap" style="margin:0 0 6px">' + esc(quando(f.criado_em)) + (admin && f.autor_nome ? " · " + esc(f.autor_nome) : "") + " · tela " + esc(f.tela || "—") + "</div>" +
      '<div style="white-space:pre-wrap">' + esc(f.mensagem) + "</div>" +
      (f.tem_print ? '<a class="cap" target="_blank" rel="noopener" href="/_casa/feedback/' + f.id + '/print">Ver o print</a>' : "") +
      (f.motivo_rejeicao ? '<div class="aviso crit" style="margin:10px 0 0">Motivo: ' + esc(f.motivo_rejeicao) + "</div>" : "") +
      (f.resposta ? '<div class="aviso ok" style="margin:10px 0 0"><b>Resposta:</b> ' + esc(f.resposta) + (f.commit_hash ? " · commit " + esc(f.commit_hash) : "") + "</div>" : "") +
      "</div>";
  }
  function meus(corpo) {
    corpo.innerHTML = '<p class="cap">Carregando…</p>';
    api("GET", "/_casa/feedback/meus").then(function (d) {
      corpo.innerHTML = (d.feedbacks || []).map(function (f) { return cartao(f, false); }).join("") ||
        '<p class="sub">Você ainda não enviou nenhum feedback.</p>';
      badge();
    }).catch(function (e) { corpo.innerHTML = '<div class="aviso crit">' + esc(e.message) + "</div>"; });
  }
  function triagem(corpo) {
    corpo.innerHTML = '<p class="cap">Carregando…</p>';
    api("GET", "/_casa/feedback").then(function (d) {
      var t = d.triagem || [];
      corpo.innerHTML = '<p class="sub">Aprovado vai para o TI. Recusado volta para quem enviou, com o motivo.</p>' +
        (t.map(function (f) {
          return cartao(f, true).replace(/<\/div>$/, "") +
            '<label class="campo" style="margin-top:10px">Motivo (obrigatório para recusar)<input class="inp" data-motivo="' + f.id + '"></label>' +
            '<div class="acts" style="margin-top:10px"><button type="button" class="btn pri peq" data-aprovar="' + f.id + '">Aprovar e mandar ao TI</button>' +
            '<button type="button" class="btn perigo peq" data-recusar="' + f.id + '">Recusar</button></div></div>';
        }).join("") || '<div class="aviso ok">Nenhum feedback esperando triagem.</div>') +
        ((d.historico || []).length ? '<details class="det" style="margin-top:14px"><summary>Já triados (' + d.historico.length + ")</summary>" +
          d.historico.map(function (f) { return cartao(f, true); }).join("") + "</details>" : "");
      corpo.querySelectorAll("[data-aprovar],[data-recusar]").forEach(function (b) {
        b.addEventListener("click", function () {
          var fid = b.getAttribute("data-aprovar") || b.getAttribute("data-recusar");
          var aprovado = b.hasAttribute("data-aprovar");
          var motivo = (corpo.querySelector('[data-motivo="' + fid + '"]') || {}).value || "";
          if (!aprovado && !motivo.trim()) return aviso("Escreva o motivo da recusa. Ele volta para quem enviou.", "err");
          var pergunta = aprovado ? "Aprovar o feedback #" + fid + " e mandar ao TI?" : "Recusar o feedback #" + fid + "?";
          (window.DP && DP.confirmar ? DP.confirmar(pergunta) : Promise.resolve(true)).then(function (ok) {
            if (!ok) return;
            api("POST", "/_casa/feedback/" + fid + "/triagem", { aprovado: aprovado, motivo: motivo })
              .then(function () { aviso(aprovado ? "Aprovado. Foi para o TI." : "Recusado. O motivo voltou para quem enviou.", "ok"); triagem(corpo); badge(); })
              .catch(function (e) { aviso(e.message, "err"); });
          });
        });
      });
    }).catch(function (e) { corpo.innerHTML = '<div class="aviso crit">' + esc(e.message) + "</div>"; });
  }
  function codigo(corpo) {
    corpo.innerHTML = '<p class="sub">Para o assistente de quem desenvolve: o contrato e a chave do ciclo de código com a Central.</p>' +
      '<div class="acts"><a class="btn peq" href="/_casa/codigo/contrato">⤓ Baixar o contrato</a>' +
      '<button type="button" class="btn peq" id="fbChave">Mostrar a chave</button></div><div id="fbChaveTxt" class="cap"></div>' +
      '<label class="campo" style="margin-top:14px">Enviar o código (.zip, sem venv, .git nem banco)<input type="file" id="fbZip" accept=".zip"></label>' +
      '<div class="acts" style="margin-top:10px"><button type="button" class="btn azul peq" id="fbZipEnviar">Enviar para a Central</button></div><div id="fbZipRes" class="cap"></div>';
    corpo.querySelector("#fbChave").addEventListener("click", function () {
      api("GET", "/_casa/codigo/chave").then(function (d) {
        var alvo = corpo.querySelector("#fbChaveTxt");
        if (!d.configurado) { alvo.textContent = "A chave da Central não está configurada neste servidor (etapa do TI)."; return; }
        alvo.innerHTML = '<code style="user-select:all">' + esc(d.chave) + "</code> · some em " + Math.round((d.segundos || 300) / 60) + " min";
        setTimeout(function () { alvo.textContent = ""; }, (d.segundos || 300) * 1000);
      }).catch(function (e) { aviso(e.message, "err"); });
    });
    corpo.querySelector("#fbZipEnviar").addEventListener("click", function () {
      var f = corpo.querySelector("#fbZip").files[0];
      if (!f) return aviso("Escolha o .zip primeiro.", "err");
      var fd = new FormData(); fd.append("zip", f);
      api("POST", "/_casa/codigo", fd).then(function (d) {
        corpo.querySelector("#fbZipRes").textContent = (d.arquivos || 0) + " arquivo(s) recebidos." +
          ((d.conferencia || []).length ? " Conferência: " + d.conferencia.join(" · ") : "");
      }).catch(function (e) { aviso(e.message, "err"); });
    });
  }

  function iniciar() {
    if (/^\/(login|definir-senha)/.test(location.pathname)) return;
    fetch("/api/eu", { credentials: "same-origin", cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (eu) { if (!eu) return; EU = eu; chip(); badge(); setInterval(badge, 60000); })
      .catch(function () {});
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar); else iniciar();
})();
