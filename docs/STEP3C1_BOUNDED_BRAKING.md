# Step 3C1: bounded front-vehicle braking

Implemented locally October 10, 2026. This completes one small slice of Step 3C,
not the complete simulator-validation gate (M2).

## What changed

The braking disturbance no longer instantly changes the front car's speed.
An independent prescribed pulse moves its actual body with bounded acceleration:

| Phase | Default moderate event |
|---|---|
| Before trigger | Cruise at 25 m/s until 5 s |
| Braking | Decelerate at 3 m/s² for 2 s, reaching 19 m/s |
| Hold | Maintain the lower speed for 1 s |
| Recovery | Accelerate at 2 m/s² until returning to 25 m/s at 11 s |

Mild braking uses 1.8 m/s². Hard requests 4.5 m/s² but is capped at 4 m/s².
The speed floor is 8 m/s. Configuration lives in `configs/env/default.yaml` and
the environment defaults. This profile is a declared synthetic scenario choice,
not a parameter estimate or reproduction from the selected cancellation paper.

Front position and speed are integrated analytically across phase boundaries,
including triggers between simulation ticks and speed-floor/recovery caps.
Beacon payloads use this same trajectory evaluated at their generation timestamp.
The manager still receives only delivered payloads and constant-speed extrapolation;
it does not receive the pulse schedule, acceleration, severity or hidden current speed.
The viewer labels actual speed separately from the last received speed.

Physics provenance is now `step3c1-bounded-braking-v1`; the unchanged 35-feature
policy input contract remains `received-state-v1`. Earlier braking results are
not directly comparable. Earlier checkpoint policies require re-evaluation.

## Evidence and how to reproduce

Use the local Python environment from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check src scripts tests
.\.venv\Scripts\python.exe scripts/trace_communication.py --disturbance braking --delay-ms 100 --loss 0
.\.venv\Scripts\python.exe scripts/trace_communication.py --disturbance braking --delay-ms 100 --loss 1
.\.venv\Scripts\python.exe scripts/record_video.py --manager rule_cancel --disturbance braking --delay-ms 100 --loss 0 --output results/figures/step3c1_bounded_braking.gif --contact-sheet results/figures/step3c1_bounded_braking_frames.png
```

104 tests pass, including 22 new cases for severity bounds, exact trajectories,
off-grid boundaries, final partial integration, profile reset, speed caps,
received-state timing, outage isolation, unchanged cruise and invalid settings.
The sampled preview frames were visually checked: relative vehicle positions
change, the front car slows and recovers, and its received speed lags its actual speed.

Seed-42 diagnostic records (100 ms delay, moderate event, generic rule_cancel):

- No loss: local cancellation requested at 8 s, confirmed at 8.2 s; no collision,
  no completed merge, 400 beacons and 6 control messages. One safety-shield override:
  this is not evidence that the manager itself correctly detected the danger.
- Complete loss: cancellation requested at 1 s due to stale data, timed out at
  4 s; no collision and no completed merge. All 460 messages were dropped.
- Traces save effective environment configuration, evaluator-only truth, received
  observations, decisions and communication events under `results/raw/communication/`.
  Generated evidence is Git-ignored; rerun the commands on another machine.
- Trace directory timestamps use UTC and may show October 11 for this local session.

These are implementation diagnostics, not final baseline comparisons. Known reward
and cancellation-label limitations remain until Step 3D.

## Hardware and fidelity

The Python process runs on the local machine's CPU. No CUDA or GPU is used by
these tests, rule-based episodes or GIF rendering. Vehicle coordinates are computed
by the simulator and rendered from its state; they are not invented video footage.
The road, traffic and disturbances are synthetic, and the custom environment is
not HighwayEnv, SUMO, a real-world test, or a validated high-fidelity driving model.

## Remaining limitations and next slices

- The rear car still cruises rather than reacting through a car-following controller.
  Extreme/custom brake profiles may therefore produce implausible traffic behavior.
- Acceleration is bounded but its phase transitions are not jerk limited.
- Collision checking still uses Step 3A's swept linear interpolation over a physics
  tick, not an exact curved/accelerating swept-body solver. Ego integration, safety
  look-ahead and body geometry remain simplified and require Step 3E validation.
- Cut-in remains a legacy diagnostic placeholder with no physical intruder.
  Intent mismatch also awaits physical implementation.
- Renegotiation remains disabled; no candidate acceptance or execution is added here.

Proceed in small slices: (3C2) physical cut-in fixture and body/message coverage;
(3C3) physical intent mismatch; (3C4) shared bounded timing candidates;
(3C5) proposal/acceptance/expiry; (3C6) accepted execution and integration tests.
Only then continue Step 3D metrics and Step 3E validation before research baselines.
