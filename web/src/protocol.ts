import type { Frame, Manifest, Network } from "./types";
export const RECORD_BYTES = 32;
export function decodeChunk(buffer: ArrayBuffer): Frame[] {
  if (buffer.byteLength % RECORD_BYTES)
    throw new Error("轨迹块长度不是 32 字节的整数倍");
  const view = new DataView(buffer),
    frames: Frame[] = [];
  let frame: Frame | undefined;
  for (let i = 0; i < buffer.byteLength; i += 32) {
    const time = view.getFloat32(i, true);
    const x = view.getFloat32(i + 8, true),
      y = view.getFloat32(i + 12, true),
      angle = view.getFloat32(i + 16, true),
      speed = view.getFloat32(i + 20, true);
    if (![time, x, y, angle, speed].every(Number.isFinite) || speed < 0)
      throw new Error("轨迹包含无效数值");
    if (frame && time < frame.time) throw new Error("轨迹时间未排序");
    if (!frame || frame.time !== time) {
      frame = { time, vehicles: [] };
      frames.push(frame);
    }
    frame.vehicles.push({
      time,
      id: view.getUint32(i + 4, true),
      x,
      y,
      angle,
      speed,
      lane: view.getUint32(i + 24, true),
      flags: view.getUint32(i + 28, true),
    });
  }
  return frames;
}
export function assertCompatible(network: Network, manifest: Manifest) {
  if (manifest.schema_version !== "1.0") throw new Error("不支持的轨迹版本");
  if (network.network_hash !== manifest.network_hash)
    throw new Error("路网哈希不匹配，已拒绝混播");
  if (
    manifest.lanes &&
    (manifest.lanes.length !== network.lanes.length ||
      manifest.lanes.some((lane, index) => lane !== network.lanes[index].id))
  )
    throw new Error("车道字典与对应路网不同，拒绝播放");
  if (!manifest.run_id || !manifest.demand_hash || !manifest.policy_hash)
    throw new Error("运行身份不完整");
}
export function frameAt(frames: Frame[], time: number): Frame | undefined {
  let lo = 0,
    hi = frames.length - 1,
    best = -1;
  while (lo <= hi) {
    let mid = (lo + hi) >> 1;
    if (frames[mid].time <= time) {
      best = mid;
      lo = mid + 1;
    } else hi = mid - 1;
  }
  return best < 0 ? undefined : frames[best];
}
export function localToWorld(
  x: number,
  north: number,
  height = 0,
): [number, number, number] {
  return [x, height, -north];
}
export function validateOD(rate: number, shares: number[]): string[] {
  const errors: string[] = [];
  if (!Number.isFinite(rate) || rate < 0) errors.push("入口流率必须为非负数");
  if (shares.some((v) => !Number.isFinite(v) || v < 0))
    errors.push("出口比例不能为负数");
  if (Math.abs(shares.reduce((a, b) => a + b, 0) - 100) > 0.01)
    errors.push("出口比例之和必须为 100%");
  return errors;
}

export async function decodePayload(
  buffer: ArrayBuffer,
  records: number,
  compression?: string,
): Promise<Frame[]> {
  if (compression && compression !== "gzip" && compression !== "none")
    throw new Error("不支持的轨迹压缩格式");
  if (compression === "gzip") {
    const stream = new Blob([buffer])
      .stream()
      .pipeThrough(new DecompressionStream("gzip"));
    buffer = await new Response(stream).arrayBuffer();
  }
  if (buffer.byteLength !== records * RECORD_BYTES)
    throw new Error("轨迹记录数与清单不一致");
  return decodeChunk(buffer);
}
