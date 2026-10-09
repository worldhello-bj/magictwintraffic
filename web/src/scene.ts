import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import type { Network, Point, Vehicle } from "./types";
import { localToWorld } from "./protocol";
export type Selection = {
  kind: "lane" | "vehicle" | "gate" | "junction";
  id: string;
  data: unknown;
  source?: "A" | "B";
};
export class CityScene {
  renderer: THREE.WebGLRenderer;
  camera: THREE.PerspectiveCamera;
  controls: OrbitControls;
  scene = new THREE.Scene();
  comparison = new THREE.Scene();
  private buildings = new THREE.Group();
  private vehicles: THREE.InstancedMesh;
  private otherVehicles: THREE.InstancedMesh;
  private vehicleData: Vehicle[] = [];
  private otherData: Vehicle[] = [];
  private picker: THREE.Object3D[] = [];
  private raycaster = new THREE.Raycaster();
  private selected = new THREE.Group();
  private diff = new THREE.Group();
  private roads = new THREE.Group();
  private split = false;
  private dummy = new THREE.Object3D();
  private observer: ResizeObserver;
  private pointerDown = [0, 0];
  private capacity = 20000;
  private otherNetwork: Network | undefined;
  private otherPicker: THREE.Object3D[] | undefined;
  private otherBuildings: THREE.Group | undefined;
  private separateComparison = false;
  private roadLabels: { element: HTMLElement; position: THREE.Vector3 }[] = [];
  private clickHandler: (e: PointerEvent) => void;
  private downHandler: (e: PointerEvent) => void;
  private last = performance.now();
  private frameTimes: number[] = [];
  private compass: HTMLElement | null = null;
  constructor(
    private host: HTMLElement,
    public network: Network,
    private onSelect: (s: Selection) => void,
  ) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
    this.renderer.setClearColor(0xe8ede9);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    host.append(this.renderer.domElement);
    this.renderer.domElement.setAttribute(
      "aria-label",
      "真实路网三维视图，可拖动旋转、滚轮缩放并点击道路车辆",
    );
    this.camera = new THREE.PerspectiveCamera(38, 1, 1, 14000);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.maxPolarAngle = Math.PI * 0.48;
    this.controls.minDistance = 60;
    this.controls.maxDistance = 6500;
    this.controls.target.set(0, 0, 0);
    this.camera.position.set(900, 1200, 1000);
    this.scene.background = new THREE.Color(0xe8ede9);
    this.scene.fog = new THREE.Fog(0xe8ede9, 3500, 9000);
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0xb1bcad, 2.7));
    const sun = new THREE.DirectionalLight(0xffffff, 2.4);
    sun.position.set(-1000, 1800, 700);
    this.scene.add(sun);
    const plane = new THREE.Mesh(
      new THREE.PlaneGeometry(12000, 12000),
      new THREE.MeshStandardMaterial({ color: 0xe7ece5, roughness: 1 }),
    );
    plane.rotation.x = -Math.PI / 2;
    plane.position.y = -0.12;
    this.scene.add(plane);
    this.buildCity();
    this.scene.add(this.selected, this.diff);
    this.createRoadLabels();
    const carGeo = new THREE.BoxGeometry(1.85, 1.5, 4.7);
    carGeo.translate(0, 0.95, 0);
    this.vehicles = new THREE.InstancedMesh(
      carGeo,
      new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.6 }),
      this.capacity,
    );
    this.vehicles.count = 0;
    this.vehicles.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    this.vehicles.frustumCulled = false;
    this.vehicles.userData.kind = "vehicles";
    this.scene.add(this.vehicles);
    this.comparison = this.scene.clone(true);
    this.comparison.remove(
      this.comparison.children.find((v) => v.userData.kind === "vehicles")!,
    );
    this.otherVehicles = new THREE.InstancedMesh(
      carGeo,
      this.vehicles.material,
      this.capacity,
    );
    this.otherVehicles.count = 0;
    this.otherVehicles.frustumCulled = false;
    this.comparison.add(this.otherVehicles);
    this.observer = new ResizeObserver(() => this.resize());
    this.observer.observe(host);
    this.resize();
    this.downHandler = (e) => {
      this.pointerDown = [e.clientX, e.clientY];
    };
    this.clickHandler = (e) => {
      if (
        Math.hypot(
          e.clientX - this.pointerDown[0],
          e.clientY - this.pointerDown[1],
        ) > 5
      )
        return;
      this.pick(e);
    };
    this.renderer.domElement.addEventListener("pointerdown", this.downHandler);
    this.renderer.domElement.addEventListener("pointerup", this.clickHandler);
    this.renderer.setAnimationLoop(() => this.render());
  }
  private polygon(points: Point[], height: number, color: number) {
    if (points.length < 3) return null;
    const shape = new THREE.Shape(
      points.map(([x, y]) => new THREE.Vector2(x, -y)),
    );
    const geo = new THREE.ShapeGeometry(shape);
    geo.rotateX(-Math.PI / 2); // shape x,-north maps x,+north in world z; corrected below
    const positions = geo.getAttribute("position");
    for (let i = 0; i < positions.count; i++)
      positions.setZ(i, -positions.getZ(i));
    geo.computeVertexNormals();
    geo.deleteAttribute("uv");
    const mesh = new THREE.Mesh(
      geo,
      new THREE.MeshStandardMaterial({
        color,
        side: THREE.DoubleSide,
        roughness: 1,
      }),
    );
    mesh.position.y = height;
    return mesh;
  }
  private ribbon(points: Point[], width: number, height: number) {
    const p: number[] = [],
      idx: number[] = [];
    for (let i = 0; i < points.length; i++) {
      const prev = points[Math.max(0, i - 1)],
        next = points[Math.min(points.length - 1, i + 1)],
        dx = next[0] - prev[0],
        dy = next[1] - prev[1],
        len = Math.hypot(dx, dy) || 1,
        nx = ((-dy / len) * width) / 2,
        ny = ((dx / len) * width) / 2;
      p.push(
        points[i][0] + nx,
        height,
        -points[i][1] - ny,
        points[i][0] - nx,
        height,
        -points[i][1] + ny,
      );
      if (i < points.length - 1) {
        let n = i * 2;
        idx.push(n, n + 1, n + 2, n + 1, n + 3, n + 2);
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(p, 3));
    g.setIndex(idx);
    g.computeVertexNormals();
    return g;
  }
  private boundary(points: Point[], color: number, dashed = false) {
    const verts = [...points, points[0]].map(
      ([x, y]) => new THREE.Vector3(x, 1.5, -y),
    );
    const g = new THREE.BufferGeometry().setFromPoints(verts);
    const line = new THREE.Line(
      g,
      dashed
        ? new THREE.LineDashedMaterial({ color, dashSize: 12, gapSize: 8 })
        : new THREE.LineBasicMaterial({ color }),
    );
    line.computeLineDistances();
    this.scene.add(line);
  }
  private buildCity() {
    const geometries: THREE.BufferGeometry[] = [];
    const roadMaterial = new THREE.MeshStandardMaterial({
      color: 0x7c8886,
      roughness: 1,
      side: THREE.DoubleSide,
    });
    const internal = new THREE.MeshStandardMaterial({
      color: 0x88928f,
      roughness: 1,
      side: THREE.DoubleSide,
    });
    const roads: THREE.BufferGeometry[] = [],
      junctions: THREE.BufferGeometry[] = [],
      closed: THREE.BufferGeometry[] = [],
      markings: number[] = [];
    for (const lane of this.network.lanes) {
      if (lane.shape.length < 2) continue;
      const elevation = lane.display_elevation ?? 0,
        geometry = this.ribbon(lane.shape, lane.width || 3.2, elevation + 0.08);
      const mesh = new THREE.Mesh(geometry, roadMaterial);
      mesh.userData = { kind: "lane", id: lane.id, data: lane };
      mesh.updateMatrixWorld();
      this.picker.push(mesh);
      (lane.closed_passenger
        ? closed
        : lane.id.startsWith(":")
          ? junctions
          : roads
      ).push(geometry);
      if (!lane.id.startsWith(":")) {
        for (let j = 0; j < lane.shape.length - 1; j++) {
          const a = lane.shape[j],
            b = lane.shape[j + 1],
            length = Math.hypot(b[0] - a[0], b[1] - a[1]);
          for (let k = 0; k < length; k += 9) {
            const end = Math.min(k + 3, length);
            markings.push(
              a[0] + ((b[0] - a[0]) * k) / length,
              elevation + 0.14,
              -a[1] - ((b[1] - a[1]) * k) / length,
              a[0] + ((b[0] - a[0]) * end) / length,
              elevation + 0.14,
              -a[1] - ((b[1] - a[1]) * end) / length,
            );
          }
        }
      }
    }
    for (const j of this.network.junctions ?? []) {
      if (j.shape?.length) {
        const mesh = this.polygon(j.shape, 0.04, 0x88928f);
        if (mesh) {
          mesh.userData = { kind: "junction", id: j.id, data: j };
          mesh.updateMatrixWorld();
          this.picker.push(mesh);
          const geometry = mesh.geometry.clone();
          geometry.translate(0, 0.04, 0);
          junctions.push(geometry);
        }
      }
    }
    for (const [list, material] of [
      [roads, roadMaterial],
      [junctions, internal],
      [
        closed,
        new THREE.MeshStandardMaterial({
          color: 0xb69374,
          roughness: 1,
          side: THREE.DoubleSide,
        }),
      ],
    ] as [THREE.BufferGeometry[], THREE.Material][]) {
      if (list.length) {
        const merged = mergeGeometries(list, false);
        if (merged) this.roads.add(new THREE.Mesh(merged, material));
      }
    }
    if (markings.length) {
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.Float32BufferAttribute(markings, 3));
      this.roads.add(
        new THREE.LineSegments(
          g,
          new THREE.LineBasicMaterial({
            color: 0xd3dace,
            transparent: true,
            opacity: 0.6,
          }),
        ),
      );
    }
    this.scene.add(this.roads);

    for (const b of this.network.buildings ?? []) {
      if (b.polygon.length < 3) continue;
      const shape = new THREE.Shape(
        b.polygon.map(([x, y]) => new THREE.Vector2(x, y)),
      );
      const geo = new THREE.ExtrudeGeometry(shape, {
        depth: Math.max(2, b.height || 8),
        bevelEnabled: false,
      });
      geo.rotateX(-Math.PI / 2);
      geometries.push(geo);
    }
    if (geometries.length) {
      const merged = mergeGeometries(geometries, false);
      if (merged) {
        const mesh = new THREE.Mesh(
          merged,
          new THREE.MeshStandardMaterial({ color: 0xd0d7ce, roughness: 1 }),
        );
        this.buildings.add(mesh);
        const edges = new THREE.LineSegments(
          new THREE.EdgesGeometry(merged, 35),
          new THREE.LineBasicMaterial({
            color: 0xbac4b9,
            transparent: true,
            opacity: 0.4,
          }),
        );
        this.buildings.add(edges);
      }
      for (const g of geometries) g.dispose();
    }
    this.buildings.name = "buildings";
    this.scene.add(this.buildings);
    if (this.network.core_polygon?.length)
      this.boundary(this.network.core_polygon, 0x378d87, true);
    if (this.network.simulation_polygon?.length)
      this.boundary(this.network.simulation_polygon, 0x99aaa0);
    for (const gate of this.network.gates ?? []) {
      const mesh = new THREE.Mesh(
        new THREE.CylinderGeometry(6, 6, 2, 16),
        new THREE.MeshBasicMaterial({ color: 0x238f8c }),
      );
      mesh.position.set(...localToWorld(gate.position[0], gate.position[1], 2));
      mesh.userData = { kind: "gate", id: gate.id, data: gate };
      this.scene.add(mesh);
      this.picker.push(mesh);
    }
  }
  private createRoadLabels() {
    const names = new Set<string>();
    const edges = [...(this.network.edges ?? [])]
      .filter((e) => e.name && e.shape.length > 1)
      .sort((a, b) => {
        const av = a.shape[Math.floor(a.shape.length / 2)],
          bv = b.shape[Math.floor(b.shape.length / 2)];
        return Math.hypot(...av) - Math.hypot(...bv);
      });
    for (const edge of edges) {
      if (names.has(edge.name) || names.size >= 14) continue;
      const p = edge.shape[Math.floor(edge.shape.length / 2)];
      if (Math.hypot(...p) > 1150) continue;
      names.add(edge.name);
      const element = document.createElement("span");
      element.className = "road-label";
      element.textContent = edge.name;
      this.host.append(element);
      this.roadLabels.push({
        element,
        position: new THREE.Vector3(
          p[0],
          (edge.display_elevation ?? 0) + 4,
          -p[1],
        ),
      });
    }
  }
  private resize() {
    const w = this.host.clientWidth,
      h = this.host.clientHeight;
    this.renderer.setSize(w, h);
    this.camera.aspect = (this.split ? w / 2 : w) / h;
    this.camera.updateProjectionMatrix();
  }
  setComparison(split: boolean) {
    this.split = split;
    this.resize();
  }
  setBuildings(visible: boolean) {
    this.buildings.visible = visible;
    const group = this.comparison.getObjectByName("buildings");
    if (group) group.visible = visible;
  }
  setCompareNetwork(network: Network) {
    if (
      (this.otherNetwork?.network_hash ?? this.network.network_hash) ===
      network.network_hash
    )
      return;
    if (this.separateComparison) {
      this.comparison.traverse((o) => {
        const m = o as THREE.Mesh;
        if (m === this.otherVehicles) return;
        m.geometry?.dispose();
        for (const material of m.material
          ? Array.isArray(m.material)
            ? m.material
            : [m.material]
          : [])
          material.dispose();
      });
      for (const o of this.otherPicker ?? [])
        (o as THREE.Mesh).geometry.dispose();
    }
    const saved = {
      scene: this.scene,
      network: this.network,
      buildings: this.buildings,
      roads: this.roads,
      picker: this.picker,
    };
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xe8ede9);
    this.scene.fog = new THREE.Fog(0xe8ede9, 3500, 9000);
    this.scene.add(new THREE.HemisphereLight(0xffffff, 0xb1bcad, 2.7));
    const sun = new THREE.DirectionalLight(0xffffff, 2.4);
    sun.position.set(-1000, 1800, 700);
    this.scene.add(sun);
    const plane = new THREE.Mesh(
      new THREE.PlaneGeometry(12000, 12000),
      new THREE.MeshStandardMaterial({ color: 0xe7ece5, roughness: 1 }),
    );
    plane.rotation.x = -Math.PI / 2;
    plane.position.y = -0.12;
    this.scene.add(plane);
    this.network = network;
    this.buildings = new THREE.Group();
    this.roads = new THREE.Group();
    this.picker = [];
    this.buildCity();
    this.otherBuildings = this.buildings;
    this.otherPicker = this.picker;
    this.otherNetwork = network;
    this.comparison = this.scene;
    this.comparison.add(this.otherVehicles);
    this.separateComparison = true;
    this.scene = saved.scene;
    this.network = saved.network;
    this.buildings = saved.buildings;
    this.roads = saved.roads;
    this.picker = saved.picker;
    this.otherBuildings.visible = this.buildings.visible;
  }
  setView(mode: "core" | "full" | "top") {
    const d = mode === "full" ? 2400 : 1150;
    this.controls.target.set(0, 0, 0);
    this.camera.position.set(
      mode === "top" ? 0 : d * 0.8,
      mode === "top" ? 1900 : d,
      mode === "top" ? 0.01 : d * 0.85,
    );
    this.controls.update();
  }
  setVehicles(data: Vehicle[], other = false) {
    if (data.length > this.capacity)
      throw new Error(
        `轨迹帧超过 ${this.capacity} 辆的配置显示容量，未截断显示`,
      );
    const mesh = other ? this.otherVehicles : this.vehicles;
    if (other) this.otherData = data;
    else this.vehicleData = data;
    mesh.count = data.length;
    const color = new THREE.Color();
    for (let i = 0; i < data.length; i++) {
      const v = data[i];
      this.dummy.position.set(
        v.x,
        (other ? (this.otherNetwork ?? this.network) : this.network).lanes[
          v.lane
        ]?.display_elevation ?? 0,
        -v.y,
      );
      this.dummy.rotation.set(0, (-v.angle * Math.PI) / 180, 0);
      this.dummy.scale.set(
        v.flags & 1 ? 1.35 : 1,
        v.flags & 1 ? 1.7 : 1,
        v.flags & 1 ? 12 / 4.7 : 1,
      );
      this.dummy.updateMatrix();
      mesh.setMatrixAt(i, this.dummy.matrix);
      color.set(v.speed < 1 ? 0xcc7455 : v.speed < 5 ? 0xccad63 : 0x2e9696);
      mesh.setColorAt(i, color);
    }
    mesh.instanceMatrix.needsUpdate = true;
    mesh.boundingSphere = null;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  }
  setDifference(enabled: boolean, a: Vehicle[] = [], b: Vehicle[] = []) {
    while (this.diff.children.length) {
      const obj = this.diff.children.pop() as THREE.Mesh;
      obj.geometry.dispose();
      (obj.material as THREE.Material).dispose();
    }
    if (!enabled) return;
    const avg = (vs: Vehicle[]) => {
      const map = new Map<number, number[]>();
      for (const v of vs) {
        const arr = map.get(v.lane) ?? [];
        arr.push(v.speed);
        map.set(v.lane, arr);
      }
      return new Map(
        [...map].map(([k, v]) => [k, v.reduce((a, b) => a + b, 0) / v.length]),
      );
    };
    const aa = avg(a),
      bb = avg(b);
    for (const [i, v] of aa) {
      if (!bb.has(i) || !this.network.lanes[i]) continue;
      const delta = bb.get(i)! - v;
      const lane = this.network.lanes[i];
      const mesh = new THREE.Mesh(
        this.ribbon(
          lane.shape,
          lane.width + 1,
          (lane.display_elevation ?? 0) + 0.24,
        ),
        new THREE.MeshBasicMaterial({
          color: delta > 1 ? 0x159783 : delta < -1 ? 0xcf7358 : 0xb9bdad,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.78,
        }),
      );
      this.diff.add(mesh);
    }
  }
  private pick(e: PointerEvent) {
    const rect = this.renderer.domElement.getBoundingClientRect(),
      right = this.split && e.clientX - rect.left > rect.width / 2,
      w = this.split ? rect.width / 2 : rect.width,
      x = ((e.clientX - rect.left - (right ? w : 0)) / w) * 2 - 1,
      y = (-(e.clientY - rect.top) / rect.height) * 2 + 1;
    this.raycaster.setFromCamera(new THREE.Vector2(x, y), this.camera);
    const hits = this.raycaster.intersectObjects(
      [
        right ? this.otherVehicles : this.vehicles,
        ...(right ? (this.otherPicker ?? this.picker) : this.picker),
      ],
      false,
    );
    if (!hits.length) return;
    const hit = hits[0];
    if (hit.instanceId !== undefined) {
      const v = (right ? this.otherData : this.vehicleData)[hit.instanceId];
      this.onSelect({
        kind: "vehicle",
        id: String(v.id),
        data: v,
        source: right ? "B" : "A",
      });
      return;
    }
    const data = hit.object.userData as Selection;
    this.onSelect({ ...data, source: right ? "B" : "A" });
    this.highlight(
      data.kind === "lane" ? (data.data as { shape: Point[] }).shape : [],
    );
  }
  highlight(points: Point[]) {
    while (this.selected.children.length) {
      const obj = this.selected.children.pop() as THREE.Mesh;
      obj.geometry.dispose();
      (obj.material as THREE.Material).dispose();
    }
    if (points.length > 1)
      this.selected.add(
        new THREE.Mesh(
          this.ribbon(points, 5, 0.3),
          new THREE.MeshBasicMaterial({
            color: 0xeec974,
            side: THREE.DoubleSide,
          }),
        ),
      );
  }
  render() {
    const now = performance.now();
    this.frameTimes.push(now - this.last);
    if (this.frameTimes.length > 180) this.frameTimes.shift();
    this.last = now;
    this.controls.update();
    if (!this.compass) this.compass = document.querySelector("#north-arrow");
    if (this.compass)
      this.compass.style.transform = `rotate(${(-this.controls.getAzimuthalAngle() * 180) / Math.PI}deg)`;
    const w = this.host.clientWidth,
      h = this.host.clientHeight;
    this.renderer.setScissorTest(this.split);
    if (this.split) {
      this.renderer.setViewport(0, 0, w / 2, h);
      this.renderer.setScissor(0, 0, w / 2, h);
      this.renderer.render(this.scene, this.camera);
      this.renderer.setViewport(w / 2, 0, w / 2, h);
      this.renderer.setScissor(w / 2, 0, w / 2, h);
      this.renderer.render(this.comparison, this.camera);
    } else {
      this.renderer.setViewport(0, 0, w, h);
      this.renderer.render(this.scene, this.camera);
    }
    for (const label of this.roadLabels) {
      const p = label.position.clone().project(this.camera);
      label.element.style.display =
        this.split || p.z > 1 || Math.abs(p.x) > 0.95 || Math.abs(p.y) > 0.8
          ? "none"
          : "block";
      label.element.style.left = `${((p.x + 1) * w) / 2}px`;
      label.element.style.top = `${((1 - p.y) * h) / 2}px`;
    }
    const scale = document.querySelector<HTMLElement>("#scale-line");
    if (scale) {
      const distance = this.camera.position.distanceTo(this.controls.target),
        width =
          (100 * h) /
          (2 *
            distance *
            Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2)));
      scale.style.width = `${Math.max(5, width)}px`;
    }
  }
  stats() {
    const sorted = [...this.frameTimes].sort((a, b) => a - b);
    return {
      fps: Math.round(
        1000 /
          (this.frameTimes.reduce((a, b) => a + b, 0) / this.frameTimes.length),
      ),
      p95: sorted[Math.floor(sorted.length * 0.95)] ?? 0,
      calls: this.renderer.info.render.calls,
      triangles: this.renderer.info.render.triangles,
    };
  }
  dispose() {
    if (this.separateComparison) {
      this.comparison.traverse((o) => {
        const m = o as THREE.Mesh;
        if (m === this.otherVehicles) return;
        m.geometry?.dispose();
        for (const material of m.material
          ? Array.isArray(m.material)
            ? m.material
            : [m.material]
          : [])
          material.dispose();
      });
      for (const o of this.otherPicker ?? [])
        (o as THREE.Mesh).geometry.dispose();
    }
    this.renderer.setAnimationLoop(null);
    for (const label of this.roadLabels) label.element.remove();
    this.observer.disconnect();
    this.controls.dispose();
    this.scene.traverse((o) => {
      const m = o as THREE.Mesh;
      if (m.geometry) m.geometry.dispose();
      if (m.material) {
        for (const material of Array.isArray(m.material)
          ? m.material
          : [m.material])
          material.dispose();
      }
    });
    this.renderer.domElement.removeEventListener(
      "pointerdown",
      this.downHandler,
    );
    this.renderer.domElement.removeEventListener(
      "pointerup",
      this.clickHandler,
    );
    for (const o of this.picker) {
      const m = o as THREE.Mesh;
      m.geometry.dispose();
    }
    this.otherVehicles.dispose();
    this.vehicles.dispose();
    this.renderer.dispose();
    this.renderer.domElement.remove();
  }
}
