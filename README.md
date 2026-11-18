# ReNe

**Learning When to Renegotiate in V2X Cooperative Merging**

## Team

- Joao Lucas Veras

## Abstract

ReNe, short for **renegotiate**, studies how connected automated vehicles should manage freeway-merge agreements after acceptance. Most cooperative-driving work emphasizes reaching the initial agreement, but an agreement that was safe when accepted can become unsafe or inefficient after a human-driven vehicle cuts into the target gap, a participant brakes, or a V2X message becomes delayed or stale. We will train a compact, risk-aware policy that chooses whether to **continue**, **cancel**, or **renegotiate** an accepted merge agreement. Low-level vehicle motion will remain rule-based, and a separate safety shield will override unsafe decisions. In simulation, the learned manager will be compared with perception-only merging, one-shot negotiation, and fixed-threshold cancellation under changing traffic and communication conditions. The main hypothesis is that learned lifecycle management can shorten failed agreements and avoid unnecessary cancellations without increasing safety violations.

## Research question

Can a learned, risk-aware agreement manager outperform fixed lifecycle rules by preserving valid cooperative merge agreements, abandoning doomed agreements earlier, and issuing useful counter-proposals under uncertain traffic and V2X communication?

## Planned implementation

The minimum viable system will use `highway-env` or SUMO to simulate a freeway on-ramp merge. A learned high-level policy will observe traffic state, agreement state, and communication quality. It will select `continue`, `cancel`, or a bounded renegotiation action, while a rule-based safety layer enforces minimum gap and time-to-collision constraints. The project will evaluate safety, merge success, delay, comfort, agreement quality, communication cost, and generalization to unseen disturbances.
## Repository link

https://github.com/JoaoLucasVeras/ReNe

## Project progress and next steps

Read [the project explained and its roadmap](docs/PROJECT_OVERVIEW_AND_ROADMAP.md)
for a plain-language introduction, completed work and the path to completion.

Start with the [project progress and decision log](docs/PROJECT_LOG.md) for completed
work, decisions, open issues and the next session's handoff. Use the
[roadmap and TODO tracker](docs/PROJECT_ROADMAP.md) for detailed milestone checklists.
The [simulator audit](docs/SIMULATION_AND_METRIC_DEFINITIONS.md) identifies corrections
required before research comparisons; the prototype has not passed that validation gate.

## Implementation status

The repository now contains a CPU-capable research prototype with:

- A seeded Gymnasium lifecycle environment for an accepted freeway-merge agreement
- Physical moving-gap and lane-transition geometry with stabilized merge completion
- Timestamped delayed/lossy state delivery, received caches, and cancellation retries/acknowledgments/timeouts
- Bounded braking, physical cut-in and physical intent mismatch with received-only residual evidence
- Continue/cancel and acknowledged earlier/later timing revisions; next-gap/order-swap remain disabled
- Shared received-state predictions, provisional paper-adapted cancellation and matched timing heuristic
- A deterministic feasibility checker and safety shield
- PPO training, paired evaluation, analysis, and worker-benchmark scripts
- Automated lifecycle, feasibility, safety, environment, and reproducibility tests

The custom environment is optimized for rapid agreement-management experiments. HighwayEnv's
`merge-v1` remains the visual/reference simulator and can be used for later cross-validation.

Step 3A's bounded geometry fixtures pass; see [the implementation and preview instructions](docs/STEP3A_PHYSICAL_MERGE.md).
Step 3B's [communication and 35-feature shared input contract](docs/STEP3B_COMMUNICATION.md)
passes its fixtures; old 22-feature models/normalizers are incompatible. Run
`python scripts/trace_communication.py --delay-ms 800 --loss 0` to inspect messages
and received state. Step 3C1 adds [bounded braking and its checks](docs/STEP3C1_BOUNDED_BRAKING.md);
Step 3C2 adds a [physical cut-in and a 40-feature shared contract](docs/STEP3C2_PHYSICAL_CUT_IN.md).
The November 12 [CPU integration and handoff](docs/CPU_TO_TRAINING_HANDOFF.md) adds
53-feature input v4, timing proposals/execution and core metric repairs. Older
checkpoints/normalizers are incompatible. November 13: input v5 adds a `NO_COMPLETION`
prediction status; input v6 (56 features) adds a non-connected follower and a next-gap
perception fallback; v7 (58 features) adds received front acceleration and sensed
intruder lateral speed; rearward sensing is 120 m (see the project log). The current suite
has 234 passing tests. Baselines are frozen in [BASELINE_FREEZE.md](docs/BASELINE_FREEZE.md);
PPO uses MaskablePPO on CPU (GPU benchmarked slower). Ramp length follows the adopted protocol in
[the experiment protocol](docs/EXPERIMENT_PROTOCOL.md) (train 260/270/290/300 m, held-out 280 m).
The initial pilot's ramp failures prompted shared controller/rear-following repairs.
Post-repair pilots of 144/384/96 episodes have no collisions/ramp departures in tested
cases. Offline cancellation counterfactuals and paired analysis are implemented.
CPU subprocess training/save/reload smokes pass; none is a final research result.
Review [the experiment protocol](docs/EXPERIMENT_PROTOCOL.md) before substantive PPO.
Tests, rule-based episodes and previews
execute on the local CPU, without a GPU. Synthetic scenarios are not real-world validation.
The full simulator-validation gate remains open. Do not interpret current runs
as final baseline results or reuse pre-Step-3A checkpoints without revalidation.

## Local setup

Python 3.11 or 3.12 is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

The default PPO configuration uses CPU and does not require an NVIDIA GPU.
Substantive training is gated while M2 remains open. Use
`python scripts/training_preflight.py` for the 128-step CPU interface smoke;
the development override in `train.py` does not validate the simulator.

## Verify the project

```powershell
python -m pytest
ruff check src scripts tests
python scripts/smoke_test.py --config configs/experiments/smoke.yaml
python scripts/benchmark_workers.py --steps 2000
```

## Train a small PPO manager

```powershell
python scripts/train.py --config configs/experiments/train.yaml --seed 1 --timesteps 10000
```

The full training budget in the configuration is a starting point, not a finalized research value.

## Evaluate and analyze

```powershell
python scripts/evaluate.py --config configs/experiments/final_eval.yaml --manager rule_cancel --episodes 100
python scripts/evaluate.py --config configs/experiments/final_eval.yaml --manager heuristic_renegotiate --episodes 100
python scripts/evaluate.py --config configs/experiments/final_eval.yaml --manager learned --model models/ppo_default/seed-1/model.zip --episodes 100
python scripts/analyze.py --input results/raw --output results/summaries/latest
```

Before final experiments, review [the manual research steps](docs/MANUAL_STEPS.md) and approve the
safety thresholds, oracle definition, reward weights, baseline rules, seeds, and test matrix.
