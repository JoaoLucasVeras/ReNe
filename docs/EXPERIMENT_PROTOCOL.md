# ReNe experiment protocol

Draft November 12, 2026. Scope approved by the instructor per student confirmation.
Engineering pilots are complete for the tested conditions; the final research
protocol/parameter freeze and desktop budget review remain separate gates.

## Question and comparisons

Test when learned post-acceptance lifecycle management adds value beyond an
interpretable cancellation manager and the same manager with heuristic timing
revision. A tie or rule-based advantage is a valid result.

Managers: `one_shot` (context), `rule_cancel` (generic threshold diagnostic),
`paper_cancel_merge_adapted` (B2), `matched_heuristic` (B3), and PPO (B4).
The old `perception_only` alias is not a distinct baseline and the legacy
`heuristic_renegotiate` is not the matched timing manager.

B2 is the documented merge operationalization, not an exact optional-lane-change
system reproduction. Preserve the source/adaptation register and component fixtures.
B3 uses the same shared predictions and +/-1 s menu available to PPO; unsupported
next-gap/order-swap actions remain unavailable.

Every manager uses the same physical controller, rear following, emergency
fallback, shield, receiver admission, channel model, feature clipping and episode
initialization. Report requests separately from shield overrides and protocol outcomes.

## Data separation

Development pilots use seeds 42/43/44, 101 and 102. Tiny API train/evaluation smoke
runs use 9001/9002. None of these is a final test set.

Planned research training seeds: 1, 2 and 3; optionally 4 and 5 if budget permits.
Training uses `TrainingScenarios` with reproducible scenario draws, not one repeated
cut-in condition. Conditions span density, disturbance, delay, loss, severity and
trigger time. Scenario labels/future schedules do not enter the policy vector.

Reserve validation seeds 201-205 for hyperparameters, rewards, thresholds and budget
selection. Use the SAME validation scenarios for candidate configurations. Log every
configuration tested and stop tuning before final test evaluation.

Final test seeds in `configs/experiments/final_eval.yaml`: 1001-1005. The current
evaluation grid has 384 conditions; crossing all five seeds yields 1,920 episodes
per manager/model. `build_manifest` generates explicit unique scenario IDs and
identical options for each comparator. Do not adjust models or thresholds using
the final test outcomes. These seeds have not been used by the development smoke.

The final grid uses moderate disturbances at the default trigger. Report hard,
early/late and out-of-range-channel stress tests separately if included; their
development pilots are not held-out robustness evidence. Any matrix reduction
requires an explicit recorded budget decision before viewing final outcomes.

## Ramp-length protocol (adopted November 18 2026)

Ramp length is a per-episode scenario factor (`ramp_end_m` reset option; merge point
200 m and merge start 140 m fixed). It was fixed from development-seed sweeps (seeds
42-44) before any final-test result was examined; see the project log, November 13.

| Role | Lengths | Use |
|---|---|---|
| Training / tuning | 260, 270, 290, 300 m | PPO training; rule thresholds, heuristic scoring, reward weights and hyperparameters |
| Held-out | 280 m | Evaluation only: interpolation inside the decision band |
| Edge | 320 m | Evaluation only: band edge (decisions matter only for intent mismatch) |
| Controls | 240, 400 m | Evaluation only: no decision window; managers are expected to tie |

- `rene.envs.scenarios` defines these sets. `TrainingScenarios` samples only training
  lengths and raises if an evaluation-only length is requested.
- The evaluation manifest crosses every condition with all eight lengths and tags each
  row with `ramp_role`. Final evaluation is 192 conditions x 8 lengths x 5 seeds = 7,680
  episodes per manager/model.
- Report per length and role; never pool across roles. A learned/rule difference on a
  control length indicates an implementation fault or a hidden safety cost.
- Cut-ins leave no decision window at any tested length; for cut-ins the comparison
  measures fallback quality, not lifecycle decisions.
- Changing these lengths after final-test inspection invalidates the protocol.

## Inputs and proposal abstraction

Current contract: 58 features, `lifecycle-prediction-v7` (v5 adds the `NO_COMPLETION`
prediction status, v6 an ideally sensed non-connected follower, v7 received front
acceleration and sensed intruder lateral speed; see the project log,
November 13). It includes received peer
state/intent residuals, idealized local intruder detection, keep/fallback prediction
summaries, candidate masks/times and local protocol state. Rules use the same
float32 decoded vector, not privileged `info` fields.

The online predictor constructs a separate constant-velocity world only from this
snapshot and fixed shared configuration. It reuses the controller, but never copies
future disturbance schedules, live RNG or unreceived state. Stale/missing inputs and
incomplete horizons are UNKNOWN. Detected intruder lateral position is held fixed
in prediction, not extrapolated from its hidden cut-in schedule.

Timing proposals reserve ego timing; peer trajectories do not change because of
the reservation. Acceptance requires two delivered replies; cancellation supersedes
pending requests. Activation also requires a usable future time and common safety
checks. This is not a full atomic distributed-commit or wireless-stack implementation.

## Outcomes

Report safety first: collision rate, ramp-end failure rate, TTC/headway exposure,
and shield/controller interventions. Current minimum TTC/headway are all-vehicle
applicable pairwise metrics; do not relabel them ego-only or infer ego responsibility
from an unrelated background pair. Adversarial cut-ins can violate headway despite
no collision; retain those observations rather than calling every rollout safe.

Report physical merge completion separately from retained-agreement completion.
`completion_mode` identifies perception fallback versus agreement execution. A
fallback merge after cancellation does not resurrect the original agreement or
count as successful renegotiation.

Completion-time means use successful merges only and always accompany completion
and failure rates. Do not average failed episodes' zero placeholders as fast merges.
Report accumulated active invalidity, message counts, cancellation/proposal outcomes,
acceleration and jerk with their definitions and denominators.

Message cost counts transmissions once, including dropped packets and retries.
Active invalid duration accumulates endpoint-sampled invalid intervals across
recoveries; its 0.2 s discretization is a limitation, not exact event-time truth.

### Offline cancellation counterfactual

At the first applied cancellation, clone the true decision-time simulator state
for an OFFLINE evaluator. The policy never receives this clone or its outcomes.
Replay CONTINUE under the unchanged common shield and the same remaining episode
deadline. Exogenous profiles and RNG state are retained only in this oracle.

Under the declared `offline_hold_continue_v1` convention, cancellation is
unnecessary only if the accepted revision would complete without cancellation or
perception fallback. Pending timing proposals are explicitly unlabelled. This is
a bounded single-intervention/hold-policy counterfactual, not proof that no possible
alternative policy could have saved the agreement. Publish label availability and
exclude unavailable/non-cancellation rows from the conditional-rate denominator.

Raw environment metrics leave the oracle label null. Evaluation/pilot scripts add
it after the actual rollout, keeping future information outside the online interface.

## Analysis and uncertainty

Use paired scenario IDs for comparisons; do not treat differing traffic conditions
as independent algorithm improvements. For each pair, report completion/failure
differences and continuous-outcome differences with sample counts.

`scripts/paired_analysis.py` implements tested paired scenario bootstrap intervals
and model-hierarchical resampling. For PPO, retain each training seed/model identity and report
between-training-seed variation; a pooled episode count is not a substitute for
independent models. Apply the hierarchical/per-model analysis to actual research
models before inferential claims. Zero observed-event bootstrap intervals do not
bound unseen collision risk. Existing `analyze.py` provides descriptive
count/mean/std summaries, not completed significance or hierarchical analysis.

Stratify by disturbance, density and channel condition. Explain where simple rules
match/beat PPO, and distinguish policy requests from common safety intervention.
Do not conclude superiority from the small development pilots or 128-step smoke.

## Reproducibility and execution

Save configurations, explicit scenario manifests, code fingerprint, input/physics/
metric versions, training seed, checkpoint and VecNormalize statistics. Reusing an
old observation vector or mismatched simulator source is refused by evaluation.
Analysis refuses mixed/missing source/schema provenance. Keep old diagnostics
separate when controller or metric definitions change.

`train.py` defaults to CPU, supports real subprocess environments, labels current
runs as unvalidated development, and refuses existing model overwrite. The explicit
development acknowledgement is NOT a scientific gate pass. No substantive PPO
training was performed during the CPU implementation session.

Desktop handoff: fresh environment, dependency checks, full tests, small local
pilot, CPU throughput benchmark, then optional CUDA comparison. A GPU is not a
strict requirement for the current MLP. Choose the final budget from measured
desktop throughput and remaining time before the early-December deadline.
