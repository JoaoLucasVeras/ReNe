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
