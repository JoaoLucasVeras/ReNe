# ReNe Project Roadmap and TODO Tracker

Last updated: October 1, 2026

Source plan: [REVISED_PROJECT_PLAN.md](REVISED_PROJECT_PLAN.md)

## Goal

Determine when learned post-acceptance agreement management improves V2X cooperative freeway merging compared with literature-derived cancellation and matched heuristic renegotiation. Learning is successful only if its operational benefits withstand a fair comparison without unacceptable empirical safety degradation. A finding that simple rules are sufficient is a valid project result.

## How we use this tracker

- Check an item only after its acceptance evidence exists.
- Record the configuration, test output, artifact path, or commit supporting completion.
- Update the current focus and progress log at the end of each work session.
- Mark blocked items with a reason and the next action needed; continue independent tasks.
- Existing prototype code is a starting point, not evidence that a research milestone has passed.
- Keep final test results separate from tuning. A change after the final freeze requires a new experiment version.

## Current focus

**Next milestone: M0, followed by M1 and M2 in parallel.**

The cancellation source paper has not been selected in this tracker. Published-method reproduction, a matched multi-option heuristic, and final statistical validation remain pending. Prototype code and scripts were previously created, but their current desktop behavior and research validity need verification.

### Next work session

- [ ] Confirm current repository state and review any changes since the prototype.
- [ ] Install and verify the desktop environment.
- [ ] Run tests, smoke evaluation, and a short rule-based episode.
- [ ] Shortlist implementable cancellation papers and capture their actual cancellation logic.
- [ ] Audit simulator dynamics, V2X observations, and metric definitions before extensive training.

## Milestone map

| Milestone | Depends on | Completion artifact |
|---|---|---|
| M0: Desktop and reproducibility | None | Setup record and passing smoke run |
| M1: Literature baseline specification | None | Source-to-implementation specification |
| M2: Simulator, V2X, and metric audit | M0 | Validated scenarios and metric checks |
| M3: Published cancellation baseline | M1, M2 | Tested B2 and reproduction notes |
| M4: Matched heuristic renegotiation | M2, M3 | Shared proposals and tested B3 |
| M5: Baseline comparison gate | M3, M4 | Paired baseline pilot report |
| M6: Evaluation and analysis infrastructure | M2; can overlap M3–M5 | Scenario manifest and verified analysis |
| M7: PPO development and validation | M5, usable M6 | Selected PPO configuration and pilot models |
| M8: Experiment freeze and final runs | M6, M7 | Frozen manifest, independent models, raw data |
| M9: Analysis and stronger validation | M8 | Main results and robustness/cross-validation evidence |
| M10: Report and submission | M9 | Reproducible repository and academic deliverables |

## M0 — Desktop setup and reproducibility

- [ ] Clone or update the repository on the desktop and record the Git revision.
- [ ] Confirm hardware and OS: Ryzen 5 3600, RTX 3060 Ti, 32 GB RAM, Windows, or document actual differences.
- [ ] Install a supported Python version and create a fresh virtual environment.
- [ ] Verify dependency versions resolve; check the existing lockfile against available packages instead of assuming it is portable.
- [ ] Install the project and development dependencies; run `python -m pip check`.
- [ ] Run `python -m pytest` and `ruff check src scripts tests`.
- [ ] Run `scripts/smoke_test.py` and inspect its outputs.
- [ ] Evaluate a prototype rule manager for a small episode count and confirm CSV creation.
- [ ] If using CUDA, install compatible NVIDIA drivers and CUDA-enabled PyTorch; verify actual GPU tensor operations.
- [ ] Benchmark CPU versus CUDA and environment-worker configurations after baseline validity is established.
- [ ] Save Python/package versions, device details, setup commands, and encountered errors.

**Gate:** a fresh desktop environment runs tests and a small non-learning simulation, producing loadable episode data. GPU acceleration is optional.

## M1 — Select and specify the literature cancellation method

- [ ] Search recent primary research on maneuver cancellation, agreement invalidation, and cooperative maneuver monitoring.
- [ ] Read the full methods sections of the strongest candidates.
- [ ] Prefer an explicit, reproducible algorithm with compatible inputs; record why unsuitable candidates were rejected.
- [ ] Select one source and verify title, authors, publication date, DOI/URL, and any available code.
- [ ] Extract equations, cancellation conditions, timing/persistence rules, and parameter definitions.
- [ ] Separate cancellation logic from unrelated planning/control components.
- [ ] Map each source input to an available or newly implemented simulator observation.
- [ ] Document exact reproduction, necessary adaptations, and unavailable components separately.
- [ ] Define expected behavior for hand-worked reference examples.
- [ ] Seek instructor guidance if adapting the source substantially changes its method.

**Artifact:** `docs/BASELINE_REPRODUCTION_SPEC.md` (create during M1).

**Gate:** every baseline decision rule traces to the selected source or an explicitly justified adaptation. No invented baseline is labeled a paper reproduction.

## M2 — Validate the simulator, V2X model, and metrics

### Dynamics and agreement lifecycle

- [ ] Inspect the actual custom environment rather than treating the planned architecture as implemented behavior.
- [ ] Verify initial acceptance, legal transitions, completion, cancellation, and fallback behavior.
- [ ] Confirm cancellation does not automatically imply merge failure; document the fallback controller and termination behavior.
- [ ] Check longitudinal motion, gap calculation, TTC/headway, merge timing, and collision geometry against hand-worked examples.
- [ ] Confirm disturbances begin after agreement acceptance and have plausible effects.
- [ ] Verify traffic density and severity parameters actually change the scenario as advertised.
- [ ] Check every renegotiation action changes a meaningful plan variable and physical outcome.
- [ ] Run and inspect no-disturbance, cut-in, braking, and intent-mismatch episodes.

### V2X abstraction

- [ ] Trace how delay, loss, message age, and communicated intent are generated and used.
- [ ] Ensure delayed/lost messages affect received information or declared protocol behavior, not only an unrelated scalar feature.
- [ ] Distinguish sensor observations, received V2X data, and privileged simulator ground truth.
- [ ] Ensure no manager receives unacknowledged future state or perfect communicated intent.
- [ ] Document whether message delivery is modeled explicitly or through an approximation.
- [ ] Validate zero-delay/zero-loss and stale/lost-message examples with deterministic traces.
- [ ] State the abstraction limits: no full wireless stack or propagation model is implied.

### Metrics and shield

- [ ] Write precise definitions and denominators for all primary metrics.
- [ ] Implement/check agreement invalidation persistence and failed-agreement duration.
- [ ] Verify unnecessary cancellation against a declared look-ahead oracle; avoid labeling it solely from the state at episode termination.
- [ ] Separate counter-proposal feasibility, acceptance, and completed-merge success.
- [ ] Define whether merge time is reported only for successful merges; report failures separately to avoid misleading averages.
- [ ] Define TTC/headway applicability and sentinel handling for non-closing vehicles.
- [ ] Validate collision, near-collision, messages, acceleration, jerk, and shield counts with hand-calculated cases.
- [ ] Log requested actions and applied actions separately, including override reasons.
- [ ] Check whether the shield cancels every invalid agreement immediately, leaving no measurable opportunity for a manager to improve detection latency.
- [ ] If that occurs, revise the metric/question or justify predictive monitoring opportunities without weakening safety merely to make PPO look useful.

**Artifacts:** scenario traces, unit/scenario tests, and `docs/SIMULATION_AND_METRIC_DEFINITIONS.md`.

**Gate:** selected episodes and metrics agree with independently checked expected behavior; unresolved simulator artifacts cannot drive the main claims.

## M3 — Implement the literature-derived cancellation manager (B2)

- [ ] Implement B2 separately from the existing generic threshold prototype.
- [ ] Move method parameters to version-controlled configuration and connect that configuration to the manager.
- [ ] Match source persistence, state history, and timing logic where required.
- [ ] Add source-linked comments for non-obvious equations and adaptations.
- [ ] Test threshold boundaries, valid agreement, persistent invalidity, and transient observations.
- [ ] Test the published method's reference cases or equivalent adapted examples.
- [ ] Record cancellation triggers and relevant input values.
- [ ] Run at least 100 seeded pilot episodes without unexplained errors.
- [ ] Compare actual behavior with the M1 specification and update adaptation notes.

**Gate:** B2 passes reproduction/scenario checks and completes a reviewed pilot run. Results from the source paper provide context; the fair numerical comparison uses locally reproduced results.

## M4 — Shared counter-proposals and matched heuristic (B3)

- [ ] Create one generator for delay, advance, next-gap, and order-swap candidates.
- [ ] Define proposal bounds, timing increments, recipient acceptance, message cost, and maximum attempts.
- [ ] Assess each candidate with the common feasibility checker.
- [ ] Give B3 and B4 identical candidate semantics and equivalent available information.
- [ ] Define deterministic ranking and tie-breaking; document safety margin, delay, and message-cost criteria.
- [ ] Handle no feasible candidate, rejection, stale proposal, and exhausted attempts.
- [ ] Test every supported proposal type using a constructed feasible example.
- [ ] Test infeasible proposals and verify the fallback remains safe.
- [ ] Check that identical states yield identical candidate sets for B3 and B4.
- [ ] Log all candidate scores, rejected candidates, chosen proposal, and outcome.

**Gate:** B3 can select from the same proposal menu as PPO. Any PPO advantage cannot be explained by having additional actions.

## M5 — Baseline-first comparison and go/no-go gate

- [ ] Run B1 one-shot, B2 cancellation, and B3 heuristic on identical pilot scenarios.
- [ ] Tune baseline settings only on designated development/validation scenarios.
- [ ] Inspect representative successful, failed, canceled, and renegotiated episodes.
- [ ] Verify shared controllers, recipient logic, safety shield, decision cadence, and observation access.
- [ ] Verify exogenous disturbances replay identically even when managers choose different actions; separate scenario and policy RNG streams if needed.
- [ ] Check whether B3 already solves nearly all tested cases and identify credible remaining challenges.
- [ ] Produce a pilot table and condition-specific findings with sample sizes.
- [ ] Freeze baseline behavior for the PPO comparison.
- [ ] Record a decision: proceed to PPO, repair the environment, or refine the experiment because it cannot yet distinguish managers.

**Gate:** plausible, stable baseline results with no unresolved fairness mismatch. Extensive PPO training begins after this gate.

## M6 — Evaluation and analysis infrastructure

- [ ] Create explicit training, validation, and held-out scenario manifests.
- [ ] Define a small pilot matrix and a final matrix covering isolated and combined disturbances.
- [ ] Specify episodes **per condition**, managers, and training seeds; the current `--episodes` budget spans conditions and must not be mistaken for episodes per condition.
- [ ] Track scenario ID, scenario seed, condition, manager, model ID, training seed, configuration, and Git revision.
- [ ] Make the evaluator require the saved normalizer for learned models; fail clearly if it is missing.
- [ ] Give every completed run a unique directory; avoid accidentally pooling exploratory and final runs.
- [ ] Support evaluation of all independent PPO models with explicit provenance.
- [ ] Aggregate primary safety, agreement, efficiency, comfort, and communication outcomes.
- [ ] Include delay, packet loss, density, disturbance, and combinations in condition summaries.
- [ ] Calculate paired differences and effect sizes using matched scenario IDs.
- [ ] Add suitable confidence intervals for continuous and binary outcomes.
- [ ] Account for repeated evaluation scenarios across training seeds; avoid treating all rows as independent evidence.
- [ ] Choose a small set of primary comparisons and document handling of secondary/multiple comparisons.
- [ ] Check analysis on small synthetic examples with known answers.
- [ ] Produce script-generated figures and tables from an explicit run manifest.

**Gate:** raw data can be traced to every summary, and a small mock/pilot experiment produces correct paired comparisons without duplicate or missing episodes.

## M7 — PPO development and validation

- [ ] Verify observations contain the intended deployable information and no oracle labels.
- [ ] Keep shared controller, shield, and counter-proposals identical to B3.
- [ ] Review reward terms and check they match desired behavior without rewarding metric loopholes.
- [ ] Run a short training/save/load/evaluation smoke test.
- [ ] Train on simplified conditions, then introduce declared traffic and communication randomization.
- [ ] Measure CPU/CUDA runtime; choose the reliable faster configuration for the small MLP.
- [ ] Tune using validation data with a recorded, bounded search budget.
- [ ] Inspect action distribution, proposed versus applied actions, overrides, and learning diagnostics.
- [ ] Compare PPO pilot performance against B2 and B3, including cases where it loses.
- [ ] Freeze policy-selection rules, reward, hyperparameters, observation normalization, and training budget.

**Gate:** repeatable PPO training and validation produce loadable models with interpretable behavior. Beating B3 is a research outcome, not a requirement for passing the implementation gate.

## M8 — Freeze and execute final experiments

- [ ] Freeze the code revision, dependencies, thresholds, proposal rules, metrics, manifests, and analysis plan.
- [ ] Define practical success thresholds and any safety non-inferiority margin before testing; obtain instructor guidance for formal safety claims.
- [ ] Train at least three independent final PPO seeds; five preferred if runtime permits.
- [ ] Preserve all seeds, checkpoints, normalizers, configurations, and runtime logs.
- [ ] Run B1/B2/B3 and each PPO model on the paired final matrix.
- [ ] Check expected episode counts and scenario coverage per method/condition.
- [ ] Record run failures and rerun rules rather than silently excluding difficult cases.
- [ ] Back up raw data and models outside the working machine.
- [ ] Lock the completed experiment data; use a new version if further tuning is needed.

**Gate:** complete, traceable held-out data with no final-test-driven tuning.

## M9 — Analyze results and strengthen validation

### Main conclusions

- [ ] Compare B1→B2 monitoring value, B2→B3 renegotiation value, and B3→B4 learning value.
- [ ] Examine safety first and report uncertainty, including when zero collisions provide limited evidence.
- [ ] Report agreement quality and efficiency by condition, not just overall means.
- [ ] Identify where PPO wins, ties within uncertainty, and loses.
- [ ] Explain major outcomes using representative decision timelines.
- [ ] Report training variability and the computational cost of learning.
- [ ] Check sensitivity to reasonable metric/threshold choices without cherry-picking favorable results.

### Targeted stronger validation

- [ ] Choose one extension after the core comparison works: targeted HighwayEnv/SUMO transfer, a predictive model-based manager, or richer communication modeling.
- [ ] Write the extension's specific validation question and acceptance criteria before implementation.
- [ ] Verify that the extension preserves shared manager interfaces and fairness controls.
- [ ] For simulator transfer, map dynamics/observations/action semantics and document discrepancies; a stock merge demo alone is not cross-validation.
- [ ] For a model-based comparator, use the same candidates/information and record its planning assumptions and computation budget.
- [ ] Run a targeted paired evaluation and report transfer or model mismatch honestly.
- [ ] If time remains, test learned management without communication features or without renegotiation to isolate their contribution.

**Gate:** evidence supports a precise answer about when learning adds value; optional extensions have clearly bounded claims.

## M10 — Final report and submission

- [ ] Update the proposal/abstract to match the completed experiment and revised question.
- [ ] Complete the required recent literature survey with verified citations and source links.
- [ ] Include the reproduced method, adaptation limitations, and matched-baseline design.
- [ ] Include architecture, scenario definitions, parameters, splits, and hardware/runtime details.
- [ ] Present primary and per-condition tables with sample sizes and uncertainty.
- [ ] Discuss positive, mixed, equivalent, or negative findings without hiding unfavorable runs.
- [ ] State custom-simulator and abstract-V2X limitations and distinguish empirical safety from formal guarantees.
- [ ] Create representative demo clips or episode timelines.
- [ ] Update the README with exact install, smoke, training, evaluation, and analysis commands.
- [ ] Run clean-clone reproduction for a short evaluation and analysis.
- [ ] Review repository contents for accidental credentials, generated caches, and large artifacts.
- [ ] Finish AI novelty/feasibility critique and course-required AI disclosure.
- [ ] Confirm README title, team, abstract, track, and repository link meet assignment requirements.
- [ ] Submit the proposal/report to Canvas and GitHub deliverables to the required destinations.
- [ ] Review commit scope and preserve the project owner's Git identity; publish only when authorized.

**Gate:** another reader can reproduce a small experiment and understand the evidence behind the final claims.

## Working artifact index

Existing entry points (confirm current behavior during M0):

- Revised goal: `docs/REVISED_PROJECT_PLAN.md`
- Prior build specification: `PROJECT_BUILD_SPEC.md`
- Simulator: `src/rene/envs/merge_lifecycle_env.py`
- Rule prototypes: `src/rene/policies/rule_based.py`
- Feasibility/shield: `src/rene/agreements/feasibility.py`, `src/rene/safety/shield.py`
- Training/evaluation/analysis: `scripts/train.py`, `scripts/evaluate.py`, `scripts/analyze.py`
- Configurations: `configs/env/`, `configs/agents/`, `configs/experiments/`
- Models and normalizers: `models/<experiment>/seed-<n>/`
- Raw episodes: `results/raw/<experiment>/<run>/episodes.csv`
- Tables and figures: `results/summaries/<experiment>/`

Planned supporting documents:

- `docs/BASELINE_REPRODUCTION_SPEC.md`
- `docs/SIMULATION_AND_METRIC_DEFINITIONS.md`
- `docs/EXPERIMENT_PROTOCOL.md`
- Baseline pilot report and final result report

## Decisions to resolve

| Decision | Resolve by | Record |
|---|---|---|
| Published cancellation source and adaptation scope | M1 | Reproduction specification |
| Oracle, invalidation persistence, and cancellation labels | M2 | Metric definitions |
| Candidate semantics and heuristic ranking | M4 | Configurations and design notes |
| Final conditions and samples per condition | M6 | Experiment protocol |
| Primary outcomes and practical safety/performance margins | M8 | Frozen analysis plan |
| CPU/CUDA and final training budget | M7 | Runtime benchmark |
| Semester deadline and available hours | Next planning session | Relative schedule below |
| Stronger validation extension | M9 | Extension specification |

## Relative schedule

No submission date has been supplied. Schedule by milestone and update after pilot runtimes are measured.

| Work block | Target |
|---|---|
| Block 1 | M0 setup; M1 literature selection; begin M2 audit |
| Block 2 | Finish M2 and implement M3 |
| Block 3 | M4 matched heuristic and M5 baseline report |
| Block 4 | M6 evaluation infrastructure and M7 PPO pilot |
| Block 5 | M7 freeze, M8 final training and evaluation |
| Block 6 | M9 analysis and one bounded validation extension |
| Block 7 | M10 report, reproducibility, and submission |

A block may span multiple sessions. Preserve baseline fairness, metric validity, multiple seeds, and honest reporting if time runs short; reduce optional extensions or matrix breadth first and document the reduced coverage.

## Work-session progress log

| Date | Tasks/IDs completed | Evidence/artifact | Finding or blocker | Next action |
|---|---|---|---|---|
| 2026-10-01 | Roadmap drafted | This document | Desktop/research gates remain to be verified | Start M0; select source under M1 |

## Project completion checklist

- [ ] Literature-derived cancellation is documented and validated.
- [ ] Heuristic and PPO share counter-proposals and relevant information.
- [ ] Simulation, V2X consequences, metrics, and shield behavior are independently checked.
- [ ] Baselines pass before substantial PPO training.
- [ ] Final results use paired held-out scenarios and multiple PPO training seeds.
- [ ] Analysis includes uncertainty and reports where learning helps and where it does not.
- [ ] Conclusions are reproducible and proportionate to the simulation evidence.
- [ ] Academic and repository deliverables are submitted.
