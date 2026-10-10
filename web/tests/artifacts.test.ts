import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { createHash } from "node:crypto";
import { validateHeatData } from "../src/heatmap.ts";
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
    assert.deepEqual(
      catalog.runs.map((run) => run.run_id),
      ["am", "pm"].flatMap((period) =>
        ["S0", "S7"].map((policy) => `high_pressure_${policy}_${period}_42_v3`),
      ),
    );
    for (const run of catalog.runs) {
      const path = resolve(base, run.manifest),
        manifest = JSON.parse(readFileSync(path, "utf8")) as Manifest;
      assert.equal(run.run_id, manifest.run_id);
      const network = JSON.parse(
        readFileSync(resolve(dirname(path), String(manifest.network)), "utf8"),
      ) as Network;
      assertCompatible(network, manifest);
      const heatBytes = readFileSync(
        resolve(dirname(path), String(manifest.road_heatmap)),
      );
      assert.equal(
        createHash("sha256").update(heatBytes).digest("hex"),
        manifest.road_heatmap_sha256,
      );
      const heat = validateHeatData(
        JSON.parse(heatBytes.toString("utf8")),
        manifest,
      );
      assert.equal(heat.windows.length, 65);
      assert.equal(heat.total.frames, 3900);
      assert.ok(Object.keys(heat.total.edges).length > 100);
      assert.ok(heat.windows.every((w) => w.frames === 60));
      for (const [edge, row] of Object.entries(heat.total.edges)) {
        assert.ok(!edge.startsWith(":"));
        for (const i of [0, 2, 4])
          assert.equal(
            heat.windows.reduce((n, w) => n + (w.edges[edge]?.[i] ?? 0), 0),
            row[i],
          );
      }
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
