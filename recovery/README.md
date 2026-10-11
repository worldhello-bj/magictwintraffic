# Chengdu visualization recovery (2026-10-11)

This independent recovery directory preserves existing published output without changing the older simulation core.

## Provenance and limits

- Source repository: https://github.com/worldhello-bj/magictwintraffic, remote main `62f7b86333df6d9d6cabed3d55b513bf840ba9c5`.
- Source Site snapshot commit: `77306a89fc4d89b5f7477df62696ae0bef82547d`.
- `site-v10/story-data/` is a byte-for-byte copy of the previously exported, published aggregate output from 40 simulations. It is not raw simulation input or a new simulation run.
- Original `persons.jsonl.gz`, original run summaries, and original 40-run simulation/export code were not recovered from the GitHub repository. Their historical hashes remain in the saved catalog as provenance, not proof that those original files are present.
- `site-v10/data/` preserves the separate older vehicle-replay data as a local recovery copy. It must not be mistaken for the 40-run person-level experiment.
- No policy conclusions, physical runs, road observations, or final results have been regenerated.

## Integrity

Run `python recovery/verify_site_recovery.py` from the repository root. This checks 40 unique run IDs (36 core runs and 4 adoption-sensitivity runs), file hashes declared by the catalog, the network hash, matched inventory and cohort across references, final status conservation, and 24 heatmap windows plus 240 time-series samples per run.

Only the small `story-data/` aggregate export is intended for the repository increment. The 194 MB legacy `data/` copy is ignored by Git and classified as `local_only_legacy_site_asset` in the manifest; its source remains the saved Site.

`site-v10-verification.json` records per-file preservation classification, sizes and SHA-256 hashes, the source Site commit, the final 120-minute results, and the verification outcome. `source-recovery.json` records the remote repository recovery result.

## Display limitations

The person-event snapshot columns have a known equality-boundary issue. Preserve these bytes for provenance, but do not present the intermediate `scheduled_due_people`, `started_people`, `completed_people`, or `due_unfinished_people` as corrected or independently reverified event ledgers. Correcting their event-time sampling requires original person records, which were not recovered.

Retain the exported road/network aggregate time series and road heatmaps. For people results, use explicitly labeled fixed 120-minute catalog values: `completed` for arrivals and `cohort - completed` for all unfinished people. The catalog `status_counts.unfinished` alone excludes other incomplete states such as `not_inserted` and `waiting_for_bus`. These fixed final results must not change when the selected heatmap time changes.

The road heatmap is a 5-minute aggregate and the road time series uses 30-second snapshots. Neither is a reconstructed vehicle trajectory nor real-time observed Chengdu traffic.
