# ReNe CPU work and training handoff

Started November 12, 2026. User authorized CPU-ready implementation in tested slices.
Publication was subsequently authorized November 12; see the project log's
publication entry. Existing course/study files are outside this work.

There is no strict GPU requirement for the current simulator or small MLP PPO.
The handoff is a validated-baseline and measured training-budget decision, not
an artificial CUDA dependency. Do not start large training before the research gates pass.

## Work packages

| Order | Package | Acceptance evidence | Status |
|---|---|---|---|
| 1 | Physical intent mismatch and received plan evidence | Bounded motion, honest state beacons, no injected labels, delay/loss tests | Implemented and tested |
| 2 | Shared timing candidates | Same received-input predictions/features for rules and PPO | Implemented for earlier/later timing |
| 3 | Proposal acceptance and physical execution | Delay/loss/expiry/revision tests; no unaccepted activation | Implemented for ego-only reservations |
| 4 | Metric repairs | Messages charged once, invalidity accumulated, isolated offline labels | Implemented, including hold-CONTINUE oracle |
| 5 | CPU validation and baseline components | Fixtures, paired pilots, source traceability | Necessary engineering checks pass after repair |
| 6 | Research gate and device handoff | Review/freeze and benchmark training | CPU pipeline passes; desktop/research review next |

## Open research constraints

- Instructor approval of the adaptation was confirmed by the student November 12. Deadline is early December; exact date remains unspecified.
- Existing simulator validation is incomplete; test counts are not scientific validation.
- Short headways and conservative true-state shield/fallback can dominate outcomes.
- Candidate timing changes must affect real motion and be acknowledged, not add gap bonuses.
- Baseline comparison must precede substantial PPO training. Negative results are valid.

## Resume record

- Starting regression: 134 tests pass on the local CPU.
- Final regression: 200 tests and lint pass. These are not scientific validation.
- Scope approval is resolved; remaining gates are technical, not professor approval.

## Current decision

**The CPU implementation and training-interface handoff is reached for the declared
fixtures. GPU use is optional.** Review the prototype limits and freeze the research
baseline/protocol before substantive training. Broader validation and scientific
claims remain distinct from passing engineering checks.

The initial pilot found 51 ramp departures in 144 episodes. The session continued
with a common-controller repair: reserve stopping distance when a peer slows;
avoid returning to an infeasible ramp during a partial lane change; use physical
perception fallback and bounded rear following. Fallback completion is separate
from completion of the accepted agreement. Ramp length/braking limits did not change.

Post-repair pilot runs of 144, 384 and 96 episodes had zero collisions or ramp
departures in their tested cases. Headway violations remain in adversarial cut-ins;
this is not a formal or general real-world safety guarantee.

## Implemented behavior

- Intent mismatch: bounded front-car deceleration while its accepted cruise intent
  stays unchanged. Honest state beacons support received-only position/speed residuals.
- Shared prediction: reconstruct a constant-velocity traffic world from the decoded
  policy vector and fixed configuration, then reuse the common controller. Never clone
  live RNG/future schedules. Missing/stale inputs or an incomplete horizon give UNKNOWN.
- Timing menu: +/-1 s for the same named pair, offered when the predictor finds a
  complete merge. Unsupported next-gap/order-swap actions remain disabled.
- Protocol: 100 ms retries, 1 s expiry, two delivered replies, session/revision/token/
  route checks and safety/time checks before activation. The old timing stays active
  until acceptance. Peers reserve ego timing only; their trajectories are not revised.
  This is not atomic distributed commit or a reproduced wireless/coordination stack.
- Common inputs: 53 features, `lifecycle-prediction-v4`, including prediction outcomes
  and candidate availability/times. Rules/PPO see the same clipped float32 data.
  Old checkpoints and normalizers are incompatible.
- Provisional managers: `paper_cancel_merge_adapted` implements the documented
  keep/fallback table; `matched_heuristic` ranks the same timing candidates as PPO.
  Reference speed-incentive fixtures exist. These are declared adaptations, not an
  exact reproduction of the source traffic experiments or a frozen B2/B3.
- Accounting: incremental transmissions, one cancellation charge, accumulated active
  invalidity across recovery, successful-only merge-time means and ramp-end failure.
  An isolated offline hold-CONTINUE evaluator now labels cancellation after a rollout;
  raw online metrics and pending-proposal counterfactuals remain unlabelled.
  Metrics version: `event-accounting-v2`.
- Analysis rejects absent/mixed schema versions or simulator-source fingerprints.

## Evidence and reproduction

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check src scripts tests
.\.venv\Scripts\python.exe scripts/cpu_pilot.py --seeds 42 43 44
.\.venv\Scripts\python.exe scripts/training_preflight.py
.\.venv\Scripts\python.exe scripts/record_video.py --manager matched_heuristic --disturbance none --delay-ms 100 --loss 0 --output results/figures/cpu_timing_revision.gif
```

Initial failed pilot: `results/raw/cpu-pilot/20261112T203416733157Z/`.
36 scenarios x four managers = 144 episodes; seeds 42/43/44, three densities, four
disturbances, fixed 100 ms delay and zero loss. Runtime about 48.5 s. These are
development seeds/conditions, not a held-out evaluation set.

| Diagnostic | Observed result |
|---|---:|
| Collisions | 0/144 |
| Ramp-end failures | 51/144 |
| Completed physical merges | 54/144 |
| Headway criterion violated in cut-in cases | 36/36 |

Initial source fingerprint: `9e8bc952adb44afa732e9d796595146a0da3530158de2bcccbfc11306a7362e9`.
Earlier same-day pilots predate the attempt-limit fix/failure reporting or the
fingerprint. Do not mix them into the current comparison.

The preview `results/figures/cpu_timing_revision.gif` and sampled frames were
visually checked: acknowledged earlier timing changes the actual lane transition
and completes at 8.2 s in the undisturbed seed-42 example, versus the original 9.2 s
fixture. This is an execution example, not a statistical or learned-policy result.

A 128-step CPU PPO smoke completed in about 10 s, including model construction,
at about 12.8 transitions/s. Torch reports CPU execution and no CUDA. No research
model was saved; the tiny run is not a reliable full-training runtime estimate.
Evidence: `results/raw/training-preflight/20261112T203040408333Z/report.json`.
Generated results remain Git-ignored and are reproducible with the commands above.

### Superseding post-repair evidence

| Run folder under results/raw/cpu-pilot | Episodes | Collisions | Ramp departures | Physical merges |
|---|---:|---:|---:|---:|
| 20261112T204645291530Z | 144 | 0 | 0 | 80 |
| 20261112T204724633048Z | 384 | 0 | 0 | 168 |
| 20261112T205212600263Z | 96 | 0 | 0 | 58 |

The first two share source fingerprint `260a8fa4191dc07a3021df7c69f1b7ee881530163e213f219908c1239d1c33ec`.
The last includes subsequently added training/evaluation helpers and has fingerprint
`3447e6cc0a579f84fe72f7b4e9d4e0672d919b7b55df0fbc9845da2084efde54`.
Keep these development snapshots separate for analysis, not one pooled final experiment.

Expanded commands:

```powershell
.\.venv\Scripts\python.exe scripts/cpu_pilot.py --seeds 101 --delay-ms 0 800 --loss 0 0.5 --severity mild hard
.\.venv\Scripts\python.exe scripts/cpu_pilot.py --seeds 102 --severity hard --trigger-s 3.5 6.5
```

The offline evaluator produced 73/228/44 identified cancellation labels respectively;
non-cancellations and pending proposals are not counted as false labels.
See [EXPERIMENT_PROTOCOL.md](EXPERIMENT_PROTOCOL.md) for the counterfactual convention.

Training infrastructure now samples conditions reproducibly, supports actual
subprocess workers, prevents checkpoint overwrite and stores input/source metadata.
A two-process 128-step CPU train/save smoke and four-episode reload/evaluation smoke
passed with development seeds 9001/9002. They are API checks, not trained research
models. Artifacts: `results/raw/development-training-smoke-20261112/seed-9001/` and
`results/raw/development-evaluation-smoke/learned-20261112T205514Z/`.

Evaluation creates a paired scenario manifest, checks model/normalizer provenance
and adds offline labels only after the actual episode. The default final manifest
crosses 384 conditions and five reserved seeds (1,920 episodes per model).
`scripts/paired_analysis.py` implements paired/model-hierarchical bootstrap rate
differences, with deterministic fixtures; zero-event intervals do not certify risk.

## Next CPU work

- [x] Repair the shared abort/fallback contract for the declared fixtures. A late blocked merge can leave
  insufficient distance to return to the ramp and stop. At 25 m/s with a 4 m/s²
  bound, stopping alone needs about 78.1 m, before reaction/lateral-return margins.
  Preserving that reserve or guaranteeing another safe fallback needs explicit
  controller design. The current repair is described above; no formal guarantee is claimed.
- [x] Revalidate nominal merges and aborts for every manager after the change.
  Do not alter only the heuristic or weaken the shared shield to favor learning.
- [x] Add bounded rear following and test early/late and severity/channel cases.
- [ ] Review short headways, sensor assumptions, and wider late/
  off-grid disturbances. Separate adversarial traffic exposure from ego safety.
- [x] Implement/test the isolated decision-time hold-CONTINUE counterfactual.
- [x] Expand paired pilots to delay/loss, severity and trigger timing.
- [x] Prepare paired held-out manifests and bootstrap analysis helpers.
- [ ] Review/freeze B2/B3, protocol limits and training hyperparameters before final experiments.
- [ ] Benchmark the intended desktop on CPU, then compare CUDA if available.
- [ ] Start substantive PPO only after validation and baseline gates pass.

## Desktop and GPU handoff

The RTX 3060 Ti is optional acceleration for the compact MLP, not a simulation
prerequisite. Recreate the desktop virtual environment rather than copying the
laptop's `.venv`; verify dependencies, tests and a short pilot there. A CPU-only
Torch build will not use the desktop GPU. Check CUDA installation when benchmarking.

`scripts/train.py` requires explicit acknowledgement of the unvalidated simulator
for development runs. That override does not pass M2 or validate a research model.

## Target schedule

Planning targets, not completed work or guaranteed runtimes:

| Period | Priority |
|---|---|
| Nov 12-18 | Shared fallback repair, M2 validation, baseline pilot/freeze |
| Nov 19-25 | Held-out protocol, desktop benchmark, PPO development/validation |
| Nov 26-Dec 2 | Final paired runs, analysis, report and presentation |
| Before actual deadline | Reproduction check and submission buffer |

If time tightens, reduce optional breadth with an explicit record; retain safety
validation. The implementation was later committed as `9fdccb0`, with the project
records grouped separately for authorized publication. See the project log and
GitHub branch head for push confirmation. Generated results/checkpoints remain local.
