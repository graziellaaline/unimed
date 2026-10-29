/* Grade da Auditoria Unimed (dash-ag-grid) — o mesmo filtro estilo Excel da versão Streamlit
   (app/grade.py): A→Z / Z→A, busca, "Selecionar tudo", caixinhas; os filtros conversam entre si.
   Classe JavaScript pura: o AG Grid aceita componente não-React dentro do dash-ag-grid. */
(function () {
  var UniFiltro = class UniFiltro {
    init(p) {
        this.p = p;
        this.aplicado = null;
        this.pend = new Set();
        this.valores = [];
        this.visiveis = [];
        this.busca = '';
        this.hidePopup = null;
        this.eGui = document.createElement('div');
        this.eGui.className = 'uni-filtro';
        this.eGui.innerHTML = '<div class="uni-ordem"><button type="button" data-act="asc">&#9650; A&rarr;Z</button><button type="button" data-act="desc">&#9660; Z&rarr;A</button></div>'
            + '<input class="uni-busca" type="text" placeholder="Buscar...">'
            + '<label class="uni-todos"><input type="checkbox" class="uni-chk-todos"><span>Selecionar tudo</span></label>'
            + '<div class="uni-lista"></div>'
            + '<div class="uni-acoes"><button type="button" data-act="limpar">Limpar</button><button type="button" class="uni-ok" data-act="ok">OK</button></div>';
        this.eLista = this.eGui.querySelector('.uni-lista');
        this.eBusca = this.eGui.querySelector('.uni-busca');
        this.eTodos = this.eGui.querySelector('.uni-chk-todos');
        this.eBusca.addEventListener('input', (e) => { this.busca = e.target.value.toLowerCase(); this.render(); });
        this.eTodos.addEventListener('change', (e) => { this.marcarVisiveis(e.target.checked); this.render(); });
        this.eGui.addEventListener('keydown', (e) => { if (e.key === 'Enter') { this.aplicar(); } });
        this.eGui.addEventListener('click', (e) => {
            const b = e.target.closest('button');
            if (!b) { return; }
            const a = b.getAttribute('data-act');
            if (a === 'asc' || a === 'desc') { this.ordenar(a); }
            else if (a === 'limpar') { this.limpar(); }
            else if (a === 'ok') { this.aplicar(); }
        });
    }

    texto(v) {
        if (v === null || v === undefined) { return ''; }
        return String(v);
    }

    escapar(s) {
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    carregarValores() {
        const vistos = new Set();
        const meu = this.p.column.getColId();
        const modelo = this.p.api.getFilterModel() || {};
        const outros = Object.keys(modelo).filter((c) => c !== meu && modelo[c] && modelo[c].valores).map((c) => [c, new Set(modelo[c].valores)]);
        this.p.api.forEachLeafNode((n) => {
            const passa = outros.every((o) => o[1].has(this.texto(this.p.api.getCellValue({ rowNode: n, colKey: o[0] }))));
            if (passa) { vistos.add(this.texto(this.p.getValue(n))); }
        });
        this.valores = Array.from(vistos).sort((a, b) => a.localeCompare(b, 'pt-BR', { numeric: true, sensitivity: 'base' }));
        this.pend = this.aplicado === null ? new Set(this.valores) : new Set(this.aplicado);
    }

    render() {
        const termo = this.busca;
        this.visiveis = termo ? this.valores.filter((v) => v.toLowerCase().indexOf(termo) >= 0) : this.valores.slice();
        let html = '';
        this.visiveis.forEach((v, i) => {
            const marcado = this.pend.has(v) ? ' checked' : '';
            const rotulo = v === '' ? '<i>(vazio)</i>' : this.escapar(v);
            html += '<label class="uni-item" title="' + this.escapar(v) + '"><input type="checkbox" data-i="' + i + '"' + marcado + '><span>' + rotulo + '</span></label>';
        });
        this.eLista.innerHTML = html || '<div class="uni-vazio">Nenhum valor encontrado</div>';
        this.eLista.querySelectorAll('input[type=checkbox]').forEach((el) => {
            el.addEventListener('change', (ev) => {
                const v = this.visiveis[parseInt(ev.target.getAttribute('data-i'), 10)];
                if (ev.target.checked) { this.pend.add(v); } else { this.pend.delete(v); }
                this.sincTodos();
            });
        });
        this.sincTodos();
    }

    sincTodos() {
        const marcados = this.visiveis.filter((v) => this.pend.has(v)).length;
        this.eTodos.checked = this.visiveis.length > 0 && marcados === this.visiveis.length;
        this.eTodos.indeterminate = marcados > 0 && marcados < this.visiveis.length;
    }

    marcarVisiveis(ligar) {
        this.visiveis.forEach((v) => { if (ligar) { this.pend.add(v); } else { this.pend.delete(v); } });
    }

    ordenar(dir) {
        this.p.api.applyColumnState({ state: [{ colId: this.p.column.getColId(), sort: dir }], defaultState: { sort: null } });
        this.fechar();
    }

    limpar() {
        this.aplicado = null;
        this.busca = '';
        this.eBusca.value = '';
        this.carregarValores();
        this.render();
        this.p.filterChangedCallback();
        this.fechar();
    }

    aplicar() {
        this.aplicado = this.valores.every((v) => this.pend.has(v)) ? null : new Set(this.pend);
        this.p.filterChangedCallback();
        this.fechar();
    }

    fechar() {
        if (this.hidePopup) { this.hidePopup(); }
    }

    getGui() { return this.eGui; }

    isFilterActive() { return this.aplicado !== null; }

    doesFilterPass(pr) { return this.aplicado.has(this.texto(this.p.getValue(pr.node))); }

    getModel() { return this.aplicado === null ? null : { valores: Array.from(this.aplicado) }; }

    setModel(m) { this.aplicado = m && m.valores ? new Set(m.valores) : null; }

    afterGuiAttached(pr) {
        this.hidePopup = pr && pr.hidePopup ? pr.hidePopup : null;
        this.busca = '';
        this.eBusca.value = '';
        this.carregarValores();
        this.render();
        setTimeout(() => { this.eBusca.focus(); }, 10);
    }
};
  var VAZIOS = ["", "NAT", "NAN", "NONE", "NULL", "NONE."];
  function vazio(v) { return v === null || v === undefined || VAZIOS.indexOf(String(v).trim().toUpperCase()) >= 0; }

  window.dashAgGridComponentFunctions = Object.assign(window.dashAgGridComponentFunctions || {}, { UniFiltro: UniFiltro });
  window.dashAgGridFunctions = Object.assign(window.dashAgGridFunctions || {}, {
    uniVazio: function (p) { return vazio(p.value) ? "—" : p.value; },
    uniBRL: function (p) {
      if (vazio(p.value)) return "—";
      var n = Number(p.value); if (isNaN(n)) return String(p.value);
      return "R$ " + n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    },
    uniData: function (p) {
      if (vazio(p.value)) return "—";
      var s = String(p.value).trim(), m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
      if (m) return m[3] + "/" + m[2] + "/" + m[1];
      var d = new Date(s); if (isNaN(d.getTime())) return s;
      return String(d.getUTCDate()).padStart(2, "0") + "/" + String(d.getUTCMonth() + 1).padStart(2, "0") + "/" + d.getUTCFullYear();
    },
    // duplo clique copia a célula (coluna editável fica de fora: nela o clique edita)
    uniCopiar: function (e) {
      if (!e.colDef || e.colDef.editable || vazio(e.value)) return;
      var v = String(e.value);
      (navigator.clipboard ? navigator.clipboard.writeText(v) : Promise.reject()).catch(function () {
        var ta = document.createElement("textarea"); ta.value = v; ta.style.position = "fixed"; ta.style.opacity = "0";
        document.body.appendChild(ta); ta.select(); try { document.execCommand("copy"); } catch (x) {} ta.remove();
      });
      try { e.api.flashCells({ rowNodes: [e.node], columns: [e.column.getColId()] }); } catch (x) {}
      if (window.DP) DP.toast("Copiado: " + (v.length > 40 ? v.slice(0, 40) + "…" : v), "ok");
    }
  });
})();
