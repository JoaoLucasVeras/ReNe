# ReNe Revised Project Goal and Execution Plan

## 1. Project title

**ReNe: When Does Learned Post-Acceptance Agreement Management Improve V2X Cooperative Merging?**

## 2. Revised project goal

The goal of ReNe is to determine whether reinforcement learning is actually necessary for managing an accepted cooperative freeway-merge agreement when traffic behavior or V2X communication changes after acceptance.

The project will not assume that PPO is better than an interpretable rule-based manager. Instead, it will compare increasingly capable agreement-management methods under the same simulated scenarios:

1. One-shot agreement execution with no lifecycle management.
2. A recent literature-derived rule-based maneuver-cancellation method.
3. The same rule-based cancellation method augmented with deterministic heuristic renegotiation.
4. A learned PPO lifecycle manager with the same renegotiation options.

Every method must use the same simulated traffic, V2X impairment model, low-level vehicle controller, counter-proposal generator, feasibility checker, and safety shield. The final contribution will be an empirical account of the conditions in which learned lifecycle management provides value over simple rules, as well as the conditions in which it does not.

## 3. Motivation

An accepted cooperative maneuver is not guaranteed to remain appropriate. A human-driven vehicle may enter a reserved gap, a cooperating vehicle may brake unexpectedly, communicated intent may no longer match observed behavior, or V2X messages may become delayed, lost, or stale.

Fixed rules can respond to many of these events. Because the observation space is compact and structured and the action space is small, a rule-based or model-based manager may already perform very well. Therefore, the project must test whether learning offers a meaningful advantage rather than treating reinforcement learning as the assumed solution.

The project is specifically about **post-acceptance agreement lifecycle management**, not generic reinforcement learning for freeway merging and not end-to-end vehicle control.

## 4. Central research question

**Under what traffic and V2X communication conditions does a learned post-acceptance lifecycle manager outperform interpretable rule-based cancellation and matched heuristic renegotiation without degrading empirical safety?**

### Supporting questions

1. How much value is gained by monitoring an accepted agreement and cancelling it when it deteriorates?
2. How much additional value comes from adding deterministic renegotiation to rule-based cancellation?
3. Does PPO improve decisions beyond a heuristic that has access to the same observations and counter-proposals?
4. In which disturbance and communication regimes do rules remain sufficient?
5. Does any performance improvement require more shield interventions or introduce worse safety outcomes?

## 5. Hypotheses and valid outcomes

### Primary hypothesis

The learned manager may reduce failed-agreement duration and unnecessary cancellations under combinations of traffic disturbances and communication uncertainty, while maintaining safety performance comparable to the matched heuristic when both use the same safety shield.

### Null or negative result

A well-designed rule-based or model-based manager may match or outperform PPO because the decision problem is compact and structured.

### Valid semester outcomes

- **Positive:** PPO improves agreement-management metrics without a meaningful safety degradation.
- **Conditional:** PPO helps only under specific combined or uncertain conditions.
- **Equivalent:** The matched heuristic performs similarly, making learning unnecessary for the tested problem.
- **Negative:** PPO is less reliable, less interpretable, or less efficient than the rule-based methods.

All four outcomes answer the central research question and should be reported honestly.

## 6. Experimental comparison

| ID | Manager | Purpose |
|---|---|---|
| B0 | Perception-only fallback | Optional reference for merging without an explicit agreement; it must be implemented distinctly before being reported. |
| B1 | One-shot agreement | Continues the accepted agreement unless the common emergency shield intervenes. |
| B2 | Literature-derived rule cancellation | Reproduces or faithfully adapts a recent published maneuver-cancellation method. |
| B3 | Matched heuristic renegotiation | Uses B2 cancellation logic and deterministically selects among the same counter-proposals available to PPO. |
| B4 | Learned lifecycle manager | Uses PPO to select continue, cancel, or one of the shared bounded counter-proposals. |

### Key comparisons

- **B1 versus B2:** value of post-acceptance monitoring and cancellation.
- **B2 versus B3:** value of having renegotiation capability.
- **B3 versus B4:** value contributed specifically by learning.

B3 is the most important baseline. If B4 beats B2 but not B3, the improvement comes from adding renegotiation rather than from reinforcement learning.

## 7. Fairness requirements

The following components must be identical across B2, B3, and B4:

- Initial vehicle states and paired scenario seeds
- Traffic and V2X disturbances
- Observation information, except information inherently unused by the published B2 method
- Low-level acceleration and merge controller
- Candidate counter-proposal generator for B3 and B4
- Counter-proposal feasibility checks
- Safety shield and override behavior
- Maximum renegotiation attempts
- Simulation duration and decision interval
- Evaluation metrics and logging

The heuristic must not receive privileged simulator state if PPO does not receive it. Offline privileged state may be used only to calculate evaluation labels such as unnecessary cancellation.

## 8. Literature-derived cancellation baseline

### Selection criteria

Select one recent paper that:

- Addresses cooperative or automated maneuver cancellation, invalidation, or safety monitoring
- Defines explicit cancellation conditions, formulas, or state transitions
- Uses inputs that can be represented in the ReNe simulator
- Provides enough technical detail to implement a defensible adaptation
- Does not depend on unavailable proprietary hardware or data
- Falls within the literature-review date requirements

### Reproduction specification

Before implementation, document:

```text
Source paper and citation:
Original domain and maneuver:
Required state variables:
Cancellation formula or logic:
Thresholds and persistence rules:
Original assumptions:
Components reproduced exactly:
Adaptations made for ReNe:
Components that could not be reproduced:
Validation scenarios:
```

The existing gap, TTC, and message-age threshold manager is a prototype. It must not be described as a published-method reproduction until its logic and parameters are tied to a selected source.

## 9. Matched heuristic renegotiation baseline

The heuristic and PPO must use one shared counter-proposal generator. The initial proposal menu is:

- Delay the planned merge by a bounded increment
- Advance the planned merge by a bounded increment
- Select the next feasible gap
- Swap merge order when feasible

The shared feasibility checker should remove unsafe or impossible proposals. The heuristic should then select deterministically using frozen criteria such as:

1. Largest predicted minimum TTC
2. Largest predicted time headway or gap margin
3. Lowest merge delay
4. Lowest communication cost
5. Stable deterministic tie-breaking order

The exact score, weights, and tie-breaking behavior must be fixed using training or validation scenarios before the final test set is examined.

## 10. System boundary and V2X scope

ReNe uses an abstract V2X-aware simulation. It represents the decision consequences of:

- Accepted cooperative merge agreements
- Message delay and age
- Packet loss
- Stale or inconsistent communicated intent
- Agreement messages and revisions
- Bounded renegotiation counter-proposals

It does not currently model a complete C-V2X, NR-V2X, or DSRC radio stack, wireless propagation, interference, standardized message encoding, or network routing. Claims should therefore refer to a **V2X-aware agreement-management simulation**, not a complete V2X network simulation.

## 11. Scenario design

### Control scenario

- No disturbance and reliable communication

### Individual disturbances

- Non-connected vehicle cuts into the reserved gap
- Cooperating or nearby vehicle brakes unexpectedly
- Observed motion differs from communicated intent
- V2X message delay
- Packet loss or stale messages

### Combined and held-out conditions

- Cut-in plus delayed communication
- Braking plus packet loss
- Intent mismatch plus stale messages
- Disturbance timings or severities not used for training

### Condition factors

- Low, medium, and high traffic density
- Multiple disturbance severities
- Delay levels such as 0, 100, 300, and 500 ms
- Packet-loss rates such as 0%, 5%, 10%, and 20%

The pilot experiment may use a targeted subset. The final matrix should include enough isolated and combined conditions to identify where learning adds value.

## 12. Metrics and decision criteria

### Safety metrics

- Collision rate
- Near-collision rate
- Minimum TTC
- Minimum time headway
- Safety-shield override rate and reason

Safety is a constraint. An efficiency improvement does not count as a success if it produces a meaningful safety degradation.

### Agreement-management metrics

- Completed-merge rate
- Failed-agreement duration
- Unnecessary-cancellation rate
- Correct continuation rate, once formally defined
- Renegotiation attempt, acceptance, and success rates
- Lifecycle messages per successful merge

### Efficiency and comfort metrics

- Merge-completion time
- Ramp or maneuver delay
- Peak absolute acceleration
- Peak jerk
- Mainline disturbance, if supported

### Learning and runtime metrics

- Training return and reward components
- Training stability across seeds
- Environment steps per second
- Wall-clock training time
- CPU, GPU, RAM, and VRAM utilization for representative runs

Total reward is a training diagnostic, not the primary proof that PPO is better. Final claims must rely on interpretable safety and operational metrics.

## 13. Data splitting and statistical design

- Use separate training, validation, and final-test seeds.
- Tune rule thresholds, heuristic scoring, reward weights, and PPO hyperparameters without examining final-test results.
- Replay identical test scenarios for every manager using paired seeds.
- Train at least three independent PPO seeds; five is preferred.
- Preserve every completed episode and record failed runs rather than silently deleting them.
- Report aggregate and per-condition results.
- Report means, medians where useful, standard deviations, effect sizes, and 95% confidence intervals.
- Use paired episode differences for continuous outcomes when scenarios are replayed identically.
- Use appropriate confidence intervals for collision and other binary rates.
- Do not interpret a nonsignificant difference as proof of equivalence.
- Define an acceptable safety margin in advance before making any non-inferiority claim.

## 14. Current implementation status

### Already available

- Agreement lifecycle state machine
- Continue, cancel, and several bounded renegotiation actions
- Prototype threshold-based cancellation manager
- Prototype heuristic renegotiation manager
- PPO training script and configuration
- Shared deterministic feasibility checker
- Shared action-level safety shield
- Cut-in, braking, intent-mismatch, delay, and packet-loss conditions
- Seeded evaluation and episode-level CSV metrics
- Basic summary generation

### Gaps created or clarified by the professor's feedback

- The cancellation baseline is not yet a documented reproduction of a recent paper.
- The heuristic currently uses only the next-gap counter-proposal, while PPO has several renegotiation actions.
- The counter-proposal generator and selection process must be explicitly shared and matched.
- The perception-only and one-shot managers are currently equivalent in implementation and cannot yet be reported as distinct baselines.
- The final analysis needs confidence intervals, paired comparisons, effect sizes, and delay/packet-loss breakdowns.
- Multiple independently trained PPO seeds must be supported and aggregated.
- Final PPO training should wait until B2 and B3 pass their acceptance gates.

## 15. Implementation phases and acceptance gates

### Phase 1: Select and specify the published baseline

Tasks:

- Search recent literature and choose the cancellation method.
- Extract its equations, thresholds, state variables, and assumptions.
- Complete the reproduction specification.
- Identify simulator adaptations and obtain instructor confirmation if the adaptation is substantial.

Acceptance gate:

- Another reader can trace every cancellation rule to the source paper or to a clearly labeled ReNe adaptation.

### Phase 2: Implement B2

Tasks:

- Implement the published cancellation logic as a separate manager.
- Put thresholds in version-controlled configuration.
- Add unit tests at threshold boundaries.
- Add scenario tests for valid, invalid, transient, and persistently invalid agreements.
- Log the triggering condition for every cancellation.

Acceptance gate:

- B2 completes at least 100 seeded pilot episodes without errors and behaves as expected in hand-checked scenarios.

### Phase 3: Build the shared counter-proposal system

Tasks:

- Implement all permitted proposal transformations in one shared module.
- Evaluate every proposal with the common feasibility checker.
- Return the same feasible proposal set to B3 and B4.
- Log generated, rejected, selected, accepted, and failed proposals.

Acceptance gate:

- Automated tests show that B3 and B4 receive identical candidate sets for identical states.

### Phase 4: Implement and validate B3

Tasks:

- Add deterministic proposal ranking.
- Freeze scoring weights and tie-breaking behavior.
- Test feasible and infeasible renegotiation cases.
- Compare B2 and B3 on paired pilot scenarios.

Acceptance gate:

- B3 can successfully use every allowed proposal type in a constructed test and falls back safely when none is feasible.

### Phase 5: Freeze baseline behavior

Tasks:

- Run B1, B2, and B3 across a pilot matrix.
- Inspect raw decisions and shield overrides.
- Confirm shared controllers, shield, seeds, and metrics.
- Fix implementation errors before training PPO.
- Freeze baseline configurations for final testing.

Acceptance gate:

- A baseline report demonstrates plausible behavior and contains no unresolved fairness mismatch.

### Phase 6: Train B4

Tasks:

- Verify random-agent and short PPO smoke runs.
- Train first on simplified disturbances.
- Add traffic and communication randomization gradually.
- Tune only on training and validation scenarios.
- Train at least three final independent seeds after configuration freeze.

Acceptance gate:

- Every final model loads correctly, uses the saved observation normalizer, and completes validation episodes without missing metrics.

### Phase 7: Frozen paired evaluation

Tasks:

- Freeze the Git commit, dependencies, configurations, thresholds, and selected PPO settings.
- Evaluate every manager on identical held-out scenarios.
- Run isolated and combined disturbances.
- Preserve raw CSV files, logs, models, and configuration snapshots.

Acceptance gate:

- No final-test scenario was used to modify a manager, threshold, reward, or hyperparameter.

### Phase 8: Analysis and reporting

Tasks:

- Calculate aggregate and per-condition metrics.
- Add confidence intervals, paired differences, and effect sizes.
- Produce safety, agreement-quality, and efficiency plots.
- Identify where PPO wins, ties, and loses.
- Report simulator and V2X abstraction limitations.

Acceptance gate:

- Every reported number and figure can be regenerated from committed analysis code and preserved raw data.

## 16. Immediate next actions

Complete these in order:

1. Reframe the proposal around whether and when learning is necessary.
2. Find and select the recent rule-based maneuver-cancellation paper.
3. Complete the reproduction specification before changing baseline code.
4. Implement and test the literature-derived B2 manager.
5. Create a shared multi-option counter-proposal generator.
6. Upgrade B3 so it has the same proposal options as PPO.
7. Run and manually inspect paired B1/B2/B3 pilot episodes.
8. Freeze the baseline rules and fairness controls.
9. Train PPO only after the baseline acceptance gates pass.
10. Extend the analysis pipeline before the frozen final evaluation.

## 17. Final deliverables

- Updated project proposal with the revised central question
- Literature survey identifying the reproduced cancellation method
- Reproduction specification and adaptation notes
- Tested B1, B2, B3, and B4 implementations
- Shared feasibility checker, safety shield, and counter-proposal generator
- Version-controlled experiment configurations
- At least three independently trained PPO models, with five preferred
- Paired held-out raw episode data
- Statistical summary tables and reproducible figures
- Analysis of the conditions where learning helps and where it does not
- Demo video or representative episode timeline
- Updated README with exact setup, training, evaluation, and analysis commands
- Limitations and AI-assistance disclosure required by course policy

## 18. Completion definition

The project is complete when it can answer the central research question with a fair, reproducible comparison. Completion does not require PPO to win. It requires demonstrating, with shared controls and held-out evidence, whether learned lifecycle management adds value beyond literature-derived cancellation and matched heuristic renegotiation.
