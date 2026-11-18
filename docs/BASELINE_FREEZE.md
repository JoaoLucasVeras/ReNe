# ReNe baseline freeze (November 18 2026)

This record freezes B1-B3, the shared environment, the reward and the training/
evaluation protocol before PPO training and before any final-test seed is run.
Changing anything listed here after the final evaluation starts invalidates the
comparison; record any change as a new dated entry and rerun everything affected.

Evidence comes only from development seeds (42-44, 9101-9301). Reserved final-test
seeds 1001-1005 have not been run.

## Frozen managers

| ID | Name in code | Definition |
|---|---|---|
| B1 | `one_shot` | Always requests CONTINUE. The common shield may still cancel. |
| B2 | `paper_cancel_merge_adapted` | Declared adaptation of Molina-Masegosa et al. (VTC2026-Spring), see BASELINE_REPRODUCTION_SPEC.md. Keep/fallback table with `NO_COMPLETION`; switch margin 0 s; ties retain the agreement. |
| B3 | `matched_heuristic` | B2, plus: if a feasible +/-1 s timing candidate is predicted to complete at least 0.05 s earlier than the reference branch (or the reference is not SAFE_COMPLETION), request the earliest candidate; ties prefer DELAY (lower action index). |
| B4 | `learned` | MaskablePPO over the same 58 inputs and the same action menu; masks expose only CONTINUE, CANCEL and feasible timing revisions. |

`rule_cancel` (gap/TTC/message-age thresholds) is kept as a prototype reference only;
it is not a literature baseline.

## Frozen environment and protocol

- Input contract `lifecycle-prediction-v7` (58 features). Physics version string
  unchanged; source fingerprint recorded in each run's outputs.
- Merge geometry: merge point 200 m; merge zone starts at 175 m (the nominal plan is
  already the earliest feasible timing); ramp end per episode.
- Ramp-length protocol: train/tune 260/270/290/300 m; held-out 280 m; edge 320 m;
  controls 240/400 m (EXPERIMENT_PROTOCOL.md).
- Shield and feasibility limits: min gap 12 m, min TTC 2 s, min headway 0.8 s;
  invalidation persistence 0.6 s; one renegotiation per episode.
- Fallback: next-gap perception fallback with nominal merge location, gap-center
  tracking, closing-gap rejection, scoped stopping reserve, lane-change finish cap.
- Sensing: forward 60 m, rearward 120 m; front acceleration received in beacons;
  intruder lateral speed from a 0.1 s difference.
- Reward (per component, unchanged since the November 12 handoff): success +20;
  collision -100; ramp-end failure -100; near-collision -0.5 per s below min TTC;
  persistent invalid agreement -0.2 per s; cancellation -0.1 once; message -0.01 each;
  comfort -0.01 x |accel|; progress +0.02 per s. Agreement and fallback completions
  earn the same success reward, so B4 is optimized for completed merges, not for
  preserving agreements; agreement preservation is reported separately.
- PPO (B4): MaskablePPO, MLP 128x128, lr 3e-4, n_steps 512, batch 128, 10 epochs,
  gamma 0.99, GAE 0.95, clip 0.2, entropy 0.01; observation normalization saved with
  each model; training seeds 1-5; ramp lengths sampled from the training set only.

## Development pilot supporting the freeze (sweep v3, after all fixes)

972 paired scenarios per length (seeds 42-44; three densities; four disturbances;
delay 0/100/800 ms; loss 0/0.2/0.5; mild/moderate/hard; trigger 5 s).
0 collisions and 0 ramp-end violations for B1, B2, B3 and both random policies at
every length.

| Ramp end | B2 differs from B1 | B1 merges | B2 merges | B2 agreement | B2 own cancels | B3 = B2 |
|---|---:|---:|---:|---:|---:|---:|
| 240 m | 0.0% | 432 | 432 | 378 | 23 | 100% |
| 260 m | 3.9% | 486 | 496 | 351 | 61 | 100% |
| 270 m | 4.6% | 504 | 513 | 354 | 91 | 100% |
| 280 m | 8.1% | 459 | 494 | 355 | 125 | 100% |
| 290 m | 10.7% | 459 | 504 | 353 | 150 | 100% |
| 300 m | 10.8% | 486 | 527 | 356 | 174 | 100% |
| 320 m | 2.6% | 486 | 486 | 380 | 25 | 100% |
| 400 m | 0.0% | 648 | 648 | 351 | 0 | 100% |

## Known limitations carried into the final comparison

- B3 equals B2 in every pilot scenario: once the free "advance at t = 0" was removed,
  a +/-1 s timing revision never improved a predicted outcome. The B2 -> B3 comparison
  is expected to show no value from timing renegotiation in this simulator.
- Cut-ins never open a decision window at any tested length; for cut-ins the study
  measures fallback quality only.
- Headway below 0.8 s still occurs in adversarial cut-in exposure for every manager
  (traffic exposure, not an ego decision); reported, not hidden.
- Synthetic, single-lane-pair simulator; idealized sensing; abstract V2X. Results are
  not real-world validation.

## Verification commands

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check src scripts tests
.\.venv\Scripts\python.exe scripts\measure_decision_window.py --seeds 42 43 44 --delay-ms 0 100 800 --loss 0 0.2 0.5 --severity mild moderate hard --env "{\"ramp_end_m\": 280}"
```
