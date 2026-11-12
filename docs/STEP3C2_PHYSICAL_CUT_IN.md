# Step 3C2: physical cut-in and shared local perception

Implemented locally October 10, 2026, after [bounded braking](STEP3C1_BOUNDED_BRAKING.md).
This completes one more Step 3C slice, not the M2 simulator-validation gate.

## Scenario and physical behavior

The cut-in is now a fourth vehicle with a real body, instead of a diagnostic
change to `synthetic_gap_bonus_m`. It exists from reset in the adjacent freeway
lane at y = -3.6 m; it is not spawned inside the target gap. The mainline is at
y = 0 and the ramp at y = +3.6 m. Its longitudinal speed is constant at the initial
desired speed (25 m/s), and its lateral motion starts at the configured trigger.

The default car crosses one lane in 2 s, starting at 5 s and finishing at 7 s.
Its lateral rate is therefore bounded at 1.8 m/s. Motion is evaluated from an
absolute-time trajectory, including off-grid trigger and final-step times.
Lateral acceleration/jerk are not modeled: rate changes at the start/end are
abrupt. This remains an axis-aligned simplified vehicle, not a steering model.

Initial offset ahead of the ego is:

`(initial_gap_m + vehicle_length_m) / 2 * cut_in_offset_fraction / severity_scale`

Default fraction = 0.4. In medium density, mild/moderate/hard offsets are
21.5/12.9/8.6 m. Severity changes proximity, not speed or lane-change duration.
Configuration validation rejects trajectories that do not fit between the named
mainline bodies. The intruder moves independently of manager choices.

Collision, actual pairwise TTC and actual headway now cover every vehicle pair,
including the intruder. The named front/rear gap itself does not shrink numerically;
it becomes **occupied** by an intervening vehicle. Contact with the target lane
counts, so default occupation begins at 6 s (halfway through the lane crossing).

An agreement still refers to its original contiguous front/rear opening. We do
not silently reinterpret it as a new opening around the intruder. While occupied,
the shared controller blocks entry, completion cannot be reported, and the safety
shield can cancel continued execution. Useful revised gaps require later candidate work.

## What the managers know

The intruder is **unconnected**: no additional V2X peer, beacon or acknowledgment
is manufactured for it. The two original peers retain the Step 3B delayed/lossy
communication model.

For this slice, local perception is an explicit idealized sensor abstraction:
instantaneous, noiseless body position/speed within +/-60 m longitudinally of the
ego, with no occlusion model or retained out-of-range track. It works even during
V2X outages. These are simulated sensor readings, not a trained vision pipeline.

Rules and PPO share the same encoded/decoded **40-feature** vector. Five new fields:

- `intruder_detected`: validity mask; zero when absent/out of range.
- `intruder_relative_m`, `intruder_speed_mps`, `intruder_lateral_m`: current readings;
  neutral zeros when not detected.
- `slot_occupied`: detected body overlaps the target lane and its center lies
  between **cached/extrapolated** original peer positions.

The vector contains no cut-in trigger, future trajectory, severity or intent label.
Original peer estimates are not corrected using hidden current truth. Existing
pair-gap/TTC/headway features retain their original named-pair meaning; actual
all-vehicle safety metrics are evaluator-only. The generic cancellation prototype
also cancels when `slot_occupied > 0.5`; this is not the literature-derived B2 yet.

Input version: `received-state-plus-local-sensor-v2`. Physics version:
`step3c2-physical-cut-in-v1`. All earlier 22/35-feature policies and normalizers are
incompatible with this observation shape. Regenerate diagnostics and re-evaluate
policies after physical/controller changes; do not combine older results as matched runs.

## Shared fallback repair

The new scenario exposed ramp overshoot: waiting until the gap is blocked can leave
insufficient stopping distance. The common controller now preserves an abort/stop
option while a nearby adjacent vehicle is locally detected and the ego has not
committed to a lane change. It uses current detection, not the future cut-in schedule.

Also corrected the stopping cap during cancellation: a fallback target of 18 m/s
does not guarantee that gradual braking stays within the next-step stopping bound.
That bound is now enforced even when the target is already below it. No positions
are clamped or vehicles teleported to manufacture a safe stop; acceleration remains bounded.

This is conservative and may reject useful cooperation even if the adjacent car
never cuts in. Review its influence, missed detections and late disturbances in
Step 3E. It is identical for every manager; do not attribute its effect to learning.

## Verification and reproduction

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check src scripts tests
.\.venv\Scripts\python.exe scripts/smoke_test.py --config configs/experiments/smoke.yaml
.\.venv\Scripts\python.exe scripts/trace_communication.py --disturbance cut_in --delay-ms 100 --loss 0
.\.venv\Scripts\python.exe scripts/record_video.py --manager rule_cancel --disturbance cut_in --delay-ms 100 --loss 0 --output results/figures/step3c2_physical_cut_in.gif --contact-sheet results/figures/step3c2_physical_cut_in_frames.png
```

- 134 tests and lint pass, including 30 new cut-in/perception/fallback cases.
- Tests cover nine density/severity combinations; each default fixture cancels,
  has no collision or original-slot completion, and stops within the ramp boundary.
- Off-grid timing, seeded replay, reset, missing detection, V2X outage isolation,
  identical rule/PPO information and swept contact between tick endpoints are checked.
- The default 10-episode smoke workflow runs and reports zero completed merges.
  This is expected for this occupied-original-slot fixture without revised-gap actions,
  not a claim that the overall project should always cancel or fail to merge.
- Seed 42, moderate cut-in, 100 ms delay and no loss: cancellation requested at 6 s,
  confirmed at 6.2 s; no collision/completion and zero shield overrides. 400 beacons,
  6 control messages, 404 deliveries and 2 in-flight messages at episode end.
- Actual minimum headway is 0.594 s, below the configured 0.8 s criterion. All cars
  cruise at equal longitudinal speed, so actual TTC is infinite, serialized as null.
  No collision is not equivalent to meeting all traffic-safety criteria.
- GIF/sampled frames visually checked: purple car crosses from the upper lane;
  occupancy appears halfway across; ego remains on the ramp and stops before its end.

Trace JSON includes effective config, versions, decisions and communication events;
CSV separates manager observations from evaluator-only intruder/peer truth.
Results are Git-ignored and generated on the local CPU, without CUDA/GPU use.
Output timestamps are UTC and may show October 11 for this local October 10 session.

## Remaining work

Next small slice: **Step 3C3 physical intent mismatch**. Then shared feasible
candidates, message-based proposal acceptance/expiry and accepted execution.
All renegotiation actions remain disabled. The rear/front cars do not yet have
reactive car-following; sensor realism, late cut-ins, conservative occupancy,
reward/event accounting and wider safety validation remain open. This slice is
not a paper reproduction, wireless-stack simulation, or final baseline experiment.

No commit or push was requested for this implementation session.
