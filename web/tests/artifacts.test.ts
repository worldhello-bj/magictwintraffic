import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { createHash } from "node:crypto";
import { decodePayload, assertCompatible } from "../src/protocol.ts";
import type { Network, Manifest, RunEntry } from "../src/types.ts";
const base = resolve("public/data");
test(
  "published catalog assets decode and match their own network, identities and checksums",
  { skip: !existsSync(resolve(base, "catalog.json")) },
  async () => {
    const catalog = JSON.parse(
      readFileSync(resolve(base, "catalog.json"), "utf8"),
    ) as { runs: RunEntry[] };
    assert.ok(catalog.runs.length);
    for (const run of catalog.runs) {
      const path = resolve(base, run.manifest),
        manifest = JSON.parse(readFileSync(path, "utf8")) as Manifest;
      assert.equal(run.run_id, manifest.run_id);
      const network = JSON.parse(
        readFileSync(resolve(dirname(path), String(manifest.network)), "utf8"),
      ) as Network;
      assertCompatible(network, manifest);
      for (const chunk of manifest.chunks) {
        const buffer = readFileSync(resolve(dirname(path), chunk.file));
        assert.equal(
          createHash("sha256").update(buffer).digest("hex"),
          chunk.sha256,
        );
        const frames = await decodePayload(
          Uint8Array.from(buffer).buffer,
          chunk.records,
          chunk.compression,
        );
        for (const frame of frames) {
          assert.ok(frame.time >= chunk.start && frame.time <= chunk.end);
          assert.equal(
            new Set(frame.vehicles.map((v) => v.id)).size,
            frame.vehicles.length,
          );
          for (const v of frame.vehicles)
            assert.ok(v.lane < network.lanes.length);
        }
      }
    }
  },
);
