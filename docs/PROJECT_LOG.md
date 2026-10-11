# ReNe Project Progress and Decision Log

Last updated: October 10, 2026

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
  Instructor acceptance of the lane-change-to-merge adaptation remains pending.
- Step 3: CPU-only audit completed; the M2 simulator-validation gate has **not passed**.
- Simulator repairs, literature-derived B2 implementation, matched B3 validation,
  and main PPO experiments remain pending. Existing rules are prototype managers.
- Step 3A is implemented for the bounded physical fixtures; 35 tests pass.
  See [the implementation record](STEP3A_PHYSICAL_MERGE.md). The custom simulator
  remains primary; full M2 validation is still open.
- Step 3B is implemented for the abstract channel/protocol fixtures; current suite
  has 82 passing tests. See [the communication record](STEP3B_COMMUNICATION.md).
- Next implementation task: Step 3C, physical disturbances and candidate
  acceptance/execution. M2, literature baselines and final metrics remain open.
- Desktop setup remains unverified. Reported hardware: Ryzen 5 3600, RTX 3060 Ti,
  32 GB RAM. No GPU is needed for the immediate deterministic repairs.

## Start the next session here

1. Read this log, the roadmap's current focus, and the [audit](SIMULATION_AND_METRIC_DEFINITIONS.md).
2. Check `git status` and the current commit; preserve unrelated or uncommitted work.
   The publication snapshot below is historical, not a substitute for checking Git.
3. Review Step 3A/3B implementation records and remaining audit limitations.
4. Keep the custom physical simulator for now; HighwayEnv integration remains optional.
5. Agree on Step 3C's physical disturbance and candidate/acceptance fixtures before implementation.
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

## Publication snapshot

At the October 1 push, the research documents and then-current roadmap were
published in `ce7d47c`. At the October 10 documentation session, the audit document,
audit script and subsequent roadmap edits were still local, alongside this log
and its navigation edits. Those records and Step 3A were subsequently pushed as
`9976057`. Step 3B and updated records are now authorized for publication in the
commit containing the latest session entry; check local/remote Git heads when resuming.
Unrelated untracked files must not be staged automatically.

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
