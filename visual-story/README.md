# Chengdu visual story

Standalone recovered visualization for the 40-run exported aggregate experiment. This directory is separate from the original `web/` application and simulation code. No package installation is required: use Node.js 18+ and Python 3.

## Build, verify, and serve

From the repository root:

```
node visual-story/scripts/build-story.mjs
node --input-type=module --check < visual-story/src/story.js
node --test visual-story/tests/story-repair.test.mjs
python recovery/verify_site_recovery.py
python -m http.server 8080 --directory visual-story/dist
```

Open http://localhost:8080/story.html or http://localhost:8080/. Serve `dist` as the web root; do not open the HTML directly as a file. Build output is ignored by Git. The build copies the preserved `recovery/site-v10/story-data/` bytes without modifying them and emits content-hashed JS/CSS. It does not install dependencies, run simulations, or require the older 194 MB replay assets.

`src/story.js` is the recovered browser module, not the unavailable original TypeScript authoring project. The standalone copy changes old laboratory navigation links into links back to this visualization; the existing repository `web/` application is untouched. See `REPAIR.md` and `../recovery/README.md` for the repair scope and evidence limits.

Final people results are fixed at 120 minutes. All unfinished people are `cohort - completed`, including not inserted and waiting for a bus. Intermediate person-event counts are not displayed because the original person records needed to correct their equality-boundary sampling were not recovered. The exported road windows and vehicle series remain unchanged.

Node tests use DOM stubs; they do not replace browser rendering or pointer-interaction QA. The published Site is separately browser-tested.
