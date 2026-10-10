/** DOM wiring tests only. Rendering is intentionally mocked; these are not WebGL acceptance. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";
import { JSDOM } from "jsdom";
const result = await build({
  entryPoints: ["src/main.ts"],
  bundle: true,
  write: false,
  format: "iife",
  loader: { ".css": "empty" },
  plugins: [
    {
      name: "render-test-double",
      setup(b) {
        b.onResolve({ filter: /^\.\/scene$/ }, () => ({
          path: "scene",
          namespace: "mock",
        }));
        b.onResolve({ filter: /^\.\/playback$/ }, () => ({
          path: "playback",
          namespace: "mock",
        }));
        b.onLoad({ filter: /.*/, namespace: "mock" }, (args) => ({
          contents:
            args.path === "scene"
              ? `export class CityScene {constructor(host,network,onSelect){if(window.__forceWebGLFailure)throw new Error("Error creating WebGL context");this.network=network;window.__scene=this}setVehicles(){}setTraffic(v,other=false){if(other)this.otherTraffic=v;else this.traffic=v}setDifference(){}setComparison(v){this.split=v}setCompareNetwork(n){this.otherNetwork=n}setBuildings(v){this.buildings=v}setView(v){this.view=v}stats(){return {fps:0,calls:0,triangles:0}}dispose(){}}`
              : `export class Playback{constructor(manifest,url){this.manifest=manifest}async frame(time){return {time,vehicles:[]}}dispose(){}}`,
          loader: "js",
        }));
      },
    },
  ],
});
const network = {
  schema_version: "1.0",
  network_hash: "n",
  origin: {},
  lanes: [
    {
      id: "lane",
      edge_id: "edge",
      shape: [
        [0, 0],
        [100, 0],
      ],
      width: 3.2,
      speed: 10,
    },
  ],
  buildings: [],
  junctions: [],
  core_polygon: [],
  simulation_polygon: [],
  gates: [
    { id: "entry", edge_id: "e", direction: "entry", position: [0, 0] },
    { id: "exit", edge_id: "x", direction: "exit", position: [100, 0] },
  ],
};
const manifest = (id: string, policy: string) => ({
  schema_version: "1.0",
  run_id: id,
  policy,
  network_hash: "n",
  demand_hash: "d",
  policy_hash: policy,
  lanes: ["lane"],
  start_time: 0,
  end_time: 600,
  step_seconds: 0.5,
  chunks: [{ file: "chunk.bin", start: 0.5, end: 600, records: 0 }],
  network: "../../network.json",
  metrics: "metrics.json",
  timeseries: "timeseries.json",
  events: "events.json",
  audit: "audit.json",
});
async function mount(
  online = false,
  failWebGL = false,
  failCanvas = false,
  warmup = false,
  extended = false,
  extendedB = false,
) {
  const dom = new JSDOM('<div id="app"></div>', {
    url: "http://localhost/",
    runScripts: "outside-only",
  });
  const w = dom.window;
  Object.assign(w, {
    __forceWebGLFailure: failWebGL,
    ResizeObserver: class {
      constructor(private callback: () => void) {}
      observe() {
        this.callback();
      }
      disconnect() {}
    },
  });
  w.HTMLCanvasElement.prototype.getContext = function () {
    if (failCanvas) return null;
    return new Proxy({}, { get: () => () => undefined, set: () => true });
  } as unknown as typeof w.HTMLCanvasElement.prototype.getContext;

  const requests: {
    url: string;
    method?: string;
    body?: Record<string, unknown>;
  }[] = [];
  let cancelled = false;
  w.requestAnimationFrame = () => 0;
  w.setInterval = () => 0;
  const originalTimeout = w.setTimeout.bind(w);
  w.setTimeout = ((fn: TimerHandler, ms?: number, ...args: unknown[]) =>
    ms && ms > 1000
      ? 0
      : originalTimeout(fn, ms, ...args)) as typeof w.setTimeout;
  w.HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  w.HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
  w.fetch = async (input, init) => {
    const url = new URL(String(input), "http://localhost").pathname;
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    requests.push({ url, method: init?.method, body });
    let payload: unknown = {};
    if (url === "/api/health") {
      if (!online) return new Response("{}", { status: 404 });
      payload = { status: "ok" };
    } else if (url === "/api/policies") payload = { policies: [] };
    else if (url === "/api/scenarios/validate") payload = { valid: true };
    else if (url === "/api/runs" && init?.method === "POST")
      payload = { run_id: "new", status: "queued" };
    else if (url === "/api/runs/new/cancel") {
      cancelled = true;
      payload = { status: "cancelled" };
    } else if (url === "/api/runs/new")
      payload = { run_id: "new", status: cancelled ? "cancelled" : "running" };
    else if (url === "/data/network.json") payload = network;
    else if (url === "/data/catalog.json")
      payload = {
        runs: [
          {
            run_id: "a",
            playback_start_seconds: warmup ? 300 : undefined,
            scenario_kind: warmup
              ? "uncalibrated_synthetic_busy_demo"
              : undefined,
            policy: "S0",
            manifest: "runs/a/manifest.json",
            metrics: "runs/a/metrics.json",
          },
          {
            run_id: "b",
            policy: "S1",
            manifest: "runs/b/manifest.json",
            metrics: "runs/b/metrics.json",
          },
        ],
      };
    else if (url.endsWith("/manifest.json")) {
      payload = manifest(
        url.includes("/b/") ? "b" : "a",
        url.includes("/b/") ? "S1" : "S0",
      );
      if (extended && (!url.includes("/b/") || extendedB))
        Object.assign(
          payload as object,
          Object.fromEntries(
            [
              "signal_topology",
              "queue_hotspots",
              "stock_timeseries",
              "internal_zones",
              "od_matrix",
              "od_csv",
            ].map((k) => [k, k + ".json"]),
          ),
        );
    } else if (url.endsWith("/metrics.json"))
      payload = {
        tstt_vehicle_seconds: 3600,
        completion_rate: 0.5,
        external_waiting: 2,
        inside: 3,
        explicit_failure: 0,
      };
    else if (url.endsWith("/audit.json"))
      payload = {
        conservation_passed: true,
        conservation_max_residual: 0,
        teleports: 0,
        collisions: 0,
      };
    else if (url.endsWith("/timeseries.json"))
      payload = [
        { time: 5, inside: 2 },
        { time: 10, inside: 3 },
      ];
    else if (extended && url.endsWith("/signal_topology.json"))
      payload = [
        {
          tls: "tls",
          source: "SUMO",
          position: [100, 0],
          links: [
            {
              index: 0,
              incoming_lane: "lane",
              outgoing_lane: "out",
              via_lane: ":via",
            },
          ],
        },
      ];
    else if (extended && url.endsWith("/signals.json"))
      payload = [
        {
          tls: "tls",
          time: 0,
          state: url.includes("/b/") ? "G" : "r",
          phase: 0,
        },
        {
          tls: "tls",
          time: 5,
          state: url.includes("/b/") ? "r" : "G",
          phase: 1,
        },
      ];
    else if (extended && url.endsWith("/queue_hotspots.json"))
      payload = [
        { time: 0, edges: [], total_stopped: 0, threshold_m_s: 0.1 },
        {
          time: 5,
          edges: [{ edge_id: "edge", stopped_vehicles: 8 }],
          total_stopped: 8,
          threshold_m_s: 0.1,
        },
      ];
    else if (extended && url.endsWith("/stock_timeseries.json"))
      payload = [0, 5].map((time) => ({
        time,
        parked_total: 100 - time,
        parked_by_zone: { zone: 100 - time },
        initial_parked_total: 100,
        inside: time,
        internal_insertion_waiting: 0,
        boundary_insertion_waiting: 0,
        conservation_residual: 0,
      }));
    else if (extended && url.endsWith("/internal_zones.json"))
      payload = {
        zones: [
          {
            id: "zone",
            name: "建筑分区",
            position: [0, 0],
            initial_parked: 100,
            building_count: 30,
            access_edge: "edge",
            source: "ASSUMED",
          },
        ],
        assumptions: ["未经现场调查"],
      };
    else if (extended && url.endsWith("/od_matrix.json"))
      payload = [
        {
          origin: "zone",
          destination: "exit",
          origin_kind: "internal",
          destination_kind: "boundary",
          interval_start: 0,
          interval_end: 300,
          trip_count: 50,
          source: "ASSUMED",
        },
      ];
    else payload = [];
    return new Response(JSON.stringify(payload), {
      headers: { "Content-Type": "application/json" },
    });
  };
  w.eval(result.outputFiles[0].text);
  for (let i = 0; i < 15; i++) await new Promise((r) => setTimeout(r, 0));
  return { dom, w, requests };
}
test("offline viewer loads recorded metrics and its working scene controls", async () => {
  const { dom, w } = await mount();
  try {
    const d = w.document;
    assert.equal(d.querySelector("#active-run")?.textContent, "a");
    assert.equal(d.querySelector("#metric-tstt")?.textContent, "1.00");
    assert.equal(d.querySelector("#metric-completion")?.textContent, "50.0%");
    assert.equal(
      (d.querySelector("#run-button") as HTMLButtonElement).disabled,
      true,
    );
    (d.querySelector("#full-view") as HTMLButtonElement).click();
    assert.equal(
      (w as unknown as { __scene: { view: string } }).__scene.view,
      "full",
    );
    (d.querySelector("#evidence-button") as HTMLButtonElement).click();
    assert.equal(
      d.querySelector("#evidence-dialog")?.hasAttribute("open"),
      true,
    );
    (
      d.querySelector('[data-close="evidence-dialog"]') as HTMLButtonElement
    ).click();
    assert.equal(
      d.querySelector("#evidence-dialog")?.hasAttribute("open"),
      false,
    );
  } finally {
    dom.window.close();
  }
});
test("policy and explicit custom OD go into submitted config; duplicate submission blocked and cancellation works", async () => {
  const { dom, w, requests } = await mount(true);
  try {
    const d = w.document;
    (d.querySelector('[data-policy="S7"]') as HTMLButtonElement).click();
    assert.equal(d.querySelectorAll("[data-parameter]").length, 3);
    (d.querySelector("#add-od-row") as HTMLButtonElement).click();
    (d.querySelector("#custom-od-enabled") as HTMLInputElement).checked = true;
    const rate = d.querySelector(
      '[data-key="rate_per_hour"]',
    ) as HTMLInputElement;
    rate.value = "240";
    rate.dispatchEvent(new w.Event("change"));
    const button = d.querySelector("#run-button") as HTMLButtonElement;
    button.click();
    button.click();
    for (let i = 0; i < 10; i++) await new Promise((r) => setTimeout(r, 0));
    const posts = requests.filter(
      (r) => r.url === "/api/runs" && r.method === "POST",
    );
    assert.equal(posts.length, 1);
    assert.equal(posts[0].body?.policy, "S7");
    assert.deepEqual(posts[0].body?.od, [
      {
        origin_gate: "entry",
        destination_gate: "exit",
        rate_per_hour: 240,
        interval_start: 0,
        interval_end: 300,
      },
    ]);
    assert.equal(
      (posts[0].body?.policy_parameters as Record<string, unknown>)
        .green_extension_seconds,
      8,
    );
    (d.querySelector("#cancel-button") as HTMLButtonElement).click();
    for (let i = 0; i < 10; i++) await new Promise((r) => setTimeout(r, 0));
    assert.match(d.querySelector("#job-status")?.textContent ?? "", /已取消/);
    assert.equal(button.disabled, false);
  } finally {
    dom.window.close();
  }
});
test("comparison requires explicit second run and switches synchronized view", async () => {
  const { dom, w } = await mount();
  try {
    const d = w.document;
    (d.querySelector('[data-mode="split"]') as HTMLButtonElement).click();
    assert.equal(
      d.querySelector("#split-labels")?.classList.contains("hidden"),
      true,
    );
    const select = d.querySelector("#compare-select") as HTMLSelectElement;
    select.value = "b";
    select.dispatchEvent(new w.Event("change"));
    for (let i = 0; i < 10; i++) await new Promise((r) => setTimeout(r, 0));
    (d.querySelector('[data-mode="split"]') as HTMLButtonElement).click();
    assert.equal(
      d.querySelector("#split-labels")?.classList.contains("hidden"),
      false,
    );
    assert.match(
      d.querySelector("#comparison-note")?.textContent ?? "",
      /需求哈希一致/,
    );
  } finally {
    dom.window.close();
  }
});

test("WebGL creation failure falls back to real-data Canvas without hiding valid catalog or metrics", async () => {
  const { dom, w } = await mount(false, true);
  try {
    const d = w.document;
    assert.equal(d.querySelector("#active-run")?.textContent, "a");
    assert.equal(d.querySelector("#metric-tstt")?.textContent, "1.00");
    assert.equal(d.querySelector("#run-select")?.children.length, 2);
    assert.equal(d.querySelectorAll(".fallback-canvas").length, 1);
    assert.match(
      d.querySelector("#renderer-note")?.textContent ?? "",
      /2D 兼容视图/,
    );
    assert.ok(d.querySelector("#scene-error")?.classList.contains("hidden"));
    (d.querySelector("#full-view") as HTMLButtonElement).click();
    (d.querySelector("#buildings-button") as HTMLButtonElement).click();
    const select = d.querySelector("#compare-select") as HTMLSelectElement;
    select.value = "b";
    select.dispatchEvent(new w.Event("change"));
    for (let i = 0; i < 10; i++) await new Promise((r) => setTimeout(r, 0));
    (d.querySelector('[data-mode="split"]') as HTMLButtonElement).click();
    assert.equal(
      d.querySelector("#split-labels")?.classList.contains("hidden"),
      false,
    );
  } finally {
    dom.window.close();
  }
});

test("even when both graphics contexts fail, valid run metrics remain independently accessible", async () => {
  const { dom, w } = await mount(false, true, true);
  try {
    assert.equal(w.document.querySelector("#active-run")?.textContent, "a");
    assert.equal(w.document.querySelector("#metric-tstt")?.textContent, "1.00");
    assert.match(
      w.document.querySelector("#scene-error")?.textContent ?? "",
      /图形视图不可用/,
    );
    assert.equal(
      w.document.querySelector("#scene-error")?.classList.contains("hidden"),
      false,
    );
  } finally {
    dom.window.close();
  }
});

test("dense demo opens at its recorded warmup offset and remains explicitly uncalibrated", async () => {
  const { dom, w } = await mount(false, false, false, true);
  try {
    assert.equal(w.document.querySelector("#clock")?.textContent, "05:00");
    assert.match(
      w.document.querySelector("#data-status")?.textContent ?? "",
      /合成高需求演示（未校准）/,
    );
    assert.match(
      w.document.querySelector("#sample-status")?.textContent ?? "",
      /核心 0 \/ 次区 0/,
    );
    assert.equal(w.document.querySelectorAll(".boundary-key").length, 2);
  } finally {
    dom.window.close();
  }
});

test("building OD, signal phases, stock and hotspot records stay synchronized on pause and backward seek", async () => {
  const { dom, w } = await mount(false, false, false, false, true);
  try {
    const d = w.document,
      scene = (w as any).__scene;
    assert.equal(scene.traffic.signals[0].state, "r");
    assert.equal(scene.traffic.zones[0].parked, 100);
    const select = d.querySelector("#signal-select") as HTMLSelectElement;
    select.value = "tls";
    select.dispatchEvent(new w.Event("change"));
    assert.match(
      d.querySelector("#signal-details")!.textContent!,
      /lane → out/,
    );
    const range = d.querySelector("#timeline-range") as HTMLInputElement;
    const seek = async (time: number) => {
      range.value = String(time);
      range.dispatchEvent(new w.Event("input"));
      for (let i = 0; i < 3; i++) await new Promise((r) => setTimeout(r, 0));
    };
    await seek(6);
    assert.equal(scene.traffic.signals[0].state, "G");
    assert.equal(scene.traffic.zones[0].parked, 95);
    assert.equal(scene.traffic.hotspots[0].stopped_vehicles, 8);
    await seek(4);
    assert.equal(scene.traffic.signals[0].state, "r");
    assert.equal(scene.traffic.zones[0].parked, 100);
    assert.equal(scene.traffic.hotspots.length, 0);
    (d.querySelector("#show-signals") as HTMLInputElement).click();
    assert.equal(scene.traffic.signals.length, 0);
    (d.querySelector("#recorded-od-button") as HTMLButtonElement).click();
    assert.ok(d.querySelector("#recorded-od-dialog")!.hasAttribute("open"));
    assert.match(d.querySelector("#recorded-od-body")!.textContent!, /ASSUMED/);
    assert.match(
      (d.querySelector("#recorded-od-download") as HTMLAnchorElement).href,
      /runs\/a\/od_csv.json$/,
    );
    (
      d.querySelector('[data-close="recorded-od-dialog"]') as HTMLButtonElement
    ).click();
    assert.ok(!d.querySelector("#recorded-od-dialog")!.hasAttribute("open"));
    const run = d.querySelector("#run-select") as HTMLSelectElement;
    run.value = "b";
    run.dispatchEvent(new w.Event("change"));
    for (let i = 0; i < 15; i++) await new Promise((r) => setTimeout(r, 0));
    assert.equal(scene.traffic.zones.length, 0);
    assert.equal(scene.traffic.signals.length, 0);
    assert.equal(d.querySelector("#active-run")!.textContent, "b");
    assert.ok((d.querySelector("#recorded-od-download") as HTMLElement).hidden);
  } finally {
    dom.window.close();
  }
});

test("paired views carry independent A/B signals, stock and source-aware inspection at one clock", async () => {
  const { dom, w } = await mount(false, false, false, false, true, true);
  try {
    const d = w.document,
      scene = (w as any).__scene;
    const compare = d.querySelector("#compare-select") as HTMLSelectElement;
    compare.value = "b";
    compare.dispatchEvent(new w.Event("change"));
    for (let i = 0; i < 15; i++) await new Promise((r) => setTimeout(r, 0));
    (d.querySelector('[data-mode="split"]') as HTMLButtonElement).click();
    assert.equal(scene.traffic.signals[0].state, "r");
    assert.equal(scene.otherTraffic.signals[0].state, "G");
    const source = d.querySelector("#traffic-source") as HTMLSelectElement;
    source.value = "B";
    source.dispatchEvent(new w.Event("change"));
    const controller = d.querySelector("#signal-select") as HTMLSelectElement;
    controller.value = "tls";
    controller.dispatchEvent(new w.Event("change"));
    (d.querySelector("[data-signal]") as HTMLButtonElement).click();
    assert.match(d.querySelector("#selection")!.textContent!, /视图来源B/);
    assert.match(d.querySelector("#selection")!.textContent!, /SUMO 状态G/);
    const range = d.querySelector("#timeline-range") as HTMLInputElement;
    range.value = "6";
    range.dispatchEvent(new w.Event("input"));
    for (let i = 0; i < 3; i++) await new Promise((r) => setTimeout(r, 0));
    assert.equal(scene.traffic.signals[0].state, "G");
    assert.equal(scene.otherTraffic.signals[0].state, "r");
    assert.match(d.querySelector("#selection")!.textContent!, /SUMO 状态r/);
    assert.match(d.querySelector("#traffic-status")!.textContent!, /^B ·/);
    source.value = "A";
    source.dispatchEvent(new w.Event("change"));
    controller.value = "tls";
    controller.dispatchEvent(new w.Event("change"));
    (d.querySelector("[data-signal]") as HTMLButtonElement).click();
    assert.match(d.querySelector("#selection")!.textContent!, /视图来源A/);
    assert.match(d.querySelector("#selection")!.textContent!, /SUMO 状态G/);
  } finally {
    dom.window.close();
  }
});
