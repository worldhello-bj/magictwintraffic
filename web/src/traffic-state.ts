import type { Network, Point } from "./types";
export interface SignalEvent {
  time: number;
  tls: string;
  state: string;
  phase: number;
}
export interface SignalTopology {
  tls: string;
  position: Point | null;
  source: string;
  links: {
    index: number;
    incoming_lane: string;
    outgoing_lane: string;
    via_lane: string;
  }[];
}
export interface QueueSample {
  time: number;
  edges: { edge_id: string; stopped_vehicles: number }[];
  total_stopped: number;
  threshold_m_s: number;
}
export interface StockSample {
  time: number;
  parked_total: number;
  parked_by_zone: Record<string, number>;
  initial_parked_total: number;
  boundary_inserted: number;
  boundary_completed: number;
  inside: number;
  internal_insertion_waiting: number;
  boundary_insertion_waiting: number;
  conservation_residual: number;
}
export interface InternalZone {
  id: string;
  name: string;
  position: Point;
  initial_parked: number;
  building_count: number;
  access_edge: string;
  source: string;
}
export interface RecordedOD {
  origin: string;
  destination: string;
  origin_kind: string;
  destination_kind: string;
  interval_start: number;
  interval_end: number;
  trip_count: number;
  source: string;
}
export interface InternalZones {
  zones: InternalZone[];
  od_matrix?: RecordedOD[];
  assumptions?: unknown;
  limitations?: unknown;
}
export interface SignalMarker {
  id: string;
  position: Point;
  color: string;
  tls: string;
  index: number;
  state: string;
  phase: number;
  time: number;
  incoming_lane: string;
  outgoing_lane: string;
  source: string;
}
export interface TrafficOverlay {
  heatmap?: import("./heatmap").HeatSegment[];
  signals: SignalMarker[];
  hotspots: { edge_id: string; shape: Point[]; stopped_vehicles: number }[];
  zones: (InternalZone & { parked: number | null })[];
}
export const emptyTraffic = (): TrafficOverlay => ({
  signals: [],
  hotspots: [],
  zones: [],
});
export function sampleAt<T extends { time: number }>(
  samples: T[],
  time: number,
): T | undefined {
  // Do not show a future sample when seeking before the first recorded state.
  let low = 0,
    high = samples.length;
  while (low < high) {
    const mid = (low + high) >>> 1;
    if (samples[mid].time <= time) low = mid + 1;
    else high = mid;
  }
  return samples[low - 1];
}
export function signalColor(state: string): string {
  return state === "r"
    ? "#e64646"
    : state === "y" || state === "Y"
      ? "#f2bf34"
      : state === "G" || state === "g"
        ? "#23b878"
        : "#808b90";
}
export function signalMarkers(
  network: Network,
  topology: SignalTopology[],
  events: SignalEvent[],
  time: number,
): SignalMarker[] {
  const latest = new Map<string, SignalEvent>();
  for (const event of events) {
    if (event.time > time) continue;
    const old = latest.get(event.tls);
    if (!old || event.time >= old.time) latest.set(event.tls, event);
  }
  const lanes = new Map(network.lanes.map((l) => [l.id, l]));
  return topology.flatMap((t) => {
    const event = latest.get(t.tls);
    if (!event) return [];
    return t.links.flatMap((link) => {
      const lane = lanes.get(link.incoming_lane),
        end = lane?.shape.at(-1);
      if (!end) return []; // Never invent a position or uncontrolled signal.
      const sameLane = t.links.filter(
        (l) => l.incoming_lane === link.incoming_lane,
      );
      const slot = sameLane.findIndex((l) => l.index === link.index);
      const prev = lane!.shape.at(-2) ?? end;
      const dx = end[0] - prev[0],
        dy = end[1] - prev[1],
        norm = Math.hypot(dx, dy) || 1;
      const inset = 3 + slot * 5;
      const position: Point = [
        end[0] - (dx / norm) * inset,
        end[1] - (dy / norm) * inset,
      ];
      const state = event.state[link.index] ?? "?";
      return [
        {
          id: `${t.tls}:${link.index}`,
          position,
          color: signalColor(state),
          tls: t.tls,
          index: link.index,
          state,
          phase: event.phase,
          time: event.time,
          incoming_lane: link.incoming_lane,
          outgoing_lane: link.outgoing_lane,
          source: t.source,
        },
      ];
    });
  });
}
export function trafficOverlay(
  network: Network,
  topology: SignalTopology[],
  signals: SignalEvent[],
  queue: QueueSample | undefined,
  zones: InternalZones | undefined,
  stock: StockSample | undefined,
  time: number,
): TrafficOverlay {
  const edges = new Map<string, Point[]>();
  for (const lane of network.lanes)
    if (!edges.has(lane.edge_id)) edges.set(lane.edge_id, lane.shape);
  return {
    signals: signalMarkers(network, topology, signals, time),
    hotspots: (queue?.edges ?? [])
      .filter((e) => e.stopped_vehicles > 0 && edges.has(e.edge_id))
      .map((e) => ({ ...e, shape: edges.get(e.edge_id)! })),
    zones: (zones?.zones ?? []).map((z) => ({
      ...z,
      parked: stock?.parked_by_zone[z.id] ?? null,
    })),
  };
}
