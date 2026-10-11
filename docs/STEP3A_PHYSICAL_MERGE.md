# Step 3A physical merging implementation

Date: October 10, 2026. Status: implemented and checked for the bounded fixtures
below; **the full M2 simulator-validation gate remains open**. The project owner
authorized publication on October 10; see the project log and Git history for
publication scope and revision. This step keeps the custom Gymnasium simulator as the
primary development implementation; HighwayEnv integration is not included.

This is the Step 3A implementation record. Subsequent [Step 3B](STEP3B_COMMUNICATION.md)
adds delivery/cache/protocol handling, replaces the observation contract with 35
features and disables all provisional timing revisions pending Step 3C.

## What changed in simple terms

The merging car now moves sideways into the freeway lane between the actual
blue cars. A position crossing alone cannot count as success. Cars have physical
sizes, so two bodies touching or crossing during a simulation step can register
a collision. A car that misses the gap stays on the ramp and brakes instead of
being awarded a successful merge.

The controller is still a simplified rule-based controller. These changes are
not a learned policy, a reproduction of the selected paper, a full vehicle
dynamics model, or proof of safety in arbitrary traffic.

## Physical contract

| Setting | Meaning and current default |
|---|---|
| Coordinates | Vehicle centers in meters; x follows the road, freeway y = 0, ramp y = 3.6 |
| Vehicle body | Axis-aligned rectangle, 4.5 m long and 1.8 m wide; no rotation |
| Initial speeds | Ego and both mainline vehicles start at the configured desired speed, 25 m/s |
| Initial gap | Free opening between mainline bumpers: medium 60 m, low 72 m, high 50 m |
| Initial alignment | Gap midpoint is aligned longitudinally with the ego; equal speeds preserve it in the undisturbed case |
| Minimum clearance | 12 m for each ego/front and rear/ego pair, plus minimum follower headway of 0.8 s |
| Merge corridor | Lateral transition may begin after x = 140 m and must fit before the ramp end at x = 240 m |
| Reference position | x = 200 m schedules the midpoint of the transition, not a success event |
| Lateral duration | 2 s at bounded constant lateral speed of 1.8 m/s |
| Completion | Ego reaches target lane center, occupies the actual named gap with safe clearance/headways, and remains valid for 1 s |
| Integration | Default dt = 0.2 s; decision interval = 1 s, required to be an integer multiple of dt |

The configured initial gap is now honored; density scales it by 1.2, 1.0 and
5/6 for low, medium and high, respectively. Reset rejects gaps that cannot meet the starting clearance
criteria, and rejects nominal lane-change plans that cannot fit the corridor.
These are simple aligned accepted-plan fixtures, not realistic traffic-flow distributions.

## Geometry and safety calculations

`src/rene/envs/geometry.py` provides pure functions for signed bumper clearance,
body overlap, constant-speed longitudinal TTC and swept overlap.

- Bumper clearance subtracts half of each body's length from center separation.
- Body contact counts as a collision only when longitudinal AND lateral extents
  overlap. Vehicles alongside each other in separate lanes do not collide.
- Swept overlap checks the whole linear segment between integration samples,
  avoiding endpoint-only collision checks that miss a vehicle passing through another.
- Actual TTC uses relative speed for bodies currently sharing lateral space.
  Infinity means non-closing/non-applicable; it is not a measured safety duration.
- `target_slot_ttc_s` separately projects the ego into the target lane to assess
  prospective slot suitability. It is not an actual current-lane collision event.
- `headway_s` in manager info is prospective ego/front and rear/ego headway.
  `actual_headway_s` and episode minimum headway use currently applicable pairs.
- Near-collision continues to use the configured TTC threshold, now with actual
  longitudinal TTC. Richer future-path conflicts and exposure accounting remain later work.

The common controller gates lateral entry on constant-speed clearances over the
remaining transition and stabilization horizon. It can retreat toward the ramp
when a partially merged slot becomes unsuitable, caps approach speed at the ramp
end, and applies a front-vehicle speed bound when laterally overlapping.
Acceleration/deceleration remain bounded. These checks are not a formal safety
shield or guarantees against all sudden disturbances. Collisions can still be
detected if a constructed or disturbed state cannot be recovered safely.

Cancellation remains separate from task completion. The fallback target is
18 m/s; it may finish a physically safe merge into the same pair, or remain on
the ramp. Searching for a different fallback gap is not implemented.

## Prototype shortcuts removed or restricted

- Synthetic gap bonuses no longer change clearance, collision, completion or TTC.
- Next-gap and order-swap proposals are disabled through proposal feasibility;
  requests fall back to cancellation until Step 3C supplies physical candidates.
- Delay/advance modify the scheduled transition time without instantly changing
  vehicle speed. They are still provisional timing actions, not validated negotiated plans.
- The legacy cut-in penalty remains a diagnostic field only; **there is no physical
  cut-in vehicle yet**, so do not interpret a `cut_in` run as a cut-in experiment.
- Braking still instantaneously changes front speed and intent mismatch still
  changes diagnostic features. Both require Step 3C repairs.
- Info labels the physical version and whether the disturbance is `none`.
  That flag is a narrow declaration, not certification of a whole scenario.

Observation dimension remains 22, but geometry and TTC semantics changed. Do not
reuse old trained checkpoints as if they were compatible research results.
Observation-access/scaling and lateral-state features are part of the upcoming
shared information contract. Full metric accounting and reward fixes remain Step 3D.

## Validation performed

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check src scripts tests
.\.venv\Scripts\python.exe scripts/smoke_test.py --config configs/experiments/smoke.yaml
```

- **35 tests passed**, including the original seven and 28 new physical fixtures/
  parameter cases. Lint passed across `src`, `scripts` and `tests`.
- Fixtures cover clearance/contact boundaries, separate lanes, closing versus
  non-closing TTC, swept longitudinal/lateral contact and a two-axis near miss,
  three density settings, rejected initial gaps/corridor, true merge completion,
  missed gap, unsafe lateral entry, collision termination, headway, timing actions,
  stabilization reset and cancellation separate from completion.
- Undisturbed completion was checked at dt = 0.1, 0.2 and 0.25 s. This is bounded
  step-size coverage, not a convergence proof for every controller/disturbance.
- A diagnostic sweep of 90 undisturbed episodes (three densities × three prototype
  managers × seeds 0–9, zero delay/loss) yielded 90 physical completions, zero
  collisions and zero cancellations. It does not rank the managers.
- The default ten-episode smoke run (seeds 42–51) yielded six completions and no
  collisions. It retains default loss/staleness and invalid physical disturbance
  abstractions; failures and cancellations are not final research metrics.
- Smoke files: `results/raw/smoke/rule_cancel-20261011T012349Z/` (UTC filename;
  session date is October 10 in America/Los_Angeles). This run preceded adding
  the physics-version field to CSV rows; its provenance is recorded here.
- Audit script reran successfully. It now exports infinite/non-applicable times
  as JSON null rather than fake finite TTC values. Original audit numbers remain
  historical evidence for the pre-repair implementation.

Hand calculation for seed 42, medium density, no disturbance:

- Initial free opening 60 m gives each ego clearance `(60 − 4.5)/2 = 27.75 m`.
- Equal speed 25 m/s gives each follower headway `27.75/25 = 1.11 s` and no closing TTC.
- Lateral transition starts at t = 6.2 s, finishes at t = 8.2 s; stabilization
  completes at t = 9.2 s. Ego x = 250.548 m, with both clearances still 27.75 m.
- Success beyond x = 240 m is valid here because the ego has already fully left
  the ramp before its end; simply driving past that position on the ramp would fail.

## Watch the corrected merge

```powershell
.\.venv\Scripts\python.exe scripts/record_video.py --manager one_shot --seed 42 --disturbance none --output results/figures/step3a_physical_merge.gif
```

The renderer follows the ego, uses the same scale for x/y, and displays time,
manager and agreement state. Default playback is one second per decision frame;
use `--frame-ms 200` to speed it up. It samples decision frames, not every physical
substep, and the final interval may be shorter than one second.

Generated GIF: `results/figures/step3a_physical_merge.gif`. Selected frames:
`results/figures/step3a_merge_frames.png`. Visually checked: the orange body moves
into the lane between the blue bodies; completion occurs after stabilization.
Generated previews and smoke results are ignored by Git.

## Next step

**Step 3B: timestamped message delivery, received-state caching and the shared
information/protocol contract.** Do not collect a full rule-based results table or
train PPO yet. Real disturbance/candidate behavior (3C), event metrics (3D), full
scenario review (3E), source-adaptation guidance and desktop verification remain open.
