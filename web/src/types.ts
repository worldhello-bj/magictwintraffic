export type Point = [number, number];
export interface Lane {
  id: string;
  edge_id: string;
  shape: Point[];
  width: number;
  speed: number;
  name?: string;
  index?: number;
  display_elevation?: number;
  closed_passenger?: boolean;
}
export interface Network {
  schema_version: string;
  network_hash: string;
  origin: unknown;
  lanes: Lane[];
  buildings: { id: string; polygon: Point[]; height: number }[];
  junctions: { id: string; position: Point; shape?: Point[] }[];
  gates: { id: string; edge_id: string; direction: string; position: Point }[];
  core_polygon: Point[];
  simulation_polygon: Point[];
  source?: unknown;
  edges?: {
    id: string;
    name: string;
    shape: Point[];
    type: string;
    display_elevation?: number;
  }[];
  traffic_lights?: { id: string; junction_ids: string[] }[];
}
export interface ChunkInfo {
  file: string;
  start: number;
  end: number;
  records: number;
  sha256?: string;
  compression?: string;
  uncompressed_bytes?: number;
}
export interface Manifest {
  schema_version: string;
  run_id: string;
  network_hash: string;
  demand_hash: string;
  policy_hash: string;
  chunks: ChunkInfo[];
  start_time?: number;
  end_time?: number;
  duration_seconds?: number;
  vehicles?: Record<string, unknown> | unknown[];
  lanes?: unknown[];
  [key: string]: unknown;
}
export interface Vehicle {
  time: number;
  id: number;
  x: number;
  y: number;
  angle: number;
  speed: number;
  lane: number;
  flags: number;
}
export interface Frame {
  time: number;
  vehicles: Vehicle[];
}
export interface RunEntry {
  playback_start_seconds?: number;
  scenario_kind?: string;
  run_id: string;
  label?: string;
  policy?: string;
  manifest: string;
  metrics?: string;
  network?: string;
  status?: string;
}
export type Metric = Record<string, unknown>;
