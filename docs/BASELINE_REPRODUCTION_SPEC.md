# ReNe Cancellation Baseline Reproduction Specification

Version: 0.1 — implementation specification; final experiment parameters are not frozen.

Date: October 1, 2026

Status: Step 2 document complete. Baseline implementation, simulator validation, and instructor acceptance of the maneuver adaptation remain pending.

Related documents: [Paper selection](BASELINE_PAPER_SELECTION.md), [overlap check](RELATED_WORK_OVERLAP_CHECK.md), [roadmap](PROJECT_ROADMAP.md).

## 1. Purpose and claim boundary

Specify an interpretable cancellation reference and an explicitly adapted merge baseline before implementing B2, extending it to B3, or training PPO.

Use two separately named components:

- `paper_cancel_reference`: a small optional-lane-change reference harness for source behavior tests.
- `paper_cancel_merge_adapted`: the proposed ReNe B2 manager, using the same cancellation framework but an explicit merge-specific benefit calculation.

The second component is a **literature-derived adaptation**, not a full replication of the original traffic/network experiment. Passing a reference harness verifies component behavior; it does not reproduce the paper's reported system-level results.

## 2. Sources and traceability

**S1:** Molina-Masegosa et al., *When Cooperation Should End: Maneuver Coordination Cancellation for Connected Automated Driving*, IEEE VTC2026-Spring. [Author record](https://arxiv.org/abs/2606.22052), [full postprint](https://arxiv.org/pdf/2606.22052). The arXiv DOI identifies the postprint.

| Source location | Extracted behavior/parameter |
|---|---|
| S1 II, page 3 | Lane incentive favors speeds nearer the desired speed; comfort bound −3 m/s². |
| S1 III.B, page 4 | Cancellation trigger: loss of lane-change incentive. |
| S1 III.A, page 3 | Host repeats cancellation every 100 ms until remote Intent or execution timeout; remote aborts on receipt and replies within 100 ms. |
| S1 IV, page 4 | Prediction horizon 5 s; execution timeout CIF + 3 s; negotiation margin 1 s. |

These source facts are distinct from all ReNe design choices below. [S1](https://arxiv.org/pdf/2606.22052)

**S2:** *Towards effective V2X maneuver coordinations: state machine, challenges and countermeasures*, IEEE VTC2024-Fall. [Author manuscript](https://uwicore.umh.es/files/paper/2024_internacional/VTC-Fall_2024-Toyota_UMH_v10_final.pdf). Its state-machine and failure taxonomy inform protocol background; it does not supply the new cancellation trigger.

**S3:** *AI-Assisted Maneuver Coordination for Connected and Automated Vehicles*. [Author manuscript](https://iris.polito.it/retrieve/df3a71f2-389c-42a6-ac2c-6c1de47e3fe3/ManeuverCoordination.pdf). Section III.A describes lane incentive using minimum preceding-vehicle speeds. Its six-second prediction horizon and −2 m/s² comfort setting must not be silently substituted for S1's settings.

### Unresolved source precision

The inspected material does not establish a complete executable incentive/predictor implementation, its numerical tolerance, or every boundary case. The reference formula below is our declared operationalization of the qualitative criterion. Follow-up source clarification may improve fidelity; any claim of exact reproduction must reflect what has actually been verified.

## 3. Reference harness: optional lane change

This harness exercises decision and protocol components using supplied lane-speed estimates and scripted events. It does not require an entire multilane simulator.

### Declared operationalization

Inputs in m/s: desired speed `v_des`, achievable current-lane speed `v_current`, and achievable target-lane speed `v_target`. Speeds are nonnegative and capped at `v_des` before comparison.

```text
D_current = v_des - min(v_current, v_des)
D_target  = v_des - min(v_target, v_des)
incentive = D_current - D_target
requested_action = CONTINUE if incentive > epsilon else CANCEL
```

`epsilon = 0` for exact arithmetic fixtures. This is a ReNe implementation choice, not a published numerical threshold. Actual predictor aggregation and a floating-point tolerance must be documented before running realistic reference scenarios. No persistence window is added to this reference predicate; a smoothed variant must be labeled separately.

### Reference fixture expectations

| Fixture | Inputs/event | Expected component behavior |
|---|---|---|
| R1 | Desired 30, current 20, target 27 | Incentive +7; continue. |
| R2 | Desired 30, current 27, target 20 | Incentive −7; request cancel. |
| R3 | Desired 30, current 25, target 25 | Tie; request cancel under the declared epsilon convention. |
| R4 | Desired 30, both estimates above 30 | Both capped; tie behavior. |
| R5 | R1 followed by R2 followed by R1 | Once cancellation starts, do not revive that agreement merely because incentive recovers. |
| R6 | Invalid negative/non-finite speed | Reject input or enter a logged unavailable-estimate branch; never silently make a numerical decision. |

## 4. Merge adaptation: proposed B2 contract

An on-ramp vehicle's need to merge is distinct from the value of a particular accepted gap/time agreement. Define incentive relative to retaining **that agreement**, compared with ending coordination and using the common fallback controller.

The following logic is entirely a ReNe adaptation. It must be reviewed through pilot scenarios before final use.

### Shared deterministic predictor

From one timestamped observation snapshot, predict two branches:

- `P_keep`: execute the accepted gap/time plan with the common controller.
- `P_fallback`: end that agreement and use the common perception-based fallback.

Both branches use identical received data, motion assumptions, safety constraints, and integration resolution. Predictions must not clone future disturbance schedules, random-generator state, or unrevealed simulator truth. A default neighbor predictor uses received intent when usable and constant-velocity extrapolation otherwise; prediction error is expected and evaluated.

Return, for each branch:

```text
status: SAFE_COMPLETION | INFEASIBLE | UNKNOWN
estimated_completion_time_s: finite value only for SAFE_COMPLETION
constraint_margins: gap, conflict/headway, acceleration, ramp-end
reason_code
prediction_horizon_s
input_timestamp and age
```

`INFEASIBLE` requires an explicit constraint violation or demonstrated inability to complete before the usable ramp ends. A rollout that merely ends before completion is `UNKNOWN`, not proof of infeasibility.

### Proposed decision rules

| Keep branch | Fallback branch | B2 requested action |
|---|---|---|
| Safe completion | Safe completion | Compare completion times as below. |
| Safe completion | Infeasible or unknown | Continue. |
| Infeasible | Safe completion | Cancel with reason `accepted_plan_infeasible`. |
| Any other combination | Any other combination | Continue with reason `prediction_unresolved`; shared emergency shield remains active. |

When both branches predict safe completion:

```text
benefit_s = T_fallback - T_keep
if benefit_s < -switch_margin_s:
    request CANCEL, reason accepted_plan_slower
else:
    request CONTINUE, reason retained_or_tied
```

The pilot margin is 0 s. Ties retain the agreement to avoid cancelling useful cooperation solely because of an equal time estimate. This tie rule deliberately differs from the reference predicate and is an adaptation, not attributed to S1. Any later positive margin is validation-tuned and recorded.

No additional gap/TTC/message-age trigger is attributed to the source. Immediate safety overrides belong to the common shield. Communication uncertainty may change predictions, but an added stale-message cancellation rule must have its own declared provenance and comparator treatment.

### Horizon convention

Reference fixtures may use the source-associated five-second horizon. For merge pilots, use a declared bounded horizon that can cover the remaining accepted plan: `min(remaining_episode_s, max(5 s, remaining_planned_time_s + 3 s))`. This adaptive horizon is a ReNe choice. Log the actual horizon and classify incomplete rollouts as unknown. Compare sensitivity to a fixed horizon before freezing the protocol.

### Adapted fixture expectations

| Fixture | Predictor result | Expected request |
|---|---|---|
| A1 | Keep safe at 4 s; fallback safe at 6 s | Continue; benefit +2 s. |
| A2 | Keep safe at 7 s; fallback safe at 5 s | Cancel; benefit −2 s. |
| A3 | Both safe at 5 s | Continue under adapted tie rule. |
| A4 | Keep infeasible; fallback safe | Cancel. |
| A5 | Keep safe; fallback infeasible | Continue. |
| A6 | Neither branch demonstrably safe/complete | Logged unresolved prediction; common shield applies independently. |
| A7 | Horizon ends before either completes | Unknown, not automatically infeasible. |
| A8 | Immediately unsafe actual maneuver but manager requests continue | Shield applies fallback and logs a safety override independently. |

## 5. Cancellation execution and communication

Use a separate protocol substate so a manager request and completed disengagement are distinguishable. Planned substates are `ACTIVE`, `CANCEL_PENDING`, `REMOTE_RELEASED`, `CANCEL_CONFIRMED`, and `TIMED_OUT`. These names are ReNe interface choices.

Implementation requirements:

- A cancellation request is idempotent; repeated manager requests do not reset its start time.
- Bind messages to agreement ID, revision, sender, receiver, generation time, and sequence number.
- Deliver messages through an event queue with declared delay/loss behavior.
- Match receipts to the active session; stale messages cannot terminate a different agreement.
- Record transmission, delivery, remote release, confirmation, and timeout separately.
- Keep the agreement unavailable for revision while cancellation is pending.
- Define deterministic ordering for simultaneous delivery, completion, and timeout events; reject late session messages after terminal processing.
- Maintain safe physical control while cancellation is in progress; never assume undelivered messages have changed the remote vehicle's behavior.

For protocol fidelity tests, use a scheduler that represents 100 ms events. The current 200 ms dynamics timestep cannot directly reproduce that cadence; use a separate communication clock or refine dynamics resolution equally for all managers.

Deterministic test cases should cover successful delivery, first-packet loss followed by retry, lost reply, all-packet loss until timeout, duplicate requests, stale acknowledgment, and cancellation concurrent with completion. These are proposed test cases; they are not claims that the source evaluated all these conditions.

The post-acceptance study can begin with an accepted agreement and omit initial negotiation. Log the assumed initialization and do not claim that initial request/response behavior was reproduced.

## 6. Required observation contract

| Input | Available in current prototype? | Required work |
|---|---|---|
| Ego state, desired speed, distance to merge | Internally available | Expose in a typed shared snapshot with units. |
| Neighbor positions/speeds | Internally available as true state | Define sensor/received-message origin; stop treating internal truth as delivered V2X data. |
| Target gap, merge order, planned time | In agreement record | Expose consistently to every manager. |
| Received intent and timestamps | No actual received trajectory buffer | Add delivery and last-received-data storage. |
| Keep/fallback rollout | Absent | Add common deterministic predictor; verify controller semantics first. |
| Current/target lane-speed estimate | Absent for an optional lane-change task | Supply explicit reference fixture values; richer reference scenarios remain separate. |
| Host and remote cancellation states | Absent | Add protocol substates, event queue, and release tracking. |

B2/B3 may use physical-unit snapshots rather than normalized arrays, but PPO must receive equivalent information with sufficient precision. Avoid clipped-away features or unrestricted `info` fields that grant the rules more information than the learned manager.

Evaluation oracles are separate. Only offline metric computation may use future true simulator trajectories.

## 7. Current code gaps confirmed during specification

Inspection of `src/rene/envs/merge_lifecycle_env.py`, `agreements/protocol.py`, `agreements/state.py`, and `disturbances/base.py` found:

1. `protocol.py` constructs an accepted agreement; it does not exchange or acknowledge cancellation messages.
2. The environment switches directly to `CANCELED`, activates fallback, and increments one message count.
3. Delay/loss affects synthetic message-age information, but no received vehicle-state/intent buffer exists.
4. The property called `ttc_s` is an absolute difference between arrival times at the merge point. It is not conventional longitudinal TTC. Rename or replace it and document the conflict metric before using source thresholds.
5. Next-gap and order-swap actions add a synthetic gap bonus; they do not yet identify real alternative vehicle gaps.
6. Completion is triggered by crossing the merge point; this alone does not validate placement in a collision-free target gap.
7. Unnecessary cancellation is labeled using end-of-episode feasibility, rather than a declared counterfactual at the cancellation decision.
8. Failed-agreement duration is finalized from the current invalidity timestamp; recovery can clear the timestamp and erase previously invalid intervals.
9. No lane-speed incentive or keep/fallback predictor is implemented.

These are findings from code inspection, not observed runtime failures. M2 must resolve them or explicitly narrow the experiment before the baseline can be called validated. Existing synthetic gap behavior is unsuitable as evidence of realistic counter-proposal feasibility.

## 8. Safety and fair comparator design

- Reuse one low-level controller, shield, recipient policy, received-data snapshot, and protocol executor across B2, B3, and B4.
- B2 requests continue/cancel; B3 adds deterministic selection from the same candidates offered to B4.
- Keep manager decisions separate from shield interventions; record both.
- Do not weaken the shield to manufacture an advantage for learning.
- Use the predictor and counter-proposal assessments consistently; give PPO equivalent accessible features or declare a separate information-access ablation.
- Distinguish emergency disengagement from incentive-based cancellation in both metrics and traces.
- Keep exogenous scenario randomness independent of action-dependent communication events so paired traffic disturbances remain comparable.

## 9. Parameter provenance register

The S1 values are listed once in Section 2. All additional parameters below are ReNe settings and remain subject to pilot validation.

| Setting | Pilot convention | Freeze requirement |
|---|---|---|
| Reference incentive epsilon | 0 for exact fixtures | Document numerical tolerance in actual predictor. |
| Merge switch margin | 0 s | Tune only on validation data if changed. |
| Merge horizon | Adaptive rule in Section 4 | Record sensitivity and selected rule. |
| Dynamics and manager interval | Existing 0.2 s / 1 s | Audit and apply equally across methods. |
| Gap, headway, conflict constraints | Existing prototype values are placeholders | Validate semantics and engineering/literature rationale under M2. |
| Counter-proposal menu/attempt limit | Shared bounded menu | Define physically meaningful candidates under M4. |
| Stale-data handling | Extrapolate last usable intent; unknown if unavailable | Freeze admissibility and sensor fallback rules. |

## 10. Logging and metrics

Every decision trace should store snapshot provenance, agreement ID/revision, prediction outcomes, estimated completion times, benefit, requested action/reason, shield result, protocol substate, and configuration version.

Record separate times for manager cancellation request, first successful delivery, remote release, acknowledgment, and timeout. Report detection delay and protocol delay separately.

Do not equate time from initial agreement creation to abortion with time spent managing an invalid agreement. Define both if useful. A fallback merge may succeed after the original agreement is canceled; distinguish original-agreement completion from vehicle merge success.

Unnecessary-cancellation labels require a declared offline counterfactual at the decision time. If that counterfactual is not implemented, label the metric unavailable rather than returning a misleading boolean.

## 11. Implementation sequence

1. Complete the M2 simulator/metric audit using the gaps in Section 7.
2. Add typed observation and prediction result records.
3. Implement reference incentive fixtures and protocol tests.
4. Implement keep/fallback prediction without future-information leakage.
5. Implement the adapted B2 table and reason codes.
6. Connect protocol execution, safe fallback, and logging.
7. Validate all reference/adaptation fixtures plus at least 100 seeded pilot episodes.
8. Review instructor acceptance of the adaptation and document the claim boundary.
9. Freeze B2 before implementing matched B3 and running the baseline comparison.

Suggested new modules: `policies/literature_cancellation.py`, `agreements/cancellation.py`, and `prediction/rollouts.py`. Their names are implementation suggestions, not files already created.

## 12. Acceptance and remaining decisions

- [x] Source behavior and locations recorded.
- [x] Original behavior separated from adaptation choices.
- [x] Inputs, decision rules, timing needs, and parameter provenance specified.
- [x] Reference examples and expected results defined.
- [x] Current simulator gaps mapped to required work.
- [ ] Optional-lane-change operationalization accepted as sufficiently faithful, or refined with source clarification.
- [ ] Instructor confirms whether the merge adaptation meets the requested reproduction scope.
- [ ] M2 dynamics, communication, and metric requirements pass.
- [ ] Reference and adapted implementations pass automated and scenario tests.
- [ ] Baseline pilot report reviewed and final parameters frozen.

The specification is ready to guide the next audit and implementation. M1's instructor-guidance gate remains open; no implementation or reproduction result is claimed by this document.
