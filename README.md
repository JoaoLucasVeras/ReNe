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

## Implementation status

The repository now contains a CPU-capable research prototype with:

- A seeded Gymnasium lifecycle environment for an accepted freeway-merge agreement
- Post-acceptance cut-in, braking, intent-mismatch, latency, and packet-loss disturbances
- Continue, cancel, and bounded renegotiation actions
- One-shot, rule-cancellation, and heuristic-renegotiation baselines
- A deterministic feasibility checker and safety shield
- PPO training, paired evaluation, analysis, and worker-benchmark scripts
- Automated lifecycle, feasibility, safety, environment, and reproducibility tests

The custom environment is optimized for rapid agreement-management experiments. HighwayEnv's
`merge-v1` remains the visual/reference simulator and can be used for later cross-validation.

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
