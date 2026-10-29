/* Gráficos da Auditoria Unimed: o servidor manda os números em data-g, aqui vira SVG com as
   cores do tema (var(--chart-main) / var(--chart-ctx)) — trocar claro/escuro não pede redesenho.
   Modelo do kit: uma cor de série, grade pontilhada clara, número escuro, um eixo só. */
(function () {
  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  var FMT = {
    num: function (v) { return v.toLocaleString("pt-BR"); },
    casos: function (v) { return v.toLocaleString("pt-BR") + (v === 1 ? " caso" : " casos"); },
    brl: function (v) { return "R$ " + v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); },
    brl0: function (v) { return "R$ " + Math.round(v).toLocaleString("pt-BR"); }
  };
  var CORES = ["var(--chart-main)", "var(--chart-ctx)", "var(--chart-3)"];
  function barras(d, fmt, series) {
    // d: [[rótulo, v1, v2, ...]]; várias séries = barras agrupadas, na ordem fixa das cores
    var k = Math.max(1, d.length ? d[0].length - 1 : 1), bh = 14, lh = k * (bh + 3) + 12;
    var W = 680, pl = 230, pr = 120, topo = k > 1 ? 24 : 0, H = d.length * lh + 10 + topo, s = "";
    var mx = Math.max.apply(null, d.map(function (x) { return Math.max.apply(null, x.slice(1)); })) || 1;
    if (k > 1) (series || []).forEach(function (nome, j) {
      var x0 = pl + j * 130;
      s += '<rect x="' + x0 + '" y="4" width="12" height="12" rx="3" fill="' + CORES[j % 3] + '"/><text x="' + (x0 + 18) + '" y="14">' + esc(nome) + "</text>";
    });
    d.forEach(function (x, i) {
      var y0 = topo + i * lh + 6, rot = x[0].length > 32 ? x[0].slice(0, 31) + "…" : x[0];
      s += '<text x="' + (pl - 8) + '" y="' + (y0 + (lh - 12) / 2 + 5) + '" text-anchor="end">' + esc(rot) + "<title>" + esc(x[0]) + "</title></text>";
      for (var j = 0; j < k; j++) {
        var v = x[j + 1] || 0, w = Math.max((W - pl - pr) * Math.abs(v) / mx, 1), y = y0 + j * (bh + 3);
        s += '<rect x="' + pl + '" y="' + y + '" width="' + w.toFixed(1) + '" height="' + bh + '" rx="4" fill="' + CORES[j % 3] + '"><title>' +
          esc((series && series[j] ? series[j] + ": " : "") + fmt(v)) + "</title></rect>" +
          '<text class="v" x="' + (pl + w + 6).toFixed(1) + '" y="' + (y + bh - 2) + '">' + esc(fmt(v)) + "</text>";
      }
    });
    return '<svg class="ch" viewBox="0 0 ' + W + " " + H + '">' + s + "</svg>";
  }
  function tempo(d, fmt) {
    var W = 520, H = 210, pb = 28, pt = 26, pl = 8, n = d.length;
    var bw = Math.min(46, (W - 2 * pl) / n * 0.6), gap = (W - 2 * pl - n * bw) / Math.max(n - 1, 1);
    var mx = (Math.max.apply(null, d.map(function (x) { return x[1]; })) || 1) * 1.08, s = "";
    [1, 2, 3].forEach(function (g) { var y = pt + (H - pb - pt) * (1 - g / 3); s += '<line x1="0" x2="' + W + '" y1="' + y + '" y2="' + y + '" stroke="var(--grid)" stroke-dasharray="3 4"/>'; });
    d.forEach(function (x, i) {
      var px = pl + i * (bw + gap), h = (H - pb - pt) * x[1] / mx, y = H - pb - h, ult = i === n - 1;
      s += '<rect x="' + px.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + h.toFixed(1) + '" rx="7" fill="' +
        (ult ? "var(--chart-main)" : "var(--chart-ctx)") + '"><title>' + esc(x[0]) + ": " + esc(fmt(x[1])) + "</title></rect>" +
        '<text x="' + (px + bw / 2).toFixed(1) + '" y="' + (H - 8) + '" text-anchor="middle">' + esc(x[0]) + "</text>";
      if (ult) s += '<text class="v" x="' + (px + bw / 2).toFixed(1) + '" y="' + (y - 8).toFixed(1) + '" text-anchor="middle">' + esc(fmt(x[1])) + "</text>";
    });
    return '<svg class="ch" viewBox="0 0 ' + W + " " + H + '">' + s + "</svg>";
  }
  function desenhar(el) {
    var bruto = el.getAttribute("data-g");
    if (el.__desenhado === bruto) return;
    el.__desenhado = bruto;
    try {
      var d = JSON.parse(bruto), fmt = FMT[el.getAttribute("data-fmt")] || FMT.num;
      var series = JSON.parse(el.getAttribute("data-series") || "[]");
      el.innerHTML = el.getAttribute("data-tipo") === "tempo" ? tempo(d, fmt) : barras(d, fmt, series);
    } catch (e) { el.textContent = "Não foi possível desenhar o gráfico."; }
  }
  function varrer() { document.querySelectorAll(".grafico[data-g]").forEach(desenhar); }
  new MutationObserver(varrer).observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["data-g"] });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", varrer); else varrer();
})();
