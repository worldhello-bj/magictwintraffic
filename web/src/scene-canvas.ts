/** Real-data, north-up Canvas fallback when the device cannot create WebGL. */
import type { Network, Point, Vehicle } from "./types";
import type { Selection } from "./scene";
export class CitySceneCanvas {
  readonly renderMode = "Canvas 2D";
  private canvas = document.createElement("canvas");
  private context: CanvasRenderingContext2D;
  private cache = document.createElement("canvas");
  private cacheContext: CanvasRenderingContext2D;
  private observer: ResizeObserver;
  private width = 1;
  private height = 1;
  private scale = 1;
  private center: Point = [0, 0];
  private split = false;
  private buildings = true;
  private otherNetwork: Network;
  private vehicles: Vehicle[] = [];
  private otherVehicles: Vehicle[] = [];
  private difference = false;
  private selected: Point[] = [];
  private disposed = false;
  private renderCount = 0;
  private lastRender = performance.now();
  private intervals: number[] = [];
  private drag:
    | { x: number; y: number; cx: number; cy: number; moved: boolean }
    | undefined;
  constructor(
    private host: HTMLElement,
    public network: Network,
    private onSelect: (s: Selection) => void,
  ) {
    this.context = this.canvas.getContext("2d")!;
    this.cacheContext = this.cache.getContext("2d")!;
    if (!this.context || !this.cacheContext)
      throw new Error(
        "此浏览器同时缺少 WebGL 与 Canvas 2D；指标和回放数据仍可读取",
      );
    this.otherNetwork = network;
    this.canvas.setAttribute(
      "aria-label",
      "真实路网二维兼容视图，可拖动平移、滚轮缩放，点击道路或车辆检查",
    );
    this.canvas.className = "fallback-canvas";
    this.host.append(this.canvas);
    this.canvas.addEventListener("pointerdown", this.down);
    this.canvas.addEventListener("pointermove", this.move);
    this.canvas.addEventListener("pointerup", this.up);
    this.canvas.addEventListener("pointercancel", this.cancel);
    this.canvas.addEventListener("wheel", this.wheel, { passive: false });
    this.observer = new ResizeObserver(() => this.resize());
    this.observer.observe(host);
    this.resize();
    this.setView("core");
  }
  private down = (e: PointerEvent) => {
    this.drag = {
      x: e.clientX,
      y: e.clientY,
      cx: this.center[0],
      cy: this.center[1],
      moved: false,
    };
    this.canvas.setPointerCapture?.(e.pointerId);
  };
  private move = (e: PointerEvent) => {
    if (!this.drag) return;
    const dx = e.clientX - this.drag.x,
      dy = e.clientY - this.drag.y;
    if (Math.hypot(dx, dy) > 4) this.drag.moved = true;
    this.center = [
      this.drag.cx - dx / this.scale,
      this.drag.cy + dy / this.scale,
    ];
    this.redrawStatic();
  };
  private up = (e: PointerEvent) => {
    if (this.drag && !this.drag.moved) this.pick(e);
    this.drag = undefined;
    this.canvas.releasePointerCapture?.(e.pointerId);
  };
  private cancel = () => {
    this.drag = undefined;
  };
  private wheel = (e: WheelEvent) => {
    e.preventDefault();
    this.scale = Math.min(
      8,
      Math.max(0.04, this.scale * Math.exp(-e.deltaY * 0.001)),
    );
    this.redrawStatic();
  };
  private resize() {
    this.width = Math.max(1, this.host.clientWidth);
    this.height = Math.max(1, this.host.clientHeight);
    const dpr = Math.min(devicePixelRatio || 1, 2);
    for (const canvas of [this.canvas, this.cache]) {
      canvas.width = Math.round(this.width * dpr);
      canvas.height = Math.round(this.height * dpr);
      canvas.style.width = this.width + "px";
      canvas.style.height = this.height + "px";
    }
    this.context.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.cacheContext.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.redrawStatic();
  }
  private paneWidth() {
    return this.width / (this.split ? 2 : 1);
  }
  private point(p: Point, offset = 0): Point {
    return [
      offset + this.paneWidth() / 2 + (p[0] - this.center[0]) * this.scale,
      this.height * 0.56 - (p[1] - this.center[1]) * this.scale,
    ];
  }
  private path(
    ctx: CanvasRenderingContext2D,
    points: Point[],
    offset = 0,
    closed = false,
  ) {
    ctx.beginPath();
    points.forEach((p, i) => {
      const [x, y] = this.point(p, offset);
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    });
    if (closed) ctx.closePath();
  }
  private staticPane(
    ctx: CanvasRenderingContext2D,
    n: Network,
    offset: number,
  ) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(offset, 0, this.paneWidth(), this.height);
    ctx.clip();
    if (this.buildings) {
      ctx.fillStyle = "#d1d9cd";
      ctx.strokeStyle = "#becbb9";
      ctx.lineWidth = 0.7;
      for (const b of n.buildings) {
        if (b.polygon.length < 3) continue;
        this.path(ctx, b.polygon, offset, true);
        ctx.fill();
        ctx.stroke();
      }
    }
    ctx.fillStyle = "#939d97";
    for (const j of n.junctions) {
      if (j.shape?.length) {
        this.path(ctx, j.shape, offset, true);
        ctx.fill();
      }
    }
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    const lanes = [...n.lanes].sort(
      (a, b) => (a.display_elevation ?? 0) - (b.display_elevation ?? 0),
    );
    for (const lane of lanes) {
      if (lane.shape.length < 2) continue;
      this.path(ctx, lane.shape, offset);
      ctx.strokeStyle = lane.closed_passenger
        ? "#b29370"
        : (lane.display_elevation ?? 0) > 0
          ? "#6a817b"
          : "#8b9790";
      ctx.lineWidth = Math.max(0.55, lane.width * this.scale);
      ctx.stroke();
    }
    for (const [polygon, color, dash] of [
      [n.simulation_polygon, "#a1b69f", []],
      [n.core_polygon, "#398c83", [7, 5]],
    ] as [Point[], string, number[]][]) {
      if (!polygon.length) continue;
      this.path(ctx, polygon, offset, true);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.3;
      ctx.setLineDash(dash);
      ctx.stroke();
    }
    ctx.setLineDash([]);
    for (const gate of n.gates) {
      const [x, y] = this.point(gate.position, offset);
      ctx.beginPath();
      ctx.arc(x, y, 3.2, 0, Math.PI * 2);
      ctx.fillStyle = "#388f85";
      ctx.fill();
    }
    const names = new Set<string>(),
      labels: [number, number][] = [];
    ctx.font = '12px -apple-system, "Microsoft YaHei", sans-serif';
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (const edge of n.edges ?? []) {
      if (!edge.name || !edge.shape.length || names.has(edge.name)) continue;
      const [x, y] = this.point(
        edge.shape[Math.floor(edge.shape.length / 2)],
        offset,
      );
      if (
        x < offset + 45 ||
        x > offset + this.paneWidth() - 45 ||
        y < 180 ||
        y > this.height - 85 ||
        labels.some(([a, b]) => Math.hypot(x - a, y - b) < 68)
      )
        continue;
      names.add(edge.name);
      labels.push([x, y]);
      ctx.lineWidth = 3;
      ctx.strokeStyle = "#edf2e7";
      ctx.strokeText(edge.name, x, y);
      ctx.fillStyle = "#536f5c";
      ctx.fillText(edge.name, x, y);
      if (names.size >= 18) break;
    }
    ctx.restore();
  }
  private redrawStatic() {
    if (this.disposed) return;
    const c = this.cacheContext;
    c.clearRect(0, 0, this.width, this.height);
    c.fillStyle = "#e8ede5";
    c.fillRect(0, 0, this.width, this.height);
    this.staticPane(c, this.network, 0);
    if (this.split) this.staticPane(c, this.otherNetwork, this.width / 2);
    const scale = document.querySelector<HTMLElement>("#scale-line");
    if (scale) scale.style.width = 100 * this.scale + "px";
    const north = document.querySelector<HTMLElement>("#north-arrow");
    if (north) north.style.transform = "none";
    this.draw();
  }
  private vehiclePane(
    ctx: CanvasRenderingContext2D,
    vehicles: Vehicle[],
    offset: number,
  ) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(offset, 0, this.paneWidth(), this.height);
    ctx.clip();
    for (const v of vehicles) {
      const [x, y] = this.point([v.x, v.y], offset);
      if (
        x < offset - 10 ||
        x > offset + this.paneWidth() + 10 ||
        y < 0 ||
        y > this.height
      )
        continue;
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate((v.angle * Math.PI) / 180);
      ctx.fillStyle =
        v.speed < 1 ? "#c96e50" : v.speed < 5 ? "#c6a158" : "#208e87";
      const length = Math.max(4, (v.flags & 1 ? 12 : 4.7) * this.scale),
        width = Math.max(2.2, (v.flags & 1 ? 2.5 : 1.8) * this.scale);
      ctx.fillRect(-width / 2, -length / 2, width, length);
      ctx.restore();
    }
    ctx.restore();
  }
  private draw() {
    if (this.disposed) return;
    const c = this.context;
    c.clearRect(0, 0, this.width, this.height);
    c.drawImage(this.cache, 0, 0, this.width, this.height);
    if (this.difference) {
      const mean = (vs: Vehicle[]) => {
          const m = new Map<number, [number, number]>();
          for (const v of vs) {
            const a = m.get(v.lane) ?? [0, 0];
            a[0] += v.speed;
            a[1]++;
            m.set(v.lane, a);
          }
          return m;
        },
        a = mean(this.vehicles),
        b = mean(this.otherVehicles);
      for (const [i, av] of a) {
        const bv = b.get(i),
          lane = this.network.lanes[i];
        if (!bv || !lane) continue;
        const d = bv[0] / bv[1] - av[0] / av[1];
        this.path(c, lane.shape);
        c.strokeStyle = d > 1 ? "#159783" : d < -1 ? "#cf7358" : "#b9bdad";
        c.lineWidth = Math.max(2, (lane.width + 1) * this.scale);
        c.stroke();
      }
    }
    this.vehiclePane(c, this.vehicles, 0);
    if (this.split) this.vehiclePane(c, this.otherVehicles, this.width / 2);
    if (this.selected.length) {
      this.path(c, this.selected);
      c.strokeStyle = "#ddb447";
      c.lineWidth = 3;
      c.stroke();
    }
    const now = performance.now();
    this.intervals.push(now - this.lastRender);
    if (this.intervals.length > 100) this.intervals.shift();
    this.lastRender = now;
    this.renderCount++;
  }
  private pick(e: PointerEvent) {
    const rect = this.canvas.getBoundingClientRect(),
      x = e.clientX - rect.left,
      y = e.clientY - rect.top,
      right = this.split && x > this.width / 2,
      offset = right ? this.width / 2 : 0,
      n = right ? this.otherNetwork : this.network,
      vehicles = right ? this.otherVehicles : this.vehicles,
      source = right ? "B" : "A";
    for (const v of vehicles) {
      const [px, py] = this.point([v.x, v.y], offset);
      if (Math.hypot(px - x, py - y) < 7) {
        this.onSelect({ kind: "vehicle", id: String(v.id), data: v, source });
        return;
      }
    }
    for (const gate of n.gates) {
      const [px, py] = this.point(gate.position, offset);
      if (Math.hypot(px - x, py - y) < 7) {
        this.onSelect({ kind: "gate", id: gate.id, data: gate, source });
        return;
      }
    }
    let best: Network["lanes"][number] | undefined,
      distance = 7;
    for (const lane of n.lanes)
      for (let i = 1; i < lane.shape.length; i++) {
        const [a, b] = this.point(lane.shape[i - 1], offset),
          [c, d] = this.point(lane.shape[i], offset),
          dx = c - a,
          dy = d - b,
          t = Math.max(
            0,
            Math.min(
              1,
              ((x - a) * dx + (y - b) * dy) / (dx * dx + dy * dy || 1),
            ),
          ),
          dist = Math.hypot(x - a - t * dx, y - b - t * dy);
        if (dist < distance) {
          distance = dist;
          best = lane;
        }
      }
    if (best) {
      this.selected = right ? [] : best.shape;
      this.draw();
      this.onSelect({ kind: "lane", id: best.id, data: best, source });
      return;
    }
    for (const j of n.junctions) {
      const [px, py] = this.point(j.position, offset);
      if (Math.hypot(px - x, py - y) < 10) {
        this.onSelect({ kind: "junction", id: j.id, data: j, source });
        return;
      }
    }
  }
  setVehicles(data: Vehicle[], other = false) {
    if (other) this.otherVehicles = data;
    else this.vehicles = data;
    this.draw();
  }
  setCompareNetwork(n: Network) {
    this.otherNetwork = n;
    this.redrawStatic();
  }
  setComparison(value: boolean) {
    this.split = value;
    this.redrawStatic();
  }
  setBuildings(value: boolean) {
    this.buildings = value;
    this.redrawStatic();
  }
  setView(mode: "core" | "full" | "top") {
    this.center = [0, 0];
    let size = 1250;
    if (mode === "full") {
      const p = this.network.simulation_polygon;
      const xs = p.map((v) => v[0]),
        ys = p.map((v) => v[1]);
      if (p.length) {
        this.center = [
          (Math.min(...xs) + Math.max(...xs)) / 2,
          (Math.min(...ys) + Math.max(...ys)) / 2,
        ];
        size =
          Math.max(
            Math.max(...xs) - Math.min(...xs),
            Math.max(...ys) - Math.min(...ys),
          ) * 1.1;
      } else size = 2500;
    }
    this.scale = Math.max(
      0.04,
      Math.min(this.paneWidth() / size, (this.height - 150) / size),
    );
    this.redrawStatic();
  }
  setDifference(
    value: boolean,
    a: Vehicle[] = this.vehicles,
    b: Vehicle[] = this.otherVehicles,
  ) {
    this.difference = value;
    if (value) {
      this.vehicles = a;
      this.otherVehicles = b;
    }
    this.draw();
  }
  highlight(points: Point[]) {
    this.selected = points;
    this.draw();
  }
  stats() {
    return {
      fps: 0,
      calls: 0,
      triangles: 0,
      mode: "Canvas 2D",
      renderCount: this.renderCount,
    };
  }
  dispose() {
    this.disposed = true;
    this.observer.disconnect();
    this.canvas.removeEventListener("pointerdown", this.down);
    this.canvas.removeEventListener("pointermove", this.move);
    this.canvas.removeEventListener("pointerup", this.up);
    this.canvas.removeEventListener("pointercancel", this.cancel);
    this.canvas.removeEventListener("wheel", this.wheel);
    this.canvas.remove();
    this.cache.width = 0;
    this.cache.height = 0;
  }
}
