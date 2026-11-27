/* ACE site: navigation, the simulated phone, and the coverage and status pages.
   Everything from the server is placed with textContent, never as HTML. */
(function () {
  "use strict";
  const page = document.body.dataset.page;
  const $ = (sel, root) => (root || document).querySelector(sel);
  const el = (tag, attrs, ...kids) => {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat()) if (kid !== null && kid !== undefined) node.append(kid.nodeType ? kid : document.createTextNode(kid));
    return node;
  };

  // Navigation ------------------------------------------------------------------------------------------------
  const current = $(`[data-nav="${page}"]`);
  if (current) current.setAttribute("aria-current", "page");
  const menu = $(".menu"), nav = $("#nav");
  if (menu && nav) menu.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    menu.setAttribute("aria-expanded", String(open));
  });

  let countriesPromise = null;
  const countries = () => countriesPromise || (countriesPromise = fetch("/v1/countries").then((r) => {
    if (!r.ok) throw new Error("countries " + r.status);
    return r.json();
  }));

  // The simulated phone ---------------------------------------------------------------------------------------
  const KIND = {
    answer: "Grounded answer from checked sources",
    emergency: "Safety rail: the national emergency numbers, before anything else",
    scam: "Scam Shield verdict",
    clarify: "No checked guidance matched, so ACE said so",
    system: "Command",
  };
  const CHANNELS = [["ussd", "USSD"], ["sms", "SMS"], ["voice", "Voice"], ["whatsapp", "WhatsApp"], ["rcs", "RCS"]];

  async function post(path, body) {
    const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body), credentials: "same-origin" });
    const data = await r.json().catch(() => ({ error: "ACE did not answer. Try again in a moment." }));
    if (!r.ok) throw new Error(data.error || "ACE did not answer.");
    return data;
  }

  function regionCountry(list) {
    const codes = new Set(list.map((c) => c.code));
    for (const tag of navigator.languages || [navigator.language || ""]) {
      const region = (tag.split("-")[1] || "").toUpperCase();
      if (codes.has(region)) return region;
    }
    return "";
  }

  async function buildSim(root) {
    const compact = root.dataset.mode === "compact";
    let data;
    try { data = await countries(); } catch (e) {
      root.append(el("p", { class: "noscript", text: "The phone could not load. Refresh the page to try again." }));
      return;
    }
    const byCode = Object.fromEntries(data.countries.map((c) => [c.code, c]));
    const langs = data.languages;
    const state = { country: "", language: "auto", channel: compact ? "sms" : "ussd", path: [], threads: {} };

    // controls
    const countrySel = el("select", { "aria-label": "Country" }, el("option", { value: "", text: "Choose a country" }),
      data.countries.map((c) => el("option", { value: c.code, text: c.name })));
    const langSel = el("select", { "aria-label": "Language" });
    const controls = el("div", { class: "controls" },
      el("label", {}, "Country", countrySel), el("label", {}, "Language", langSel));

    // phone
    const tabs = el("div", { class: "tabs", role: "tablist", "aria-label": "Channel" });
    const views = {};
    const screen = el("div", { class: "screen", "aria-live": "polite" });
    const meter = el("div", { class: "meter" }, el("span", { text: "*384#" }), el("span", { text: "" }));
    const ussdInput = el("input", { placeholder: "Reply with a number or text", autocomplete: "off", "aria-label": "USSD reply" });
    const ussdSend = el("button", { type: "button", text: "Send" });
    const keypad = el("div", { class: "keypad" }, ["1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#"].map((k) =>
      el("button", { type: "button", text: k, "aria-label": "Key " + k, onclick: () => { ussdInput.value += k; ussdInput.focus(); } })));
    const dial = el("button", { type: "button", class: "dial", text: "Dial *384#" });
    views.ussd = el("div", { role: "tabpanel" }, screen, meter, el("div", { class: "compose" }, ussdInput, ussdSend),
      compact ? null : keypad, dial);
    const chat = el("div", { class: "chat", "aria-live": "polite" });
    const chatInput = el("input", { autocomplete: "off", "aria-label": "Message" });
    const chatSend = el("button", { type: "button", text: "Send" });
    views.chat = el("div", { role: "tabpanel", hidden: true }, chat, el("div", { class: "compose" }, chatInput, chatSend));
    const forget = el("button", { type: "button", class: "linkish", text: "Forget this session" });
    const footNote = el("span", { class: "meta", text: "" });
    const phone = el("div", { class: "phone" }, tabs, views.ussd, views.chat, el("div", { class: "phone-foot" }, footNote, forget));
    const previewNote = el("p", { class: "preview-note", hidden: true });
    const left = el("div", {}, controls, phone, previewNote);

    // panel
    const why = el("div", { class: "explain" }, el("span", { class: "muted", text: "Send a message to see how ACE grounded its answer." }));
    const cites = el("div");
    const tries = el("div", { class: "tries" });
    const panel = compact
      ? el("div", { class: "panel" }, why, cites, el("p", { class: "muted" }, el("a", { href: "/try", text: "Open the full phone, with every channel and its sources" })))
      : el("div", { class: "panel" }, el("h2", { text: "What ACE did" }), why, cites,
        el("h2", { class: "gap-top", text: "Try these" }), tries,
        el("p", { class: "muted gap-top", text: "Suggestions are in English, or in French or Portuguese where English is not offered. Ask in any language the country lists, and ACE answers in it." }));
    if (compact) panel.append(el("div", { class: "tries" }));
    root.append(left, panel);
    const triesBox = compact ? panel.lastChild : tries;

    // tabs
    const tabButtons = CHANNELS.filter(([id]) => !compact || id !== "voice").map(([id, label]) =>
      el("button", { type: "button", role: "tab", "aria-selected": String(id === state.channel), text: label,
        onclick: () => setChannel(id) }));
    tabs.append(...tabButtons);
    if (compact) tabs.style && tabs.classList.add("four");

    function setChannel(id) {
      state.channel = id;
      tabButtons.forEach((b, i) => b.setAttribute("aria-selected", String(CHANNELS.filter(([c]) => !compact || c !== "voice")[i][0] === id)));
      views.ussd.hidden = id !== "ussd";
      views.chat.hidden = id === "ussd";
      chat.className = "chat" + (id === "whatsapp" ? " wa" : id === "voice" ? " voice" : "");
      chatInput.placeholder = id === "voice" ? "Say something, as you would on a call" : "Type a message in any language the country lists";
      renderThread();
    }

    function langLabel(code) {
      const l = langs[code];
      if (!l) return code;
      const name = l.native === l.name ? l.name : `${l.native} (${l.name})`;
      return l.preview ? `${name}, preview` : name;
    }

    function fillLanguages() {
      const c = byCode[state.country];
      langSel.replaceChildren(el("option", { value: "auto", text: "Automatic" }));
      const own = c ? c.languages : [];
      if (own.length) langSel.append(el("optgroup", { label: c.name }, own.map((code) => el("option", { value: code, text: langLabel(code) }))));
      const rest = Object.keys(langs).filter((code) => !own.includes(code));
      langSel.append(el("optgroup", { label: "Other languages ACE reads" }, rest.map((code) => el("option", { value: code, text: langLabel(code) }))));
      langSel.value = own.includes(state.language) || rest.includes(state.language) ? state.language : "auto";
      state.language = langSel.value;
    }

    // Suggestions in a language the country offers: English where it is offered, otherwise French or Portuguese,
    // so a suggestion is never answered in a language its reader did not write in.
    function tryList(c) {
      const p = c.example_place || c.name;
      const own = c.languages || [];
      if (!own.includes("en") && own.includes("fr")) return [
        `Va-t-il pleuvoir à ${p} cette semaine ?`, `Prix du maïs à ${p}`, `Hôpital le plus proche à ${p}`,
        "Je suis enceinte de 20 semaines, quand est ma prochaine visite ?", "Les feuilles de mon maïs ont des trous et de la sciure",
        "Votre compte est bloqué, envoyez votre code PIN pour confirmer", "Mon enfant a bu du pétrole", "AIDE",
      ];
      if (!own.includes("en") && own.includes("pt")) return [
        `Vai chover em ${p} esta semana?`, `Preço do milho em ${p}`, `Hospital mais próximo em ${p}`,
        "Estou grávida de 20 semanas, quando é a minha próxima consulta?", "As folhas do meu milho têm buracos e serradura",
        "A sua conta está bloqueada, envie o seu PIN para confirmar", "O meu filho bebeu petróleo", "AJUDA",
      ];
      return [
        `Will it rain in ${p} this week?`, `Maize price in ${p}`, `Nearest hospital in ${p}`,
        "I am 20 weeks pregnant, when is my next check?", "My maize leaves have holes and sawdust",
        "Your account is blocked, send your PIN to confirm", "My child drank paraffin", "HELP",
      ];
    }

    function fillTries() {
      const c = byCode[state.country];
      triesBox.replaceChildren();
      if (!c) return;
      const list = tryList(c);
      for (const t of compact ? list.slice(0, 4) : list) {
        triesBox.append(el("button", { type: "button", text: t, onclick: () => {
          if (state.channel === "ussd") setChannel("sms");
          chatInput.value = t; sendChat();
        } }));
      }
    }

    function updatePreview() {
      const code = state.language;
      if (code !== "auto" && langs[code] && langs[code].preview) {
        previewNote.hidden = false;
        previewNote.textContent = `${langs[code].name} is a preview: a draft no fluent speaker has reviewed yet.`;
      } else previewNote.hidden = true;
    }

    function setCountry(code) {
      state.country = code;
      countrySel.value = code;
      state.path = [];
      state.threads = {};
      fillLanguages(); fillTries(); updatePreview(); renderThread();
      const c = byCode[code];
      screen.textContent = c ? "Press Dial to open the ACE menu." : "Choose a country to begin.";
      screen.classList.remove("ended");
      meter.lastChild.textContent = "";
      footNote.textContent = c ? `${c.name}: ${c.emergency.length ? "emergency " + c.emergency.map((n) => n.number).join(", ") : "no checked national emergency number"}` : "";
    }

    function ready() {
      if (state.country) return true;
      why.replaceChildren(el("span", { class: "chip gold", text: "Choose a country first" }),
        el("span", { class: "muted", text: "ACE answers with that country's facts and emergency numbers." }));
      countrySel.focus();
      return false;
    }

    // USSD
    async function ussd() {
      if (!ready()) return;
      try {
        const r = await post("/try/ussd", { country: state.country, language: state.language, text: state.path.join("*") });
        screen.textContent = r.screen;
        screen.dir = langs[r.language] && langs[r.language].rtl ? "rtl" : "ltr";
        meter.lastChild.textContent = `${r.chars} of ${r.limit} characters`;
        if (r.end) { state.path = []; screen.classList.add("ended"); screen.textContent += "\n\n[session ended]"; }
        else screen.classList.remove("ended");
      } catch (e) { screen.textContent = e.message; }
    }
    dial.addEventListener("click", () => { state.path = []; ussd(); });
    ussdSend.addEventListener("click", () => {
      const v = ussdInput.value.trim();
      if (!v) return;
      state.path.push(v); ussdInput.value = ""; ussd();
    });
    ussdInput.addEventListener("keydown", (e) => { if (e.key === "Enter") ussdSend.click(); });

    // chat channels
    function thread() { return state.threads[state.channel] || (state.threads[state.channel] = []); }

    function bubble(item) {
      const voice = state.channel === "voice";
      if (item.who === "me") {
        return el("div", { class: "msg me", dir: "auto" }, voice ? `You said: ${item.text}` : item.text);
      }
      const r = item.reply;
      const node = el("div", { class: "msg ace" + (r.emergency ? " emergency" : ""), dir: "auto" });
      if (state.channel === "sms") {
        node.append(r.segments.join(" "));
        node.append(el("span", { class: "meta", text: `${r.segments.length} SMS segment${r.segments.length === 1 ? "" : "s"}, ${r.encoding}` }));
      } else if (state.channel === "whatsapp") {
        node.append(r.messages.join("\n"));
      } else if (state.channel === "rcs") {
        node.append(r.text);
        if (r.citations.length) node.append(el("span", { class: "meta", text: "Sources: " + [...new Set(r.citations.map((c) => c.source))].join("; ") }));
        if (r.chips && r.chips.length) node.append(el("div", { class: "chips" }, r.chips.map((chip) =>
          el("button", { type: "button", text: chip, onclick: () => { chatInput.value = chip; sendChat(); } }))));
      } else {
        node.append(r.text);
        const how = r.voice === "say" ? "spoken with a standard voice" : r.voice === "play" ? "spoken with generated audio" : "no voice for this language: keypad menu, and the full answer by SMS";
        node.append(el("span", { class: "meta", text: `Call script, ${how}` }));
      }
      return node;
    }

    function renderThread() {
      const items = thread();
      chat.replaceChildren(...(items.length ? items.map(bubble) : [el("p", { class: "empty", text: state.country
        ? (state.channel === "voice" ? "Type what a caller would say. ACE shows the script the call would speak." : "Send a message, or tap a suggestion.")
        : "Choose a country to begin." })]));
      chat.scrollTop = chat.scrollHeight;
    }

    function explain(r) {
      const l = langs[r.language];
      why.replaceChildren(
        el("span", { class: "chip" + (r.kind === "emergency" ? " danger" : r.kind === "clarify" ? " stone" : ""), text: r.kind }),
        el("span", { text: KIND[r.kind] || "" }),
        l ? el("span", { class: l.preview ? "chip gold" : "chip stone", text: l.preview ? `${l.name}, preview` : l.name }) : null);
      cites.replaceChildren();
      if (!r.citations.length) {
        cites.append(el("p", { class: "muted", text: r.kind === "clarify" ? "No source matched this question." : "This reply has no source to show." }));
        return;
      }
      for (const c of compact ? r.citations.slice(0, 1) : r.citations) {
        const data = c.fact_id.startsWith("snapshot:");
        const facts = [data ? (c.licence ? `Data licence: ${c.licence}` : null) : (c.licence ? `ACE pack text: ${c.licence}` : null),
          c.date ? (data ? `data of ${c.date}` : `checked ${c.date}`) : null, c.review_status].filter(Boolean).join(" · ");
        cites.append(el("div", { class: "cite" }, el("b", { text: c.source }), el("small", { text: facts }),
          c.source_url ? el("a", { href: c.source_url, target: "_blank", rel: "noopener noreferrer", text: c.source_url }) : null));
      }
    }

    async function sendChat() {
      const text = chatInput.value.trim();
      if (!text || !ready()) return;
      chatInput.value = "";
      const t = thread();
      t.push({ who: "me", text });
      renderThread();
      try {
        const r = await post("/try/message", { country: state.country, language: state.language, channel: state.channel, text });
        t.push({ who: "ace", reply: r });
        explain(r);
      } catch (e) {
        t.push({ who: "ace", reply: { text: e.message, segments: [e.message], encoding: "", messages: [e.message], citations: [], chips: [], voice: "none" } });
      }
      renderThread();
    }
    chatSend.addEventListener("click", sendChat);
    chatInput.addEventListener("keydown", (e) => { if (e.key === "Enter") sendChat(); });

    forget.addEventListener("click", async () => {
      if (!state.country) return;
      try { await post("/try/forget", { country: state.country }); } catch (e) { /* the next message starts fresh anyway */ }
      state.threads = {}; state.path = [];
      renderThread();
      screen.textContent = "Session deleted. Press Dial to start again.";
      why.replaceChildren(el("span", { class: "chip", text: "forgotten" }), el("span", { text: "Everything ACE held for this session is deleted." }));
      cites.replaceChildren();
    });

    countrySel.addEventListener("change", () => setCountry(countrySel.value));
    langSel.addEventListener("change", () => { state.language = langSel.value; updatePreview(); });
    setCountry(regionCountry(data.countries));
    setChannel(state.channel);
  }

  const sim = $("#sim");
  if (sim) buildSim(sim);

  // Coverage ---------------------------------------------------------------------------------------------------
  async function buildCoverage(root) {
    let data;
    try { data = await countries(); } catch (e) { root.append(el("p", { text: "Coverage could not load. Refresh to try again." })); return; }
    const services = Object.entries(data.services);
    const langName = (code) => { const l = data.languages[code]; return l.native === l.name ? l.name : `${l.native} (${l.name})`; };
    const detail = el("div", { class: "card detail", "aria-live": "polite" });
    function show(c) {
      rows.forEach((r) => r.classList.toggle("on", r.dataset.code === c.code));
      detail.replaceChildren(
        el("h2", { text: c.name }),
        el("div", { class: "detail-grid" },
          el("div", {}, el("h3", { text: "Services" }), services.map(([sid, title]) => {
            const s = c.services[sid] || { available: false, reason: "" };
            return el("p", {}, el("span", { class: "dot" + (s.available ? "" : " off") }), el("b", { text: title }),
              el("br"), el("span", { class: "muted", text: s.reason }));
          })),
          el("div", {}, el("h3", { text: "Languages" }), c.languages.map((code) => {
            const l = data.languages[code];
            return el("p", {}, el("b", { text: langName(code) }), " ",
              el("span", { class: l.preview ? "chip gold" : "chip", text: l.preview ? "preview" : "reviewed" }), " ",
              el("span", { class: "chip stone", text: l.voice === "none" ? "keypad and SMS on calls" : "voice on calls" }));
          }),
          el("h3", { class: "gap-top", text: "Emergency numbers" }),
          c.emergency.length ? c.emergency.map((n) => el("p", {}, el("b", { text: n.number }), " ", el("span", { class: "muted", text: n.label })))
            : el("p", { class: "muted", text: "ACE has no checked national emergency number for this country, so it tells people to call their local emergency number or go to the nearest health facility." }))));
    }
    const search = el("input", { type: "search", placeholder: "Country or language", "aria-label": "Filter countries" });
    const head = el("tr", {}, el("th", { text: "Country" }), el("th", { text: "Languages" }),
      services.map(([, title]) => el("th", { text: title })));
    const body = el("tbody");
    const rows = data.countries.map((c) => {
      const row = el("tr", { tabindex: "0", class: "pick" }, el("td", {}, el("b", { text: c.name })),
        el("td", { class: "muted", text: c.languages.map((code) => data.languages[code].name).join(", ") }),
        services.map(([sid]) => {
          const s = c.services[sid] || { available: false, reason: "" };
          return el("td", { class: s.available ? "yes" : "no", title: s.reason }, el("span", { class: "dot" + (s.available ? "" : " off") }), s.available ? "Yes" : "Gap");
        }));
      row.dataset.code = c.code;
      row.dataset.search = (c.name + " " + c.languages.map((code) => data.languages[code].name + " " + data.languages[code].native).join(" ")).toLowerCase();
      row.addEventListener("click", () => { show(c); detail.scrollIntoView({ behavior: "smooth", block: "nearest" }); });
      row.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); show(c); } });
      return row;
    });
    body.append(...rows);
    search.addEventListener("input", () => {
      const q = search.value.trim().toLowerCase();
      rows.forEach((r) => { r.hidden = q && !r.dataset.search.includes(q); });
    });
    root.append(el("div", { class: "filters" }, el("label", {}, "Filter", search),
      el("span", { class: "muted", text: "Choose a country for the reason behind each gap, its languages and its emergency numbers." })),
      detail, el("div", { class: "table-wrap gap-top" }, el("table", {}, el("thead", {}, head), body)));
    const codes = new Set(data.countries.map((c) => c.code));
    const mine = (navigator.languages || []).map((t) => (t.split("-")[1] || "").toUpperCase()).find((r) => codes.has(r));
    show(data.countries.find((c) => c.code === mine) || data.countries.find((c) => c.code === "NG") || data.countries[0]);
  }
  const cov = $("#coverage");
  if (cov) buildCoverage(cov);

  // Status -----------------------------------------------------------------------------------------------------
  async function buildStatus(root) {
    let s;
    try { s = await fetch("/v1/status").then((r) => r.json()); } catch (e) { root.append(el("p", { text: "Status could not load." })); return; }
    const set = s.snapshot_set || {};
    root.append(el("div", { class: "cards" },
      el("div", { class: "card" }, el("h3", { text: "Version" }), el("p", { class: "mono", text: `ACE ${s.version}` }), el("p", { class: "muted mono", text: s.commit || "local build" })),
      el("div", { class: "card" }, el("h3", { text: "Snapshot set" }), el("p", { class: "mono", text: set.set || "bundled" }),
        el("p", { class: "muted", text: set.error ? `Kept the last good set: ${set.error}` : set.checked_at ? `Checked ${set.checked_at}` : "Bundled with this release" })),
      el("div", { class: "card" }, el("h3", { text: "Answers" }), el("p", { text: `${s.packs} knowledge packs, ${s.facts} facts` }),
        el("p", { class: "muted", text: s.model ? `A model may rephrase cited facts: ${s.model}` : "Answers by extraction only: no model" }))));
    const datasets = [...new Set(s.datasets.map((d) => d.dataset))].sort();
    const LABEL = { facilities: "Health facilities", places: "Places and boundaries", prices: "Market prices",
      warnings: "Official warnings", weather: "Weather forecasts", facilities_registry: "National facility registries" };
    const summary = el("tbody", {}, datasets.map((name) => {
      const rows = s.datasets.filter((d) => d.dataset === name);
      const expired = rows.filter((d) => d.expired).length;
      const newest = rows.map((d) => d.retrieved_at || "").sort().pop() || "";
      return el("tr", {}, el("td", {}, el("b", { text: LABEL[name] || name })), el("td", { text: String(rows.length) }),
        el("td", { text: newest.replace("T", " ").slice(0, 16) }),
        el("td", {}, el("span", { class: "dot " + (expired ? "warn" : "") }), expired ? `${expired} past their valid until time` : "all current"));
    }));
    const pick = el("select", { "aria-label": "Dataset" }, el("option", { value: "", text: "Choose a dataset for each country" }),
      datasets.map((d) => el("option", { value: d, text: LABEL[d] || d })));
    const body = el("tbody");
    const detail = el("div", { class: "table-wrap gap-top", hidden: true },
      el("table", {}, el("thead", {}, el("tr", {}, ["Country", "Data date", "Retrieved (UTC)", "Valid until (UTC)", "State"].map((h) => el("th", { text: h })))), body));
    pick.addEventListener("change", () => {
      body.replaceChildren(...s.datasets.filter((d) => d.dataset === pick.value).map((d) => {
        const state = d.expired ? ["warn", "past its valid until time"] : d.valid ? ["", "current"] : ["off", "not valid"];
        return el("tr", {}, el("td", { text: d.country }), el("td", { text: d.data_date || "" }),
          el("td", { text: (d.retrieved_at || "").replace("T", " ").slice(0, 16) }),
          el("td", { text: d.valid_until ? d.valid_until.replace("T", " ").slice(0, 16) : "no limit" }),
          el("td", {}, el("span", { class: "dot " + state[0] }), state[1]));
      }));
      detail.hidden = !pick.value;
    });
    root.append(el("h2", { class: "gap-top", text: "Data freshness" }),
      el("p", { class: "muted", text: "Weather and warnings carry a valid until time, and ACE refuses either once it passes. Places and health facilities change only with a release." }),
      el("div", { class: "table-wrap" }, el("table", {}, el("thead", {}, el("tr", {}, ["Dataset", "Countries", "Newest retrieval (UTC)", "State"].map((h) => el("th", { text: h })))), summary)),
      el("div", { class: "filters" }, el("label", {}, "By country", pick)), detail,
      el("p", { class: "muted gap-top", text: `Checked ${s.checked_at}` }));
  }
  const st = $("#status");
  if (st) buildStatus(st);
})();
