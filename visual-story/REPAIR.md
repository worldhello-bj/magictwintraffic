# Chengdu story repair

This checkout was restored from the published static Site. The original TypeScript project was not present. `src/story.js` is the recovered browser module with focused edits; `src/story.css` preserves the original visual system with compact guide and disclosure styles. No package installation is needed.

## Rebuild and test

From this directory:

- `node scripts/build-story.mjs`
- `node --input-type=module --check < src/story.js`
- `node --test tests/story-repair.test.mjs`

The standalone build uses SHA-256 content-hashed asset names, generates `dist/story.html` and `dist/index.html`, and copies the frozen data from the sibling recovery directory. It leaves the original laboratory and preserved JSON artifacts untouched. Repeating the build produces the same entry point and assets. Build output is ignored by Git.

## Evidence boundary

Per-window person counts were removed, including their rendering function and validation dependency. The frozen export used an inclusive person-event boundary; raw person events are unavailable here, so a corrected half-open series cannot be reconstructed. The map retains the actual 5-minute road windows. The queue chart retains actual 30-second vehicle counts. Person-event columns remain in the unchanged downloadable original artifacts but are not consumed by the interface.

Only the verified final 120-minute cohort and arrival totals inform the person results. Final unfinished is cohort minus completed, including people not inserted into the network or still waiting for a bus. Final results do not change with the playback window. Three repetitions are labeled groups 1–3 in the main interface; underlying seed IDs and limitations are in folded details.

## Verification

The Node suite checks every frozen catalog/file hash, every one of the 40 runs, all 960 playback windows with deliberately poisoned person-event columns, constant final results, timeline and transport behavior, missing observations versus observed zero, comparison controls, actual data loading and checksum checks, unavailable conditions and recovery, rapid selections, and balanced main HTML.

These are deterministic module and DOM-stub checks, not browser rendering tests. Desktop/mobile visual QA, canvas painting, real pointer gestures, and deployment verification are separate and must be completed in the supported browser workflow.
