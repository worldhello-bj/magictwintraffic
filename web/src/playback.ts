import type { Manifest, Frame } from "./types";
import { frameAt } from "./protocol";
export class Playback {
  readonly cache = new Map<number, Frame[]>();
  private pending = new Map<number, Promise<Frame[]>>();
  private worker = new Worker(new URL("./decode.worker.ts", import.meta.url), {
    type: "module",
  });
  private jobs = new Map<
    number,
    { resolve: (v: Frame[]) => void; reject: (e: Error) => void }
  >();
  private serial = 0;
  private controller = new AbortController();
  private disposed = false;
  constructor(
    public manifest: Manifest,
    public url: string,
    public limit = 4,
  ) {
    this.worker.onmessage = (e) => {
      const job = this.jobs.get(e.data.id);
      if (!job) return;
      this.jobs.delete(e.data.id);
      e.data.error
        ? job.reject(new Error(e.data.error))
        : job.resolve(e.data.frames);
    };
    this.worker.onerror = () => {
      for (const job of this.jobs.values())
        job.reject(new Error("轨迹解码 Worker 失败"));
      this.jobs.clear();
    };
  }
  private async load(index: number): Promise<Frame[]> {
    const existing = this.cache.get(index);
    if (existing) {
      this.cache.delete(index);
      this.cache.set(index, existing);
      return existing;
    }
    const pending = this.pending.get(index);
    if (pending) return pending;
    const task = this.read(index);
    this.pending.set(index, task);
    try {
      return await task;
    } finally {
      this.pending.delete(index);
    }
  }
  private async read(index: number) {
    const chunk = this.manifest.chunks[index];
    const response = await fetch(
      new URL(
        this.manifest.chunks_base_url
          ? chunk.file.split("/").at(-1)!
          : chunk.file,
        this.manifest.chunks_base_url
          ? new URL(String(this.manifest.chunks_base_url), this.url)
          : this.url,
      ),
      { signal: this.controller.signal },
    );
    if (!response.ok) throw new Error(`轨迹加载失败 (${response.status})`);
    const buffer = await response.arrayBuffer();
    if (chunk.sha256) {
      if (!crypto.subtle)
        throw new Error("请使用 localhost 或 HTTPS 验证轨迹校验和");
      const digest = await crypto.subtle.digest("SHA-256", buffer);
      const hash = Array.from(new Uint8Array(digest), (v) =>
        v.toString(16).padStart(2, "0"),
      ).join("");
      if (hash !== chunk.sha256) throw new Error("轨迹 SHA-256 校验失败");
    }
    const frames = await new Promise<Frame[]>((resolve, reject) => {
      const id = ++this.serial;
      this.jobs.set(id, { resolve, reject });
      this.worker.postMessage(
        { id, buffer, records: chunk.records, compression: chunk.compression },
        [buffer],
      );
    });
    if (this.disposed) throw new Error("回放已切换");
    if (
      this.manifest.lanes &&
      frames.some((f) =>
        f.vehicles.some((v) => v.lane >= this.manifest.lanes!.length),
      )
    )
      throw new Error("轨迹车道索引超出字典");
    this.cache.set(index, frames);
    while (this.cache.size > this.limit)
      this.cache.delete(this.cache.keys().next().value!);
    return frames;
  }
  async frame(time: number) {
    const chunks = this.manifest.chunks;
    let index = chunks.findIndex(
      (c) =>
        time >= c.start &&
        time <
          c.end +
            Number(
              this.manifest.trajectory_step_seconds ??
                this.manifest.step_seconds ??
                0.5,
            ),
    );
    if (index < 0 && chunks.length && time === chunks[chunks.length - 1].end)
      index = chunks.length - 1;
    if (index < 0) return undefined;
    const frames = await this.load(index);
    const frame = frameAt(frames, time);
    const step = Number(
      this.manifest.trajectory_step_seconds ??
        this.manifest.step_seconds ??
        0.5,
    );
    return frame && time - frame.time < step ? frame : undefined;
  }
  dispose() {
    this.disposed = true;
    this.controller.abort();
    this.worker.terminate();
    for (const job of this.jobs.values()) job.reject(new Error("回放已切换"));
    this.jobs.clear();
    this.cache.clear();
    this.pending.clear();
  }
}
