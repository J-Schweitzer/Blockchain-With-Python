"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const ns = "http://www.w3.org/2000/svg";
  const state = {token: "", generation: 0, data: null, view: "overview", busy: false,
    auto: true, timer: null, refresh: null, pauseUntil: 0, chartSensor: "", sensor: "",
    historyStart: 0, txStart: 0, txTab: "pending", blockStart: 0, controllers: new Set()};
  const views = {
    overview: ["Visão geral", "Visão geral da rede", "Acompanhe o percurso dos dados, da origem ao bloco confirmado."],
    sensors: ["Sensores", "Identidade em cada leitura", "Consulte dispositivos autorizados e acompanhe a origem dos registros."],
    transactions: ["Transações", "Da leitura à confirmação", "Acompanhe a fila e explore as transações registradas no histórico."],
    blocks: ["Blocos", "Explore a cadeia de registros", "Inspecione o conteúdo, as assinaturas e o vínculo entre os blocos."],
    integrity: ["Integridade", "Uma confiança que se verifica", "Valide o histórico e observe a detecção de alterações em uma cópia isolada."],
    guide: ["Guia da apresentação", "Apresente o caminho do dado", "Um roteiro para mostrar o funcionamento e os limites do protótipo."]
  };
  function el(tag, cls, text) { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = String(text); return n; }
  function icon(name) { const s = document.createElementNS(ns, "svg"); const u = document.createElementNS(ns, "use"); u.setAttribute("href", `#i-${name}`); s.setAttribute("aria-hidden", "true"); s.append(u); return s; }
  function btn(text, cls, action, glyph) { const b = el("button", cls, text); b.type = "button"; if (glyph) b.prepend(icon(glyph)); if (!text) b.setAttribute("aria-label", "Abrir detalhes"); b.addEventListener("click", action); return b; }
  const text = (id, value) => { $(id).textContent = String(value); };
  const short = (value, length = 16) => { const v = String(value ?? "—"); return v.length > length ? `${v.slice(0, length)}…` : v; };
  const number = (value) => new Intl.NumberFormat("pt-BR", {maximumFractionDigits: 2, notation: Math.abs(value) > 1e8 ? "scientific" : "standard"}).format(value);
  function date(value, onlyTime = false) {
    const d = new Date(Number(value) * 1000);
    if (!Number.isFinite(d.getTime())) return "Data indisponível";
    return new Intl.DateTimeFormat("pt-BR", onlyTime ? {hour: "2-digit", minute: "2-digit", second: "2-digit"} : {day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit"}).format(d);
  }
  const pill = (label, kind = "") => el("span", `pill ${kind}`, label);
  function empty(message, detail = "", glyph = "sensor") { const n = el("div", "empty-state"); n.append(icon(glyph), el("strong", "", message)); if (detail) n.append(el("span", "", detail)); return n; }
  function toast(message, error = false) {
    $("toast").className = error ? "toast error" : "toast"; text("toast", message); $("toast").hidden = false;
    clearTimeout(toast.timer); toast.timer = setTimeout(() => { $("toast").hidden = true; }, 5500);
  }
  async function api(path, options = {}) {
    const generation = state.generation;
    const controller = new AbortController(); state.controllers.add(controller);
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const headers = {"Accept": "application/json", "Authorization": `Bearer ${state.token}`};
      if (options.body !== undefined) headers["Content-Type"] = "application/json";
      const response = await fetch(path, {method: options.method || "GET", headers,
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
        signal: controller.signal, credentials: "omit", cache: "no-store", redirect: "error"});
      if (generation !== state.generation) throw Object.assign(new Error("Sessão encerrada"), {ignored: true});
      const data = await response.json();
      if (!response.ok) {
        if (response.status === 429 && response.headers.has("Retry-After")) state.pauseUntil = Date.now() + 60000;
        throw Object.assign(new Error(data.erro?.mensagem || "Não foi possível concluir a operação."), {status: response.status});
      }
      return data;
    } catch (error) {
      if (generation !== state.generation) error.ignored = true;
      if (error.name === "AbortError" && !error.ignored) error.message = "A API demorou para responder. Verifique o servidor local.";
      if (error instanceof TypeError) error.message = "Não foi possível conectar à API. Confira se o servidor está em execução.";
      throw error;
    } finally { clearTimeout(timeout); state.controllers.delete(controller); }
  }
  function disconnected() {
    state.generation += 1; state.token = ""; state.data = null; clearTimeout(state.timer);
    state.controllers.forEach((c) => c.abort()); state.controllers.clear();
    document.querySelectorAll("dialog[open]").forEach((d) => d.close());
    $("app").hidden = true; $("auth-screen").hidden = false; $("token").value = "";
    $("auth-error").hidden = true; $("toast").hidden = true; state.refresh = null; state.busy = false;
    state.sensor = state.chartSensor = ""; state.historyStart = state.txStart = state.blockStart = 0;
    $("sensor-history-card").hidden = true; $("member-name").value = $("member-key").value = "";
    $("lab-result").className = "card lab-result";
    $("lab-result").replaceChildren(el("h2", "", "Uma alteração, uma evidência"), el("p", "", "Execute o teste para comparar a cadeia original com a cópia modificada."));
    ["sensor-grid", "history-rows", "recent-blocks", "queue-preview", "authorities-list", "block-grid", "transactions-rows", "detail-content"].forEach((id) => $(id).replaceChildren());
    $("token").focus();
  }
  function handle(error) {
    if (error.ignored) return;
    if (error.status === 401) { disconnected(); text("auth-error", "Acesso recusado. Confira o token ou conecte-se novamente."); $("auth-error").hidden = false; return; }
    text("global-error", error.message); $("global-error").hidden = false;
    $("connection-badge").classList.add("offline"); $("connection-badge").replaceChildren(el("span", "dot"), document.createTextNode(" Sem atualização"));
    text("overview-integrity", "Atualização indisponível"); text("overview-integrity-note", "Os dados exibidos são da última consulta bem-sucedida.");
    text("integrity-title", "Verificação indisponível"); text("integrity-description", "Confira a conexão com a API e execute a verificação novamente.");
    toast(error.message, true);
  }
  function schedule() { clearTimeout(state.timer); if (state.token && state.auto) state.timer = setTimeout(async () => { if (!document.hidden && Date.now() >= state.pauseUntil) await refresh(); schedule(); }, 6000); }
  async function refresh(force = false) {
    if (!state.token) return;
    if (state.refresh) { if (!force) return state.refresh; await state.refresh; if (!state.token) return; }
    const generation = state.generation;
    const task = (async () => {
      try {
        const data = await api("/painel/dados"); state.data = data;
        $("global-error").hidden = true; $("connection-badge").classList.remove("offline");
        $("connection-badge").replaceChildren(el("span", "dot"), document.createTextNode(" Conectado"));
        renderCommon(); await renderView();
      } catch (error) { handle(error); }
      finally { if (generation === state.generation) state.refresh = null; }
    })();
    state.refresh = task; return task;
  }
  function renderCommon() {
    const d = state.data;
    text("network-short", short(d.rede_id, 17)); $("network-short").title = d.rede_id;
    text("sync-time", `Sincronizado às ${date(d.validacao.verificado_em, true)}`);
    text("mode-label", d.apresentacao ? "MODO DE APRESENTAÇÃO" : "AMBIENTE LOCAL");
    text("nav-pending", d.pendentes); text("overview-integrity", "Integridade verificada");
    text("overview-integrity-note", "Hashes e assinaturas verificados ao carregar o histórico.");
    text("integrity-title", "Histórico válido e verificável"); text("integrity-description", `${d.blocos} blocos verificados, incluindo o gênese. Última consulta às ${date(d.validacao.verificado_em, true)}.`);
    $("demo-block").max = String(Math.max(1, d.blocos - 1));
    $("demo-run").disabled = state.busy || !d.apresentacao || d.blocos <= 1;
    text("demo-availability", !d.apresentacao ? "Inicie a API com --apresentacao para ativar o laboratório." : d.blocos <= 1 ? "Confirme ao menos um bloco com leituras para executar o teste." : "Teste em cópia isolada. O registro original permanece preservado.");
    updateButtons();
  }
  function updateButtons() {
    const d = state.data;
    if (!d) return;
    $("generate-button").disabled = state.busy || !d.simulacao_disponivel;
    $("generate-button").title = d.simulacao_disponivel ? "Gerar uma leitura por sensor autorizado do pacote local" : "Requer pacote de sensores e API iniciada com --apresentacao";
    $("produce-button").disabled = $("produce-transactions").disabled = state.busy || !d.pendentes;
    $("demo-run").disabled = state.busy || !d.apresentacao || d.blocos <= 1;
    text("queue-hint", d.simulacao_disponivel ? "As leituras só entram no histórico após a produção do bloco." : "Envie leituras pelo simulador. Para gerar aqui, use --apresentacao.");
  }
  async function renderView() {
    if (!state.data) return;
    if (state.view === "overview") renderOverview();
    if (state.view === "sensors") { renderSensors(); if (state.sensor) await loadHistory(); }
    if (state.view === "transactions") await loadTransactions();
    if (state.view === "blocks") await loadBlocks();
  }
  function navigate(view) {
    if (!views[view]) return;
    state.view = view;
    document.querySelectorAll("[data-view]").forEach((n) => { n.hidden = n.dataset.view !== view; });
    document.querySelectorAll(".nav-item[data-nav]").forEach((n) => { const active = n.dataset.nav === view; n.classList.toggle("active", active); if (active) n.setAttribute("aria-current", "page"); else n.removeAttribute("aria-current"); });
    text("breadcrumb-current", views[view][0]); text("page-title", views[view][1]); text("page-subtitle", views[view][2]);
    history.replaceState(null, "", `#${view}`); closeMenu(); renderView().catch(handle);
  }
  function renderOverview() {
    const d = state.data;
    const sensors = d.membros.filter((m) => m.papel === "dispositivo");
    text("metric-readings", number(d.transacoes_confirmadas)); text("metric-blocks", number(Math.max(0, d.blocos - 1)));
    text("metric-pending", number(d.pendentes)); text("metric-sensors", sensors.filter((m) => m.ativo).length);
    text("metric-sensors-note", `${sensors.length} dispositivos cadastrados`); text("queue-count", `${d.pendentes} pendentes`);
    const select = $("chart-sensor"); select.replaceChildren();
    sensors.forEach((s) => { const o = el("option", "", s.nome); o.value = s.nome; select.append(o); });
    if (!sensors.some((s) => s.nome === state.chartSensor)) state.chartSensor = sensors[0]?.nome || "";
    select.value = state.chartSensor; select.disabled = !sensors.length;
    renderChart();
    const authorities = d.membros.filter((m) => m.papel === "validador");
    $("authorities-list").replaceChildren(...authorities.map((m) => {
      const next = m.nome === d.proximo_validador;
      const row = el("div", `authority-row${next ? " next" : ""}`); const info = el("div");
      info.append(el("strong", "", m.nome), el("small", "", m.ativo ? "Autoridade autorizada" : "Identidade revogada"));
      row.append(el("span", "authority-avatar", short(m.nome, 3)), info, pill(next ? "Próximo produtor" : m.ativo ? "Autorizado" : "Revogado", next ? "green" : "")); return row;
    }));
    table("recent-blocks", d.ultimos_blocos.map((b) => [btn(`#${b.indice}`, "row-link", () => showBlock(b.indice)),
      b.indice === 0 ? "Gênese" : b.validador, String(b.transacoes), el("span", "mono", short(b.hash, 14)), b.indice === 0 ? "Modelo fixo" : date(b.ts), btn("", "icon-button", () => showBlock(b.indice), "arrow")]), "Nenhum bloco disponível.");
    const queue = d.fila_recente.slice(0, 3).map((t) => {
      const row = el("div", "queue-item"), info = el("div"), glyph = el("span", "sensor-icon"); glyph.append(icon(t.medicao?.unidade === "%" ? "drop" : "temp"));
      info.append(el("strong", "", short(t.dispositivo, 23)), el("small", "", date(t.ts, true)));
      row.append(glyph, info, el("span", "queue-value", `${short(t.valor, 10)} ${t.medicao?.unidade || ""}`)); return row;
    });
    $("queue-preview").replaceChildren(...(queue.length ? queue : [empty("A fila está livre", "Envie ou gere leituras para começar.", "check")]));
  }
  function renderChart() {
    const all = state.data.leituras_recentes.filter((t) => t.dispositivo === state.chartSensor);
    const values = all.filter((t) => String(t.valor).trim() !== "" && Number.isFinite(Number(t.valor))).slice(-20);
    const last = all.at(-1) || state.data.sensores.find((s) => s.nome === state.chartSensor)?.ultima, value = $("chart-value"); value.replaceChildren();
    value.append(el("strong", "", last ? short(last.valor, 17) : "—"), el("span", "", last?.medicao?.unidade || ""), el("small", "", last ? `Última leitura · ${date(last.ts, true)}` : "Aguardando confirmação"));
    text("chart-sample-count", `${values.length} leituras exibidas`);
    const target = $("overview-chart"); target.replaceChildren();
    if (!values.length) { target.append(empty(last ? "Sem valores numéricos na janela recente" : "Ainda não há leituras confirmadas", last ? "Consulte o histórico do sensor para explorar seus registros." : "Gere leituras e produza o primeiro bloco.", "sensor")); return; }
    const svg = document.createElementNS(ns, "svg"); svg.setAttribute("viewBox", "0 0 600 160"); svg.setAttribute("role", "img"); svg.setAttribute("aria-label", `Últimas ${values.length} leituras de ${state.chartSensor}. Valor mais recente: ${last.valor} ${last.medicao?.unidade || ""}.`);
    const add = (tag, attrs, content) => { const n = document.createElementNS(ns, tag); Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, String(v))); if (content !== undefined) n.textContent = String(content); svg.append(n); return n; };
    const nums = values.map((t) => Number(t.valor)), max = Math.max(...nums), min = Math.min(...nums), scale = Math.max(Math.abs(min), Math.abs(max), 1);
    const normMin = min / scale, normMax = max / scale, range = normMax - normMin;
    const xy = values.map((t, i) => [48 + (values.length === 1 ? 265 : i * 535 / (values.length - 1)), 124 - (range === 0 ? .5 : (Number(t.valor) / scale - normMin) / range) * 102]);
    for (let i = 0; i < 4; i++) { const y = 22 + i * 34; add("line", {x1: 48, y1: y, x2: 583, y2: y, class: "grid"}); const val = range === 0 ? min : (normMax - range * i / 3) * scale; add("text", {x: 38, y: y + 3, "text-anchor": "end"}, number(val)); }
    add("path", {d: `M ${xy[0][0]} 128 L ${xy.map((p) => p.join(" ")).join(" L ")} L ${xy.at(-1)[0]} 128 Z`, class: "area"});
    add("polyline", {points: xy.map((p) => p.join(",")).join(" "), class: "line"});
    xy.forEach(([x, y], i) => { const p = add("circle", {cx: x, cy: y, r: values.length < 10 ? 3 : 2, class: "point"}); const title = document.createElementNS(ns, "title"); title.textContent = `${values[i].valor} ${values[i].medicao?.unidade || ""} · ${date(values[i].ts)}`; p.append(title); });
    [...new Set([0, Math.floor((values.length - 1) / 2), values.length - 1])].forEach((i) => add("text", {x: xy[i][0], y: 150, "text-anchor": "middle"}, date(values[i].ts, true)));
    target.append(svg);
  }
  function table(id, rows, message) {
    const target = $(id); target.replaceChildren();
    if (!rows.length) { const tr = el("tr"), td = el("td"); td.colSpan = 10; td.append(empty(message, "", "arrows")); tr.append(td); target.append(tr); return; }
    rows.forEach((cells) => { const tr = el("tr"); cells.forEach((v) => { const td = el("td"); td.append(v instanceof Node ? v : document.createTextNode(String(v ?? "—"))); tr.append(td); }); target.append(tr); });
  }
  function pagination(id, total, start, size, action) {
    const label = total ? `${start + 1}–${Math.min(start + size, total)} de ${total} registros` : "Nenhum registro";
    const prev = btn("Anterior", "button subtle", () => action(Math.max(0, start - size)));
    const next = btn("Próxima", "button subtle", () => action(start + size)); prev.disabled = start === 0; next.disabled = start + size >= total;
    $(id).replaceChildren(el("span", "", label), prev, next);
  }
  function renderSensors() {
    const sensors = state.data.membros.filter((m) => m.papel === "dispositivo");
    text("sensor-total", `${sensors.length} dispositivos cadastrados · ${sensors.filter((s) => s.ativo).length} autorizados`);
    const cards = sensors.map((m) => {
      const s = state.data.sensores.find((v) => v.nome === m.nome), last = s?.ultima;
      const card = el("article", "card sensor-card"), top = el("div", "sensor-card-top"), glyph = el("span", "sensor-icon");
      glyph.append(icon(last?.medicao?.unidade === "%" ? "drop" : "sensor")); top.append(glyph, pill(m.ativo ? "Autorizado" : "Revogado", m.ativo ? "green" : ""));
      const value = el("div", "sensor-reading", last ? short(last.valor, 16) : "—"); value.append(el("span", "", last?.medicao?.unidade || ""));
      const key = el("p", "mono sensor-key", `Chave pública · ${short(m.pub, 19)}`); key.title = m.pub;
      card.append(top, el("h2", "", m.nome), key, value, el("p", "", last ? `${s.leituras} leituras · última em ${date(last.ts)}` : "Nenhuma leitura confirmada"));
      const actions = el("div", "sensor-actions");
      actions.append(btn("Histórico ↗", "text-button", () => openHistory(m.nome)), btn(m.ativo ? "Trocar chave" : "Ativar com nova chave", "text-button", () => openMember(m.nome)));
      if (m.ativo) actions.append(btn("Revogar", "text-button destructive", async () => { if (await confirm("Revogar dispositivo?", `Novas operações de ${m.nome} serão bloqueadas. O histórico confirmado permanece válido.`, "Revogar dispositivo")) await mutate(`/membros/${encodeURIComponent(m.nome)}/revogar`, {}, "Dispositivo revogado. O histórico foi preservado."); }));
      card.append(actions); return card;
    });
    $("sensor-grid").replaceChildren(...(cards.length ? cards : [empty("Nenhum sensor cadastrado", "Cadastre uma chave pública para começar.")]));
  }
  async function openHistory(nome) { state.sensor = nome; state.historyStart = 0; await loadHistory(); $("sensor-history-card").scrollIntoView({behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "nearest"}); }
  async function loadHistory() {
    const nome = state.sensor; if (!nome) return;
    try {
      const page = await api(`/historico/${encodeURIComponent(nome)}?inicio=${state.historyStart}&limite=10`);
      if (state.sensor !== nome) return;
      $("sensor-history-card").hidden = false; text("history-title", `Histórico · ${nome}`); text("history-total", `${page.total} leituras`);
      table("history-rows", page.itens.map((t) => [date(t.ts), `${short(t.valor, 25)} ${t.medicao?.unidade || ""}`, t.medicao?.grandeza || "Não informada", btn(`#${t.bloco}`, "row-link", () => showBlock(t.bloco)), btn(short(t.id_transacao), "row-link mono", () => showTransaction(t.id_transacao))]), "Nenhuma leitura neste histórico.");
      pagination("history-pagination", page.total, page.inicio, 10, (n) => { state.historyStart = n; loadHistory(); });
    } catch (error) { handle(error); }
  }
  async function loadTransactions() {
    const pending = state.txTab === "pending", tab = state.txTab, start = state.txStart;
    const page = await api(`${pending ? "/pendentes" : "/transacoes"}?inicio=${start}&limite=12`);
    if (state.txTab !== tab || state.txStart !== start) return;
    text("transactions-title", pending ? "Fila de transações" : "Transações confirmadas"); text("transactions-note", pending ? "Recebidas com assinatura válida, aguardando confirmação." : "Leituras assinadas e vinculadas aos blocos do histórico."); text("transactions-total", `${page.total} registros`);
    table("transactions-rows", page.itens.map((t) => [t.dispositivo, `${short(t.valor, 20)} ${t.medicao?.unidade || ""}`, date(t.ts), btn(short(t.id_transacao), "row-link mono", () => showTransaction(t.id_transacao)), pending ? pill("Pendente", "amber") : btn(`Bloco #${t.bloco}`, "row-link", () => showBlock(t.bloco)), pending ? btn("Descartar", "text-button", async () => { if (await confirm("Descartar pendência?", "Esta leitura será removida da fila. Nenhum bloco confirmado será alterado.", "Descartar pendência")) await mutate(`/pendentes/${encodeURIComponent(t.id_transacao)}`, undefined, "Pendência descartada.", "DELETE"); }) : btn("Detalhes ↗", "text-button", () => showTransaction(t.id_transacao))]), pending ? "Nenhuma transação na fila." : "Nenhuma transação confirmada.");
    pagination("transactions-pagination", page.total, page.inicio, 12, (n) => { state.txStart = n; loadTransactions().catch(handle); });
  }
  async function loadBlocks() {
    const start = state.blockStart;
    const page = await api(`/cadeia?inicio=${start}&limite=12`); if (state.blockStart !== start) return;
    text("blocks-total", `${page.total} blocos · inclui gênese`);
    $("block-grid").replaceChildren(...page.itens.map((b) => {
      const card = btn("", "card block-card", () => showBlock(b.indice)), top = el("div", "block-card-top");
      card.setAttribute("aria-label", `Abrir bloco #${b.indice}`);
      top.append(el("h2", "", b.indice === 0 ? "#0 · Gênese" : `Bloco #${b.indice}`), pill(b.indice === 0 ? "Inicial" : "Assinado", b.indice === 0 ? "" : "green"));
      const footer = el("div", "block-card-footer"); footer.append(el("span", "", `${b.transacoes.length} leituras`), el("span", "", b.indice === 0 ? "Modelo fixo" : date(b.ts)));
      card.append(top, el("p", "block-validator", b.indice === 0 ? "Início da cadeia" : `Autoridade · ${b.validador}`), el("div", "hash-label", "HASH DO BLOCO"), el("div", "mono block-hash", short(b.hash, 30)), el("div", "hash-label", "HASH ANTERIOR"), el("div", "mono block-hash", short(b.hash_anterior, 30)), footer); return card;
    }));
    pagination("blocks-pagination", page.total, page.inicio, 12, (n) => { state.blockStart = n; loadBlocks().catch(handle); });
  }
  function detail(title, nodes, data, filename) {
    text("detail-title", title); $("detail-content").replaceChildren(...nodes);
    const raw = el("details"), summary = el("summary", "", "Inspecionar registro JSON"); raw.append(summary, el("pre", "json-box", JSON.stringify(data, null, 2)));
    $("detail-content").append(raw, btn("Exportar JSON", "button subtle", () => {
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: "application/json"}));
      const a = el("a"); a.href = url; a.download = filename; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    }));
    $("detail-dialog").showModal();
  }
  function detailRow(label, value) { const n = el("div", "detail-row"); n.append(el("span", "", label), el("code", "mono", value || "Não se aplica")); return n; }
  async function showBlock(indice) {
    try {
      const b = await api(`/blocos/${indice}`), meta = el("div", "detail-meta");
      [["Validador", b.validador], ["Leituras", b.transacoes.length], ["Registro", b.indice === 0 ? "Bloco inicial fixo" : date(b.ts)]].forEach(([k, v]) => { const d = el("div"); d.append(el("span", "", k), el("strong", "", v)); meta.append(d); });
      const reads = el("div", "detail-transactions"); reads.append(el("h3", "", "Leituras incluídas"));
      if (!b.transacoes.length) reads.append(empty("O gênese não contém leituras.", "", "cube"));
      b.transacoes.forEach((t) => { const row = el("div", "queue-item"), info = el("div"); info.append(el("strong", "", t.dispositivo), el("small", "", date(t.ts))); row.append(info, el("span", "queue-value", `${short(t.valor, 25)} ${t.medicao?.unidade || ""}`)); reads.append(row); });
      detail(`Bloco #${b.indice}`, [meta, detailRow("Hash do bloco", b.hash), detailRow("Hash do bloco anterior", b.hash_anterior), detailRow("Assinatura do validador", b.assinatura), reads], b, `bloco-${b.indice}.json`);
    } catch (error) { handle(error); }
  }
  async function showTransaction(id) {
    try { const t = await api(`/transacoes/${encodeURIComponent(id)}`); const tx = t.transacao; detail("Detalhes da transação", [pill(t.situacao === "pendente" ? "Pendente" : `Confirmada · bloco #${t.bloco}`, t.situacao === "pendente" ? "amber" : "green"), detailRow("Dispositivo", tx.dispositivo), detailRow("Leitura", `${tx.valor} ${tx.medicao?.unidade || ""}`), detailRow("Identificador", tx.id_transacao), detailRow("Assinatura do dispositivo", tx.assinatura)], t, `transacao-${tx.id_transacao}.json`); } catch (error) { handle(error); }
  }
  async function mutate(path, body, message, method = "POST") {
    if (state.busy) return;
    state.busy = true; updateButtons();
    try { const data = await api(path, {method, body}); toast(message || "Operação concluída."); await refresh(true); return data; }
    catch (error) { handle(error); return null; }
    finally { state.busy = false; updateButtons(); }
  }
  async function produce() { const b = await mutate("/blocos", {}, "Bloco confirmado e histórico atualizado."); if (b) toast(`Bloco #${b.indice} confirmado por ${b.validador}.`); }
  async function verify() {
    try { const result = await api("/validar"); if (result.valida) { await refresh(true); toast(`${result.blocos} blocos verificados. Hashes e assinaturas válidos.`); } else throw new Error(result.motivo || "Falha na validação."); } catch (error) { handle(error); }
  }
  function confirm(title, message, label) {
    const dialog = $("confirm-dialog"); dialog.returnValue = "cancel"; text("confirm-title", title); text("confirm-message", message); text("confirm-accept", label); dialog.showModal();
    return new Promise((resolve) => dialog.addEventListener("close", () => resolve(dialog.returnValue === "ok"), {once: true}));
  }
  function openMember(name = "") { state.memberMode = name ? "rotate" : "create"; text("member-title", name ? "Atualizar chave do sensor" : "Cadastrar sensor"); $("member-name").value = name; $("member-name").readOnly = Boolean(name); $("member-key").value = ""; $("member-error").hidden = true; $("member-dialog").showModal(); }
  function closeMenu() { $("sidebar").classList.remove("open"); $("nav-backdrop").hidden = true; $("menu-button").setAttribute("aria-expanded", "false"); }
  $("auth-form").addEventListener("submit", async (event) => {
    event.preventDefault(); $("login-button").disabled = true; $("auth-error").hidden = true;
    state.generation += 1; state.token = $("token").value; state.pauseUntil = 0;
    try { state.data = await api("/painel/dados"); $("token").value = ""; $("auth-screen").hidden = true; $("app").hidden = false; renderCommon(); navigate(views[location.hash.slice(1)] ? location.hash.slice(1) : "overview"); schedule(); }
    catch (error) { state.token = ""; text("auth-error", error.status === 401 ? "Token inválido. Use o mesmo token definido ao iniciar a API." : error.message); $("auth-error").hidden = false; }
    finally { $("login-button").disabled = false; }
  });
  document.querySelectorAll("[data-nav]").forEach((b) => b.addEventListener("click", () => navigate(b.dataset.nav)));
  $("logout-button").addEventListener("click", disconnected);
  $("refresh-button").addEventListener("click", () => refresh());
  $("verify-button").addEventListener("click", verify); $("integrity-check").addEventListener("click", verify);
  $("auto-button").addEventListener("click", () => { state.auto = !state.auto; $("auto-button").setAttribute("aria-pressed", String(state.auto)); $("auto-button").title = state.auto ? "Pausar atualização automática" : "Retomar atualização automática"; $("auto-button").replaceChildren(el("span", "pulse-dot"), document.createTextNode(state.auto ? "Atualização a cada 6s" : "Atualização pausada")); schedule(); });
  document.addEventListener("visibilitychange", () => { if (!document.hidden && state.token && state.auto && Date.now() >= state.pauseUntil) refresh(); });
  $("chart-sensor").addEventListener("change", (e) => { state.chartSensor = e.target.value; renderChart(); });
  $("generate-button").addEventListener("click", async () => { const result = await mutate("/apresentacao/leituras", {}, "Leituras simuladas assinadas e adicionadas à fila."); if (result) toast(`${result.leituras.length} leituras simuladas na fila. Produza um bloco para confirmá-las.`); });
  $("produce-button").addEventListener("click", produce); $("produce-transactions").addEventListener("click", produce);
  for (const tab of ["pending", "confirmed"]) $(tab === "pending" ? "tab-pending" : "tab-confirmed").addEventListener("click", () => { state.txTab = tab; state.txStart = 0; for (const [id, name] of [["tab-pending", "pending"], ["tab-confirmed", "confirmed"]]) { $(id).classList.toggle("selected", name === tab); $(id).setAttribute("aria-pressed", String(name === tab)); } loadTransactions().catch(handle); });
  $("detail-close").addEventListener("click", () => $("detail-dialog").close()); $("member-close").addEventListener("click", () => $("member-dialog").close());
  $("confirm-cancel").addEventListener("click", () => $("confirm-dialog").close("cancel")); $("confirm-accept").addEventListener("click", () => $("confirm-dialog").close("ok"));
  $("register-button").addEventListener("click", () => openMember());
  $("member-form").addEventListener("submit", async (event) => {
    event.preventDefault(); if (state.busy) return; state.busy = true; updateButtons(); $("member-error").hidden = true;
    const nome = $("member-name").value.trim(), pub = $("member-key").value.trim();
    try { const rotate = state.memberMode === "rotate"; await api(rotate ? `/membros/${encodeURIComponent(nome)}` : "/membros", {method: rotate ? "PUT" : "POST", body: rotate ? {pub_hex: pub} : {nome, pub_hex: pub}}); $("member-dialog").close(); toast("Identidade salva no cadastro."); await refresh(); }
    catch (error) { if (error.status === 401) handle(error); else if (!error.ignored) { text("member-error", error.message); $("member-error").hidden = false; } }
    finally { state.busy = false; updateButtons(); }
  });
  $("integrity-form").addEventListener("submit", async (event) => {
    event.preventDefault(); if (state.busy) return; state.busy = true; updateButtons();
    try {
      const r = await api("/apresentacao/integridade", {method: "POST", body: {bloco: Number($("demo-block").value), valor: $("demo-value").value, recalcular_hash: $("demo-recalculate").checked}});
      const result = $("lab-result"); result.className = "card lab-result complete";
      const outcome = el("div", "result-outcome"); outcome.append(el("h2", "", r.copia_valida ? "A cópia passou na validação" : "Alteração detectada na cópia"), el("p", "", r.motivo || "Nenhuma divergência encontrada."));
      const comparison = el("div", "result-comparison"); for (const [label, val] of [["VALOR ORIGINAL", r.valor_original], ["VALOR NA CÓPIA", r.valor_alterado]]) { const item = el("div"); item.append(el("span", "", label), el("strong", "", short(val, 26))); comparison.append(item); }
      const foot = el("div", "result-footer"); foot.append(icon("check"), el("span", "", "Cadeia original preservada. Nenhum dado foi gravado."));
      result.replaceChildren(outcome, pill(`Bloco #${r.bloco} · ${r.hash_atualizado_na_copia ? "Hash recalculado" : "Conteúdo alterado"}`), comparison, el("div", "hash-label", "HASH REGISTRADO"), el("div", "result-hash", r.hash_registrado), el("div", "hash-label", "HASH DO CONTEÚDO ALTERADO"), el("div", "result-hash", r.hash_recalculado), foot);
      toast("Demonstração concluída em uma cópia isolada.");
    } catch (error) { handle(error); }
    finally { state.busy = false; updateButtons(); }
  });
  $("menu-button").addEventListener("click", () => { const open = !$("sidebar").classList.contains("open"); $("sidebar").classList.toggle("open", open); $("nav-backdrop").hidden = !open; $("menu-button").setAttribute("aria-expanded", String(open)); });
  $("nav-backdrop").addEventListener("click", closeMenu);
})();
