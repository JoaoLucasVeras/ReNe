# Step 3B communication and manager information

Date: October 10, 2026. Status: implemented for the abstract channel and protocol
fixtures below. Full M2 validation remains open. The owner authorized publication
on October 10; see Git history and the project log for revision and scope.
No PPO training or full baseline experiment was performed.

## What changed

Previously delay/loss only changed a number; managers still saw current neighbor
truth. Now neighbors send timestamped state beacons. Messages wait in a queue,
may be dropped, and update a received-state cache only when delivered. During
an outage, the manager keeps its last received data and sees its increasing age.

Cancellation also travels through the queue. Local fallback starts immediately,
but the host cannot claim confirmation until both peers' release acknowledgments
arrive. Complete loss leads to timeout, not assumed remote release.

This is an abstract V2X implementation, not a radio/propagation/network-stack
model or a complete reproduction of the source paper.

## Channel contract

- Beacons: each mainline vehicle sends x position and speed every 100 ms.
- Delay: fixed configurable one-way delay, in milliseconds; not round-trip delay.
- Loss: independent Bernoulli drop at transmission for each message.
- Message identity: sender, receiver, kind, agreement ID, revision, per-route/kind
  sequence, generation time, scheduled delivery time and a copied payload.
- The scheduler represents communication events inside the 200 ms dynamics step.
  Beacon positions are interpolated on that step's declared linear physical
  segment. Managers only observe delivered data at their decision times.
- Drop streams are independent per beacon sender and separate from control
  messages, so cancellation retries cannot alter the beacon-loss realization.
- Cache updates require the correct session/route and a newer generation/sequence.
  Duplicates and out-of-order older packets cannot overwrite new information.
- Reset begins with an accepted agreement and assumed last received states at
  t = 0. These are explicit initialization fixtures, not zero-delay deliveries
  under the configured channel. Initial negotiation is not simulated or counted.

Parameters: `communication_delay_ms`, `packet_loss`, `beacon_interval_s`,
`cancel_retry_s`, `cancel_timeout_s`. The last three default to 0.1, 0.1 and 3.0 s.
They are validated as finite/nonnegative or positive as appropriate.

## Who sees what

| Consumer | Available information |
|---|---|
| Lifecycle manager | Current own speed/acceleration/lateral position and distances; received neighbor estimates, ages and availability; local agreement/protocol state |
| Common safety controller and action shield | Current simulator state for the shared safety abstraction; identical for every manager |
| Evaluator | True state, message queue/drop/release events, decision traces and final metrics |

Neighbor positions are estimated by constant-speed extrapolation from the last
delivered payload and its age. The extrapolator never corrects itself from hidden
neighbor truth. A speed change remains unknown until a new message arrives.
No local neighbor sensor model is implemented; perfect neighbor sensing is
restricted to the common safety abstraction, not the high-level manager.

The deployable information contract is `received-state-v1` in
`src/rene/envs/manager_inputs.py`. Its **35 features** include signed relative
positions, projected slot clearances/TTC/headway, separate peer ages/availability,
ego lateral position, and cancellation pending/confirmed/timeout/ACK indicators.
The TTC is a received-data target-slot estimate, not evaluator actual-lane TTC.

The learned observation is a bounded float32 vector. The rule managers decode
that exact vector rather than read unbounded `info` or ground-truth fields. Both
therefore share clipping, precision and missing-data conventions. Bounds are
explicit in `FEATURES`; ages saturate at 60 s, TTC at 20 s with a finite-TTC flag,
and signed distances at their declared bounds. Cache availability means a
received/assumed initial packet exists, not that it is fresh; age remains separate.

`info['manager_inputs']` is the same decoded vector for inspection. Lifecycle
metadata is for debugging; evaluator event logs and metrics are returned at
episode termination and are not used by the prototype managers. The full
`communication_log` records sent/delivered/dropped/cache/protocol events.

**Compatibility change:** old 22-feature policies and normalizers are not
compatible. Retrain only after later validation gates pass. Neither hidden
intent-mismatch diagnostic errors nor the configured true loss probability is
provided as a policy feature.

## Cancellation contract

The common local agreement's `canceled` state means the host has requested
disengagement and enabled fallback; it does NOT mean all participants know.
The separate communication session follows:

```text
active -> cancel_pending -> cancel_confirmed
                        -> timed_out
```

- The host sends cancellation to both peers, retrying every 100 ms for peers
  not yet acknowledged. Repeated manager requests do not reset the timer.
- A peer is marked released only after receipt of a valid cancellation.
  A duplicate valid request may prompt another ACK but cannot release twice.
- A release ACK uses the same delayed/lossy channel. Confirmation requires both.
- IDs/revisions, routes, request tokens and expiry protect against stale-session
  receipts. The request lifetime is the configured timeout; late control traffic
  cannot reopen a timed-out or confirmed session.
- ACKs delivered exactly at the deadline are processed before timeout. Queued
  delivery order is deterministic for ties; zero-delay replies are drained before
  the deadline check. Retries/beacon generation follow due deliveries.
- Remote release is evaluator-only until acknowledged. Timeout never asserts
  that remote vehicles received a request.
- If physical completion ends an episode while cancellation is pending, the
  record stays pending/right-censored; it is not relabeled confirmed or timed out.

Release ACKs and a fixed 3 s request lifetime are ReNe abstractions. They are not
the source's complete Intent/CIF-dependent timeout method. Peer release currently
changes protocol state only: cooperative remote acceleration/reservation control
has not been implemented and must not be inferred from the acknowledgment.

All renegotiation actions are now unavailable through the production executor.
This includes Step 3A's provisional timing changes: no revision can be assumed
accepted without a physical candidate and acceptance executor. Step 3C will
restore supported actions with meaningful trajectories and protocol handling.

## Diagnostics you can run

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check src scripts tests
.\.venv\Scripts\python.exe scripts/trace_communication.py --delay-ms 100 --loss 0
.\.venv\Scripts\python.exe scripts/trace_communication.py --delay-ms 100 --loss 1
.\.venv\Scripts\python.exe scripts/trace_communication.py --delay-ms 800 --loss 0
```

Each trace run creates a unique Git-ignored folder under
`results/raw/communication/`, containing `received_states.csv` and `trace.json`.
The CSV separates evaluator true state from manager data; JSON includes settings,
decisions, messages and final metrics. Infinite/non-applicable values become null
in JSON, not fake finite safety times. Folder timestamps are UTC; this session
is October 10 in America/Los_Angeles.

| Seed 42 rule-manager diagnostic, no physical disturbance | Observed behavior |
|---|---|
| 100 ms delay, no loss | Data age about 0.1 s; merge at 9.2 s; no cancellation; 184 beacons sent, 182 delivered, 2 still in flight |
| 100 ms delay, complete loss | Cancellation at 1 s, timeout at 4 s; no remote release/ACK; 400 beacons and 60 control requests dropped over the 20 s episode |
| 800 ms delay, no loss | Cancellation at 1 s; peers released at 1.8 s; host confirmation at 2.6 s |

These are behavior checks, not claims that the threshold rule is optimal. In the
high-delay fixture the rule's arbitrary 0.5 s stale threshold causes cancellation
even though neighbor motion remains predictable. The selected paper's B2 is still
not implemented.

**82 tests passed; lint passed.** Coverage includes delay, full loss/recovery,
duplicate/stale/out-of-order traffic, wrong IDs/revisions/routes/request tokens,
lost first request or reply, retries, timeout, same-deadline acknowledgment,
seeded event reproducibility and beacon-drop fairness, truth isolation, identical
clipped inputs, missing cache, signed distances, in-flight accounting, physical
completion with cancellation pending and exact episode clock termination.

The existing smoke workflow completed ten episodes. This remains diagnostic:
its physical cut-in is still absent and full metric definitions remain unfinished.
The audit script also ran; complete-outage ages now grow 1, 2, 3 s rather than
remaining 1.1 s. A floating-point episode-boundary overshoot discovered during
trace checks was fixed, including a final partial dynamics step when necessary.

## Watch a communication scenario

```powershell
.\.venv\Scripts\python.exe scripts/record_video.py --manager rule_cancel --seed 42 --disturbance none --delay-ms 800 --loss 0 --output results/figures/step3b_high_delay.gif
```

The preview displays received-data age and the cancellation session state.
Generated evidence is not staged by Git automatically.

## Remaining work and next step

**Step 3C: physical disturbances, common candidate trajectories and proposal
acceptance/execution.** Real cut-ins, bounded braking, actual intent mismatch and
cooperative remote actuation still need work. Follow with Step 3D metric/reward
accounting and Step 3E full scenario review before literature baselines or PPO.

Basic sent/delivered/dropped/in-flight counts and cancellation timestamps are now
event-derived; message count includes background beacons separately labeled from
control traffic. Reward still repeatedly charges cumulative message count, and
failed-agreement duration, unnecessary cancellation and failed merge-time labels
remain legacy definitions. Do not treat those values as final research metrics.
