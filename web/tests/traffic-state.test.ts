import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  signalColor,
  signalMarkers,
  sampleAt,
  trafficOverlay,
  type SignalTopology,
  type SignalEvent,
} from "../src/traffic-state.ts";
import type { Network } from "../src/types.ts";
const network = {
  lanes: [
    {
      id: "in",
      edge_id: "edge",
      shape: [
        [0, 0],
        [100, 0],
      ],
      width: 3,
      speed: 10,
    },
  ],
} as Network;
const topology: SignalTopology[] = [
  {
    tls: "tls",
    position: [100, 0],
    source: "sumo",
    links: [
      { index: 0, incoming_lane: "in", outgoing_lane: "out", via_lane: ":via" },
      {
        index: 1,
        incoming_lane: "in",
        outgoing_lane: "out2",
        via_lane: ":via2",
      },
    ],
  },
];
const events: SignalEvent[] = [
  { time: 0, tls: "tls", state: "rG", phase: 0 },
  { time: 10, tls: "tls", state: "yg", phase: 1 },
  { time: 12, tls: "tls", state: "Gr", phase: 2 },
];
test("signal state respects exact link index, phase changes, and rewind without future leakage", () => {
  assert.equal(signalMarkers(network, topology, events, -1).length, 0);
  const start = signalMarkers(network, topology, events, 0);
  assert.deepEqual(
    start.map((s) => s.state),
    ["r", "G"],
  );
  assert.deepEqual(
    signalMarkers(network, topology, events, 10).map((s) => s.state),
    ["y", "g"],
  );
  assert.deepEqual(
    signalMarkers(network, topology, events, 12).map((s) => s.state),
    ["G", "r"],
  );
  assert.deepEqual(
    signalMarkers(network, topology, events, 9).map((s) => s.state),
    ["r", "G"],
  );
  assert.notDeepEqual(start[0].position, start[1].position);
  assert.equal(start[0].incoming_lane, "in");
});
test("unknown/off states stay gray; missing topology lanes do not invent lights", () => {
  assert.equal(signalColor("o"), "#808b90");
  assert.equal(signalColor("?"), "#808b90");
  assert.equal(signalColor("G"), signalColor("g"));
  assert.equal(
    signalMarkers({ ...network, lanes: [] }, topology, events, 0).length,
    0,
  );
});
test("recorded samples use previous observation on seek, including old data with no extras", () => {
  const samples = [{ time: 0 }, { time: 5 }, { time: 10 }];
  assert.equal(sampleAt(samples, 4.9)?.time, 0);
  assert.equal(sampleAt(samples, 5)?.time, 5);
  assert.equal(sampleAt(samples, -1), undefined);
  assert.equal(sampleAt([], 100), undefined);
  assert.deepEqual(
    trafficOverlay(network, [], [], undefined, undefined, undefined, 100),
    { signals: [], hotspots: [], zones: [] },
  );
});
test("hotspots map measured stopped vehicle counts to real edges, never queue length", () => {
  const result = trafficOverlay(
    network,
    [],
    [],
    {
      time: 5,
      threshold_m_s: 0.1,
      total_stopped: 20,
      edges: [
        { edge_id: "edge", stopped_vehicles: 20 },
        { edge_id: "missing", stopped_vehicles: 9 },
      ],
    },
    undefined,
    undefined,
    5,
  );
  assert.equal(result.hotspots.length, 1);
  assert.equal(result.hotspots[0].stopped_vehicles, 20);
  assert.deepEqual(result.hotspots[0].shape, network.lanes[0].shape);
});
test("packaged building OD run provides resolvable recorded signal and stock overlays", () => {
  const path = "public/data/runs/internal_demo_S0_am_42_v1/";
  const read = (p: string) => JSON.parse(readFileSync(p, "utf8"));
  const n = read("public/data/network.json"),
    topology = read(path + "signal_topology.json"),
    events = read(path + "signals.json"),
    queue = read(path + "queue_hotspots.json"),
    stock = read(path + "stock_timeseries.json"),
    zones = read(path + "internal_zones.json");
  const overlay = trafficOverlay(
    n,
    topology,
    events,
    sampleAt(queue, 300),
    zones,
    sampleAt(stock, 300),
    300,
  );
  assert.ok(overlay.signals.length > 0);
  assert.equal(overlay.zones.length, 16);
  assert.ok(overlay.hotspots.length > 0);
  assert.ok(
    overlay.signals.every(
      (s) => s.time <= 300 && s.incoming_lane && s.outgoing_lane,
    ),
  );
  assert.equal(
    overlay.zones.reduce((n, z) => n + (z.parked ?? 0), 0),
    sampleAt<any>(stock, 300).parked_total,
  );
  assert.equal(sampleAt<any>(stock, 300).conservation_residual, 0);
});

test("Canvas draws actual link colors above vehicle layer and exposes signal/zone selection", async () => {
  const { CitySceneCanvas } = await import("../src/scene-canvas.ts");
  const scene = Object.create(CitySceneCanvas.prototype) as any;
  const overlay = trafficOverlay(
    network,
    topology,
    events,
    undefined,
    undefined,
    undefined,
    10,
  );
  const fills: string[] = [],
    selections: any[] = [];
  const context = new Proxy(
    { fillStyle: "" },
    {
      get(o: any, key) {
        if (key === "fill") return () => fills.push(o.fillStyle);
        if (key === "fillStyle") return o.fillStyle;
        return () => {};
      },
      set(o: any, k, v) {
        o[k] = v;
        return true;
      },
    },
  );
  Object.assign(scene, {
    traffic: overlay,
    width: 300,
    height: 200,
    split: false,
    point: (p: any) => p,
    canvas: { getBoundingClientRect: () => ({ left: 0, top: 0 }) },
    vehicles: [],
    network,
    onSelect: (s: any) => selections.push(s),
  });
  scene.drawTraffic(context, true);
  assert.deepEqual(fills, [signalColor("y"), signalColor("g")]);
  scene.pick({ clientX: 97, clientY: 0 });
  assert.equal(selections[0].kind, "signal");
  assert.equal(selections[0].data.state, "y");
  assert.equal(selections[0].data.index, 0);
});

test("Three signal overlay replaces GPU objects and picker entries rather than accumulating stale states", async () => {
  const { CityScene } = await import("../src/scene.ts");
  const THREE = await import("three");
  const scene = Object.create(CityScene.prototype) as any;
  Object.assign(scene, {
    scene: new THREE.Scene(),
    traffic: new THREE.Group(),
    trafficKey: "",
    picker: [],
  });
  scene.setTraffic(
    trafficOverlay(
      network,
      topology,
      events,
      undefined,
      undefined,
      undefined,
      0,
    ),
  );
  assert.equal(scene.picker.length, 2);
  assert.equal(scene.picker[0].userData.data.state, "r");
  scene.setTraffic(
    trafficOverlay(
      network,
      topology,
      events,
      undefined,
      undefined,
      undefined,
      10,
    ),
  );
  assert.equal(scene.picker.length, 2);
  assert.equal(scene.picker[0].userData.data.state, "y");
  assert.equal(scene.scene.children.length, 1);
  scene.setTraffic({ signals: [], zones: [], hotspots: [] });
  assert.equal(scene.picker.length, 0);
});

test("Canvas split panes draw and pick each run own link state with pane-relative coordinates", async () => {
  const { CitySceneCanvas } = await import("../src/scene-canvas.ts");
  const scene = Object.create(CitySceneCanvas.prototype) as any;
  const a = trafficOverlay(
      network,
      topology,
      events,
      undefined,
      undefined,
      undefined,
      0,
    ),
    b = trafficOverlay(
      network,
      topology,
      events,
      undefined,
      undefined,
      undefined,
      12,
    );
  const selected: any[] = [];
  Object.assign(scene, {
    traffic: a,
    otherTraffic: b,
    width: 600,
    height: 300,
    split: true,
    point: (p: any, offset = 0) => [p[0] + offset, p[1]],
    canvas: { getBoundingClientRect: () => ({ left: 0, top: 0 }) },
    vehicles: [],
    otherVehicles: [],
    network,
    otherNetwork: network,
    onSelect: (s: any) => selected.push(s),
  });
  scene.pick({ clientX: 97, clientY: 0 });
  scene.pick({ clientX: 397, clientY: 0 });
  assert.deepEqual(
    selected.map((s) => [s.source, s.data.state]),
    [
      ["A", "r"],
      ["B", "G"],
    ],
  );
  const colors: string[] = [],
    positions: number[] = [];
  const ctx = new Proxy(
    { fillStyle: "" },
    {
      get(o: any, k) {
        if (k === "fill") return () => colors.push(o.fillStyle);
        if (k === "arc") return (x: number) => positions.push(x);
        return () => {};
      },
      set(o: any, k, v) {
        o[k] = v;
        return true;
      },
    },
  );
  scene.drawTraffic(ctx, true, true);
  assert.deepEqual(colors, [signalColor("G"), signalColor("r")]);
  assert.ok(positions.every((x) => x > 300));
});

test("Three comparison scene isolates signal meshes and B picking cannot read A state", async () => {
  const { CityScene } = await import("../src/scene.ts");
  const THREE = await import("three");
  const scene = Object.create(CityScene.prototype) as any,
    selected: any[] = [];
  Object.assign(scene, {
    scene: new THREE.Scene(),
    comparison: new THREE.Scene(),
    traffic: new THREE.Group(),
    otherTraffic: new THREE.Group(),
    trafficKey: "",
    otherTrafficKey: "",
    picker: [],
    split: true,
    vehicles: new THREE.Mesh(),
    otherVehicles: new THREE.Mesh(),
    camera: new THREE.PerspectiveCamera(),
    renderer: {
      domElement: {
        getBoundingClientRect: () => ({
          left: 0,
          top: 0,
          width: 600,
          height: 300,
        }),
      },
    },
    onSelect: (s: any) => selected.push(s),
    highlight: () => {},
  });
  scene.setTraffic(
    trafficOverlay(
      network,
      topology,
      events,
      undefined,
      undefined,
      undefined,
      0,
    ),
  );
  scene.setTraffic(
    trafficOverlay(
      network,
      topology,
      events,
      undefined,
      undefined,
      undefined,
      12,
    ),
    true,
  );
  assert.equal(scene.traffic.parent, scene.scene);
  assert.equal(scene.otherTraffic.parent, scene.comparison);
  scene.raycaster = {
    setFromCamera() {},
    intersectObjects(objects: any[]) {
      const signals = objects.filter((o) => o.userData.kind === "signal");
      assert.ok(signals.every((o) => o.parent === scene.otherTraffic));
      return [{ object: signals[0] }];
    },
  };
  scene.pick({ clientX: 450, clientY: 150 });
  assert.equal(selected[0].source, "B");
  assert.equal(selected[0].data.state, "G");
  assert.equal(scene.traffic.children[0].userData.data.state, "r");
});

test("missing stock observations remain unknown instead of inventing current parked vehicles", () => {
  const overlay = trafficOverlay(
    network,
    [],
    [],
    undefined,
    {
      zones: [
        {
          id: "z",
          name: "zone",
          position: [0, 0],
          initial_parked: 100,
          building_count: 10,
          access_edge: "edge",
          source: "ASSUMED",
        },
      ],
    },
    undefined,
    300,
  );
  assert.equal(overlay.zones[0].parked, null);
  assert.equal(overlay.zones[0].initial_parked, 100);
});
