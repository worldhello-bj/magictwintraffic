import { test } from "node:test";
import assert from "node:assert/strict";
import {
  decodeChunk,
  decodePayload,
  frameAt,
  localToWorld,
  assertCompatible,
  validateOD,
} from "../src/protocol.ts";
import type { Manifest, Network } from "../src/types.ts";
function record(t: number, id: number) {
  const b = new ArrayBuffer(32),
    v = new DataView(b);
  v.setFloat32(0, t, true);
  v.setUint32(4, id, true);
  v.setFloat32(8, 100, true);
  v.setFloat32(12, 200, true);
  v.setFloat32(16, 90, true);
  v.setFloat32(20, 8, true);
  v.setUint32(24, 3, true);
  return b;
}
test("32-byte little-endian records preserve identity and state", () => {
  assert.deepEqual(decodeChunk(record(0.5, 120))[0], {
    time: 0.5,
    vehicles: [
      {
        time: 0.5,
        id: 120,
        x: 100,
        y: 200,
        angle: 90,
        speed: 8,
        lane: 3,
        flags: 0,
      },
    ],
  });
});
test("empty recording never creates vehicles", () =>
  assert.deepEqual(decodeChunk(new ArrayBuffer(0)), []));
test("reject truncated and invalid records", () => {
  assert.throws(() => decodeChunk(new ArrayBuffer(31)));
  const b = record(1, 0);
  new DataView(b).setFloat32(8, NaN, true);
  assert.throws(() => decodeChunk(b));
});
test("reject unordered recording", () => {
  const b = new Uint8Array(64);
  b.set(new Uint8Array(record(2, 0)));
  b.set(new Uint8Array(record(1, 0)), 32);
  assert.throws(() => decodeChunk(b.buffer));
});
test("selection uses recorded time and never extrapolates before first frame", () => {
  const frames = decodeChunk(record(1, 0));
  assert.equal(frameAt(frames, 0.5), undefined);
  assert.equal(frameAt(frames, 1.2)?.time, 1);
});
test("east/up/north mapping is correct", () =>
  assert.deepEqual(localToWorld(10, 20, 3), [10, 3, -20]));
test("hash mismatch and missing identity rejected", () => {
  const n = { network_hash: "network" } as Network;
  const m = {
    schema_version: "1.0",
    network_hash: "different",
    run_id: "r",
    demand_hash: "d",
    policy_hash: "p",
  } as Manifest;
  assert.throws(() => assertCompatible(n, m));
  assert.doesNotThrow(() =>
    assertCompatible(n, { ...m, network_hash: "network" }),
  );
  assert.throws(() =>
    assertCompatible(n, { ...m, network_hash: "network", policy_hash: "" }),
  );
});
test("OD shares must be nonnegative and conserved", () => {
  assert.deepEqual(validateOD(100, [40, 60]), []);
  assert.ok(validateOD(100, [40, 50]).length);
  assert.ok(validateOD(-1, [100]).length);
  assert.ok(validateOD(100, [-10, 110]).length);
});

test("gzip transport decodes real record and rejects unsupported compression", async () => {
  const raw = record(0.5, 17);
  const zipped = await new Response(
    new Blob([raw]).stream().pipeThrough(new CompressionStream("gzip")),
  ).arrayBuffer();
  assert.equal((await decodePayload(zipped, 1, "gzip"))[0].vehicles[0].id, 17);
  await assert.rejects(decodePayload(raw, 1, "br"), /压缩/);
});
