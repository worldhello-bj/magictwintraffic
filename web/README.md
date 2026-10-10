# MagicTwin traffic viewer

Chinese-language Three.js + TypeScript viewer for the hash-bound SUMO artifacts in this repository. All runtime modules are bundled by Vite; there are no CDN, online tile, or external font dependencies.

## Run

```sh
npm ci
npm run dev -- --host 127.0.0.1
# Python API normally listens at 127.0.0.1:8000; Vite proxies /api.
```

The published catalog contains exactly four final-v3 high-pressure replays: S0/S7 × AM/PM, seed 42, 4,200 seconds each. The npm dev/test/build lifecycle restores bundled base assets and verifies these runs, generating only missing final-v3 physics. Retired dense/internal/preview demos are not generated. Existing verified runs are reused when the catalog or derived heatmap needs rebuilding.

Each run includes a SHA-256-bound road heatmap summary derived from its verified recorded chunks, with 60-second windows and the complete post-warmup (300, 4200] window. It preserves missing data and includes empty recorded instants in the frame denominator; it does not manufacture observed traffic or trip delay. See [definitions and limitations](../docs/high_pressure_demo.md).

`npm run build` creates the static offline package and removes unpublished replay/network copies from `dist/` only. Raw `runs/`, archived source exports and research evidence remain intact. Serve `dist/` over localhost HTTP (not file://); the Worker and SHA-256 checks require a normal secure browser context, including localhost. With no API, playback stays available while submission is disabled. `npm run build` and `npm test` are independent of a running API; the first missing replay generation requires the locked Python/SUMO dependencies.

## Implemented behavior

- Three.js is the primary renderer. When WebGL context creation fails, a north-up Canvas 2D fallback uses the same real roads, OSM building footprints and recorded vehicles, with pan/zoom, picking, synchronous comparison and real scale. Catalog and metrics load independently even when both graphics contexts are unavailable.
- Real network ribbons, junction polygons and extruded OSM buildings in 3D; no illustrative replacement grid, synthetic car motion, or invented KPIs.
- Instanced recorded cars/buses, merged static road/marking/building geometry, and raycast picking only on click.
- East → X, up → Y, north → −Z. Mapped bridge elevations derive from the same network lanes. Building heights and non-observed control assumptions are disclosed.
- Binary records are little-endian 32 bytes; checksum and record counts verified, decoding in a Worker, at most four 20-second chunks per player cached.
- No straight-line interpolation between lanes or over junctions. Missing samples clear vehicles; stale requests cannot replace a newly selected run.
- Whole-demand terminal KPIs and genuine recorded time series, audit anomalies, and signal-extension event bookmarks. Junction inspector displays recorded signal state when available.
- Same-demand paired comparison with time/version guards, synchronized camera/time/legend, each topology's own network. Changed permissions use brown roads. Numeric speed differences require the same network and lanes sampled in both runs.
- Editable per-origin OD rates/shares and a separately enabled multi-row OD list actually submitted to the API. 300-second interval and reachability checks happen before a run. Optional parameters are sent only to applicable policies.
- Jobs are validated, submitted, polled, cancellable and opened only after success. Existing playback is never relabelled as a newly edited policy.

## Verification

`npm test`: decoder, gzip, coordinate convention, identity/hash guards, OD conservation, empty frames, record count, SHA-256 rejection and bounded chunk cache; all published actual artifacts; DOM interaction tests for offline loading, controls, policy/OD submission, duplicate prevention, cancellation and comparison. DOM tests intentionally mock the renderer and do not establish WebGL correctness. `npm run build`: strict TypeScript + production bundle.

Visual/browser acceptance must be performed on a usable browser execution host. An authorized temporary cloud preview exposed WebGL unavailability; this is now explicitly handled with the same-data Canvas fallback and covered by forced-failure DOM tests. In the initial cloud workspace, separate shell calls had isolated loopback networks, direct Chromium was denied Unix socket creation, and Playwright's official headless-shell download returned invalid empty ZIP content. Consequently no browser screenshot, client FPS target or pixel-level acceptance is asserted by the source build/tests.

The UI shows measured rendering counters only when a renderer actually runs; these counters are not a hardware benchmark. This application represents an uncalibrated offline scenario experiment, not field-validated local traffic.
