# ReNe Project Progress and Decision Log

Last updated: November 12, 2026

This is the starting point for resuming ReNe after a break or on another machine.
It records completed work, decisions, unresolved issues, and the next session's
scope. The [roadmap](PROJECT_ROADMAP.md) owns the detailed TODOs and milestone gates;
this log owns the chronological history and current handoff.

## Project goal

For the plain-language explanation and phase-level plan, read
[PROJECT_OVERVIEW_AND_ROADMAP.md](PROJECT_OVERVIEW_AND_ROADMAP.md).

Determine when learned post-acceptance agreement management improves cooperative
freeway merging over literature-derived cancellation and matched rule-based
renegotiation, and when simple rules are sufficient. Compare managers using the
same controller, safety protection, scenarios, candidate proposals, and relevant
information. Learning does not have to win for the project to produce a useful result.

## Current status

- Steps 1 and 2: paper selection and reproduction specification are documented.
  Instructor approval of the adaptation was confirmed November 12. Deadline is early December.
- Step 3: CPU-only audit completed; the M2 simulator-validation gate has **not passed**.
- Simulator/scientific validation, B2/B3 freeze and main PPO remain pending.
  Provisional paper-adapted cancellation and matched timing managers now exist.
- Step 3A is implemented for the bounded physical fixtures; 35 tests pass.
  See [the implementation record](STEP3A_PHYSICAL_MERGE.md). The custom simulator
  remains primary; full M2 validation is still open.
- Step 3B is implemented for the abstract channel/protocol fixtures; its checkpoint
  had 82 passing tests. See [the communication record](STEP3B_COMMUNICATION.md).
- Step 3C1: bounded front braking/hold/recovery and generation-time beacon sampling
  are implemented locally; that checkpoint had 104 passing tests. See
  [the braking record](STEP3C1_BOUNDED_BRAKING.md).
- Step 3C2: physical cut-in, shared local perception and stopping-bound repairs
  implemented locally; that checkpoint had 134 passing tests and lint passed. Its
  input vector had 40 features; current v4 is documented below. See
  [the cut-in record](STEP3C2_PHYSICAL_CUT_IN.md).
- November 12 CPU integration: intent mismatch, shared received-state predictions,
  timing proposals/acceptance/execution and accounting repairs implemented. 200 tests
  and lint pass; v4 has 53 inputs. Old checkpoints are incompatible.
- Initial pilot found 51 ramp failures; shared abort/fallback and rear following were
  then repaired. Three post-repair pilots (144/384/96 episodes) have no collisions or
  ramp departures in their tested cases. Offline counterfactuals are implemented.
  Next: protocol/baseline review and desktop training benchmark; broader scientific
  validation/freeze remains distinct. See [CPU handoff](CPU_TO_TRAINING_HANDOFF.md).
- Desktop setup remains unverified. Reported hardware: Ryzen 5 3600, RTX 3060 Ti,
  32 GB RAM. No GPU is needed for the immediate deterministic repairs.

## Start the next session here

1. Read this log, the roadmap's current focus, and the [audit](SIMULATION_AND_METRIC_DEFINITIONS.md).
2. Check `git status` and the current commit; preserve unrelated or uncommitted work.
   The publication snapshot below is historical, not a substitute for checking Git.
3. Review Step 3A/3B implementation records and remaining audit limitations.
4. Keep the custom physical simulator for now; HighwayEnv integration remains optional.
5. Read the CPU handoff and experiment protocol; review/freeze limits and benchmark the desktop.
6. After work, append a session entry, update this status and the roadmap, and record
   tests and publication state. Commit or push only when authorized.

## Next work in order

| Step | Work | Completion evidence |
|---|---|---|
| 3A completed for bounded fixtures | Moving target gaps, body/lane geometry, physical completion, collision and pairwise safety | 35 tests pass; implementation record and visually checked preview; full M2 still open |
| 3B implemented for abstract fixtures | Timestamped delivery/drop, received cache, ages, cancellation/ACK/timeout, shared inputs | 82 tests pass; diagnostic traces; peer physical cooperative actuation remains pending |
| 3C | Physical disturbances and shared candidate trajectories, with bounded controls and acceptance behavior | Each candidate and disturbance has a physical effect; no artificial gap bonuses |
| 3D | Event-based metric accounting, decision-time traces and counterfactual cancellation evaluation | Hand-calculated metric cases and regression tests |
| 3E | Review corrected scenarios, communication, density/severity and fallback | M2 validation evidence, not merely passing API tests |
| M3 | Literature-derived cancellation manager B2 | Source/adaptation traceability and reproduction fixtures |
| M4 and M5 | Shared candidates, matched heuristic B3, then paired baseline pilot | Fair baseline comparison and go/no-go decision for PPO |
| M6 onward | Evaluation infrastructure, PPO, held-out experiments and report | Follow the roadmap's individual gates |

## Decisions and constraints

| Decision | Reason | Status and reference |
|---|---|---|
| Treat the necessity of learning as the experimental question | Professor noted that compact observations and a small action space may be handled well by rules or a model-based manager | Adopted; [revised plan](REVISED_PROJECT_PLAN.md) |
| Build and validate baselines before substantial PPO training | A learned-policy advantage must survive a fair cancellation and renegotiation comparison | Adopted; roadmap M3–M7 |
| Use the selected cancellation source with explicitly labeled adaptations | The source's lane-change setting differs from the project's freeway merge | Specified, instructor guidance pending; [reproduction specification](BASELINE_REPRODUCTION_SPEC.md) |
| Do not call the existing threshold manager a paper reproduction | Its gap/TTC/staleness triggers do not reproduce the selected source's incentive-loss trigger | Adopted; B2 implementation pending |
| Preserve common safety and information across managers | Extra actions, privileged state or weakened protection must not manufacture an RL advantage | Adopted; implementation still needs correction |
| Do not interpret current prototype outcomes as physical merge evidence | Geometry, V2X and metrics contain artifacts | M2 gate open; audit findings A01–A13 |
| Use the owner's Git identity without AI/coauthor attribution | Explicit publication instruction | Apply to authorized commits; do not silently commit or push |

## Session history

Historical entries below summarize the existing roadmap and recorded work.
October 10 entries describe documentation work only; the October 1 tests were
not rerun for this log.

### October 1 2026 research specification

- Selected the cancellation source and documented supporting research and overlap.
- Wrote the source-to-implementation specification, separating verified source
  behavior from merge adaptations and components still missing from the prototype.
- Artifacts: [paper selection](BASELINE_PAPER_SELECTION.md),
  [overlap check](RELATED_WORK_OVERLAP_CHECK.md),
  [reproduction specification](BASELINE_REPRODUCTION_SPEC.md), updated roadmap.
- Published these four files in commit `ce7d47c2817d7e5a685f10d64325c4db92fd1d5d`.
  Author and committer: JoaoLucasVeras. No AI/coauthor trailer was added.
- Follow-up: instructor guidance on adaptation and Step 3 audit.

### October 1 2026 simulator audit and pause

- Inspected the custom environment, lifecycle, communication proxy, shield,
  managers, metrics, evaluation and analysis code.
- Seven existing tests passed. Added and ran `scripts/audit_simulator.py`:
  12 manager/disturbance episodes, two loss-comparison episodes and targeted probes.
  Lint passed. These checks were diagnostic, not statistical validation.
- Findings: recorded success only crosses a fixed position; the reserved gap can
  be far ahead; TTC is an arrival-time separation; delay/loss does not delay
  observed vehicle state; candidate actions and metric accounting need repairs.
- Three prototype managers had identical outcomes in the four seed-42 scenarios.
  This does not establish equivalence between correctly implemented methods.
- Artifacts: [audit and proposed metric contract](SIMULATION_AND_METRIC_DEFINITIONS.md),
  diagnostic script and roadmap updates. Simulator behavior was not changed.
- User requested a pause to review findings in depth. These audit changes remained
  local and unpushed at the pause.
- Follow-up: review findings, then agree on Step 3A implementation.

### October 10 2026 progress documentation

- Reviewed the existing roadmap, README and local Git status.
- Created this persistent history/handoff, linked it from the README and roadmap,
  and made it the canonical session-history location for future updates.
- No simulator changes, training or new scientific test results in this session.
- Documentation checked for local link targets and whitespace. No commit or push
  requested for this session.
- Follow-up: owner reviews audit findings; Step 3A remains the next implementation task.

### October 10 2026 plain language roadmap

- Created `PROJECT_OVERVIEW_AND_ROADMAP.md` explaining the problem, goal,
  completed research/software work, audit limitations and phased next steps.
- Linked the overview from the README, detailed roadmap and this log.
- Reviewed current saved status; no new simulator tests, behavior changes or training.
- Validation: local documentation link targets and whitespace checks.
- Publication: local only; no commit or push requested.
- Next task: review the audit and agree on Step 3A's physical scenario/tests.

### October 10 2026 physical merge implementation

- User approved the Step 3A scope, including retaining the custom simulator.
- Added pure body/swept geometry and physical lane transition, corrected initial
  moving gaps, TTC/headways, success and ramp-end stopping. Removed synthetic
  gap effects and instantaneous timing-action speed jumps; next-gap/order-swap
  requests remain unavailable until physical candidates exist.
- Validation: 35 tests pass; full Python lint passes; 90 undisturbed diagnostic
  episodes complete without collisions. Default smoke run: 6/10 completions,
  0 collisions; uncorrected communication/disturbances prevent research interpretation.
- Evidence: [STEP3A_PHYSICAL_MERGE.md](STEP3A_PHYSICAL_MERGE.md),
  `tests/test_physical_merge.py`, generated GIF and frame sheet under `results/figures/`.
- No PPO training, published-method reproduction, real V2X delivery or full metric
  repair in this step. M2 remains open.
- Publication: local only; no commit/push. Generated results/previews are Git-ignored.
- Next task: Step 3B's timestamped message delivery and received information contract.

### October 10 2026 authorized publication

- User authorized committing and pushing the Step 3A work and supporting project records.
- Scope: physical geometry/environment/configuration, metrics version, regression
  tests, preview recorder, audit script, audit/implementation records, project log,
  overview, roadmap and README. Unrelated study notes, old proposal artifacts,
  generated results and temporary files are excluded.
- Git author and committer must remain JoaoLucasVeras, without AI/coauthor trailers.
- The commit containing this entry records the publication scope; remote push
  confirmation is reported separately. Check Git's local/remote heads when resuming.
- Next task is planning/approval for Step 3B; no communication implementation is
  included in this publication session.

### October 10 2026 communication implementation

- Implemented Step 3B after owner approval: delayed/lossy timestamped messages,
  independent beacon/control RNG streams, cache ordering, cancellation retries,
  acknowledgment/token/expiry handling and timeout.
- Rules decode the same 35-feature vector supplied to PPO; no hidden neighbor
  truth or injected mismatch labels are policy inputs. Old checkpoints are incompatible.
- Disabled all provisional revisions until Step 3C can execute/acknowledge real candidates.
- Validation: 82 tests and lint pass; perfect/outage/high-delay traces, smoke and
  audit scripts ran. Complete loss yields growing age and timeout, not remote release.
- Evidence: [STEP3B_COMMUNICATION.md](STEP3B_COMMUNICATION.md),
  `tests/test_communication.py`, `scripts/trace_communication.py`; generated
  JSON/CSV/GIF evidence under Git-ignored `results/`.
- No source-method reproduction, PPO training or full baseline experiments. Metric
  and physical disturbance limitations remain; full M2 gate is open.
- Publication: Step 3A and prior records were pushed as `9976057`; Step 3B changes
  are local only, with no new commit/push authorized in this session.
- Next task: plan Step 3C physical disturbances and shared candidate acceptance/execution.

### October 10 2026 Step 3B publication and Step 3C planning

- User authorized committing/pushing Step 3B, then planning the next step.
- Rechecked the full suite: 82 tests and lint pass. Publication scope is the
  communication model, shared inputs, cancellation execution, traces/tests/config,
  preview support and associated project records. Unrelated notes and generated
  artifacts are excluded. Author/committer remain JoaoLucasVeras without coauthor trailers.
- Step 3C proposed sequence: physical cut-in/braking/intent-mismatch fixtures;
  one shared candidate generator; message-based proposal acceptance/rejection/expiry;
  bounded execution and tests for stale proposals, loss and unsafe candidates.
- Proposed scope control: begin with physical timing revisions; add next-gap only
  after a real alternative vehicle pair is represented and communicated. Keep
  unsupported order-swap disabled rather than synthesize space or capability.
- This is planning only; no Step 3C implementation in the publication session.
  Review and approve the first slice before changing physical disturbance behavior.
- The commit containing this entry records the authorized publication scope;
  push confirmation is reported separately and can be checked against remote Git.

### October 10 2026 Step 3C1 bounded braking

- User authorized proceeding in smaller slices; selected bounded braking first.
- Replaced instantaneous front speed changes with bounded braking/hold/recovery.
  Exact phase integration and generation-time beacon sampling handle off-grid events.
- Preserved received-state isolation: no pulse parameters or hidden current speed
  exposed to policies. The preview distinguishes actual and last received speed.
- Validation: 104 tests pass; no-loss and complete-outage CPU diagnostics generated;
  GIF and sampled frames visually checked. Full commands, results and limitations
  are in [STEP3C1_BOUNDED_BRAKING.md](STEP3C1_BOUNDED_BRAKING.md).
- Rear car-following, physical cut-in/intent mismatch, candidate acceptance/execution
  and metric repairs remain pending. M2 is not passed. No PPO training performed.
- Publication: Step 3B confirmed pushed as `2be2ee2`; this slice is local only.
  No commit or push requested in this session; preserve unrelated untracked notes.
- Next: Step 3C2 physical cut-in fixture, then the separately tracked remaining slices.

### October 10 2026 Step 3C2 physical cut-in

- User authorized the next small slice. Added a fourth body crossing from an
  adjacent freeway lane into the original agreed opening, without synthetic bonuses.
- Included the intruder in collision and actual pairwise TTC/headway calculations.
  Represented it as unconnected, with idealized local sensor inputs shared by rules/PPO.
- Added five sensor/occupancy fields: contract v2 has 40 features, incompatible with
  older checkpoints/normalizers. No future cut-in time, intent or hidden peer truth
  is exposed to managers. Generic rules cancel when the observed slot is occupied.
- Cut-in tests exposed ramp overshoot. Repaired the common stopping bound during
  fallback and conservatively retained an abort option when nearby traffic is detected.
  This may suppress useful cooperation; review controller influence under Step 3E.
- Validation: 134 tests and lint pass; nine density/severity fixtures, seeded replay,
  sensor isolation and swept intruder contact checked. Standard ten-episode smoke
  workflow runs (zero original-slot merges). Seed-42 trace and preview generated;
  sampled frames visually checked. Details/limitations in the cut-in record.
- Minimum actual headway is below the configured criterion despite no collisions.
  Do not interpret fixture success as complete traffic-safety or scientific validation.
- Publication: Step 3C1 and 3C2 are local only, no commit/push requested. Unrelated
  untracked notes and generated evidence are untouched/excluded from publication.
- Next: Step 3C3 physical intent mismatch, then candidates/acceptance/execution.
  M2 remains open; no main PPO training or final baseline comparison.

### November 12 2026 CPU implementation and failed validation gate

- User authorized CPU-ready implementation toward the training/device handoff;
  confirmed instructor approval and an early-December deadline.
- Added intent mismatch, received-state-only shared predictions, +/-1 s timing
  candidates, two-peer reservation replies/expiry/activation, and provisional
  paper-adapted cancellation plus matched timing heuristic components.
- V4 has 53 features. Unsupported gap/order swaps stay disabled; peer trajectories
  are not revised by the timing reservations. All managers retain the same shield.
- Accounting repairs: incremental message/cancellation cost, accumulated active
  invalidity, explicit ramp failure, null unavailable counterfactual labels,
  successful-only merge-time means and version/source-fingerprint analysis checks.
- 184 tests and lint pass. A paired 144-episode CPU pilot has no collisions but
  51 ramp-end failures: M2 and substantive training gates do NOT pass. A quantized
  attempt-count bug found by the pilot was repaired and regression-tested.
- Tiny 128-step CPU PPO API smoke passed; no research model saved or CUDA used.
  A visually checked preview shows physical earlier merging after acknowledgment.
- Remaining CPU work and evidence: [CPU_TO_TRAINING_HANDOFF.md](CPU_TO_TRAINING_HANDOFF.md).
  Failure-detection tests are not proof of safe control; hardware is not the blocker.
- All changes remain local; no commit/push/contributor changes. Unrelated homework
  and study artifacts were preserved.

### November 12 2026 continued controller repair and training handoff

- Continued CPU work after the failed pilot. Added stopping reserve on observed
  peer slowing, emergency perception fallback when ramp return is infeasible,
  bounded rear following and real-gap fallback stabilization. Fallback completion
  no longer completes/credits the original agreement. Rear beacons sample the
  acceleration trajectory at their actual generation times.
- Added an isolated offline hold-CONTINUE cancellation oracle, with explicit unknown
  labels for pending proposals and no future information in online policy inputs.
- Post-repair development pilots: 144/384/96 episodes, each with zero collisions
  and ramp departures. Short-headway stress exposures persist; no general safety
  guarantee or final performance claim. See CPU handoff for exact runs/fingerprints.
- Added reproducible mixed training scenarios, real subprocess workers, checkpoint
  overwrite protection, paired evaluation manifests, provenance checks, and paired/
  model-hierarchical bootstrap helpers. Full regression now 200 tests and lint pass.
- Two-process 128-step CPU train/save and four-episode model/normalizer reload smoke
  passed using development seeds 9001/9002. No substantive research training performed.
- Instructor scope is approved. Next is baseline/protocol freeze and desktop budget
  benchmarking, not GPU-required simulation. Broader scientific review remains open.
- All changes local; no commit/push/contributor changes. Study/homework files preserved.

### November 12 2026 authorized publication

- User requested committing and pushing the ReNe implementation and project records.
- Implementation/configurations/tests committed as `9fdccb0` after a fresh check:
  200 tests and lint pass. Documentation is grouped in the following commit.
- Both commits use JoaoLucasVeras as author and committer, with no coauthor trailers.
- Scope excludes unrelated coursework/study notes, proposal drafts, temporary tools,
  generated results/previews, virtual environments and development checkpoints.
- CPU handoff, experiment protocol and completed-slice records are included so
  another machine can reproduce the checks. Clone/update and create a fresh environment;
  do not expect Git-ignored generated assets or laptop dependencies to transfer.
- Push confirmation is reported after checking GitHub's branch head. The documentation
  commit containing this entry and `9fdccb0` are the authorized publication scope.

### November 13 2026 shield measurement and predictor NO_COMPLETION status

- Goal and scope: measure whether the common shield decides outcomes before PPO
  training; trace why the shared predictor returns UNKNOWN; implement fix A.
- Measurement (development seeds 42-44; 972 paired scenarios x 5 managers; densities,
  four disturbances, delay 0/100/800 ms, loss 0/0.2/0.5, mild/moderate/hard):
  B1 and B2 outcomes were identical in 972/972 scenarios; every B2 cancellation came
  from the shield. An offline unshielded hold-CONTINUE replay of all 1,503 shield
  cancellations never recovered feasibility, completed the agreement or collided.
  Random policies cancelled in 972/972 episodes, mostly via infeasible renegotiation
  requests converted to CANCEL; action masking is required before PPO.
  B3 had 123 forced mid-lane-change fallback completions versus 27 for B1/B2.
- Root cause: about 93% of UNKNOWN predictions were `horizon_without_completion`
  (safe rollout that never merged), not missing/stale data, and B2 maps UNKNOWN to
  CONTINUE. Contributing biases: fallback may only reuse the same physical gap, so
  it nearly always ends in a ramp stop; constant-velocity peers plus the speed-based
  stopping reserve make braking/intent predictions pessimistic; frozen intruder
  lateral position makes cut-in predictions optimistic.
- Work completed: predictor status `NO_COMPLETION` (ego fully on the ramp has stopped
  or can no longer fit its lateral move before the usable ramp end), per the
  specification's "demonstrated inability" wording. UNKNOWN still covers missing/
  stale data and insufficient horizon. B2 cancels on NO_COMPLETION + fallback safe
  completion. Status features widened to 0..3; input version `lifecycle-prediction-v5`.
  Files: prediction/rollouts.py, envs/manager_inputs.py, envs/merge_lifecycle_env.py,
  policies/literature_cancellation.py, metrics/episode_metrics.py, tests.
- Validation: 208 tests and lint pass. Rerun of the same 972-scenario grid: outcomes
  unchanged; B2 still never cancels. The predictor now reports NO_COMPLETION 1-2 s
  before the shield in braking/intent cases at medium/high density, but the fallback
  branch is also NO_COMPLETION, and the specified table continues in that case.
- Remaining issues: fallback modelling (fix B) now determines whether B2 can ever
  cancel; decide whether both-branches-fail should cancel (a protocol choice, not
  attributed to S1); peer-braking prediction (C); cut-in lateral prediction (D).
- Publication: local branch `fix/predictor-no-completion`, not committed or pushed.
- Next task: decide fallback design (B) and the both-fail rule, then rerun the measurement.

### November 13 2026 next-gap perception fallback (fix B)

- Goal and scope: give cancellation a physically meaningful alternative. Previously
  the fallback could only reuse the same named gap, so it nearly always ended in a
  ramp stop and B2's "keep fails, fallback succeeds" row could never apply.
- Work completed: a non-connected mainline follower starts one density gap behind the
  rear peer and uses the shared bounded car-following law. After cancellation, the
  ego tracks the nearest large-enough gap between consecutive mainline vehicles,
  with relative speed bounded by sqrt(2 * 0.8 * limit * distance) to avoid overshoot,
  and a 1.5 speed-loop gain while tracking (cruise gain unchanged). It may start a
  lane change into any bounded opening passing the same gap/headway/TTC limits and
  projection as the agreement slot; open road past the last modeled vehicle never
  counts. The fallback keeps the nominal merge location (lane change centered on the
  merge point) but not the canceled plan's timing. Without the location rule, B2
  cancelled healthy nominal agreements because an earlier uncooperative merge looked
  faster. The ramp-end stopping reserve is unchanged. Inputs v6 (56 features) add an
  ideally sensed follower within the 60 m local range; the predictor assumes an
  unseen follower just beyond that range, and the fallback branch uses a 10 s horizon.
  `fallback_next_gap: false` restores the previous behaviour.
- Validation: 214 tests and lint pass. Stale fixtures (body indices, "no merge at
  all") now assert their intent (no agreement completion, no ramp-end violation).
  The same 972-scenario grid: 0 collisions and 0 ramp-end violations for every
  manager. Random early cancels now reach a fallback merge in 369/972 episodes
  (previously 2); about 36-40% success when cancelling in the first 2 s, rare after 4 s.
  B1 cut-ins: 18 fallback merges (previously 0).
- Finding: B2 still equals B1 (972/972), also with triggers at 2 and 3.5 s. The
  shield fires at the same decision step the predictor first sees trouble, because
  the predictor assumes constant peer speed (bias C) and frozen intruder lateral
  position (bias D). Late fallbacks are limited by ramp geometry: after slowing for
  the next gap, the stopping reserve keeps the ego below gap speed.
- Remaining issues: anticipatory prediction (C, D) decides whether any manager can act
  before the shield; review ramp length/trigger timing as a scenario-design choice.
- Publication: local branch `fix/predictor-no-completion`, not committed or pushed.

### November 13 2026 anticipatory prediction (fixes C and D)

- Goal and scope: let the shared predictor see trouble before the truth-based shield.
- Work completed: front state beacons carry the current acceleration (as cooperative
  awareness messages do; `BrakingPulse.accel_at`). The predictor holds a received
  acceleration for 2 s (deadband 0.1 m/s^2), then constant speed, or accelerates up
  to the desired speed. The local sensor reports intruder lateral speed from a 0.1 s
  backward difference (zero at the exact onset), and `predicted_intruder` continues
  that motion until lane-centered instead of freezing the lateral position. Inputs v7
  (58 features): `front_accel_mps2`, `intruder_lateral_speed_mps`. These are declared
  ReNe prediction assumptions, recorded in the specification.
- Validation: 219 tests and lint pass (new: pulse acceleration phases, received
  acceleration input, pessimism versus constant velocity, onset-zero lateral speed,
  continued intruder trajectory). Same 972-scenario grid: 0 collisions/ramp-end
  violations. B2 now initiates 16 cancellations and B3 142, but at the same decision
  step the shield would have fired; B1/B2 outcomes remain identical (972/972).
- Finding: in a 36-episode trace (triggers 3.5/5 s, hard severity) the predictor flags
  a failing keep branch 1-6 s before the shield in 28/30 cases, but the fallback
  branch is NO_COMPLETION in 118/120 such decisions, so the B2 table continues. Causes:
  the unseen follower is placed at the 60 m sensor limit, about 30 m behind the rear
  peer, leaving no usable predicted next gap; and late fallbacks are limited by the
  240 m ramp (random cancels reach a fallback merge 36-40% of the time in the first 2 s,
  about 27% at 4-5 s, rarely later).
- Remaining design choices: rear sensing range or unseen-vehicle assumption; ramp
  length/trigger timing; whether "both branches fail" should cancel (not from S1).
- Publication: local branch `fix/predictor-no-completion`, not committed or pushed.

### November 13 2026 rearward sensing range

- Work completed: `rear_sensor_range_m: 120.0` (rear-radar class) applies to bodies
  behind the ego; the forward `local_sensor_range_m` stays 60 m. The predictor's
  unseen-follower phantom moves to the rearward limit. No input-contract change.
- Validation: 222 tests and lint pass (new: low-density follower detected beyond 60 m,
  forward range unchanged, early nominal fallback prediction is SAFE_COMPLETION).
  972-scenario grid unchanged: 0 collisions/ramp-end violations; B1/B2 identical.
- Finding: before a disturbance both branches are now predicted SAFE, but at the first
  decision after it both flip to NO_COMPLETION together in every braking, intent and
  cut-in trace. The shared controller's ramp-end stopping reserve triggers on
  `slowing_peer` (named front below desired speed) and `uncertain_adjacent_traffic`
  (any sensed intruder) even after cancellation, when the ego targets another gap.
  In the constant-speed predicted world these never clear, so the canceled ego cannot
  regain gap speed. The B2 table continues on NO/NO.
- Next design choice: scope those reserve triggers to the vehicles bounding the gap
  actually being targeted (a shared controller change affecting every manager).
- Publication: local branch `fix/predictor-no-completion`, not committed or pushed.

### November 13 2026 scoped fallback reserve and gap-tracking corrections

- Work completed: after cancellation (next-gap mode) the stopping-reserve triggers read
  the targeted gap: `slowing_peer` uses its leader, and `uncertain_adjacent_traffic`
  counts only an intruder still beside the lane and alongside that gap. Agreement
  behaviour is unchanged. Two corrections to the fix-B gap tracking: the gap center
  is tracked at the mean of its bounding speeds (not the follower's), and a gap is
  usable only if still large enough after the 3 s entry window (closing gaps skipped).
  Shared `_target_gap()` serves alignment and the reserve.
- Validation: 225 tests and lint pass (closing gap skipped, center speed, reserve
  target). 972-scenario grid: 0 collisions/ramp-end violations for every manager;
  fallback merges B1 45 -> 54, random 369 -> 378. B1/B2 still identical (972/972).
- Finding (root limit): the scoped triggers did not change predictions. A rollout
  probe (braking, medium, trigger 3.5 s, t = 4 s) shows the fallback now switching to
  the gap behind the rear peer at 5 s, but the ego is then ~30 m ahead of the rear
  with the gap center ~65 m behind and ~95 m of ramp left; dropping back one whole
  gap is not reachable, and the gap later closes as the follower catches the slowed
  rear. The original gap was open at 4.2 s, but the fallback is held to the nominal
  merge location (fix-B fairness rule). In this geometry (merge near 175-200 m, ramp
  end 240 m, disturbances visible at 3.5-6.5 s) no physically reachable alternative
  remains once a disturbance is visible, so lifecycle decisions cannot change outcomes.
- Next design choice: scenario geometry (ramp/merge-zone length, merge-location
  flexibility applied equally to agreement and fallback, trigger timing), or report
  the equivalence as a geometry-bounded result.
- Publication: local branch `fix/predictor-no-completion`, not committed or pushed.

### November 13 2026 ramp-length sensitivity sweep

- Goal and scope: test whether a longer ramp opens a decision window. Config-only
  override of `ramp_end_m` (merge point 200 m, merge start 140 m unchanged); defaults
  NOT changed. Same 972-scenario development grid (seeds 42-44) per length.
- Results (B1 one-shot / B2 paper-adapted / B3 matched heuristic; merges = agreement +
  fallback completions; 0 collisions and 0 ramp-end violations at every length):

  | Ramp end | B2 differs from B1 | B1 merges | B2 merges | B2 agreement | B2 own cancels | B3 forced commits |
  |---|---:|---:|---:|---:|---:|---:|
  | 240 m | 0.0% | 432 | 432 | 378 | 23 (same step as shield) | 123 |
  | 280 m | 8.1% | 459 | 494 | 355 | 125 | 7 |
  | 320 m | 2.6% | 486 | 486 | 380 | 25 | 0 |
  | 400 m | 0.0% | 648 | 648 | 351 | 0 | 0 |

- Interpretation: the decision window is non-monotone. At 240 m no alternative is
  reachable once a disturbance is visible; at 400 m even a late shield cancellation
  reaches a fallback, so early cancellation adds nothing. Around 280 m B2's own
  cancellations trade 23 lost agreements for 35 more total merges, which is the
  unnecessary-versus-useful cancellation trade-off the research question targets.
  B3's apparent 240 m advantage came mainly from forced mid-lane-change completions
  (emergency commits), which disappear on longer ramps; B3 also renegotiates in
  every episode (972/972) and needs review before it is frozen.
- Evidence: `results/raw/ramp-sweep/ramp-{280,320,400}/` (Git-ignored); 240 m baseline
  `results/raw/shield-measurement/20261113T210328Z`.
- Next design choice: adopt a ramp length (or a small set) where decisions matter,
  then rerun pilots, review B3, and freeze baselines before PPO.
- Publication: local branch `fix/predictor-no-completion`, not committed or pushed.

### November 13 2026 finer ramp sweep and lane-change overrun fix

- Finer sweep (260/270/290/300 m) found 45 ramp-end violations at 290 m: the same
  9 cut-in/low/hard scenarios for every manager. Cause (introduced by the next-gap
  fallback): a lane change eligible at constant speed was followed by gap-tracking
  acceleration, overrunning the ramp end by about 1.5 m. Fix: while a lane change is in
  progress on the ramp, speed is capped so the remaining lateral move finishes on the
  ramp. Regression test for the exact case; a predicate test replaces a fixture that
  had relied on the overrun. 227 tests and lint pass.
- Full rerun of all lengths after the fix (`results/raw/ramp-sweep-v2/`), 972 scenarios
  each, 0 collisions and 0 ramp-end violations for every manager at every length:

  | Ramp end | B2 differs | B1 merges | B2 merges | B2 agreement | B2 own cancels | B3 forced commits | Differing disturbances |
  |---|---:|---:|---:|---:|---:|---:|---|
  | 240 m | 0.0% | 432 | 432 | 378 | 23 | 123 | none |
  | 260 m | 3.9% | 486 | 496 | 351 | 61 | 78 | braking 20, intent 18 |
  | 270 m | 4.6% | 504 | 513 | 354 | 91 | 36 | braking 31, intent 14 |
  | 280 m | 8.1% | 459 | 494 | 355 | 125 | 7 | braking 43, intent 36 |
  | 290 m | 10.7% | 459 | 504 | 353 | 150 | 6 | braking 51, intent 53 |
  | 300 m | 10.8% | 486 | 527 | 356 | 174 | 0 | braking 48, intent 57 |
  | 320 m | 2.6% | 486 | 486 | 380 | 25 | 0 | intent 25 |
  | 400 m | 0.0% | 648 | 648 | 351 | 0 | 0 | none |

- Interpretation: decisions matter in a band of about 260-300 m (peak 290-300 m), only for
  braking and intent mismatch; cut-ins never leave a decision window. 240 m and 400 m
  are no-decision controls. Earlier ramp-sweep numbers (pre-fix) are superseded.
- Proposed protocol (not yet adopted): train on {260, 270, 290, 300} m, hold out 280 m
  (interpolation), report 320 m as an edge case and 240/400 m as controls, per length.
- Publication: local branch `fix/predictor-no-completion`, not committed or pushed.

### November 18 2026 ramp-length protocol adopted

- Decision: train/tune on 260, 270, 290, 300 m; hold out 280 m; 320 m edge case;
  240 and 400 m no-decision controls; report per length. Recorded in
  EXPERIMENT_PROTOCOL.md before any final-test inspection.
- Work completed: `ramp_end_m` is a per-episode reset option (reverts to the base when
  omitted; must lie beyond the merge point). `rene.envs.scenarios` defines the length
  sets and `ramp_role`; `TrainingScenarios` samples only training lengths and rejects
  evaluation-only lengths, including through options. The manifest crosses all eight
  lengths with `ramp_role`; `reset_options` strips reporting labels; `evaluate.py` logs
  `ramp_end_m`/`ramp_role`. `final_eval.yaml` budget 7,680 episodes (192 x 8 x 5).
  `train.py` records `training_ramp_ends_m` in checkpoint metadata.
- Validation: 231 tests and lint pass (training lengths only, rejection paths,
  per-episode revert, manifest roles/unique IDs/option stripping). Development
  smokes on non-reserved seeds: 32-episode evaluation for one_shot and paper-adapted
  across all eight lengths (0 collisions/ramp-end violations); 128-step PPO preflight
  on input v7; a 256-step, 2-subprocess development train with ramp sampling saved
  metadata recording the training lengths (scratch output, not a research model).
- Not done: no final-seed evaluation, no research training, no GPU use. B3 review and
  baseline freeze remain before PPO.
- Publication: local branch `fix/predictor-no-completion`, not committed or pushed.

### November 18 2026 B3 (matched heuristic) review

- Finding: B3 renegotiates in every episode, always RENEGOTIATE_ADVANCE at t = 0, with
  the accepted plan predicted SAFE_COMPLETION and before any disturbance (192/192
  traced episodes on training lengths). The rule picks any candidate predicted to
  finish 0.05 s sooner; with one renegotiation allowed, B3 spends it before anything
  goes wrong. This departs from the revised plan's B3 ranking (TTC/gap margin first).
- Comparison (2,304 scenarios: training lengths 260/270/290/300 m, densities, four
  disturbances, delay 0/100/800 ms, loss 0/0.2, moderate/hard, triggers 3.5/5 s, dev seeds
  42-43; 0 collisions/ramp-end violations for all):

  | Manager | Agreement merges | Total merges | Renegotiations | After a disturbance | Mean agreement merge time |
  |---|---:|---:|---:|---:|---:|
  | B2 | 670 | 972 | 0 | 0 | 9.28 s |
  | B3 current (advance at t = 0) | 855 | 1,065 | 2,304 | 0 | 8.54 s |
  | B3 reactive prototype | 687 | 972 | 24 | 24 | 9.23 s |

  The reactive prototype renegotiates only when the accepted plan is not predicted
  SAFE_COMPLETION, choosing the earliest feasible candidate (ties to delay); it lives in
  the scratch comparison script, not the repository.
- Interpretation: "advance by 1 s at t = 0" is a free improvement on the initial plan in
  every episode; current B3's gains come from merging before the fixed-time disturbance,
  not from reacting to it. Once the plan is predicted to fail, a feasible timing candidate
  almost never exists (24/2,304). A PPO manager would learn the same free improvement,
  so B2 -> B3 -> B4 would mostly measure initial-plan optimization.
- Open decision: how the initial plan and renegotiation availability should be defined
  so that renegotiation measures lifecycle management (see options in the session
  report). B3 is not frozen.
- Publication: local branch `fix/predictor-no-completion`, not committed or pushed.

### November 18 2026 B3 fix, action masking, benchmark and baseline freeze

- B3 free-advance removed: merge zone start 140 -> 175 m, so the nominal plan is
  already the earliest feasible timing (merge point and ramp ends unchanged). Three
  timing-mechanics tests pinned to the old 140 m zone; new test that advance is not
  free by default. Sweep v3 (`results/raw/ramp-sweep-v3/`) reproduces the v2 decision
  band exactly with 0 collisions/ramp-end violations; B3 now equals B2 in 100% of
  scenarios (timing renegotiation adds nothing once the free advance is removed).
- Action masking: `MergeLifecycleEnv.action_masks()` (continue/cancel always; timing
  revisions only when feasible; next-gap/swap never). `train.py`/`evaluate.py` use
  sb3-contrib MaskablePPO (`algorithm: maskable_ppo`, recorded in metadata); new
  dependency `sb3-contrib`. Tests: mask equals shared feasibility flags; masked random
  play never triggers an infeasible-renegotiation override. 234 tests and lint pass.
- Benchmark (`scripts/benchmark_training.py`, Ryzen 7 3700X, RTX 3060 Ti, torch
  2.15.0+cu132 in a separate short-path venv because of Windows path length):
  CPU 143/198/208 vs CUDA 123/176/182 transitions/s at 4/8/12 workers. Decision: CPU,
  8 subprocess workers. GPU not used for training.
- Baseline freeze written (`docs/BASELINE_FREEZE.md`). Scripts added:
  `measure_decision_window.py` (sweep/shield measurement used for the cited numbers),
  `benchmark_training.py`, `learning_curve.py` (pilot to choose the step budget on
  validation scenarios: training lengths, dev seeds 42-43, never final seeds).
- Git author on this machine is `JoaoLucasVeras-ImpacterAI` (machine config, not changed).

### November 18 2026 PPO pilot: agreements have no value (training paused)

- Pilot MaskablePPO (dev seed 101, 8 CPU workers, 426k steps; validation 768 scenarios
  on training lengths, dev seeds 42-43, never final seeds): from about 100k steps the
  policy cancels in every validation episode (768/768) and never completes an agreement,
  yet merges more vehicles than B2 (344 vs 299; B2 210 agreement merges). 0 collisions
  and 0 ramp-end violations. Curve: `results/raw/learning-curve/` (Git-ignored).
- Cause: in this simulator the accepted agreement changes nothing physically. Peers
  only reserve the ego's timing; the rear peer does not yield or hold the gap. The
  perception fallback can use the same or the next gap, so abandoning the agreement
  immediately is optimal under the reward (agreement and fallback completions both +20).
- Consequence: training B4 now would answer "always cancel", which does not address
  agreement lifecycle management. Final PPO training is paused pending a design
  decision: (1) cooperative behaviour that only an active agreement provides (e.g. the
  rear peer holds the gap); (2) a reward premium for agreement completion; or (3) report
  the finding as the result.

### November 18 2026 cooperative rear peer, traffic gap closing, final training start

- Goal and scope: give agreements a value only they provide, after PPO pilots v1/v2
  cancelled 768/768 (fallback 9.63 s vs agreement 9.42 s mean merge time).
- Work completed: rear peer yields while holding the agreement (user decision:
  "Cooperative rear car"); non-cooperating traffic closes to natural headway
  (`traffic_gap_closing`, `natural_headway_s`, `gap_closing_margin_mps`); fallback keeps
  the stopping reserve until the lane change starts (fixes an overrun cooperation
  exposed). Files: merge_lifecycle_env.py, rollouts.py, configs/env/default.yaml, tests.
- Validation: 240 tests pass, ruff clean. Sweep v5 (results/raw/ramp-sweep-v5): 0
  collisions / 0 ramp-end at all 8 lengths; random_valid ~70 merges vs B1 ~490. Pilot v3
  (results/raw/learning-curve-v3): PPO 264 merges / 232 agreement vs B2 262 / 220,
  plateau from 106k steps.
- Decisions: final budget 300k steps x seeds 1-5, CPU 8 workers (benchmark: CPU faster
  than the RTX 3060 Ti for this MLP). BASELINE_FREEZE.md updated.
- Next: train seeds 1-5, then final evaluation on seeds 1001-1005 (7680 episodes/manager).

## Publication snapshot

At the October 1 push, the research documents and then-current roadmap were
published in `ce7d47c`. At the October 10 documentation session, the audit document,
audit script and subsequent roadmap edits were still local, alongside this log
and its navigation edits. Those records and Step 3A were subsequently pushed as
`9976057`. Step 3B and updated records are now authorized for publication in the
commit containing the latest session entry; check local/remote Git heads when resuming.
The subsequent November 12 implementation is committed as `9fdccb0`; its supporting
documentation is in the commit containing the authorized-publication entry above.
Check local/remote heads for push state. Unrelated untracked files must not be staged automatically.

## Session entry template

Append a dated entry; do not overwrite earlier observations when a fix changes
behavior. Link the correcting session instead. Keep the current-status section
short and replace outdated next steps there.

```markdown
### Month day year task description

- Goal and scope:
- Work completed and affected files:
- Decisions and reasons:
- Validation: command, configuration/seed, result, and evidence path.
- Remaining issues or unresolved choices:
- Publication: local only, or commit hash and push confirmation.
- Next task and acceptance evidence:
```

Mark roadmap items complete only when the relevant evidence exists. Distinguish
planned, implemented, tested, scientifically validated, committed and pushed.
Do not store credentials, access tokens or private machine details in this log.
