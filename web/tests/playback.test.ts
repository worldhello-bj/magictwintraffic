import { test } from "node:test";
import assert from "node:assert/strict";
import { Playback } from "../src/playback.ts";
import { decodePayload } from "../src/protocol.ts";
import type { Manifest } from "../src/types.ts";
class MockWorker {
  onmessage?: (event: { data: unknown }) => void;
  onerror?: () => void;
  postMessage(message: {
    id: number;
    buffer: ArrayBuffer;
    records: number;
    compression?: string;
  }) {
    void decodePayload(message.buffer, message.records, message.compression)
      .then((frames) => this.onmessage?.({ data: { id: message.id, frames } }))
      .catch((error) =>
        this.onmessage?.({ data: { id: message.id, error: String(error) } }),
      );
  }
  terminate() {}
}
Object.defineProperty(globalThis, "Worker", {
  value: MockWorker,
  configurable: true,
});
function bytes(time: number) {
  const b = new ArrayBuffer(32),
    v = new DataView(b);
  v.setFloat32(0, time, true);
  v.setUint32(4, 4, true);
  v.setFloat32(8, 10, true);
  v.setFloat32(12, 20, true);
  return b;
}
const manifest: Manifest = {
  schema_version: "1.0",
  network_hash: "n",
  policy_hash: "p",
  demand_hash: "d",
  run_id: "r",
  step_seconds: 0.5,
  chunks: Array.from({ length: 6 }, (_, i) => ({
    file: `${i}.bin`,
    start: i * 20 + 0.5,
    end: (i + 1) * 20,
    records: 1,
  })),
};
test("bounded playback cache and no ghost vehicles in empty recorded frame", async () => {
  const previous = globalThis.fetch;
  globalThis.fetch = async (input) => {
    const id = Number(String(input).match(/(\d+)\.bin/)![1]);
    return new Response(bytes(id * 20 + 0.5));
  };
  const player = new Playback(manifest, "http://localhost/data/manifest.json");
  try {
    assert.equal((await player.frame(0.5))?.vehicles.length, 1);
    assert.equal(await player.frame(1), undefined);
    for (let i = 1; i < 6; i++) await player.frame(i * 20 + 0.5);
    assert.equal(player.cache.size, 4);
    assert.ok(!player.cache.has(0));
    assert.equal(await player.frame(121), undefined);
  } finally {
    player.dispose();
    globalThis.fetch = previous;
  }
});
test("trajectory checksum mismatch blocks playback", async () => {
  const previous = globalThis.fetch;
  globalThis.fetch = async () => new Response(bytes(0.5));
  const player = new Playback(
    { ...manifest, chunks: [{ ...manifest.chunks[0], sha256: "wrong" }] },
    "http://localhost/data/manifest.json",
  );
  try {
    await assert.rejects(player.frame(0.5), /SHA-256/);
    assert.equal(player.cache.size, 0);
  } finally {
    player.dispose();
    globalThis.fetch = previous;
  }
});
test("incorrect record count blocks playback", async () => {
  const previous = globalThis.fetch;
  globalThis.fetch = async () => new Response(bytes(0.5));
  const player = new Playback(
    { ...manifest, chunks: [{ ...manifest.chunks[0], records: 2 }] },
    "http://localhost/data/manifest.json",
  );
  try {
    await assert.rejects(player.frame(0.5), /记录数/);
  } finally {
    player.dispose();
    globalThis.fetch = previous;
  }
});
