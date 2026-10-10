/** CPU geometry checks; these do not establish WebGL visual acceptance. */
import { test } from "node:test";
import assert from "node:assert/strict";
import * as THREE from "three";
import { CityScene } from "../src/scene.ts";
import { CitySceneCanvas } from "../src/scene-canvas.ts";
import { paneCoordinates, polygonBounds } from "../src/view-geometry.ts";
test("pane coordinates account for host offset and both split halves", () => {
  const rect = { left: 220, top: 80, width: 800, height: 600 };
  const a = paneCoordinates(420, 380, rect, true),
    b = paneCoordinates(820, 380, rect, true);
  assert.equal(a.ndcX, 0);
  assert.equal(b.ndcX, 0);
  assert.equal(a.ndcY, 0);
  assert.equal(b.ndcY, 0);
  assert.equal(a.right, false);
  assert.equal(b.right, true);
});
test("source polygon bounds retain asymmetric secondary study extent", () => {
  assert.deepEqual(
    polygonBounds([
      [-1400, -1316],
      [1223, -1316],
      [1223, 1412],
      [-1400, 1412],
    ]),
    { center: [-88.5, 48], width: 2623, height: 2728 },
  );
});
test("Canvas split refits current extent; full view fits the actual asymmetric bounds", () => {
  const scene = Object.create(CitySceneCanvas.prototype) as any;
  Object.assign(scene, {
    width: 800,
    height: 600,
    scale: 0.25,
    center: [0, 0],
    split: false,
    network: {
      core_polygon: [
        [-500, -500],
        [500, -500],
        [500, 500],
        [-500, 500],
      ],
      simulation_polygon: [
        [-1400, -1316],
        [1223, -1316],
        [1223, 1412],
        [-1400, 1412],
      ],
    },
    redrawStatic() {},
  });
  scene.setView("core");
  scene.setComparison(true);
  for (const p of scene.network.core_polygon) {
    const [x, y] = scene.point(p);
    assert.ok(x > 0 && x < 400 && y > 0 && y < 600);
  }
  const scale = scene.scale;
  scene.setComparison(true);
  assert.equal(scene.scale, scale);
  scene.setView("full");
  for (const p of scene.network.simulation_polygon) {
    const [x, y] = scene.point(p);
    assert.ok(x > 0 && x < 400 && y > 0 && y < 600);
  }
});
test("Three pivot ray uses actual ground and preserves camera offset in both panes", () => {
  function run(clientX: number) {
    const scene = Object.create(CityScene.prototype) as any;
    const camera = new THREE.PerspectiveCamera(38, 400 / 600, 1, 30000);
    camera.position.set(900, 1200, 1000);
    camera.lookAt(0, 0, 0);
    camera.updateMatrixWorld();
    const before = camera.position.clone();
    Object.assign(scene, {
      camera,
      split: true,
      renderer: {
        domElement: {
          getBoundingClientRect: () => ({
            left: 220,
            top: 80,
            width: 800,
            height: 600,
          }),
        },
      },
      raycaster: new THREE.Raycaster(),
      controls: { target: new THREE.Vector3(), update() {} },
    });
    const ray = new THREE.Raycaster();
    ray.setFromCamera(new THREE.Vector2(0.5, 0.2), camera);
    const expected = ray.ray.intersectPlane(
      new THREE.Plane(new THREE.Vector3(0, 1, 0), 0),
      new THREE.Vector3(),
    )!;
    scene.setPivot({ clientX, clientY: 320 });
    assert.ok(scene.controls.target.distanceTo(expected) < 1e-6);
    assert.ok(
      camera.position.clone().sub(scene.controls.target).distanceTo(before) <
        1e-6,
    );
    assert.equal(scene.pivotVisible, true);
    return scene.controls.target;
  }
  assert.ok(run(520).distanceTo(run(920)) < 1e-6);
});

test("Canvas middle pick then drag really rotates around the picked point; split inverse picking and right-pan remain correct", async () => {
  const { JSDOM } = await import("jsdom");
  const dom = new JSDOM('<div id="host"></div>');
  const saved = {
    document: globalThis.document,
    ResizeObserver: globalThis.ResizeObserver,
    devicePixelRatio: globalThis.devicePixelRatio,
  };
  Object.assign(globalThis, {
    document: dom.window.document,
    devicePixelRatio: 1,
    ResizeObserver: class {
      observe() {}
      disconnect() {}
    },
  });
  dom.window.HTMLCanvasElement.prototype.getContext = (() =>
    new Proxy({}, { get: () => () => undefined, set: () => true })) as any;
  const host = dom.window.document.getElementById("host")!;
  Object.defineProperties(host, {
    clientWidth: { value: 800 },
    clientHeight: { value: 600 },
  });
  let selections = 0;
  const network = {
    lanes: [],
    buildings: [],
    junctions: [],
    gates: [],
    core_polygon: [
      [-500, -500],
      [500, -500],
      [500, 500],
      [-500, 500],
    ],
    simulation_polygon: [],
  } as any;
  const scene = new CitySceneCanvas(host, network, () => selections++) as any;
  try {
    scene.setComparison(true);
    const canvas = host.querySelector("canvas")!;
    canvas.getBoundingClientRect = () =>
      ({ left: 220, top: 80, width: 800, height: 600 }) as DOMRect;
    const initialScale = scene.scale;
    const expected = [(300 - 200) / initialScale, -(240 - 336) / initialScale];
    const click = new dom.window.MouseEvent("pointerdown", {
      button: 1,
      clientX: 920,
      clientY: 320,
      cancelable: true,
    });
    canvas.dispatchEvent(click);
    assert.equal(click.defaultPrevented, true);
    assert.ok(
      Math.hypot(scene.center[0] - expected[0], scene.center[1] - expected[1]) <
        1e-9,
    );
    assert.deepEqual(scene.pivot, scene.center);
    assert.equal(scene.scale, initialScale);
    assert.equal(selections, 0);
    const aux = new dom.window.MouseEvent("auxclick", {
      button: 1,
      cancelable: true,
    });
    canvas.dispatchEvent(aux);
    assert.equal(aux.defaultPrevented, true);
    const pivot = [...scene.pivot];
    const east = [pivot[0] + 100, pivot[1]];
    const fixedBefore = scene.point(pivot),
      eastBefore = scene.point(east);
    const event = (type: string, x: number, y: number, button = 0) =>
      canvas.dispatchEvent(
        new dom.window.MouseEvent(type, {
          button,
          clientX: x,
          clientY: y,
          cancelable: true,
        }),
      );
    event("pointerdown", 820, 400);
    event("pointermove", 920, 400);
    event("pointerup", 920, 400);
    assert.equal(scene.rotation, 0.6);
    assert.deepEqual(scene.center, pivot);
    assert.deepEqual(scene.point(pivot), fixedBefore);
    const after = scene.point(east);
    assert.ok(
      Math.hypot(after[0] - eastBefore[0], after[1] - eastBefore[1]) > 10,
    );
    assert.ok(
      Math.abs(after[0] - fixedBefore[0] - Math.cos(0.6) * 100 * initialScale) <
        1e-9,
    );
    assert.ok(
      Math.abs(after[1] - fixedBefore[1] - Math.sin(0.6) * 100 * initialScale) <
        1e-9,
    );
    assert.equal(selections, 0);
    // Pick a second world point after rotation from the B pane. Inverse
    // projection must return that exact point, rather than a north-up guess.
    const nextWorld = [pivot[0] - 60, pivot[1] + 90];
    const projected = scene.point(nextWorld, 400);
    event("pointerdown", 220 + projected[0], 80 + projected[1], 1);
    assert.ok(
      Math.hypot(
        scene.center[0] - nextWorld[0],
        scene.center[1] - nextWorld[1],
      ) < 1e-9,
    );
    const panBefore = scene.point(east);
    event("pointerdown", 820, 400, 2);
    event("pointermove", 860, 430, 2);
    event("pointerup", 860, 430, 2);
    const panAfter = scene.point(east);
    assert.ok(Math.abs(panAfter[0] - panBefore[0] - 40) < 1e-9);
    assert.ok(Math.abs(panAfter[1] - panBefore[1] - 30) < 1e-9);
    assert.equal(selections, 0);
    scene.setView("core");
    assert.equal(scene.pivot, undefined);
    assert.equal(scene.rotation, 0);
  } finally {
    scene.dispose();
    Object.assign(globalThis, saved);
    dom.window.close();
  }
});

test("real OrbitControls left-drag orbits the newly selected ground target", async () => {
  const { JSDOM } = await import("jsdom");
  const { OrbitControls } = await import(
    "three/addons/controls/OrbitControls.js"
  );
  const dom = new JSDOM("<canvas></canvas>");
  const canvas = dom.window.document.querySelector("canvas")!;
  Object.defineProperties(canvas, {
    clientWidth: { value: 800 },
    clientHeight: { value: 600 },
  });
  canvas.setPointerCapture = () => {};
  canvas.releasePointerCapture = () => {};
  canvas.getBoundingClientRect = () =>
    ({ left: 220, top: 80, width: 800, height: 600 }) as DOMRect;
  const camera = new THREE.PerspectiveCamera(38, 800 / 600, 1, 30000);
  camera.position.set(900, 1200, 1000);
  camera.lookAt(0, 0, 0);
  const controls = new OrbitControls(camera, canvas);
  const scene = Object.create(CityScene.prototype) as any;
  Object.assign(scene, {
    camera,
    controls,
    split: false,
    raycaster: new THREE.Raycaster(),
    renderer: { domElement: canvas },
  });
  try {
    scene.setPivot({ clientX: 800, clientY: 420 });
    const pivot = controls.target.clone(),
      position = camera.position.clone(),
      radius = position.distanceTo(pivot);
    assert.ok(pivot.length() > 1);
    for (const [type, x] of [
      ["pointerdown", 600],
      ["pointermove", 740],
      ["pointerup", 740],
    ] as const) {
      const event = new dom.window.MouseEvent(type, {
        button: 0,
        clientX: x,
        clientY: 400,
        bubbles: true,
      });
      Object.defineProperty(event, "pointerId", { value: 1 });
      canvas.dispatchEvent(event);
    }
    assert.ok(camera.position.distanceTo(position) > 10);
    assert.ok(controls.target.distanceTo(pivot) < 1e-9);
    assert.ok(Math.abs(camera.position.distanceTo(pivot) - radius) < 1e-6);
  } finally {
    controls.dispose();
    dom.window.close();
  }
});

test("responsive styles must not hide study boundaries or current-frame vehicle counts", async () => {
  const { readFile } = await import("node:fs/promises");
  const css = await readFile(
    new URL("../src/style.css", import.meta.url),
    "utf8",
  );
  assert.doesNotMatch(
    css,
    /\.boundary-key\s*\{\s*display:\s*none\s*!important/,
  );
  assert.doesNotMatch(css, /\.playback-meta\s*\{\s*display:\s*none/);
  assert.match(css, /\.timeline-top\s*\{[^}]*flex-wrap:\s*wrap/);
});

test("CityScene constructor capture binding handles actual middle pointerdown before real OrbitControls and subsequent drag preserves the new target", async () => {
  const { JSDOM } = await import("jsdom");
  const { build } = await import("esbuild");
  const { resolve } = await import("node:path");
  const threePath = JSON.stringify(
    resolve("node_modules/three/build/three.module.js"),
  );
  const bundle = await build({
    stdin: {
      contents: 'export { CityScene } from "./src/scene.ts";',
      resolveDir: process.cwd(),
      loader: "ts",
    },
    bundle: true,
    write: false,
    format: "iife",
    globalName: "SceneTest",
    plugins: [
      {
        name: "GPU-only-test-double",
        setup(b) {
          b.onResolve({ filter: /^three$/ }, () => ({
            path: "three-gpu-double",
            namespace: "gpu",
          }));
          b.onLoad({ filter: /.*/, namespace: "gpu" }, () => ({
            contents: `export * from ${threePath}; export class WebGLRenderer { constructor(){this.domElement=document.createElement("canvas");} setPixelRatio(){} setClearColor(){} setSize(){} setAnimationLoop(){} dispose(){} }`,
            resolveDir: process.cwd(),
            loader: "js",
          }));
        },
      },
    ],
  });
  const dom = new JSDOM('<div id="host"></div>', {
    runScripts: "outside-only",
  });
  const w = dom.window;
  Object.assign(w, {
    ResizeObserver: class {
      observe() {}
      disconnect() {}
    },
  });
  w.HTMLCanvasElement.prototype.setPointerCapture = () => {};
  w.HTMLCanvasElement.prototype.releasePointerCapture = () => {};
  Object.defineProperties(w.HTMLCanvasElement.prototype, {
    clientWidth: { get: () => 800 },
    clientHeight: { get: () => 600 },
  });
  w.HTMLCanvasElement.prototype.getBoundingClientRect = () =>
    ({ left: 220, top: 80, width: 800, height: 600 }) as DOMRect;
  const host = w.document.getElementById("host")!;
  Object.defineProperties(host, {
    clientWidth: { value: 800 },
    clientHeight: { value: 600 },
  });
  w.eval(bundle.outputFiles[0].text);
  let selected = 0;
  const scene = new (w as any).SceneTest.CityScene(
    host,
    {
      lanes: [],
      buildings: [],
      junctions: [],
      gates: [],
      core_polygon: [
        [-500, -500],
        [500, -500],
        [500, 500],
        [-500, 500],
      ],
      simulation_polygon: [],
    },
    () => selected++,
  );
  const canvas = host.querySelector("canvas")!;
  const pointer = (type: string, x: number, button: number) => {
    const event = new w.MouseEvent(type, {
      button,
      clientX: x,
      clientY: 420,
      bubbles: true,
      cancelable: true,
    });
    Object.defineProperty(event, "pointerId", { value: 1 });
    canvas.dispatchEvent(event);
    return event;
  };
  try {
    const original = scene.controls.target.clone();
    const middle = pointer("pointerdown", 800, 1);
    pointer("pointerup", 800, 1);
    assert.equal(middle.defaultPrevented, true);
    assert.ok(
      scene.controls.target.distanceTo(original) > 10,
      "middle DOM event must set a new world target",
    );
    assert.equal(scene.pivotVisible, true);
    const target = scene.controls.target.clone();
    const position = scene.camera.position.clone();
    const distance = position.distanceTo(target);
    // OrbitControls update after the event must not undo the target.
    scene.controls.update();
    assert.ok(scene.controls.target.distanceTo(target) < 1e-9);
    pointer("pointerdown", 600, 0);
    pointer("pointermove", 740, 0);
    pointer("pointerup", 740, 0);
    assert.ok(
      scene.camera.position.distanceTo(position) > 10,
      "subsequent left drag must actually orbit",
    );
    assert.ok(
      scene.controls.target.distanceTo(target) < 1e-9,
      "orbit target stays at the selected world point",
    );
    assert.ok(
      Math.abs(scene.camera.position.distanceTo(target) - distance) < 1e-6,
      "middle click must not start a dolly",
    );
    assert.equal(selected, 0, "middle click must not select scene objects");
  } finally {
    scene.dispose();
    dom.window.close();
  }
});
