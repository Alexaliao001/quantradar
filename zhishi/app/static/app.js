(() => {
  const state = {
    session: localStorage.getItem("zhishi_session") || "",
    lastResult: null,
  };

  const $ = (id) => document.getElementById(id);

  async function api(path, opts = {}) {
    const headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
    if (state.session) headers["X-Session"] = state.session;
    const res = await fetch(path, { ...opts, headers });
    return res.json();
  }

  async function ensureSession() {
    if (state.session) return state.session;
    const data = await api("/api/session", { method: "POST", body: "{}" });
    state.session = data.session;
    localStorage.setItem("zhishi_session", state.session);
    return state.session;
  }

  function renderAnalyze(result) {
    const err = $("analyze-error");
    const box = $("result");
    if (!result.ok) {
      err.textContent = `无法自检：${result.error || "数据不足"}（fail-closed，不编造分数）`;
      err.classList.remove("hidden");
      box.classList.add("hidden");
      state.lastResult = null;
      return;
    }
    err.classList.add("hidden");
    box.classList.remove("hidden");
    state.lastResult = result;
    $("score").textContent = String(result.primary_score);
    $("posture").textContent = result.posture;
    $("meta").textContent = `${result.symbol} ${result.name || ""} · as_of ${result.as_of || "—"} · ${result.market}`;
    $("gates").innerHTML = (result.gates || [])
      .map(
        (g) =>
          `<li><span class="tag">${g.passed ? "通过" : "关注"}</span><strong>${g.title}</strong><div class="muted">${g.teaching}</div></li>`
      )
      .join("");
    $("checklist").innerHTML = (result.checklist || [])
      .map(
        (c) =>
          `<li><strong>${c.title}</strong> · ${c.score}/${c.max}<div class="muted">${c.reason}</div></li>`
      )
      .join("");
  }

  async function loadCases() {
    const data = await api("/api/cases?free=0");
    const free = (data.cases || []).filter((c) => c.free_demo);
    const rest = (data.cases || []).filter((c) => !c.free_demo).slice(0, 5);
    const all = free.concat(rest);
    $("case-list").innerHTML = all
      .map(
        (c) =>
          `<li><button type="button" class="secondary case-btn" data-symbol="${c.symbol}">${c.free_demo ? "免费 · " : ""}${c.title}</button><div class="muted">${c.summary}</div></li>`
      )
      .join("");
    document.querySelectorAll(".case-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        $("symbol").value = btn.dataset.symbol;
        const result = await api(`/api/analyze?symbol=${btn.dataset.symbol}&market=A&mode=artifact`);
        renderAnalyze(result);
        location.hash = "#check";
      });
    });
  }

  async function loadLessons() {
    const data = await api("/api/lessons");
    $("lesson-list").innerHTML = (data.lessons || [])
      .map(
        (l) =>
          `<li><a href="#" class="lesson-link" data-id="${l.id}">${l.track === "hkconnect" ? "[港股通] " : ""}${l.title}</a></li>`
      )
      .join("");
    document.querySelectorAll(".lesson-link").forEach((a) => {
      a.addEventListener("click", async (e) => {
        e.preventDefault();
        const lesson = await api(`/api/lessons/${a.dataset.id}`);
        if (!lesson.ok) return;
        $("lesson-view").classList.remove("hidden");
        $("lesson-title").textContent = lesson.lesson.title;
        $("lesson-body").textContent = lesson.lesson.markdown;
      });
    });
    $("lesson-close").addEventListener("click", () => $("lesson-view").classList.add("hidden"));
  }

  async function refreshReviews() {
    await ensureSession();
    const data = await api("/api/me/reviews");
    const items = data.reviews || [];
    $("review-list").innerHTML = items.length
      ? items
          .map(
            (r) =>
              `<li><strong>${r.symbol}</strong> ${r.name || ""} · ${r.posture} · 分 ${r.primary_score}<div class="muted">假设：${r.hypothesis}</div><div class="muted">失效：${r.invalidation}</div></li>`
          )
          .join("")
      : `<li class="muted">尚无记录。完成一次自检并写入假设。</li>`;
    const rem = await api("/api/me/reminders");
    const reminders = rem.reminders || [];
    $("reminder-list").innerHTML = reminders.length
      ? reminders
          .map(
            (r) =>
              `<li>${r.done ? "已完成" : "待复盘"} · ${r.symbol} · ${r.kind} <button type="button" class="secondary rem-done" data-id="${r.id}">标记完成</button></li>`
          )
          .join("")
      : `<li class="muted">写入复盘本后会自动生成次日提醒。</li>`;
    document.querySelectorAll(".rem-done").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await api("/api/reminders/complete", { method: "POST", body: JSON.stringify({ id: btn.dataset.id }) });
        refreshReviews();
      });
    });
  }

  const DRILL = {
    prompt: "A 股当日买入的股票，通常最早何时可以卖出？",
    options: {
      a: "当日随时可卖",
      b: "下一交易日（T+1）",
      c: "一周后",
    },
    answer: "b",
    explanation: "A 股股票实行 T+1：当日买入，下一交易日才能卖出。这是复盘必须写入的持有期约束。",
  };

  function setupDrill() {
    $("drill-q").textContent = `${DRILL.prompt}\nA. ${DRILL.options.a}\nB. ${DRILL.options.b}\nC. ${DRILL.options.c}`;
    document.querySelectorAll(".drill-ans").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await ensureSession();
        const correct = btn.dataset.answer === DRILL.answer;
        $("drill-feedback").textContent = correct ? "正确。" + DRILL.explanation : "未答对。" + DRILL.explanation;
        if (!correct) {
          await api("/api/drills", {
            method: "POST",
            body: JSON.stringify({
              prompt: DRILL.prompt,
              user_answer: btn.dataset.answer,
              correct: false,
              explanation: DRILL.explanation,
            }),
          });
          const drills = await api("/api/me/drills");
          $("drill-list").innerHTML = (drills.drills || [])
            .map((d) => `<li class="muted">${d.prompt} → 你的答案 ${d.user_answer}</li>`)
            .join("");
        }
      });
    });
  }

  async function loadHk() {
    const data = await api("/api/hkconnect/checklist");
    $("hk-list").innerHTML = (data.items || [])
      .map(
        (i) =>
          `<li><strong>${i.id}</strong><div class="muted">A股：${i.a_share}</div><div class="muted">港股通：${i.hkconnect}</div><div class="muted">教学：${i.teaching}</div></li>`
      )
      .join("");
  }

  $("btn-analyze").addEventListener("click", async () => {
    const symbol = $("symbol").value.trim();
    const market = $("market").value;
    const result = await api(`/api/analyze?symbol=${encodeURIComponent(symbol)}&market=${market}`);
    renderAnalyze(result);
  });

  $("btn-sample").addEventListener("click", async () => {
    const result = await api("/api/sample");
    $("symbol").value = result.symbol || "600519";
    renderAnalyze(result);
  });

  $("btn-save-review").addEventListener("click", async () => {
    await ensureSession();
    if (!state.lastResult) return;
    const payload = {
      symbol: state.lastResult.symbol,
      name: state.lastResult.name,
      primary_score: state.lastResult.primary_score,
      posture: state.lastResult.posture,
      hypothesis: $("hypothesis").value,
      invalidation: $("invalidation").value,
    };
    const res = await api("/api/reviews", { method: "POST", body: JSON.stringify(payload) });
    $("review-msg").textContent = res.ok ? "已写入，并创建次日复盘提醒。" : res.error || "失败";
    if (res.ok) {
      $("hypothesis").value = "";
      $("invalidation").value = "";
      refreshReviews();
    }
  });

  Promise.all([ensureSession(), loadCases(), loadLessons(), loadHk(), refreshReviews()]).then(setupDrill);
})();
