/* Tema pessoal (receita tema-vidro-e-relevo): marca data-estilo / data-modo / data-destaque no <html>.
   Ordem: tema da pessoa -> padrão do sistema -> padrão da receita. Quem decide o que vale é o servidor
   (/api/tema); o navegador só guarda uma cópia para a tela não piscar ao abrir. */
(function () {
  var VALORES = { estilo: ["vidro", "relevo"], modo: ["claro", "escuro"], destaque: ["azul", "marinho"] };
  var PADRAO = { estilo: "relevo", modo: "claro", destaque: "azul" };

  function normalizar(t) {
    var s = {};
    Object.keys(VALORES).forEach(function (k) {
      s[k] = t && VALORES[k].indexOf(t[k]) >= 0 ? t[k] : PADRAO[k];
    });
    return s;
  }
  function aplicar(t) {
    t = normalizar(t);
    var h = document.documentElement;
    h.setAttribute("data-estilo", t.estilo);
    h.setAttribute("data-modo", t.modo);
    h.setAttribute("data-destaque", t.destaque);
    document.querySelectorAll("[data-tema-modo]").forEach(function (b) {
      b.textContent = t.modo === "escuro" ? "☀ Modo claro" : "☾ Modo escuro";
    });
    try { localStorage.setItem("unimed-tema", JSON.stringify(t)); } catch (e) { /* sem armazenamento: segue */ }
    window.TEMA_ATUAL = t;
    return t;
  }
  function gravar(parcial) {
    return fetch("/api/tema", {
      method: "PUT", credentials: "same-origin",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(parcial)
    }).then(function (r) { if (!r.ok) throw new Error(); return r.json(); });
  }

  var guardado = null;
  try { guardado = JSON.parse(localStorage.getItem("unimed-tema") || "null"); } catch (e) { guardado = null; }
  aplicar(guardado);

  fetch("/api/tema", { credentials: "same-origin", cache: "no-store" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) { if (d && d.tema) aplicar(d.tema); })
    .catch(function () { /* fora do ar: fica a cópia local */ });

  window.Tema = {
    aplicar: aplicar,
    atual: function () { return window.TEMA_ATUAL; },
    alternarModo: function () {
      var t = aplicar(Object.assign({}, window.TEMA_ATUAL, { modo: window.TEMA_ATUAL.modo === "escuro" ? "claro" : "escuro" }));
      gravar({ modo: t.modo }).catch(function () {
        if (window.DP) DP.toast("Não consegui guardar o modo. Ele volta ao anterior quando a tela recarregar.", "err");
      });
    },
    gravar: gravar
  };

  // tela "Meu tema": prévia na hora; só o Salvar grava
  var salvo = null;
  function marcarEscolhas() {
    var t = window.TEMA_ATUAL || {};
    document.querySelectorAll("[data-escolha-estilo]").forEach(function (b) { b.classList.toggle("em-uso", b.getAttribute("data-escolha-estilo") === t.estilo); });
    document.querySelectorAll("[data-escolha-modo]").forEach(function (b) { b.classList.toggle("on", b.getAttribute("data-escolha-modo") === t.modo); });
    document.querySelectorAll("[data-escolha-destaque]").forEach(function (b) { b.classList.toggle("on", b.getAttribute("data-escolha-destaque") === t.destaque); });
  }
  function aviso(msg, tipo) { if (window.DP) DP.toast(msg, tipo || "ok"); }
  document.addEventListener("click", function (e) {
    if (e.target.closest("[data-tema-modo]")) { e.preventDefault(); window.Tema.alternarModo(); marcarEscolhas(); return; }
    var esc = e.target.closest("[data-escolha-estilo],[data-escolha-modo],[data-escolha-destaque]");
    if (esc) {
      if (!salvo) salvo = Object.assign({}, window.TEMA_ATUAL);
      var t = Object.assign({}, window.TEMA_ATUAL);
      ["estilo", "modo", "destaque"].forEach(function (k) { var v = esc.getAttribute("data-escolha-" + k); if (v) t[k] = v; });
      aplicar(t); marcarEscolhas(); return;
    }
    var ac = e.target.closest("[data-tema-acao]");
    if (!ac) return;
    var qual = ac.getAttribute("data-tema-acao"), t = window.TEMA_ATUAL;
    if (qual === "descartar") { if (salvo) aplicar(salvo); salvo = null; marcarEscolhas(); return; }
    var corpo = qual === "padrao" ? { voltar_ao_padrao: true } :
      Object.assign({ estilo: t.estilo, modo: t.modo, destaque: t.destaque }, qual === "sistema" ? { como_padrao: true } : {});
    gravar(corpo).then(function (d) {
      salvo = null; if (d && d.tema) aplicar(d.tema); marcarEscolhas();
      aviso(qual === "sistema" ? "Tema padrão do sistema salvo. Vale na entrada e para quem não personalizou." :
            qual === "padrao" ? "Voltou ao tema padrão do sistema." : "Seu tema foi salvo.");
    }).catch(function () { aviso("Não consegui salvar o tema. Tente de novo.", "err"); });
  });
  // o Dash redesenha o cabeçalho: o rótulo do botão acompanha
  new MutationObserver(function () {
    document.querySelectorAll("[data-tema-modo]").forEach(function (b) {
      var txt = window.TEMA_ATUAL.modo === "escuro" ? "☀ Modo claro" : "☾ Modo escuro";
      if (b.textContent !== txt) b.textContent = txt;
    });
    if (document.querySelector("[data-escolha-estilo]")) marcarEscolhas();
  }).observe(document.documentElement, { childList: true, subtree: true });
})();
