# Cloud browser acceptance — 2026-10-09

An owner-authorized temporary preview was tested in cloud Chrome at1170px width. The browser disables WebGL; the viewer now uses the same real network/trajectory assets in a Canvas2D fallback instead of failing initialization.

Observed and exercised:
- Genuine Yulin streets and building footprints render; catalog offers eight600s policy demonstrations and one9900s baseline.
- Baseline600s KPIs:17.13 vehicle-hours,70.1% completion,69 inside,0 external waiting,0 conservation/collision/teleport failures. These agree with the packaged metrics.
- Play/pause advances the timeline. Keyboard End seeks to600s. The time slider and population chart update.
- S7 selection validates matching demand and reports−0.08 vehicle-hours/+0.4 percentage points for this individual600s pair, matching the archived metrics. It is explicitly not a statistical ranking.
- Synchronized split view draws both real networks at a shared time/camera, with consistent color scale.
- Sidebars scroll independently; lower controls remain reachable.

The initial WebGL-only failure was found through actual screenshot inspection, fixed, rebuilt, republished and retested. Twenty frontend tests additionally cover binary integrity, fallback rendering and renderer-failure isolation. GPU Three.js rendering and FPS were not verified in this browser. API execution is tested separately; the hosted preview serves offline recorded runs.

## Source publication packaging

The tested cloud preview used the nine-run catalog. The Git source delivery deliberately includes only the complete S0/S7 600-second pair, with a matching two-entry catalog and every referenced trajectory chunk. The full nine-run catalog remains reproducible using the root README commands. The retained pair is covered again by the publication artifact tests; the previous browser observation is not a new visual acceptance of this packaging revision.
