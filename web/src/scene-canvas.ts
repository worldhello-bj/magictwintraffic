/** Real-data, rotatable Canvas fallback when the device cannot create WebGL. */
import type { Network, Point, Vehicle } from "./types";
import { emptyTraffic, type TrafficOverlay } from "./traffic-state";
import type { Selection } from "./scene";
import { paneCoordinates, polygonBounds } from "./view-geometry";
export class CitySceneCanvas {
  readonly renderMode = "Canvas 2D";
  private traffic = emptyTraffic();
  private otherTraffic = emptyTraffic();
  private canvas = document.createElement("canvas");
  private context: CanvasRenderingContext2D;
  private cache = document.createElement("canvas");
  private cacheContext: CanvasRenderingContext2D;
  private observer: ResizeObserver;
  private width = 1;
  private height = 1;
  private scale = 1;
  private rotation = 0;
  private center: Point = [0, 0];
  private split = false;
  private viewMode: "core" | "full" | "top" = "core";
  private pivot: Point | undefined;
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
    | {
        x: number;
        y: number;
        cx: number;
        cy: number;
        angle: number;
        mode: "rotate" | "pan";
        moved: boolean;
        button: number;
      }
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
      "真实路网二维兼容视图，左键拖动绕中心旋转、右键或Shift左键平移、滚轮缩放，中键设置旋转中心，点击道路或车辆检查",
    );
    this.canvas.className = "fallback-canvas";
    this.host.append(this.canvas);
    this.canvas.addEventListener("pointerdown", this.down);
    this.canvas.addEventListener("pointermove", this.move);
    this.canvas.addEventListener("pointerup", this.up);
    this.canvas.addEventListener("pointercancel", this.cancel);
    this.canvas.addEventListener("wheel", this.wheel, { passive: false });
    this.canvas.addEventListener("auxclick", this.preventMiddle);
    this.canvas.addEventListener("contextmenu", this.preventContext);
    this.observer = new ResizeObserver(() => this.resize());
    this.observer.observe(host);
    this.resize();
    this.setView("core");
  }
  private preventMiddle = (e: MouseEvent) => {
    if (e.button === 1) e.preventDefault();
  };
  private preventContext = (e: MouseEvent) => e.preventDefault();
  private down = (e: PointerEvent) => {
    if (e.button === 1) {
      e.preventDefault();
      const pane = paneCoordinates(
        e.clientX,
        e.clientY,
        this.canvas.getBoundingClientRect(),
        this.split,
      );
      this.center = this.worldPoint(pane.x, pane.y);
      this.pivot = [...this.center];
      this.drag = undefined;
      this.redrawStatic();
      return;
    }
    if (e.button !== 0 && e.button !== 2) return;
    e.preventDefault();
    this.drag = {
      x: e.clientX,
      y: e.clientY,
      cx: this.center[0],
      cy: this.center[1],
      angle: this.rotation,
      mode: e.button === 2 || e.shiftKey ? "pan" : "rotate",
      button: e.button,
      moved: false,
    };
    this.canvas.setPointerCapture?.(e.pointerId);
  };
  private move = (e: PointerEvent) => {
    if (!this.drag) return;
    const dx = e.clientX - this.drag.x,
      dy = e.clientY - this.drag.y;
    if (Math.hypot(dx, dy) > 4) this.drag.moved = true;
    if (this.drag.mode === "rotate") {
      // The shared center is the world point picked by middle click. Keep it
      // fixed while applying the same ground-plane rotation in both panes.
      this.rotation = this.drag.angle + dx * 0.006;
    } else {
      const c = Math.cos(this.drag.angle),
        s = Math.sin(this.drag.angle);
      this.center = [
        this.drag.cx - (dx * c + dy * s) / this.scale,
        this.drag.cy - (dx * s - dy * c) / this.scale,
      ];
      if (this.pivot) this.pivot = [...this.center];
    }
    this.redrawStatic();
  };
  private up = (e: PointerEvent) => {
    if (this.drag && !this.drag.moved && this.drag.button === 0) this.pick(e);
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
  private worldPoint(x: number, y: number): Point {
    const sx = (x - this.paneWidth() / 2) / this.scale;
    const sy = (y - this.height * 0.56) / this.scale;
    const c = Math.cos(this.rotation),
      s = Math.sin(this.rotation);
    return [this.center[0] + sx * c + sy * s, this.center[1] + sx * s - sy * c];
  }
  private point(p: Point, offset = 0): Point {
    const dx = p[0] - this.center[0],
      dy = p[1] - this.center[1];
    const c = Math.cos(this.rotation),
      s = Math.sin(this.rotation);
    return [
      offset + this.paneWidth() / 2 + (dx * c + dy * s) * this.scale,
      this.height * 0.56 + (dx * s - dy * c) * this.scale,
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
      [n.simulation_polygon, "#b17b36", []],
      [n.core_polygon, "#187e78", [9, 5]],
    ] as [Point[], string, number[]][]) {
      if (!polygon.length) continue;
      this.path(ctx, polygon, offset, true);
      ctx.strokeStyle = color;
      ctx.lineWidth = 5;
      ctx.strokeStyle = "#f8faf2dd";
      ctx.setLineDash([]);
      ctx.stroke();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.2;
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
    if (north)
      north.style.transform = `rotate(${(this.rotation * 180) / Math.PI}deg)`;
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
      ctx.rotate((v.angle * Math.PI) / 180 + this.rotation);
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
    this.drawTraffic(c);
    if (this.split) this.drawTraffic(c, false, true);
    this.vehiclePane(c, this.vehicles, 0);
    if (this.split) this.vehiclePane(c, this.otherVehicles, this.width / 2);
    this.drawTraffic(c, true);
    if (this.split) this.drawTraffic(c, true, true);
    if (this.selected.length) {
      this.path(c, this.selected);
      c.strokeStyle = "#ddb447";
      c.lineWidth = 3;
      c.stroke();
    }
    if (this.pivot) {
      for (const offset of this.split ? [0, this.width / 2] : [0]) {
        const [x, y] = this.point(this.pivot, offset);
        c.save();
        c.beginPath();
        c.rect(offset, 0, this.paneWidth(), this.height);
        c.clip();
        c.beginPath();
        c.arc(x, y, 7, 0, Math.PI * 2);
        c.strokeStyle = "#295f63";
        c.lineWidth = 1.5;
        c.stroke();
        c.beginPath();
        c.moveTo(x - 11, y);
        c.lineTo(x + 11, y);
        c.moveTo(x, y - 11);
        c.lineTo(x, y + 11);
        c.stroke();
        c.restore();
      }
    }
    const now = performance.now();
    this.intervals.push(now - this.lastRender);
    if (this.intervals.length > 100) this.intervals.shift();
    this.lastRender = now;
    this.renderCount++;
  }
  setTraffic(traffic: TrafficOverlay, other = false) {
    if (other) this.otherTraffic = traffic;
    else this.traffic = traffic;
    this.draw();
  }
  private drawTraffic(
    c: CanvasRenderingContext2D,
    foreground = false,
    other = false,
  ) {
    const traffic = other ? this.otherTraffic : this.traffic,
      offset = other ? this.width / 2 : 0;
    c.save();
    c.beginPath();
    c.rect(offset, 0, this.paneWidth(), this.height);
    c.clip();
    for (const h of foreground ? [] : traffic.hotspots) {
      this.path(c, h.shape, offset);
      c.strokeStyle = "#df664b80";
      c.lineWidth = Math.min(20, 4 + Math.sqrt(h.stopped_vehicles) * 2);
      c.stroke();
    }
    for (const z of foreground ? traffic.zones : []) {
      const [x, y] = this.point(z.position, offset);
      c.fillStyle = "#fffdf3";
      c.strokeStyle = "#69549b";
      c.lineWidth = 1.5;
      c.beginPath();
      c.rect(x - 9, y - 7, 18, 14);
      c.fill();
      c.stroke();
      c.font = "bold 9px sans-serif";
      c.textAlign = "center";
      c.textBaseline = "middle";
      c.fillStyle = "#594084";
      c.fillText(z.parked === null ? "?" : String(z.parked), x, y);
    }
    for (const s of foreground ? traffic.signals : []) {
      const [x, y] = this.point(s.position, offset);
      c.beginPath();
      c.arc(x, y, 3.5, 0, Math.PI * 2);
      c.fillStyle = s.color;
      c.fill();
      c.lineWidth = 1.2;
      c.strokeStyle = "#243a34";
      c.stroke();
    }
    c.restore();
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
    {
      const traffic = right ? this.otherTraffic : this.traffic;
      for (const signal of traffic.signals) {
        const [px, py] = this.point(signal.position, offset);
        if (Math.hypot(px - x, py - y) < 6) {
          this.onSelect({
            kind: "signal",
            id: signal.id,
            data: signal,
            source,
          });
          return;
        }
      }
      for (const zone of traffic.zones) {
        const [px, py] = this.point(zone.position, offset);
        if (Math.abs(px - x) < 10 && Math.abs(py - y) < 8) {
          this.onSelect({ kind: "zone", id: zone.id, data: zone, source });
          return;
        }
      }
    }
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
    if (value === this.split) return;
    const previous = this.fitScale();
    this.split = value;
    this.scale *= this.fitScale() / previous;
    this.redrawStatic();
  }
  setBuildings(value: boolean) {
    this.buildings = value;
    this.redrawStatic();
  }
  private fitScale() {
    const bounds = polygonBounds(
      this.viewMode === "full"
        ? this.network.simulation_polygon
        : this.network.core_polygon,
    );
    return Math.max(
      0.004,
      Math.min(
        Math.max(1, this.paneWidth() - 48) / (bounds.width * 1.12),
        Math.max(1, this.height - 240) / (bounds.height * 1.12),
      ),
    );
  }
  setView(mode: "core" | "full" | "top") {
    this.viewMode = mode;
    const bounds = polygonBounds(
      mode === "full"
        ? this.network.simulation_polygon
        : this.network.core_polygon,
    );
    this.center = bounds.center;
    this.pivot = undefined;
    this.rotation = 0;
    this.scale = this.fitScale();
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
    this.canvas.removeEventListener("auxclick", this.preventMiddle);
    this.canvas.removeEventListener("contextmenu", this.preventContext);
    this.canvas.remove();
    this.cache.width = 0;
    this.cache.height = 0;
  }
}
