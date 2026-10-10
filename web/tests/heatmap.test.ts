import { test } from "node:test";
import assert from "node:assert/strict";
import {
  aggregateFrame,
  heatValue,
  heatSegments,
  heatColor,
  heatWindow,
  validateHeatData,
  NO_DATA,
  ONE_SIDED,
  type HeatData,
} from "../src/heatmap";
import type { Network, Vehicle, Manifest } from "../src/types";
const network: Network = {
  schema_version: "1.0",
  network_hash: "n",
  origin: {},
  lanes: [
    {
      id: "a_0",
      edge_id: "a",
      shape: [
        [0, 0],
        [10, 0],
      ],
      width: 3,
      speed: 10,
    },
    {
      id: "a_1",
      edge_id: "a",
      shape: [
        [0, 3],
        [10, 3],
      ],
      width: 3,
      speed: 10,
    },
    {
      id: "b",
      edge_id: "b",
      shape: [
        [10, 0],
        [20, 0],
      ],
      width: 3,
      speed: 20,
    },
    {
      id: ":j",
      edge_id: ":j",
      shape: [
        [10, 0],
        [11, 0],
      ],
      width: 3,
      speed: 5,
    },
  ],
  buildings: [],
  junctions: [],
  gates: [],
  core_polygon: [],
  simulation_polygon: [],
};
const v = (lane: number, speed: number): Vehicle => ({
  id: lane,
  time: 300,
  x: 0,
  y: 0,
  angle: 0,
  flags: 0,
  lane,
  speed,
});
test("road speed, strict stop threshold, lane-limit loss and internal exclusion use real observations", () => {
  const w = aggregateFrame(
    network,
    [v(0, 0), v(1, 10), v(2, 0.1), v(3, 0)],
    300,
    true,
  );
  assert.deepEqual(w.edges.a, [2, 10, 1, 1, 2]);
  assert.equal(w.edges[":j"], undefined);
  assert.equal(heatValue(w.edges.a, "speed", 1), 18);
  assert.equal(heatValue(w.edges.a, "stopped", 1), 1);
  assert.equal(heatValue(w.edges.a, "loss", 1), 50);
  assert.equal(heatValue(w.edges.b, "stopped", 1), 0);
  assert.equal(heatValue(w.edges.a, "stopped", 60), 1 / 60);
});
test("missing roads are gray rather than zero; paired delta demands common observations and exact window", () => {
  const a = aggregateFrame(network, [v(0, 0)], 300, true),
    b = aggregateFrame(network, [v(0, 10), v(2, 5)], 300, true);
  const speed = heatSegments(network, a, "speed", b, true);
  assert.equal(speed[0].value, 36);
  assert.equal(speed[0].color, heatColor(36, "speed", true));
  assert.equal(speed[2].value, null);
  assert.equal(speed[2].color, ONE_SIDED);
  assert.equal(heatSegments(network, a, "speed")[2].color, NO_DATA);
  assert.ok(
    heatSegments(
      network,
      a,
      "speed",
      { ...b, start: 301, end: 301 },
      true,
    ).every((s) => s.value === null),
  );
  assert.equal(heatColor(-20, "speed", true), heatColor(10, "stopped", true));
  assert.equal(heatColor(-50, "loss", true), heatColor(20, "speed", true));
});
test("invalid lane reference cannot invent loss, empty samples cannot imply freeflow", () => {
  const n = { ...network, lanes: [{ ...network.lanes[0], speed: 0 }] };
  const w = aggregateFrame(n, [v(0, 5)], 10, true);
  assert.equal(heatValue(w.edges.a, "loss", 1), null);
  assert.equal(heatValue(w.edges.a, "speed", 0), null);
  assert.equal(heatValue(undefined, "speed", 1), null);
});
test("window boundaries and identity corruption reject misleading summaries", () => {
  const total = {
    start: 300,
    end: 4200,
    frames: 3900,
    edges: { a: [2, 10, 1, 1, 2] as [number, number, number, number, number] },
  };
  const d: HeatData = {
    schema_version: "1.0",
    run_id: "r",
    network_hash: "n",
    demand_hash: "d",
    total,
    windows: [{ ...total, end: 360, frames: 60 }],
  };
  const m = { run_id: "r", network_hash: "n", demand_hash: "d" } as Manifest;
  assert.equal(validateHeatData(d, m), d);
  assert.equal(heatWindow(d, "minute", 300), undefined);
  assert.equal(heatWindow(d, "minute", 360)?.end, 360);
  assert.equal(heatWindow(d, "minute", 360.5), undefined);
  assert.throws(() => validateHeatData(d, { ...m, network_hash: "x" }));
  assert.throws(() =>
    validateHeatData({ ...d, total: { ...total, frames: NaN } }, m),
  );
});

test("Canvas renders exact sampled road colors in each clipped pane without halos", async () => {
  const { CitySceneCanvas } = await import("../src/scene-canvas");
  const scene = Object.create(CitySceneCanvas.prototype) as any;
  const a = heatSegments(
    network,
    aggregateFrame(network, [v(0, 0)], 300, true),
    "speed",
  );
  const b = heatSegments(
    network,
    aggregateFrame(network, [v(0, 10)], 300, true),
    "speed",
  );
  const strokes: string[] = [];
  const paths: any[] = [];
  const context = new Proxy(
    { strokeStyle: "" },
    {
      get(o: any, k) {
        if (k === "stroke") return () => strokes.push(o.strokeStyle);
        return o[k] ?? (() => {});
      },
      set(o: any, k, v) {
        o[k] = v;
        return true;
      },
    },
  );
  Object.assign(scene, {
    traffic: { heatmap: a, signals: [], zones: [], hotspots: [] },
    otherTraffic: { heatmap: b, signals: [], zones: [], hotspots: [] },
    width: 400,
    height: 200,
    split: true,
    scale: 1,
    path: (_c: any, p: any, offset: number) => paths.push({ p, offset }),
  });
  scene.drawTraffic(context, false, false);
  scene.drawTraffic(context, false, true);
  assert.equal(strokes.length, 6);
  assert.equal(strokes[0], heatColor(0, "speed"));
  assert.equal(strokes[3], heatColor(36, "speed"));
  assert.equal(strokes[2], NO_DATA);
  assert.equal(paths[3].offset, 200);
  assert.deepEqual(paths[0].p, network.lanes[0].shape);
});
test("Three road heatmap uses one merged vertex-color mesh and replaces it without stale GPU geometry", async () => {
  const { CityScene } = await import("../src/scene");
  const THREE = await import("three");
  const scene = Object.create(CityScene.prototype) as any;
  Object.assign(scene, {
    scene: new THREE.Scene(),
    comparison: new THREE.Scene(),
    traffic: new THREE.Group(),
    otherTraffic: new THREE.Group(),
    trafficKey: "",
    otherTrafficKey: "",
    picker: [],
  });
  const a = heatSegments(
    network,
    aggregateFrame(network, [v(0, 0)], 300, true),
    "speed",
  );
  scene.setTraffic({ heatmap: a, signals: [], zones: [], hotspots: [] });
  assert.equal(scene.traffic.children.length, 1);
  const mesh = scene.traffic.children[0];
  assert.ok(mesh.geometry.getAttribute("color").count > 0);
  assert.equal(mesh.material.vertexColors, true);
  let disposed = false;
  mesh.geometry.addEventListener("dispose", () => (disposed = true));
  scene.setTraffic({
    heatmap: heatSegments(
      network,
      aggregateFrame(network, [v(0, 10)], 300, true),
      "speed",
    ),
    signals: [],
    zones: [],
    hotspots: [],
  });
  assert.equal(disposed, true);
  assert.equal(scene.scene.children.length, 1);
  scene.setTraffic({ heatmap: a, signals: [], zones: [], hotspots: [] }, true);
  assert.equal(scene.comparison.children.length, 1);
  assert.notEqual(scene.traffic, scene.otherTraffic);
});
