import "./style.css";
import { CityScene, type Selection } from "./scene";
import { CitySceneCanvas } from "./scene-canvas";
import { Playback } from "./playback";
import { insidePolygon } from "./view-geometry";
import { assertCompatible, validateOD } from "./protocol";
import type { Network, Manifest, RunEntry, Metric, Vehicle } from "./types";
const icon = (name: string) =>
  ({
    logo: "◈",
    map: "▱",
    play: "▶",
    pause: "Ⅱ",
    reset: "↺",
    arrow: "↗",
    close: "×",
  })[name] ?? name;
const policies = [
  ["S0", "合理基准", "冻结网络与实验基准配时", "00"],
  ["S1", "局部疏导", "局部路口绿信比分配", "01"],
  ["S2", "空间再分配", "车道与道路空间补丁", "02"],
  ["S3", "区域信号协调", "区域周期、相位与约束", "03"],
  ["S4", "通行组织", "禁左、单行与穿行管理", "04"],
  ["S5", "路侧治理", "临停、上下客与装卸", "05"],
  ["S6", "公交优先", "真实公交停站与优先", "06"],
  ["S7", "组合政策", "验证单项后组合对照", "07"],
];
const app = document.querySelector<HTMLDivElement>("#app")!;
app.innerHTML = `<header class="topbar"><a class="brand" href="./" aria-label="MagicTwin 首页"><span class="brand-mark">${icon("logo")}</span><span>MAGIC<span class="brand-thin">TWIN</span><small>TRAFFIC POLICY LAB</small></span></a><div class="project-heading"><span class="project-dot"></span>成都 · 玉林片区 <span class="header-divider"></span><span class="header-sub">街区交通政策实验室</span></div><div class="top-actions"><span id="backend-status" class="status-pill">离线回放</span><button id="evidence-button" class="quiet-button">数据与方法 <span>↗</span></button></div></header>
<div class="workspace"><aside class="sidebar"><div class="sidebar-title"><span class="eyebrow">EXPERIMENT WORKSPACE</span><h1>每一次改变，<br>都值得对照。</h1><p>在同一份需求下，观察交通的变化。</p></div><div class="section-heading"><span>01 / 实验情景</span><span class="tiny-label">E0 边界需求</span></div><label class="field-label" for="run-select">代表性运行</label><select id="run-select"><option value="">正在读取运行清单…</option></select><div class="segmented period-switch"><button class="active" data-period="am">早高峰</button><button data-period="pm">晚高峰</button></div><div class="input-row"><label>需求倍率 <input id="demand-scale" type="number" value="1" min="0.1" max="5" step="0.1"></label><label>随机种子 <input id="seed" type="number" value="42" min="0" max="2147483647"></label></div><button class="text-button" id="od-button">边界 OD 与输入设置 <span>↗</span></button><div class="section-heading policy-heading"><span>02 / 政策方案</span><span class="tiny-label">8 个方案族</span></div><div class="policy-list">${policies.map(([id, label, desc, num], i) => `<button class="policy-card ${i === 0 ? "selected" : ""}" data-policy="${id}" aria-pressed="${i === 0}"><span class="policy-number">${num}</span><span class="policy-copy"><strong>${label}</strong><small>${desc}</small></span><span class="policy-indicator">${i === 0 ? "●" : "○"}</span></button>`).join("")}</div><div class="policy-detail" id="policy-detail">基准方案 · 配时为实验假设，尚未经现场校准。</div><div id="policy-parameters"></div><button id="run-button" class="primary-button" disabled>提交新实验 <span>↗</span></button><div id="job-status" class="subtle-note">预计算结果可离线回放；修改参数后需后端重新计算。</div><button id="cancel-button" class="text-button hidden">取消当前任务</button><div class="sidebar-footer"><span class="dot-light"></span> SUMO 微观仿真 <span>WebGL 2</span></div></aside>
<main class="main"><div class="map-toolbar"><div><span class="eyebrow">URBAN DIGITAL TWIN</span><h2>真实街区，透明实验。<span class="location-tag">YULIN / CHENGDU</span></h2></div><div class="view-controls segmented"><button id="core-view" class="active" title="核心区斜俯视">核心区</button><button id="full-view">全路网</button><button id="top-view">俯视</button></div></div><div class="view-stage"><div id="canvas-host"></div><div class="map-top-left"><span class="data-badge"><i></i><span id="data-status">正在加载真实道路资产</span></span><div class="map-caption">1 km² 核心治理区 <span>/</span> 外围完整交通传播</div></div><div class="map-top-right"><button id="buildings-button" class="map-button active" title="显示或隐藏建筑" aria-pressed="true">▥ 建筑</button><button id="reset-view" class="map-button" title="复位镜头">↺</button></div><div id="split-labels" class="split-labels hidden"><span>A · 基准运行</span><span>B · 对照运行</span></div><div class="map-legend"><span class="legend-label" id="legend-title">车辆速度</span><span><i class="legend-dot slow"></i>停等</span><span><i class="legend-dot mid"></i>低速</span><span><i class="legend-dot fast"></i>畅行</span><span class="boundary-key"><i class="boundary-swatch core"></i>核心区边界</span><span class="boundary-key secondary"><i class="boundary-swatch"></i>次区外边界</span></div><div class="map-scale"><div class="north"><span id="north-arrow">↑</span><b>N</b></div><div id="scale-line"></div><span>100 m · 视平面近似</span></div><div class="navigation-hint"><span class="webgl-hint">左键旋转 · 右键平移 · 中键设置旋转中心</span><span class="canvas-hint">左键旋转 · 右键平移 · 中键设置旋转中心（2D）</span> · 滚轮缩放</div><div class="map-attribution">© OpenStreetMap contributors · 建筑高度为示意</div><div id="scene-error" class="scene-error hidden" role="alert"></div><div class="performance"><span id="performance">渲染初始化</span></div></div><section class="timeline"><div class="timeline-top"><div class="play-controls"><button id="play-button" class="play-button" disabled aria-label="播放">▶</button><button id="rewind-button" class="small-icon" aria-label="回到开始">↺</button><span id="clock" class="clock">00:00</span><span id="duration" class="duration">/ --:--</span><select id="speed" aria-label="回放速度"><option value="1">1×</option><option value="2">2×</option><option value="5">5×</option><option value="10">10×</option></select></div><div class="playback-meta"><span id="sample-status">等待轨迹</span><span class="mini-dot"></span>仅显示已记录状态</div></div><input id="timeline-range" aria-label="仿真时间" type="range" min="0" max="1" step="0.5" value="0" disabled><div class="timeline-labels"><span>起始</span><span id="time-mid">仿真时间（分 : 秒）</span><span id="time-end">结束</span></div><div class="sparkline-row"><span>在网车辆</span><svg id="sparkline" viewBox="0 0 600 28" preserveAspectRatio="none" aria-label="真实在网车辆时序"><path d=""/></svg><span id="series-note">无时序</span></div></section></main>
<aside class="inspector"><div class="inspector-heading"><span class="eyebrow">SYSTEM OBSERVATORY</span><h2>让结果说话<span class="info-dot">i</span></h2><p>完整路网 · 统一需求口径</p></div><div class="run-label"><span id="active-policy">S0</span><strong id="active-run">尚未选择运行</strong></div><div class="metric-primary"><span>累计系统时间 <small>含边界待入</small></span><div><strong id="metric-tstt">—</strong><em>veh·h</em></div><span class="metric-foot">有限窗口累计量，非最终总旅行时间</span></div><div class="metric-grid"><div><span>完成比例</span><strong id="metric-completion">—</strong><small>已完成 / 已到期</small></div><div><span>末端待入</span><strong id="metric-external">—</strong><small>辆 · 外部积压</small></div><div><span>末端在网</span><strong id="metric-inside">—</strong><small>辆 · 尚未到达</small></div><div><span>异常失败</span><strong id="metric-failures">—</strong><small>单独审计</small></div></div><div class="audit-note" id="audit-note">等待已完成运行的指标与守恒检查。</div><div class="inspector-section"><div class="section-heading"><span>方案对照</span><span class="tiny-label">PAIRED</span></div><select id="compare-select" aria-label="选择对照运行"><option value="">选择同需求的运行</option></select><div class="segmented comparison-switch"><button data-mode="single" class="active">单图</button><button data-mode="split">同步双图</button><button data-mode="diff">速度差值</button></div><div id="comparison-note" class="small-note">同需求哈希才可对照；所有镜头与时刻同步。</div></div><div class="inspector-section selection-section"><div class="section-heading"><span>对象检查器</span><span class="tiny-label">INSPECT</span></div><div id="selection"><div class="empty-selection">⌖</div><strong>从街区中选一个对象</strong><p>点击道路、路口、入口或车辆，查看对应的仿真属性。</p></div></div><button class="provenance-link" id="provenance-button">查看本次运行的证据链 <span>↗</span></button><div class="truth-note"><span>情景实验 / 非实时交通</span><p>真实地图不等于现场复现。需求与控制假设、未完成出行和模型局限均单独披露。</p></div></aside></div><div id="toast" role="status"></div><dialog id="evidence-dialog"><div class="dialog-heading"><span class="eyebrow">PROVENANCE & METHODS</span><button data-close="evidence-dialog" aria-label="关闭">×</button></div><h2>每一帧，都有来源。</h2><p class="dialog-intro">这是使用真实道路几何的离线交通情景实验，不是玉林片区的实时交通或经现场验证的预测。</p><div class="provenance-grid"><article><span class="source-tag">MAP_TAG</span><h3>道路与建筑</h3><p>OpenStreetMap 原始矢量数据。道路和回放由同一份 SUMO 网络生成；建筑高度为示意。</p></article><article><span class="source-tag amber">ASSUMED</span><h3>需求与控制</h3><p>合成边界 OD、实验基准配时和行为参数。没有现场数据时，不称为现状或实际政策收益。</p></article><article><span class="source-tag">DERIVED</span><h3>轨迹与指标</h3><p>只显示 SUMO 实际输出。32 字节记录、20 秒分块、SHA-256 校验；屏幕帧不改变仿真。</p></article><article><span class="source-tag neutral">UNVALIDATED</span><h3>解释范围</h3><p>软件与守恒检查不替代现场校准。单个种子的结果不构成稳定的政策排名。</p></article></div><h3>当前运行身份</h3><dl id="identity"><dt>状态</dt><dd>尚未加载运行</dd></dl><div class="dialog-actions"><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">地图许可与署名 ↗</a><button data-close="evidence-dialog" class="primary-button">了解</button></div></dialog><dialog id="od-dialog"><div class="dialog-heading"><span class="eyebrow">BOUNDARY DEMAND / E0</span><button data-close="od-dialog" aria-label="关闭">×</button></div><h2>需求从真实边界进入。</h2><p class="dialog-intro">入口流率是合成实验输入，单位 veh/h。正需求必须合法可达；无法进入的车辆保留外部等待。</p><div class="input-row light"><label>每入口流率（veh/h）<input id="gate-rate" type="number" value="120" min="1" max="1800"></label><label>仿真窗口（秒）<input id="run-duration" type="number" value="600" min="60" max="9900" step="60"></label></div><label class="field-label">入口位置 <select id="gate-select"><option>等待路网</option></select></label><div class="od-note">下方可检查单入口出口比例，也可启用自定义 OD 清单，逐条指定起终点、流率和 5 分钟时段。启用后仅使用清单中的需求。</div><div id="od-rows"></div><div id="od-validation" role="status"></div><div class="custom-od"><label><input id="custom-od-enabled" type="checkbox"> 启用自定义 OD 清单并随实验提交</label><p>时段必须按 300 秒对齐并位于仿真窗口内；无路可达会被服务端拒绝。</p><div id="custom-od-rows"></div><button id="add-od-row" class="text-button">＋ 添加 OD 时段</button></div><div class="dialog-actions"><button id="export-od" class="quiet-button">导出 OD 草案</button><button data-close="od-dialog" class="primary-button">保存本次设置</button></div></dialog>`;
const $ = <T extends HTMLElement = HTMLElement>(id: string) =>
  document.getElementById(id) as T;
let network: Network,
  city: CityScene | CitySceneCanvas | undefined,
  runs: RunEntry[] = [],
  active: RunEntry | undefined,
  manifest: Manifest | undefined,
  playback: Playback | undefined,
  otherPlayback: Playback | undefined,
  otherManifest: Manifest | undefined,
  otherRun: RunEntry | undefined,
  metrics: Metric | undefined,
  playing = false,
  current = 0,
  start = 0,
  end = 0,
  loading = false,
  epoch = 0,
  period = "am",
  policy = "S0",
  mode = "single",
  backend = false,
  buildings = true,
  jobId = "",
  jobPolicy = "S0",
  lastFrame: Vehicle[] = [],
  otherFrame: Vehicle[] = [],
  lastAnimation = 0,
  pendingSeek: number | undefined,
  comparisonEpoch = 0;
let signalEvents: Metric[] = [];
let selectedObject: Selection | undefined;
function toast(message: string) {
  $("toast").textContent = message;
  $("toast").classList.add("visible");
  setTimeout(() => $("toast").classList.remove("visible"), 6500);
}
function fmt(time: number) {
  return `${String(Math.floor(time / 60)).padStart(2, "0")}:${String(Math.floor(time % 60)).padStart(2, "0")}`;
}
function errorMessage(e: unknown) {
  return e instanceof Error ? e.message : String(e);
}
async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    let detail = "";
    try {
      detail = JSON.stringify((await response.json()).detail ?? "");
    } catch {}
    throw new Error(`${response.status} ${detail || response.statusText}`);
  }
  return response.json();
}
const esc = (v: unknown) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ]!,
  );
function selectObject(s: Selection) {
  selectedObject = s;
  const d = s.data as Record<string, unknown>;
  const selectionManifest = s.source === "B" ? otherManifest : manifest;
  if (s.kind === "vehicle" && Array.isArray(selectionManifest?.vehicles)) {
    const meta = selectionManifest.vehicles.find(
      (v) => (v as { id?: number }).id === Number(s.id),
    ) as { persistent_trip_id?: string } | undefined;
    if (meta?.persistent_trip_id) s = { ...s, id: meta.persistent_trip_id };
  }
  const names = {
    lane: "车道",
    vehicle: "车辆",
    gate: "边界口",
    junction: "路口",
  };
  const fields =
    s.kind === "lane"
      ? [
          ["道路 ID", d.edge_id],
          ["限速", `${(Number(d.speed) * 3.6).toFixed(1)} km/h`],
          ["宽度", `${d.width} m`],
        ]
      : s.kind === "vehicle"
        ? [
            ["速度", `${(Number(d.speed) * 3.6).toFixed(1)} km/h`],
            ["采样时刻", `${d.time} s`],
            ["车道索引", d.lane],
            ["坐标", `${Number(d.x).toFixed(1)}, ${Number(d.y).toFixed(1)} m`],
          ]
        : s.kind === "gate"
          ? [
              ["道路 ID", d.edge_id],
              ["方向", d.direction],
            ]
          : [["位置", JSON.stringify(d.position)]];
  if (s.kind === "junction" && s.source !== "B") {
    const tls = city?.network.traffic_lights?.find((t) =>
      t.junction_ids.includes(s.id),
    )?.id;
    let state: Metric | undefined;
    for (let i = signalEvents.length - 1; i >= 0; i--) {
      const event = signalEvents[i];
      if (event.tls === tls && Number(event.time) <= current) {
        state = event;
        break;
      }
    }
    if (state)
      fields.push(
        ["信号控制器", tls],
        ["相位编号", state.phase],
        ["实际状态", state.state],
        ["状态记录", `${state.time} s`],
      );
  }
  fields.push([
    "运行",
    s.source === "B" ? otherManifest?.run_id : manifest?.run_id,
  ]);
  if (s.kind === "junction" && s.source === "B")
    fields.push(["信号状态", "请单独打开 B 运行检查对应记录"]);
  $("selection").innerHTML =
    `<span class="object-type">${names[s.kind]}</span><h3>${esc(s.id)}</h3><dl>${fields.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl><p class="small-note">来自当前路网 / 已记录状态</p>`;
}
function populateRuns() {
  const selected = $<HTMLSelectElement>("run-select").value;
  $("run-select").innerHTML = runs.length
    ? runs
        .map(
          (r) =>
            `<option value="${esc(r.run_id)}">${esc(r.label ?? `${r.policy ?? ""} · ${r.run_id}`)}</option>`,
        )
        .join("")
    : '<option value="">没有已完成的回放</option>';
  if (runs.some((r) => r.run_id === selected))
    $<HTMLSelectElement>("run-select").value = selected;
  $("compare-select").innerHTML =
    '<option value="">选择同需求的运行</option>' +
    runs
      .filter((r) => r.run_id !== active?.run_id)
      .map(
        (r) =>
          `<option value="${esc(r.run_id)}">${esc(r.label ?? r.run_id)}</option>`,
      )
      .join("");
}
function identity() {
  if (!manifest) return;
  $("identity").innerHTML = Object.entries({
    run_id: manifest.run_id,
    network_hash: manifest.network_hash,
    demand_hash: manifest.demand_hash,
    policy_hash: manifest.policy_hash,
    schema_version: manifest.schema_version,
    engine: manifest.engine ?? "SUMO",
    time_window: `${start}–${end} s`,
  })
    .map(
      ([k, v]) =>
        `<dt>${esc(k)}</dt><dd>${esc(typeof v === "object" ? JSON.stringify(v) : v)}</dd>`,
    )
    .join("");
}
function numberAt(
  object: Metric | undefined,
  keys: string[],
): number | undefined {
  if (!object) return;
  for (const k of keys) {
    const value = k
      .split(".")
      .reduce<unknown>(
        (o, key) =>
          o && typeof o === "object" ? (o as Metric)[key] : undefined,
        object,
      );
    if (typeof value === "number" && Number.isFinite(value)) return value;
  }
  return undefined;
}
function renderMetrics(data: Metric) {
  metrics = data;
  const tstt = numberAt(data, [
    "tstt_vehicle_seconds",
    "tstt",
    "system_time_seconds",
    "summary.tstt_vehicle_seconds",
    "tstt_veh_s",
  ]);
  const completed = numberAt(data, [
    "completed",
    "n_completed",
    "summary.completed",
  ]);
  const due = numberAt(data, ["due", "n_due", "summary.due", "demand_due"]);
  const completion = numberAt(data, [
    "completion_rate",
    "completion_ratio",
    "summary.completion_rate",
  ]);
  $("metric-tstt").textContent =
    tstt === undefined ? "—" : (tstt / 3600).toFixed(2);
  $("metric-completion").textContent =
    completion !== undefined
      ? `${(completion * 100).toFixed(1)}%`
      : due !== undefined && due > 0 && completed !== undefined
        ? `${((completed / due) * 100).toFixed(1)}%`
        : "—";
  for (const [id, keys] of [
    [
      "metric-external",
      [
        "not_inserted",
        "external_waiting",
        "n_not_inserted",
        "summary.not_inserted",
        "pending",
      ],
    ],
    ["metric-inside", ["inside", "n_inside", "summary.inside", "running"]],
    [
      "metric-failures",
      [
        "explicit_failure",
        "failures",
        "n_explicit_failure",
        "summary.failures",
      ],
    ],
  ] as [string, string[]][]) {
    const v = numberAt(data, keys);
    $(id).textContent = v === undefined ? "—" : v.toLocaleString();
  }
  const audit =
    data.conservation_ok ??
    data.conservation_passed ??
    (data.audit as Metric | undefined)?.conservation_ok;
  $("audit-note").textContent =
    audit === true
      ? "✓ 数量守恒已通过 · 异常单独审计"
      : audit === false
        ? "! 守恒检查未通过，不能据此进行政策排名。"
        : "指标已加载；守恒状态请查运行审计。";
  $("audit-note").classList.toggle("warning", audit === false);
  const series = (data.timeseries ?? data.time_series ?? data.series) as
    | Metric[]
    | undefined;
  if (Array.isArray(series) && series.length) {
    const values = series.map((v) =>
      Number(v.all_cohort_inside ?? v.inside ?? v.running ?? v.n_inside ?? 0),
    );
    const max = Math.max(...values, 1);
    $("sparkline").innerHTML =
      `<path d="${values.map((v, i) => `${i ? "L" : "M"}${(i / (values.length - 1 || 1)) * 600},${26 - (v / max) * 24}`).join(" ")}"/>`;
    $("series-note").textContent = `${series.length} 个样本`;
  } else {
    $("sparkline").innerHTML = "";
    $("series-note").textContent = "无时序数据";
  }
}
function clearMetrics() {
  for (const id of [
    "metric-tstt",
    "metric-completion",
    "metric-external",
    "metric-inside",
    "metric-failures",
  ])
    $(id).textContent = "—";
  $("audit-note").textContent = "等待当前运行的指标。";
  $("sparkline").innerHTML = "";
  metrics = undefined;
}
async function loadRun(run: RunEntry) {
  const token = ++epoch;
  comparisonEpoch++;
  pendingSeek = undefined;
  signalEvents = [];
  selectedObject = undefined;
  playing = false;
  playback?.dispose();
  playback = undefined;
  otherPlayback?.dispose();
  otherPlayback = undefined;
  otherManifest = undefined;
  otherRun = undefined;
  city?.setVehicles([]);
  city?.setVehicles([], true);
  city?.setDifference(false);
  mode = "single";
  setModeUI();
  city?.setComparison(false);
  clearMetrics();
  $("play-button").textContent = "▶";
  $<HTMLButtonElement>("play-button").disabled = true;
  try {
    const url = new URL(run.manifest, location.href).href,
      m = await json<Manifest>(url);
    if (token !== epoch) return;
    let n = network;
    if (m.network_hash !== network.network_hash) {
      const asset =
        run.network ??
        (m.network_url
          ? new URL(String(m.network_url), url).href
          : new URL(String(m.network ?? "network.json"), url).href);
      n = await json<Network>(new URL(asset, location.href).href);
      if (token !== epoch) return;
    }
    assertCompatible(n, m);
    if (city?.network.network_hash !== n.network_hash) {
      city?.dispose();
      city = createScene(n);
    }
    manifest = m;
    active = run;
    playback = new Playback(m, url);
    start = m.start_time ?? m.chunks[0]?.start ?? 0;
    end = m.end_time ?? m.duration_seconds ?? m.chunks.at(-1)?.end ?? start;
    current = Math.max(
      start,
      Math.min(
        end,
        Number.isFinite(run.playback_start_seconds)
          ? run.playback_start_seconds!
          : start,
      ),
    );
    $("active-run").textContent = run.label ?? run.run_id;
    $("active-policy").textContent = run.policy ?? String(m.policy ?? "RUN");
    $("data-status").textContent =
      run.scenario_kind === "uncalibrated_synthetic_busy_demo"
        ? "真实路网 · 合成高需求演示（未校准）"
        : "真实路网 · 已校验运行";
    $("duration").textContent = `/ ${fmt(end)}`;
    $("time-end").textContent = fmt(end);
    const range = $<HTMLInputElement>("timeline-range");
    range.min = String(start);
    range.max = String(end);
    range.disabled = !m.chunks.length;
    $<HTMLButtonElement>("play-button").disabled = !m.chunks.length;
    populateRuns();
    identity();
    await seek(current);
    if (run.metrics) {
      try {
        const data = await json<Metric>(
          new URL(run.metrics, location.href).href,
        );
        if (token === epoch) renderMetrics(data);
      } catch (e) {
        toast(`指标未加载：${errorMessage(e)}`);
      }
    }
    await loadSupplemental(m, url, token);
    if (city) $("scene-error").classList.add("hidden");
  } catch (e) {
    if (token !== epoch) return;
    showSceneError(errorMessage(e));
    $("data-status").textContent = "数据校验未通过";
  }
}
async function loadSupplemental(m: Manifest, url: string, token: number) {
  const api = url.includes("/api/runs/");
  const resource = (key: string) =>
    api
      ? url.replace(/\/manifest$/, "/" + key)
      : new URL(String(m[key] ?? key + ".json"), url).href;
  const result = await Promise.allSettled([
    json<Metric[]>(resource("timeseries")),
    json<Metric>(resource("audit")),
    json<Metric[]>(resource("events")),
    json<Metric[]>(resource("signals")),
  ]);
  if (token !== epoch) return;
  signalEvents = result[3].status === "fulfilled" ? result[3].value : [];
  if (result[0].status === "fulfilled" && metrics)
    renderMetrics({ ...metrics, timeseries: result[0].value });
  if (result[1].status === "fulfilled") {
    const audit = result[1].value;
    $("audit-note").textContent =
      audit.conservation_passed === true
        ? `✓ 守恒残差 ${audit.conservation_max_residual ?? 0} · 传送 ${audit.teleports ?? "未知"} · 碰撞 ${audit.collisions ?? "未知"}`
        : "守恒未确认，请查审计";
    if (audit.collisions || audit.teleports) {
      $("audit-note").classList.add("warning");
      $("audit-note").textContent += " · 异常待复核，禁止排名";
    }
  }
  if (result[2].status === "fulfilled") {
    let bookmarks = document.getElementById("event-bookmarks");
    if (!bookmarks) {
      bookmarks = document.createElement("div");
      bookmarks.id = "event-bookmarks";
      document.querySelector(".timeline")!.append(bookmarks);
    }
    const events = result[2].value
      .filter((v) => v.type === "green_extension")
      .slice(0, 8);
    bookmarks.innerHTML = events
      .map(
        (v) =>
          `<button data-time="${Number(v.time)}" title="记录的绿灯延长事件">${fmt(Number(v.time))} · 绿灯延长 ↗</button>`,
      )
      .join("");
    bookmarks.querySelectorAll<HTMLElement>("button").forEach((b) =>
      b.addEventListener("click", () => {
        playing = false;
        void seek(Number(b.dataset.time));
      }),
    );
  }
}
function showSceneError(message: string) {
  $("scene-error").textContent = message;
  $("scene-error").classList.remove("hidden");
}
async function seek(time: number) {
  if (!playback) return;
  if (loading) {
    pendingSeek = time;
    return;
  }
  const token = epoch;
  loading = true;
  try {
    const [frame, second] = await Promise.all([
      playback.frame(time),
      otherPlayback?.frame(time),
    ]);
    if (token !== epoch) return;
    current = time;
    lastFrame = frame?.vehicles ?? [];
    otherFrame = second?.vehicles ?? [];
    city?.setVehicles(lastFrame);
    city?.setVehicles(otherFrame, true);
    if (selectedObject?.kind === "junction") selectObject(selectedObject);
    if (mode === "diff") city?.setDifference(true, lastFrame, otherFrame);
    $("clock").textContent = fmt(current);
    $<HTMLInputElement>("timeline-range").value = String(current);
    const coreCount = lastFrame.filter((v) =>
      insidePolygon([v.x, v.y], city?.network.core_polygon ?? []),
    ).length;
    $("sample-status").textContent = frame
      ? `在网 ${frame.vehicles.length.toLocaleString()} 辆 · 核心 ${coreCount} / 次区 ${frame.vehicles.length - coreCount} · ${frame.time.toFixed(1)} s`
      : "当前时段无轨迹记录";
  } catch (e) {
    if (token === epoch) {
      playing = false;
      toast(errorMessage(e));
      $("play-button").textContent = "▶";
    }
  } finally {
    loading = false;
    if (pendingSeek !== undefined) {
      const next = pendingSeek;
      pendingSeek = undefined;
      void seek(next);
    }
  }
}
function setModeUI() {
  document
    .querySelectorAll("[data-mode]")
    .forEach((b) =>
      b.classList.toggle("active", (b as HTMLElement).dataset.mode === mode),
    );
  $("split-labels").classList.toggle("hidden", mode !== "split");
  $("legend-title").textContent = mode === "diff" ? "车道均速 B−A" : "车辆速度";
  document
    .querySelector(".map-legend")
    ?.classList.toggle("difference", mode === "diff");
  const legend = document.querySelectorAll(".map-legend>span");
  for (let i = 1; i < 4; i++) {
    const dot = legend[i]?.querySelector("i");
    if (dot) {
      legend[i].replaceChildren(
        dot,
        document.createTextNode(
          mode === "diff"
            ? ["更慢", "接近", "更快"][i - 1]
            : ["停等 <1 m/s", "低速 <5 m/s", "≥5 m/s"][i - 1],
        ),
      );
    }
  }
}
async function compareRun(id: string) {
  const token = ++comparisonEpoch;
  mode = "single";
  city?.setComparison(false);
  city?.setDifference(false);
  setModeUI();
  otherPlayback?.dispose();
  otherPlayback = undefined;
  otherManifest = undefined;
  otherRun = undefined;
  if (!id) {
    mode = "single";
    city?.setComparison(false);
    setModeUI();
    return;
  }
  const run = runs.find((r) => r.run_id === id);
  if (!run || !manifest) return;
  try {
    const url = new URL(run.manifest, location.href).href,
      m = await json<Manifest>(url);
    if (token !== comparisonEpoch) return;
    if (m.valid_for_ranking === false || manifest.valid_for_ranking === false)
      throw new Error("运行存在待复核异常，暂不进行政策差值比较");
    for (const key of [
      "engine_version",
      "step_seconds",
      "action_step_seconds",
      "start_time",
      "end_time",
      "implementation_hash",
    ])
      if (m[key] !== manifest[key]) throw new Error(`实验条件不一致：${key}`);
    if (m.demand_hash !== manifest.demand_hash)
      throw new Error("两次运行的需求哈希不同，不能进行配对比较");
    let compareNetwork = city!.network;
    if (m.network_hash !== manifest.network_hash) {
      const asset =
        run.network ??
        (m.network_url
          ? new URL(String(m.network_url), url).href
          : new URL(String(m.network ?? "network.json"), url).href);
      compareNetwork = await json<Network>(asset);
      if (token !== comparisonEpoch) return;
    }
    assertCompatible(compareNetwork, m);
    city?.setCompareNetwork(compareNetwork);
    otherPlayback = new Playback(m, url);
    otherManifest = m;
    otherRun = run;
    $("comparison-note").textContent =
      `需求哈希一致 · ${run.label ?? run.run_id}。${m.network_hash !== manifest.network_hash ? "结构变化：棕色标出通行权限改变的车道；仅支持双图。" : "双图共享镜头、时间和色阶。"}`;
    await seek(current);
    if (run.metrics && metrics) {
      const b = await json<Metric>(new URL(run.metrics, location.href).href);
      if (token !== comparisonEpoch) return;
      const aTime = numberAt(metrics, ["tstt_vehicle_seconds"]),
        bTime = numberAt(b, ["tstt_vehicle_seconds"]);
      const aRate = numberAt(metrics, ["completion_rate"]),
        bRate = numberAt(b, ["completion_rate"]);
      if (aTime !== undefined && bTime !== undefined)
        $("comparison-note").textContent +=
          ` Δ累计时间 ${((bTime - aTime) / 3600).toFixed(2)} veh·h${aRate !== undefined && bRate !== undefined ? `；Δ完成比例 ${((bRate - aRate) * 100).toFixed(1)} 个百分点` : ""}。单个配对样本不代表稳定排名。`;
    }
  } catch (e) {
    toast(errorMessage(e));
    $<HTMLSelectElement>("compare-select").value = "";
    $("comparison-note").textContent = errorMessage(e);
  }
}
function animate(now: number) {
  const delta = Math.min((now - lastAnimation) / 1000, 0.25);
  lastAnimation = now;
  if (playing && !loading) {
    const next = Math.min(
      end,
      current + delta * Number($<HTMLSelectElement>("speed").value),
    );
    void seek(next);
    if (next >= end) {
      playing = false;
      $("play-button").textContent = "▶";
    }
  }
  requestAnimationFrame(animate);
}
requestAnimationFrame(animate);
type ODRow = {
  origin_gate: string;
  destination_gate: string;
  rate_per_hour: number;
  interval_start: number;
  interval_end: number;
};
let customRows: ODRow[] = [];
const parameterDefs: Record<
  string,
  { label: string; value: number; min: number; max: number; policies: string[] }
> = {
  green_extension_seconds: {
    label: "绿灯延长上限 / s",
    value: 8,
    min: 1,
    max: 15,
    policies: ["S1", "S3", "S6", "S7"],
  },
  downstream_occupancy_threshold: {
    label: "下游占有率阈值 / %",
    value: 65,
    min: 10,
    max: 90,
    policies: ["S3", "S6", "S7"],
  },
  managed_curb_stop_seconds: {
    label: "治理后临停时长 / s",
    value: 8,
    min: 0,
    max: 30,
    policies: ["S5", "S7"],
  },
};
function renderParameters() {
  $("policy-parameters").innerHTML = Object.entries(parameterDefs)
    .filter(([, p]) => p.policies.includes(policy))
    .map(
      ([key, p]) =>
        `<label>${p.label}<input data-parameter="${key}" type="number" min="${p.min}" max="${p.max}" value="${p.value}"></label>`,
    )
    .join("");
  document
    .querySelectorAll<HTMLInputElement>("[data-parameter]")
    .forEach((input) =>
      input.addEventListener("change", () => {
        parameterDefs[input.dataset.parameter!].value = Number(input.value);
      }),
    );
}

function renderCustomOD() {
  const entries = network.gates.filter((g) => g.direction === "entry"),
    exits = network.gates.filter((g) => g.direction === "exit");
  const options = (gates: Network["gates"], selected: string) =>
    gates
      .map(
        (g) =>
          `<option value="${esc(g.id)}" ${g.id === selected ? "selected" : ""}>${esc(g.id)}</option>`,
      )
      .join("");
  $("custom-od-rows").innerHTML = customRows
    .map(
      (r, i) =>
        `<div class="custom-od-row" data-row="${i}"><label>入口<select data-key="origin_gate">${options(entries, r.origin_gate)}</select></label><label>出口<select data-key="destination_gate">${options(exits, r.destination_gate)}</select></label><label>veh/h<input data-key="rate_per_hour" type="number" min="0" max="1800" value="${r.rate_per_hour}"></label><label>开始 s<input data-key="interval_start" type="number" min="0" step="300" value="${r.interval_start}"></label><label>结束 s<input data-key="interval_end" type="number" min="300" step="300" value="${r.interval_end}"></label><button data-remove="${i}" aria-label="删除 OD 条目">×</button></div>`,
    )
    .join("");
  document.querySelectorAll<HTMLElement>("[data-row]").forEach((row) =>
    row
      .querySelectorAll<HTMLInputElement | HTMLSelectElement>("[data-key]")
      .forEach((input) =>
        input.addEventListener("change", () => {
          const r = customRows[Number(row.dataset.row)] as unknown as Record<
            string,
            string | number
          >;
          r[input.dataset.key!] =
            input instanceof HTMLInputElement
              ? Number(input.value)
              : input.value;
        }),
      ),
  );
  document.querySelectorAll<HTMLElement>("[data-remove]").forEach((b) =>
    b.addEventListener("click", () => {
      customRows.splice(Number(b.dataset.remove), 1);
      renderCustomOD();
    }),
  );
}
$("add-od-row").addEventListener("click", () => {
  if (!network) return;
  const origin = network.gates.find((g) => g.direction === "entry"),
    destination = network.gates.find((g) => g.direction === "exit");
  if (!origin || !destination) return;
  customRows.push({
    origin_gate: origin.id,
    destination_gate: destination.id,
    rate_per_hour: 120,
    interval_start: 0,
    interval_end: 300,
  });
  renderCustomOD();
});
async function checkBackend() {
  try {
    await json("/api/health");
    backend = true;
    $("backend-status").textContent = "计算服务已连接";
    $("backend-status").classList.add("online");
    $<HTMLButtonElement>("run-button").disabled = false;
    $("job-status").textContent = "可提交新实验；服务端校验可达性与政策支持。";
    const data = await json<{ policies: unknown[] }>("/api/policies");
    for (const p of data.policies as {
      id: string;
      available: boolean;
      reason?: string;
    }[]) {
      if (!p.available) {
        const button = document.querySelector<HTMLElement>(
          `[data-policy="${p.id}"]`,
        );
        if (button) {
          button.classList.add("unavailable");
          button.title = p.reason ?? "需要额外资料";
          button.querySelector(".policy-copy small")!.textContent =
            "待道路空间证据 · 不可运行";
        }
      }
    }
  } catch {
    backend = false;
    $("backend-status").textContent = "离线回放";
    $<HTMLButtonElement>("run-button").disabled = true;
  }
}
function config() {
  const od = $<HTMLInputElement>("custom-od-enabled").checked
    ? customRows
    : undefined;
  if (od && !od.length) throw new Error("请至少添加一条自定义 OD");
  const parameters = Object.fromEntries(
    Object.entries(parameterDefs)
      .filter(([, p]) => p.policies.includes(policy))
      .map(([k, p]) => [k, p.value]),
  );
  return {
    ...(od ? { od } : {}),
    ...(Object.keys(parameters).length
      ? { policy_parameters: parameters }
      : {}),
    network_id: "baseline",
    policy,
    seed: Number($<HTMLInputElement>("seed").value),
    demand_scale: Number($<HTMLInputElement>("demand-scale").value),
    duration_seconds: Number($<HTMLInputElement>("run-duration").value),
    step_seconds: 0.5,
    trajectory: true,
    rate_per_gate: Number($<HTMLInputElement>("gate-rate").value),
    period,
  };
}
async function submit() {
  if (!backend) return;
  const button = $<HTMLButtonElement>("run-button");
  button.disabled = true;
  try {
    const payload = config();
    $("job-status").textContent = "正在校验配置与政策能力…";
    const validation = await json<{ valid: boolean; errors?: string[] }>(
      "/api/scenarios/validate",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    if (!validation.valid)
      throw new Error(validation.errors?.join("；") ?? "配置校验失败");
    const job = await json<{ run_id: string; status: string }>("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    jobId = job.run_id;
    jobPolicy = payload.policy;
    $("cancel-button").classList.remove("hidden");
    await pollJob();
  } catch (e) {
    $("job-status").textContent = errorMessage(e);
    toast(`未提交：${errorMessage(e)}`);
    button.disabled = false;
  }
}
async function pollJob() {
  if (!jobId) return;
  try {
    const job = await json<{ run_id: string; status: string; error?: string }>(
      `/api/runs/${encodeURIComponent(jobId)}`,
    );
    const labels: Record<string, string> = {
      validating: "校验中",
      queued: "已排队",
      running: "仿真计算中",
      finalizing: "正在核查与写入",
      succeeded: "已完成",
      failed: "失败",
      cancelled: "已取消",
    };
    $("job-status").textContent =
      `${labels[job.status] ?? job.status} · ${job.run_id}${job.error ? ` · ${job.error}` : ""}`;
    if (["succeeded", "failed", "cancelled"].includes(job.status)) {
      $("cancel-button").classList.add("hidden");
      $<HTMLButtonElement>("run-button").disabled = false;
      if (job.status === "succeeded") {
        const id = job.run_id;
        const run = {
          run_id: id,
          label: `${jobPolicy} · 新实验`,
          policy: jobPolicy,
          manifest: `/api/runs/${id}/manifest`,
          metrics: `/api/runs/${id}/metrics`,
          network: `/api/runs/${id}/network`,
        };
        if (!runs.some((r) => r.run_id === id)) runs.push(run);
        populateRuns();
        $<HTMLSelectElement>("run-select").value = id;
        await loadRun(run);
      }
      jobId = "";
      return;
    }
    setTimeout(() => void pollJob(), 1500);
  } catch (e) {
    $("job-status").textContent =
      `状态读取中断：${errorMessage(e)}，稍后重试。`;
    setTimeout(() => void pollJob(), 4000);
  }
}
function setupOD() {
  const entries = (network.gates ?? []).filter((g) =>
      /in|entry|entrance/i.test(g.direction),
    ),
    exits = (network.gates ?? []).filter((g) => /out|exit/i.test(g.direction));
  const gates = entries.length ? entries : network.gates;
  $("gate-select").innerHTML = gates
    .map(
      (g) =>
        `<option value="${esc(g.id)}">${esc(g.id)} · ${esc(g.edge_id)}</option>`,
    )
    .join("");
  $("od-rows").innerHTML = exits
    .map(
      (g, i) =>
        `<label class="od-row"><span>${esc(g.id)}</span><input class="od-share" type="number" min="0" max="100" step="0.01" value="${i === exits.length - 1 ? (100 - (Math.floor(10000 / exits.length) / 100) * (exits.length - 1)).toFixed(2) : (Math.floor(10000 / exits.length) / 100).toFixed(2)}"><span>%</span></label>`,
    )
    .join("");
  validateOd();
  document
    .querySelectorAll(".od-share")
    .forEach((v) => v.addEventListener("input", validateOd));
}
function validateOd() {
  const shares = Array.from(
    document.querySelectorAll<HTMLInputElement>(".od-share"),
  ).map((v) => Number(v.value));
  const errors = shares.length
    ? validateOD(Number($<HTMLInputElement>("gate-rate").value), shares)
    : ["没有可用出口"];
  $("od-validation").textContent = errors.length
    ? errors.join("；")
    : "✓ 比例合计 100% · 可达性仍须服务端检查";
  $("od-validation").classList.toggle("invalid", !!errors.length);
  return !errors.length;
}
$("run-select").addEventListener("change", () => {
  const run = runs.find(
    (r) => r.run_id === $<HTMLSelectElement>("run-select").value,
  );
  if (run) void loadRun(run);
});
$("compare-select").addEventListener(
  "change",
  () => void compareRun($<HTMLSelectElement>("compare-select").value),
);
$("play-button").addEventListener("click", () => {
  if (!playback) return;
  if (current >= end) void seek(start);
  playing = !playing;
  $("play-button").textContent = playing ? "Ⅱ" : "▶";
  $("play-button").setAttribute("aria-label", playing ? "暂停" : "播放");
});
$("rewind-button").addEventListener("click", () => {
  playing = false;
  $("play-button").textContent = "▶";
  void seek(start);
});
$("timeline-range").addEventListener("input", () => {
  playing = false;
  $("play-button").textContent = "▶";
  void seek(Number($<HTMLInputElement>("timeline-range").value));
});
for (const view of ["core", "full", "top"] as const)
  $(view + "-view").addEventListener("click", () => {
    city?.setView(view);
    document
      .querySelectorAll(".view-controls button")
      .forEach((b) => b.classList.toggle("active", b.id === view + "-view"));
  });
$("reset-view").addEventListener("click", () => city?.setView("core"));
$("buildings-button").addEventListener("click", () => {
  buildings = !buildings;
  city?.setBuildings(buildings);
  $("buildings-button").classList.toggle("active", buildings);
  $("buildings-button").setAttribute("aria-pressed", String(buildings));
});
document.querySelectorAll<HTMLElement>("[data-period]").forEach((button) =>
  button.addEventListener("click", () => {
    period = button.dataset.period!;
    document
      .querySelectorAll("[data-period]")
      .forEach((b) => b.classList.toggle("active", b === button));
    toast("需求时段设置已修改；当前回放保持原始输入，需提交新实验。");
  }),
);
document.querySelectorAll<HTMLElement>("[data-policy]").forEach((button) =>
  button.addEventListener("click", () => {
    policy = button.dataset.policy!;
    document.querySelectorAll<HTMLElement>("[data-policy]").forEach((b) => {
      b.classList.toggle("selected", b === button);
      b.setAttribute("aria-pressed", String(b === button));
      b.querySelector(".policy-indicator")!.textContent =
        b === button ? "●" : "○";
    });
    $("policy-detail").textContent =
      `${policy} · ${policies.find((p) => p[0] === policy)![2]}。提交前检查机制与目标支持；选择不会修改现有回放。`;
    renderParameters();
  }),
);
document.querySelectorAll<HTMLElement>("[data-mode]").forEach((button) =>
  button.addEventListener("click", () => {
    const value = button.dataset.mode!;
    if (value !== "single" && !otherPlayback) {
      toast("请先选择同需求的对照运行。");
      return;
    }
    if (
      value === "diff" &&
      otherManifest?.network_hash !== manifest?.network_hash
    ) {
      toast("结构变化只做双图对照；不同路网不计算车道数值差。");
      return;
    }
    mode = value;
    city?.setComparison(mode === "split");
    city?.setDifference(mode === "diff", lastFrame, otherFrame);
    setModeUI();
    if (mode === "diff")
      $("comparison-note").textContent =
        "仅比较两边均有车辆采样的同一车道均速：绿色更快，红色更慢，灰色接近。样本构成可能不同。";
  }),
);
$("run-button").addEventListener("click", () => void submit());
$("cancel-button").addEventListener("click", async () => {
  if (jobId) {
    try {
      await json(`/api/runs/${encodeURIComponent(jobId)}/cancel`, {
        method: "POST",
      });
      void pollJob();
    } catch (e) {
      toast(`取消请求未确认：${errorMessage(e)}`);
    }
  }
});
for (const id of ["evidence-button", "provenance-button"])
  $(id).addEventListener("click", () =>
    $<HTMLDialogElement>("evidence-dialog").showModal(),
  );
$("od-button").addEventListener("click", () =>
  $<HTMLDialogElement>("od-dialog").showModal(),
);
document
  .querySelectorAll<HTMLElement>("[data-close]")
  .forEach((b) =>
    b.addEventListener("click", () =>
      $<HTMLDialogElement>(b.dataset.close!).close(),
    ),
  );
$("gate-rate").addEventListener("input", validateOd);
$("gate-select").addEventListener("change", () => {
  const gate = network.gates.find(
    (g) => g.id === $<HTMLSelectElement>("gate-select").value,
  );
  if (gate) selectObject({ kind: "gate", id: gate.id, data: gate });
});
$("export-od").addEventListener("click", () => {
  if (!validateOd()) return;
  const blob = new Blob(
    [
      JSON.stringify(
        {
          schema_version: "1.0",
          status: "draft_not_submitted",
          network_hash: network.network_hash,
          custom_od: customRows,
          custom_od_enabled: $<HTMLInputElement>("custom-od-enabled").checked,
          origin_gate: $<HTMLSelectElement>("gate-select").value,
          rate_veh_per_hour: Number($<HTMLInputElement>("gate-rate").value),
          destination_shares: Array.from(
            document.querySelectorAll<HTMLInputElement>(".od-share"),
          ).map((v) => ({
            gate: v.closest("label")?.querySelector("span")?.textContent,
            share: Number(v.value) / 100,
          })),
          source_kind: "synthetic_scenario",
          period,
        },
        null,
        2,
      ),
    ],
    { type: "application/json" },
  );
  const url = URL.createObjectURL(blob),
    a = document.createElement("a");
  a.href = url;
  a.download = "boundary-od-draft.json";
  a.click();
  URL.revokeObjectURL(url);
});
function createScene(n: Network): CityScene | CitySceneCanvas | undefined {
  const host = $("canvas-host");
  try {
    const renderer = new CityScene(host, n, selectObject);
    document.body.classList.remove("canvas-fallback");
    return renderer;
  } catch (error) {
    host.replaceChildren();
    try {
      const renderer = new CitySceneCanvas(host, n, selectObject);
      document.body.classList.add("canvas-fallback");
      let badge = document.getElementById("renderer-note");
      if (!badge) {
        badge = document.createElement("div");
        badge.id = "renderer-note";
        badge.className = "renderer-note";
        document.querySelector(".view-stage")!.append(badge);
      }
      badge.textContent = "2D 兼容视图 · 此设备不支持 WebGL · 同源真实数据";
      return renderer;
    } catch (fallbackError) {
      showSceneError(
        `图形视图不可用：${errorMessage(fallbackError)}。指标与回放清单仍可使用。`,
      );
      return undefined;
    }
  }
}
async function init() {
  void checkBackend();
  try {
    network = await json<Network>("/data/network.json");
    city = createScene(network);
    $("data-status").textContent = "真实地图 · 等待运行";
    setupOD();
    try {
      const catalog = await json<{ runs: RunEntry[] }>("/data/catalog.json");
      runs = catalog.runs.map((r) => ({
        ...r,
        manifest: new URL(r.manifest, new URL("/data/", location.href)).href,
        metrics: r.metrics
          ? new URL(r.metrics, new URL("/data/", location.href)).href
          : undefined,
        network: r.network
          ? new URL(r.network, new URL("/data/", location.href)).href
          : undefined,
      }));
      populateRuns();
      if (runs.length) await loadRun(runs[0]);
      else $("sample-status").textContent = "尚无已完成回放";
    } catch {
      $("run-select").innerHTML = "<option>未找到回放清单</option>";
      $("sample-status").textContent = "仅显示真实静态路网";
      toast("回放清单尚未生成，当前仅展示真实地图。");
    }
  } catch (e) {
    showSceneError(
      `真实道路资产未能加载：${errorMessage(e)}。请检查数据文件与网络连接。`,
    );
    $("data-status").textContent = "等待真实路网数据";
    $("run-select").innerHTML = "<option>没有可用运行</option>";
  }
  setInterval(() => {
    if (!city) return;
    const stats = city.stats();
    $("performance").textContent =
      city instanceof CitySceneCanvas
        ? "Canvas 2D · 同源状态 · 未使用 GPU"
        : `${stats.fps} FPS · ${stats.calls} draws · ${stats.triangles.toLocaleString()} triangles`;
  }, 1800);
}
void init();
