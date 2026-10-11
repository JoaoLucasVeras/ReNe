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
- Prototype disturbance and communication signals; real cut-in motion and delayed received-state delivery remain pending
- Continue, cancel, and provisional timing revisions; next-gap/order-swap remain disabled until physical candidates exist
- One-shot, rule-cancellation, and heuristic-renegotiation baselines
- A deterministic feasibility checker and safety shield
- PPO training, paired evaluation, analysis, and worker-benchmark scripts
- Automated lifecycle, feasibility, safety, environment, and reproducibility tests

The custom environment is optimized for rapid agreement-management experiments. HighwayEnv's
`merge-v1` remains the visual/reference simulator and can be used for later cross-validation.

Step 3A's bounded geometry fixtures pass; see [the implementation and preview instructions](docs/STEP3A_PHYSICAL_MERGE.md).
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
