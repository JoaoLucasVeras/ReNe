# Step 3 — Simulator, communication, and metric audit

Date: 2026-10-01. Audited code: commit `ce7d47c`.

Historical audit: this document preserves the pre-repair findings and numbers.
On October 10, Step 3A geometry/completion repairs were implemented and checked;
see [STEP3A_PHYSICAL_MERGE.md](STEP3A_PHYSICAL_MERGE.md) for current behavior.
The full M2 gate remains open; do not treat all findings below as resolved.

Step 3B additionally implemented abstract delivery/cache, cancellation and shared
manager inputs; see [STEP3B_COMMUNICATION.md](STEP3B_COMMUNICATION.md). The original
age-scalar finding is historical; physical disturbances, rewards and full event
metrics remain unresolved.

## Decision

The CPU-only audit is complete. **M2 scientific validation has NOT passed.**
The implementation is usable as a software scaffold, not yet as evidence that
learned lifecycle management improves physical cooperative merging. Do not train
PPO for the main study or interpret prototype outcomes as research results.
Keep the literature-derived B2 specification separate from the existing
`rule_cancel`, which is a generic threshold manager, not the selected paper.

No simulator/controller/policy behavior was changed during this audit.

## Reproduce the checks

From the repository root, using the installed local virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
.\.venv\Scripts\python.exe scripts/audit_simulator.py
.\.venv\Scripts\python.exe -m ruff check scripts/audit_simulator.py
```

Observed: **7 tests passed; audit script completed; lint passed**. The first test
run produced a cache-permission warning; disabling pytest's cache removed it.
The script emits full JSON decision traces to stdout and does not write result
files. It deliberately uses internal diagnostic fields; it is not a manager API.
These tests establish API/seed behavior, not realistic geometry or safety.

The audit ran 12 episodes (three managers by four disturbances), two additional
zero-/complete-loss episodes, and targeted geometry/action/timeout/outage probes.
All episode comparisons below use seed 42, medium density, moderate severity,
zero delay and loss, unless stated otherwise. This is diagnostic coverage, not a
statistical comparison or a complete density/severity validation.

## Runtime evidence

All three managers (`one_shot`, `rule_cancel`, `heuristic_renegotiate`) returned
the same outcomes in the four tested disturbance conditions:

| Disturbance | Recorded merge | Cancellation | Collision | Recorded merge time | Failed-agreement duration | Shield overrides |
|---|---|---|---|---|---|---|
| None | Yes | No | No | 7.4 s | 0 s | 0 |
| Cut-in | Yes | Yes | No | 7.6 s | 2.4 s | 1 |
| Braking | Yes | No | No | 7.4 s | 0 s | 0 |
| Intent mismatch | Yes | No | No | 7.4 s | 0 s | 0 |

Cancellation does not automatically terminate the episode: the fallback reduces
the ramp vehicle's target speed to 18 m/s and still allows crossing the merge
point. This separation is useful, but crossing is not yet a validated merge.

Hand-checked geometry for the no-disturbance episode:

- At reset: ramp x = 20.548 m; front x = 215 m; rear x = 185 m;
  reference merge point = 200 m. The initial target gap is far ahead of the ego.
- At t = 1 s: rear x = 208 m and the reported TTC becomes 99 s because both
  mainline vehicles have passed the fixed merge point.
- At recorded completion t = 7.4 s: ego x = 200.257 m; rear x = 355.2 m;
  front x = 392.6 m. The ego is not inside the reserved gap.
- Selecting next-gap after t = 1 s makes the reported gap 42 m at t = 2 s,
  although physical front-minus-rear separation is only 32 m: the remaining
  10 m is an artificial bonus, not a different pair of vehicles.
- Complete packet loss leaves message ages at `[1.1, 1.1, 1.1]` s over three
  decisions, rather than increasing with outage duration.
- With the one-shot manager, zero loss and complete loss produce the same
  recorded completion time (7.4 s) in the tested undisturbed episode. The rule
  manager can react to the age scalar; this does not establish delayed data.
- A constructed 1 s timeout reports unsuccessful completion time as 0 s.

## Findings and required corrections

| ID | Priority | Current implementation / consequence | Required correction |
|---|---|---|---|
| A01 | Blocking | Custom `MergeLifecycleEnv` integrates three scalar positions; it does not instantiate a HighwayEnv merge simulation. Installing `highway-env` is not integration. | Explicitly choose a physical simulator implementation; document whether the corrected custom environment or integrated HighwayEnv is primary. |
| A02 | Blocking | Success is ego x >= 200 m, without lateral occupancy, ego-in-gap geometry, vehicle length, or collision-free stabilization. | Add feasible initial accepted plans and physical merge completion/vehicle-overlap criteria. Validate moving target-gap membership. |
| A03 | Blocking | `gap_m` is front-minus-rear plus a synthetic bonus. `ttc_s` is absolute ETA separation to a fixed point with sentinel 99, not longitudinal TTC. `headway_s` is entire target-gap span divided by rear speed. | Replace safety metrics with pairwise bumper clearances and lane/conflict-aware TTC/headways. If keeping ETA separation, name it explicitly and keep it separate. |
| A04 | Blocking | Delay/loss only changes a scalar age; observations still contain current true positions/speeds. No send/delivery queue or received state cache. | Add timestamped messages, scheduled delivery/drop, cached received intent/state, and accumulating age. Separate local sensing, received information, and evaluator-only truth. |
| A05 | Blocking | Cancellation is instant; renegotiation returns immediately to executing. No remote acceptance, retransmission, confirmation, or expiry. | Implement the source-linked protocol/adaptation from `BASELINE_REPRODUCTION_SPEC.md`, with independently timed host/remote states. |
| A06 | Blocking | Next-gap/order-swap add synthetic space; delay/advance instantly changes speed. Planned time and order do not control a physical maneuver. Cut-in repeatedly reapplies a gap penalty instead of adding a vehicle. | Use shared physical candidate plans and bounded controller responses. Model actual cut-in motion; implement real intended-versus-executed behavior for mismatch. |
| A07 | Blocking | A single current-state action shield forces continue -> cancel before a manager can respond to the same invalidity; it omits threshold fields used by the shield from the rule's trigger. It is not continuous collision protection. | Separate predictive lifecycle management from common low-level safety enforcement. Preserve identical safety for all managers; do not weaken protection to manufacture an RL advantage. |
| A08 | Blocking | Failed-agreement duration keeps only the final invalid interval, can continue after cancellation, and persistence affects reward rather than an explicit invalidation event. Unnecessary cancellation tests terminal feasibility; `oracle_horizon_s` is unused. | Implement persistent invalidation events, interval accounting, release timing, and a decision-time counterfactual oracle. |
| A09 | High | Every revised episode that later crosses the point can count as renegotiation success, even after subsequent cancellation. Messages are counters, not delivery events. | Track proposal, acceptance, execution, release and completion by agreement/revision IDs. Define sent/delivered/dropped/retransmitted message counts separately. |
| A10 | High | Decision log combines pre-step feasibility with end-of-step time and geometry. Evaluation discards decision traces. | Store decision-time observations and requested/applied action, then separate transition/interval-end fields; persist traces and metadata. |
| A11 | High | Message reward repeatedly charges the cumulative count; override reward is always zero. Instant speed changes are omitted from acceleration/jerk accounting. | Define event-based costs and physically derived comfort metrics, with hand-calculated reward checks before learning. |
| A12 | High | Rules use unnormalized `info`; PPO sees clipped features; signed relative positions lose negative magnitude under the current scaling. Rule YAML is not wired into manager creation. | Define a shared non-privileged manager input contract, suitable signed scaling/missing-data masks, and effective configuration logging. |
| A13 | High | Evaluation cycles 192 conditions through a total episode budget; analysis pools delay/loss and unrelated run files. No paired CIs, manifests, or training-seed stratification; learned evaluation allows missing normalization. | Use a fixed scenario manifest, explicit episodes per cell, separate pilot/final runs, mandatory model preprocessing, and paired statistical analysis. |

Other observations: disturbances are scheduled after t = 0 acceptance by default
(trigger 5 s); density changes initial span to 38/30/22 m rather than traffic
flow; severity changes a multiplier (0.6/1/1.5). Those code paths exist, but
physical plausibility and density/severity scenario coverage remain unvalidated.
Agreement UUIDs are random, so reproducible observations do not imply byte-identical
event IDs. `perception_only` and `one_shot` currently select the same manager.

## Metric contract to implement

The definitions below are requirements, **not claims about current outputs**.
Freeze exact thresholds, vehicle dimensions, applicability rules, prediction
horizons, and persistence duration in version-controlled configuration before
collecting pilot results.

| Metric | Definition / denominator | Validation required |
|---|---|---|
| Collision rate | Episodes with any physical vehicle-body overlap / all evaluated episodes; monitor during merge and fallback. | Known overlap, separated lanes, contact boundary and substep crossing fixtures. |
| Near-collision rate | Episodes with an applicable conflict-aware safety-margin breach / all episodes; report threshold and exposure. It is not automatically a collision. | Non-closing pairs, disjoint paths, and known approaching conflicts. |
| TTC | Time to first predicted body overlap under the declared motion model for relevant pairs; infinite/not-applicable is not 99 s of measured safety. | Known closing speed and clearance; non-closing and cross-path cases. |
| Headway | Directed bumper clearance divided by the relevant follower speed for a shared lane/path; low-speed/non-applicable handling explicit. | Front/ego and ego/rear fixtures with known lengths/speeds. |
| Merge completion rate | Episodes reaching target lane within a valid physical gap and satisfying configured stabilization/safety criteria / all episodes. | Crossing x alone must not pass; fallback merge may still pass. |
| Merge completion time | Completion time minus episode start, conditional on successful physical completion. Use null for failures; report success rate and timeout count alongside it. | Completion, timeout and collision termination fixtures. |
| Failed-agreement duration | Sum persistent-invalid exposure while an accepted revision remains active, ending at recovery, effective release, replacement, or episode termination. Detection is confirmed after persistence; declare whether accounting starts at first invalid sample (proposed) or confirmation. | Transient invalidity, two disjoint intervals, cancellation pending and revision replacement. |
| Cancellation / unnecessary cancellation | Report cancellations per accepted agreement. At cancellation time, evaluator forks the same state and exogenous scenario and compares retaining the plan under the shared controller/shield. Unnecessary = retaining remains safe, valid and beneficial over the declared horizon; unresolved rollouts are unknown, not unnecessary. Report known-case denominator and unknown fraction. | Safe retained plan, deteriorating plan, shield rescue, finite-horizon uncertainty. Never expose future truth to managers. |
| Renegotiation | Count proposal attempts, accepted revisions, and physically successful execution of the accepted replacement separately. Acceptance rate = accepted / attempts; execution success = successful replacement executions / accepted replacements. Zero denominators are null. | Rejection, expiry, duplicate receipt, acceptance then cancellation, successful replacement. |
| Communication | Sent, delivered, dropped and retransmitted messages by type, including background beacons separately; total per episode and per agreement. | Deterministic delivery/drop queues and retry/ack fixtures. |
| Comfort | Peak absolute physical acceleration and jerk over the same monitored vehicles/window for every manager; also report aggregated exposure if desired. | Bounded acceleration, finite-difference jerk, maneuver transitions; no unlogged speed jumps. |
| Shield intervention | Number of requested/applied action differences and separate low-level controller interventions; rates use eligible decision/control counts. | Already-canceled handling, emergency fallback and rejected candidates. |

For every metric retain episode/scenario ID, seed, manager/config version,
controller/shield version, disturbance schedule, communication settings and
model/training seed where applicable. Report safety and task completion separately
from reward. Oracle metrics must declare their finite-horizon limits.

## Next work, in dependency order

- [ ] **3A: physical scenario contract** — decide primary simulator implementation;
  add vehicle dimensions/lane occupancy, valid initial moving gaps, physical
  completion/collision, and pairwise safety metrics. Test hand-worked cases first.
- [ ] **3B: communication/information contract** — delivery queue, received cache,
  age, explicit protocol substates, and shared manager observations. Test perfect
  communication and prolonged loss without privileged observation leakage.
- [ ] **3C: physical disturbances and candidates** — bounded cut-in/braking/mismatch,
  common candidate trajectories and actual acceptance/execution. Eliminate bonuses.
- [ ] **3D: metric/event accounting** — implement the table, oracle and decision-time
  traces. Freeze definitions; add regression tests that fail on current artifacts.
- [ ] **3E: M2 review** — no-disturbance, every disturbance, density/severity sweep,
  delayed/lost communication, fallback and all proposal fixtures. Establish safety
  and meaningful baseline discrimination without requiring PPO to win.
- [ ] Only then implement/test B2 under M3, followed by matched B3 under M4.

The immediate next task is **3A**, not PPO training. Source-adaptation acceptance
from the instructor remains a separate M1 dependency. No GPU is needed for these
repairs or deterministic checks; the desktop is needed later for larger runs.

## Reviewed implementation

- `src/rene/envs/merge_lifecycle_env.py`: reset, properties, step, disturbances,
  actions, integration, observation, decision logging, metric finalization.
- `src/rene/agreements/{state,protocol,feasibility}.py` and
  `src/rene/safety/shield.py`: lifecycle and action protection.
- `src/rene/disturbances/base.py`, `src/rene/policies/rule_based.py`,
  `src/rene/metrics/episode_metrics.py`: communication proxy, managers, metrics.
- `scripts/evaluate.py`, `scripts/analyze.py`, existing core/environment tests.
- `scripts/audit_simulator.py`: added reproducible diagnostic evidence for this audit.
