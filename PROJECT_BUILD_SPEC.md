# ReNe Project Build Specification

## Role and objective

You are implementing ReNe, a semester research project that evaluates learned post-acceptance agreement management for V2X cooperative freeway merging.

The central research question is:

> Can a learned agreement manager reduce failed-agreement duration and unnecessary cancellations compared with fixed lifecycle rules, without increasing safety violations when all methods use the same safety shield?

Build a reproducible Python research codebase that simulates an already accepted cooperative merge agreement and allows a high-level manager to choose whether to continue, cancel, or issue a bounded renegotiation proposal as traffic and communication conditions change.

Do not build an end-to-end driving system. Low-level steering, acceleration, and lane-change execution must remain conventional or simulator-provided. Learning applies only to agreement lifecycle decisions.

## Read before implementation

Read these repository files completely before changing code:

1. `README.md`
2. `docs/IMPLEMENTATION_BLUEPRINT.md`
3. `docs/project_proposal.md`
4. `docs/literature_survey.md`
5. `docs/ai_novelty_feasibility_audit.md`

Treat `docs/IMPLEMENTATION_BLUEPRINT.md` as the detailed design authority. This specification controls implementation order and acceptance gates. If the files conflict, preserve the narrow minimum viable scope described here and document the conflict before proceeding.

## User hardware

- Windows development machine
- AMD Ryzen 5 3600, 6 cores and 12 threads
- NVIDIA GeForce RTX 3060 Ti, 8 GB VRAM
- 32 GB RAM

The minimum system must run locally on CPU. CUDA support is optional and should be benchmarked rather than assumed faster. Start with four vectorized environments and compare CPU throughput at 1, 4, 6, and 8 environments.

## Implementation principles

- Work in small, testable phases.
- Do not begin PPO training until the deterministic environment and all rule-based baselines work.
- Do not add SUMO, MARL, LLMs, graph networks, recurrent policies, raw sensor inputs, or real datasets to the MVP.
- Keep all important thresholds and experimental parameters in configuration files.
- Use deterministic seeds and save the exact configuration for every run.
- Use one common environment, low-level controller, feasibility checker, and safety shield for all methods.
- Do not claim that reinforcement learning, cancellation, or renegotiation is independently novel.
- Do not claim formal safety from empirical results.
- Never commit credentials, virtual environments, large checkpoints, raw videos, caches, or generated bulk data.
- Do not push, rewrite Git history, or create a pull request unless the user explicitly requests it.
- Preserve existing documents and unrelated user changes.

## Required technology

- Python 3.11
- Gymnasium
- HighwayEnv
- Stable-Baselines3
- PyTorch
- NumPy
- pandas
- SciPy
- statsmodels
- Matplotlib
- seaborn
- PyYAML
- TensorBoard
- pytest
- Ruff

Use current compatible stable versions, then lock the resolved versions. Prefer a `pyproject.toml` plus a reproducible lock or exact requirements file. Document the chosen dependency workflow in the README.

## Required repository structure

Create or complete this structure:

```text
ReNe/
|-- README.md
|-- pyproject.toml
|-- requirements-lock.txt
|-- .gitignore
|-- configs/
|   |-- env/
|   |   |-- default.yaml
|   |   `-- evaluation.yaml
|   |-- agents/
|   |   |-- ppo.yaml
|   |   `-- rules.yaml
|   `-- experiments/
|       |-- smoke.yaml
|       |-- train.yaml
|       `-- final_eval.yaml
|-- src/rene/
|   |-- __init__.py
|   |-- envs/
|   |   |-- merge_lifecycle_env.py
|   |   |-- observations.py
|   |   |-- rewards.py
|   |   `-- registration.py
|   |-- agreements/
|   |   |-- state.py
|   |   |-- protocol.py
|   |   |-- feasibility.py
|   |   `-- renegotiation.py
|   |-- disturbances/
|   |   |-- base.py
|   |   |-- traffic.py
|   |   `-- communication.py
|   |-- policies/
|   |   |-- rule_based.py
|   |   `-- heuristic_renegotiation.py
|   |-- safety/
|   |   `-- shield.py
|   |-- metrics/
|   |   |-- definitions.py
|   |   `-- episode_metrics.py
|   `-- utils/
|       |-- configuration.py
|       |-- logging.py
|       `-- seeding.py
|-- scripts/
|   |-- smoke_test.py
|   |-- benchmark_workers.py
|   |-- train.py
|   |-- evaluate.py
|   |-- analyze.py
|   `-- record_video.py
|-- tests/
|   |-- test_agreement_state.py
|   |-- test_disturbances.py
|   |-- test_environment.py
|   |-- test_feasibility.py
|   |-- test_metrics.py
|   |-- test_reproducibility.py
|   `-- test_safety_shield.py
|-- models/
`-- results/
    |-- raw/
    |-- summaries/
    `-- figures/
```

Use a `src` layout and make the package installable in editable mode.

## Core domain model

### Agreement lifecycle

Implement an explicit state machine with at least:

- `PROPOSED`
- `ACCEPTED`
- `EXECUTING`
- `RENEGOTIATING`
- `COMPLETED`
- `CANCELED`
- `FAILED`

Reject illegal transitions. The primary learning episode must begin after an agreement is accepted, or it must automatically create and accept the agreement before the learned manager receives control.

### Agreement record

Use typed dataclasses or similarly explicit structures. Store:

- Agreement identifier
- Episode identifier
- Participant identifiers
- Target gap identifier
- Merge order
- Planned merge time or time window
- Acceptance time
- Revision number
- Current lifecycle state
- Last requested and applied manager actions
- Feasibility status and reason code
- Message count
- Renegotiation count

### Manager actions

The conceptual actions are:

- `CONTINUE`
- `CANCEL`
- `RENEGOTIATE`

For a simple discrete Stable-Baselines3 action space, represent renegotiation options as separate actions:

- `RENEGOTIATE_DELAY`
- `RENEGOTIATE_ADVANCE`
- `RENEGOTIATE_NEXT_GAP`
- `RENEGOTIATE_SWAP_ORDER`

Group these as `RENEGOTIATE` in reported aggregate metrics. Limit renegotiation to one attempt initially; make the limit configurable.

### Renegotiation behavior

Counter-proposals must be bounded and interpretable. The recipient uses deterministic feasibility logic to accept or reject each proposal. Do not generate free-form text or unconstrained continuous proposals.

## Environment requirements

Create a custom Gymnasium-compatible environment derived from or composed around HighwayEnv's current merge environment.

The environment must:

- Use compact numerical observations.
- Use discrete lifecycle actions.
- Separate simulation frequency from manager decision frequency.
- Create an accepted agreement before post-acceptance management begins.
- Inject disturbances only after acceptance for the primary experiments.
- Apply the selected manager action through the safety and feasibility layer.
- Return terminated and truncated states correctly.
- Expose complete episode metrics in `info` at termination.
- Pass Gymnasium's environment checker.
- Be reproducible for a fixed seed and configuration.
- Support headless execution and optional RGB rendering.

Do not modify an installed HighwayEnv package directly. Implement the custom environment inside this repository and register it with Gymnasium.

## Observation vector

Implement a flat normalized vector containing the minimum useful subset of:

### Physical state

- Ego and relevant participant speeds
- Ego and participant accelerations
- Relative positions and relative velocities
- Current and predicted target-gap size
- Distance to merge point
- Traffic density
- Predicted minimum time-to-collision
- Predicted minimum time headway

### Agreement state

- Merge order
- Target-gap encoding
- Time until planned merge
- Agreement age
- Execution progress
- Revision count
- Previous lifecycle action
- Time since previous lifecycle decision

### Communication state

- Age of latest message
- Current sampled delay
- Rolling packet-loss estimate
- Missing-message flag
- Stale-message flag
- Out-of-order-message flag

### Uncertainty state

- Predicted-versus-observed position difference
- Predicted-versus-observed speed difference
- Intent confidence
- Consecutive inconsistent-observation count

Document every feature, range, normalization rule, and missing-value convention. Add tests for observation shape, finite values, and deterministic construction.

## Disturbance models

Implement disturbances as composable, seeded components configured through YAML.

### Required traffic disturbances

1. A non-connected vehicle cuts into the reserved target gap.
2. A participant or nearby vehicle brakes unexpectedly.
3. A communicated intent no longer matches observed motion.

### Required communication disturbances

1. Constant or randomly sampled message latency.
2. Independent packet loss.
3. Burst packet loss if it can be added without delaying the MVP.
4. Stale or out-of-order delivery if it can be added without delaying the MVP.

Start with these evaluation levels:

- Delay: 0, 100, 300, and 500 ms
- Packet loss: 0%, 5%, 10%, and 20%
- Traffic density: low, medium, and high
- Braking: mild, moderate, and hard within declared simulator bounds
- Cut-in timing: early, middle, and late after acceptance

Keep all values configurable. Do not run a full Cartesian grid during development.

## Feasibility and safety

Implement deterministic checks shared by every relevant manager:

- Predicted minimum TTC threshold
- Minimum time-headway threshold
- Minimum target-gap requirement
- Acceleration and deceleration bounds
- Ability to complete the merge before the usable ramp ends
- Feasibility for all participants in a counter-proposal

Required override behavior:

- Unsafe `CONTINUE` becomes `CANCEL` or a conservative fallback.
- Unsafe counter-proposals are rejected.
- Unsafe low-level behavior falls back to the conventional safe controller.

Log the requested action, applied action, triggering constraint, and relevant state values for every override.

Do not label this a formal safety guarantee unless a mathematically valid guarantee is actually implemented and justified. The default wording must be “deterministic safety constraints” or “empirical safety under tested conditions.”

## Required comparison methods

Implement all methods behind one common manager interface:

### B0 Perception-only

No explicit agreement. Use the conventional merge controller.

### B1 One-shot agreement

Retain the accepted agreement until completion unless the emergency safety fallback triggers.

### B2 Rule-based cancellation

Cancel when declared gap, TTC, headway, or message-staleness thresholds are crossed.

### B3 Rule-based cancellation with heuristic renegotiation

Attempt one deterministic timing, gap, or ordering revision before canceling when a feasible alternative exists.

### B4 Learned manager

Use PPO to choose continue, cancel, or a bounded renegotiation action. Apply the same low-level controller, feasibility checker, and safety shield as the rule-based managers.

B3 is mandatory. It distinguishes the value of learning from the value of merely adding renegotiation.

## Reward requirements

Implement reward components separately and log each one:

- Successful merge bonus
- Collision penalty
- Near-collision penalty
- Per-step failed-agreement penalty
- Unnecessary-cancellation penalty
- Delay penalty
- Discomfort penalty
- Communication/message cost
- Safety-shield override penalty

The final safety evaluation must use explicit metrics, not training reward. Do not tune reward weights against the final test set.

## Metric definitions

Implement and document these definitions before final training:

### Agreement invalidation time

First time the accepted agreement fails the privileged feasibility check for a configurable persistence window.

### Failed-agreement duration

Time from invalidation until cancellation, successful revision, safe recovery, or episode termination.

### Unnecessary cancellation

A cancellation for which an offline oracle using true simulator state determines that the original agreement would remain feasible over a fixed look-ahead horizon.

### Renegotiation success

A proposal that is accepted, remains feasible, and leads to merge completion without subsequent cancellation inside the evaluation window.

### Required reported metrics

Safety:

- Collision rate
- Near-collision rate
- Minimum TTC
- Minimum time headway
- Shield override count and reasons

Agreement quality:

- Agreement completion rate
- Failed-agreement duration
- Unnecessary-cancellation rate
- Renegotiation attempt, acceptance, and success rates
- Lifecycle messages per successful merge

Efficiency and comfort:

- Merge completion time
- Ramp delay
- Mainline speed disruption
- Throughput
- Peak absolute acceleration
- Peak jerk
- Hard-braking count

System:

- Environment steps per second
- Wall-clock runtime
- Training diagnostics

## PPO implementation

Use Stable-Baselines3 PPO with an `MlpPolicy`.

Initial defaults:

- Two hidden layers of 128 units
- Four parallel environments
- CPU device as the initial default
- Separate validation environment
- Observation normalization with saved statistics
- TensorBoard logging
- Periodic checkpoints
- Deterministic evaluation

Create a worker benchmark that compares 1, 4, 6, and 8 environments on CPU and at least one CUDA run. Record steps per second and wall-clock time. Select the fastest stable configuration for this machine.

Training order:

1. No disturbance or one simple disturbance.
2. Randomized disturbance timing and severity.
3. Communication delay and loss.
4. Combined training distribution.

Do not add recurrence unless frame stacking demonstrably fails to represent communication history.

## Experimental design

Create separate training, validation, and final-test scenario seeds.

Final evaluation must:

- Freeze model selection, thresholds, and configurations first.
- Use paired scenario seeds across all methods.
- Replay identical initial states and disturbances for each method.
- Include a no-disturbance condition.
- Include isolated disturbance severity sweeps.
- Include held-out combinations of physical and communication disturbances.
- Include at least one plausible out-of-distribution severity.
- Retain every completed episode, including failures.

Target five learned-policy training seeds; use three only as a documented schedule fallback. Target at least 1,000 evaluation episodes per method and major condition if runtime permits.

## Statistical output

The analysis script must generate reproducible CSV summaries, plots, and a Markdown results report.

Report:

- Sample size
- Mean and median where appropriate
- Standard deviation
- Bootstrap 95% confidence interval
- Paired differences for paired continuous outcomes
- Binomial confidence intervals for proportions
- Effect sizes

Do not interpret a nonsignificant difference as proof of equivalence. If testing safety non-inferiority, require a user-approved margin before running that analysis.

## Logging and artifacts

Each run directory must contain:

- Run ID and timestamp
- Git commit hash when available
- Full resolved configuration
- Python and package versions
- Device selection
- Training and scenario seeds
- Model identifier
- Episode-level scenario parameters
- Requested and applied actions
- Override reason codes
- Reward components
- Episode metrics
- Model checkpoint
- Observation-normalization state

Use append-only or unique run directories. Never silently overwrite results.

Recommended tabular schemas:

- `episodes.csv`: one row per episode
- `decisions.csv`: one row per lifecycle decision
- `training.csv`: learning diagnostics
- `summary.csv`: grouped final results

## Required scripts and interfaces

Provide documented CLI entry points equivalent to:

```powershell
python scripts/smoke_test.py --config configs/experiments/smoke.yaml
python scripts/benchmark_workers.py --config configs/experiments/smoke.yaml
python scripts/train.py --config configs/experiments/train.yaml --seed 1
python scripts/evaluate.py --config configs/experiments/final_eval.yaml --manager rule_cancel
python scripts/evaluate.py --config configs/experiments/final_eval.yaml --manager learned --model models/<run>/best_model.zip
python scripts/analyze.py --input results/raw --output results/summaries
python scripts/record_video.py --config configs/experiments/final_eval.yaml --manager learned
```

Exact argument syntax may differ, but each workflow must be non-interactive and documented.

## Automated tests

Write tests before or with each component.

Required unit tests:

- Valid and invalid agreement transitions
- Agreement revision and message counts
- Reproducible disturbance timing
- Packet-loss and delay behavior
- Feasibility boundary cases
- Safety-shield overrides
- Metric calculations against hand-worked examples
- Observation shape, ranges, and finite values
- Rule-baseline boundary behavior

Required integration tests:

- Gymnasium environment checker passes
- Every manager completes a short episode
- Vectorized environments reset and step correctly
- Fixed seeds reproduce initial state and disturbance schedule
- A short PPO smoke run saves and reloads a model
- Evaluation emits valid result schemas

Required deterministic scenarios:

- No disturbance: agreement generally remains feasible
- Clear gap cut-in: unsafe continuation is blocked
- Persistent stale communication: configured rule reacts as declared
- Feasible alternative gap: heuristic renegotiation succeeds
- No feasible alternative: proposal is rejected and fallback remains safe

## Phased execution plan

Do not implement the entire project in one uncontrolled pass. Complete each phase, run its checks, and report the result before moving on.

### Phase 0: Scaffold

Create package structure, dependency files, configurations, `.gitignore`, lint configuration, and test setup.

Acceptance gate:

- Editable install succeeds.
- Imports succeed.
- Ruff succeeds.
- pytest succeeds.

### Phase 1: Stock simulator smoke test

Run HighwayEnv's merge environment headlessly and optionally record a short render.

Acceptance gate:

- At least 100 seeded episodes execute without exceptions.
- A fixed seed reproduces the initial scenario.

### Phase 2: Agreement model

Implement lifecycle enums, records, legal transitions, and deterministic agreement creation.

Acceptance gate:

- Unit tests cover every legal transition and representative illegal transitions.

### Phase 3: Custom lifecycle environment

Connect the agreement to the merge simulation and expose the lifecycle action space and observation vector.

Acceptance gate:

- Gymnasium checker passes.
- Random actions can complete 100 episodes.
- Observations are finite and correctly shaped.

### Phase 4: Disturbances and oracle

Implement cut-in, braking, communication delay/loss, intent mismatch, and privileged feasibility labels.

Acceptance gate:

- Each disturbance is reproducible and visible in logs.
- Hand-designed scenarios produce expected invalidation labels.

### Phase 5: Rule-based managers

Implement B0 through B3 behind one interface.

Acceptance gate:

- Paired baseline evaluations run from one command.
- B3 successfully revises at least one known feasible scenario.

### Phase 6: Safety shield

Implement checks, overrides, and reason logging.

Acceptance gate:

- Every known unsafe scenario is blocked.
- Requested and applied actions are distinguishable in logs.

### Phase 7: PPO manager

Implement reward, vectorization, training, validation, checkpointing, normalization, and worker benchmark.

Acceptance gate:

- Smoke training saves and reloads a policy.
- Training produces finite diagnostics.
- The policy beats random lifecycle decisions on the simplified validation curriculum.

### Phase 8: Frozen pilot

Run a small paired evaluation and inspect metrics, labels, plots, and failures. Correct implementation errors, then freeze definitions and configurations.

Acceptance gate:

- No missing episodes or invalid metric values.
- The user approves final thresholds, oracle horizon, persistence window, and test matrix.

### Phase 9: Final experiments

Train independent seeds and execute the held-out paired evaluation.

Acceptance gate:

- All planned runs complete or failures are explicitly documented.
- Analysis can be regenerated from raw outputs with one command.

### Phase 10: Documentation

Update README with installation, smoke test, training, evaluation, analysis, and troubleshooting instructions. Generate final figures and a concise Markdown results report.

Acceptance gate:

- A clean-clone workflow reproduces the smoke test and a small evaluation.

## First vertical slice

The first meaningful implementation must be deliberately small:

1. Create one deterministic merge scenario.
2. Create and accept one agreement.
3. Inject one gap cut-in after acceptance.
4. Detect that the original agreement is invalid.
5. Apply rule-based cancellation.
6. Enter a conservative fallback.
7. Finish the episode safely.
8. Save a complete episode and decision log.

Do not start PPO until this vertical slice and its tests work.

## Human approval gates

Stop and request user input before finalizing any of these research choices:

- Safety thresholds for TTC, time headway, gap, and acceleration
- Offline-oracle look-ahead horizon
- Agreement-invalidation persistence window
- Final reward weights
- Final rule-baseline thresholds
- Final training budget
- Final held-out test matrix
- Safety non-inferiority margin, if used
- Reduction of seed or episode counts due to time constraints

An implementation agent or developer may propose values and explain their consequences, but must not silently turn preliminary values into final research definitions.

## Human tasks outside AI-generated code

The project owner must complete or supervise the following tasks personally.

### Before coding

- Confirm the exact course track name and submission rules.
- Confirm the final team member names, school email, and repository maintainer information.
- Install or verify Python 3.11, Git, an NVIDIA driver, and any required Windows build tools.
- Select the correct PyTorch installation command for the installed NVIDIA driver and CUDA support.
- Confirm sufficient free disk space and create a backup strategy.
- Read the cited papers closely enough to verify that the novelty and literature summaries are accurate.

### During implementation

- Review each phase rather than accepting generated code without running it.
- Run smoke tests and inspect representative rendered episodes visually.
- Confirm that disturbances occur after agreement acceptance.
- Check that rule-based and learned methods receive identical paired scenarios.
- Approve the metric definitions, safety thresholds, oracle horizon, and reward weights.
- Inspect failure traces, not only average metrics.
- Monitor CPU and GPU temperatures, memory use, and system stability during long experiments.
- Keep a research log of decisions, failed attempts, configuration changes, and reasons.
- Commit working milestones under the project owner's own identity after reviewing the diff.

### Before final experiments

- Freeze and record the code commit, dependencies, configurations, thresholds, and selected models.
- Decide the final seed count and episode count based on measured runtime.
- Confirm that the final test set was not used for tuning.
- Run a small pilot and manually verify metric calculations against several episodes.
- Ensure enough uninterrupted time and storage for all experiment runs.

### After experiments

- Review statistical claims and distinguish lack of evidence from equivalence.
- Investigate outliers, collisions, shield overrides, and failed runs.
- Confirm that plots match the underlying CSV data.
- Write the final interpretation in the student's own voice.
- Disclose AI assistance according to course policy.
- Verify every citation, author list, year, DOI, and claimed research gap.
- Remove credentials, machine-specific secrets, temporary data, and unnecessary large files.
- Test installation and a small evaluation from a clean clone or clean virtual environment.
- Submit the Canvas document and confirm that the required GitHub files are visible.

## Definition of done

The implementation is complete only when:

- A clean environment can be installed from committed dependency files.
- The custom environment passes automated validation.
- Disturbances and paired scenarios are seed-reproducible.
- B0 through B4 run through one evaluation interface.
- Safety checks and metrics have automated tests.
- At least three learned-policy seeds are evaluated, with five preferred.
- Final results include safety, agreement quality, efficiency, comfort, and communication metrics.
- Confidence intervals, effect sizes, sample sizes, and limitations are reported.
- Figures and tables are generated from scripts.
- README commands reproduce a smoke test and small evaluation.
- The report does not overstate novelty or safety.

## Initial response expected from the implementer

Before editing files, respond with:

1. A concise summary of the existing repository state.
2. Any conflicts or missing prerequisites found in the referenced documents.
3. The exact files planned for Phase 0 and Phase 1.
4. The commands that will verify those phases.
5. Any human decision required immediately.

Then implement only Phase 0 and Phase 1 unless the user explicitly authorizes a larger batch.
