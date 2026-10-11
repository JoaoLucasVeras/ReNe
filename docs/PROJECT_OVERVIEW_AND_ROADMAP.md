# ReNe explained and the path to completion

Last updated: October 10, 2026

## What is our project?

ReNe means renegotiate. We are studying what connected vehicles should do when
a merge agreement stops making sense **after the vehicles have already agreed**.

Imagine a car entering a freeway. Two freeway cars agree to leave it a space.
Before the merging car reaches that space, another driver cuts in, one of the
cars brakes, or a message arrives late. The original agreement may no longer
be safe or useful. Our system must decide whether to:

- **Continue:** keep the accepted plan.
- **Cancel:** release the agreement and use the shared fallback driving behavior.
- **Renegotiate:** ask for a revised plan, such as a later merge or a different gap.

V2X means vehicle communication with other vehicles or infrastructure. Our intended
simulation uses an abstraction of those messages, not a complete wireless network.

The system we want to learn is a **plan manager**, not an entire self-driving car.
The shared driving controller handles acceleration and motion. A separate common
safety layer protects the vehicle regardless of which manager chooses the plan.
Canceling an agreement does not necessarily mean the car cannot merge later.

## What is the goal?

Our question is: **When does a learned manager make better decisions than good
rules, and when are rules already enough?**

We originally considered using reinforcement learning directly. Your professor
pointed out that there are few choices and relatively simple inputs, so a strong
rule-based manager might perform just as well. We revised the project to test
that question rather than assume that AI will win.

Reinforcement learning learns decisions from simulated experience and feedback.
PPO is the learning algorithm we currently plan to test, after the baselines work.
We have not established that PPO is necessary or better for this problem.

The intended comparisons are:

| Manager | Plain-language behavior | What the comparison tells us |
|---|---|---|
| B1 one-shot | Keep the original agreement unless the common safety system intervenes | Starting reference |
| B2 literature-derived cancellation | Monitor the agreement and cancel according to the selected research method, with documented merge adaptations | Does monitoring help? |
| B3 matched rule-based renegotiation | Use explicit rules to choose from the same revised plans available to the learned manager | Does renegotiation help? |
| B4 learned management | Learn when to continue, cancel or choose one of those revised plans | Does learning add value beyond good rules? |

All managers must use the same scenario, driving controller, safety layer and
relevant information. B3 and B4 must have the same proposal choices. Otherwise
we could mistake an unfair advantage for a benefit of learning.

Success means trustworthy evidence about safety, useful agreement retention,
merge completion, delay, comfort and communication cost. A result showing that
rules are sufficient is still a successful research outcome. We will not claim
real-world safety guarantees from simulation alone.

## What have we done so far?

### Research direction and planning

We revised the question following your professor's feedback, selected a recent
cancellation paper, checked closely related work, and wrote a specification for
how to adapt the source method to our merge setting. The source concerns lane
changes, so we must distinguish its original rules from our adaptations.
Instructor guidance on that adaptation remains pending.

These documents establish what to build. They do not mean we have already
implemented or validated the paper's method.

### Software starting point

The repository contains a custom simulation prototype, simple rule managers,
agreement states, a feasibility checker, an action-level shield, and scripts for
training, evaluation and analysis. Think of it as a first working draft of the
experiment, not a finished research simulator.

Although HighwayEnv is a dependency/reference option, the current custom environment
does not run an integrated HighwayEnv merge simulation. For Step 3A we chose to
keep and correct the custom simulator; integration remains an optional later task.

### Audit of the prototype

On October 1, seven existing tests passed and we ran small repeatable diagnostic
episodes. That means the tested software interfaces work, not that the simulated
traffic is physically correct. The audit found important problems:

| Current problem | Why it matters |
|---|---|
| A merge succeeds when the car crosses a position, even if the agreed gap is far ahead | We could count a merge that never actually happened |
| The value named TTC measures arrival-time separation, not actual time to collision | Safety conclusions could be misleading |
| Message delay/loss does not delay the vehicle state seen by the manager | Communication experiments would not test the intended uncertainty |
| Some revised plans add artificial gap space or instantly change speed | Renegotiation could appear useful because of unrealistic shortcuts |
| Several metrics and event logs need corrected accounting | Comparing managers could reward the wrong behavior |

The three prototype managers produced the same recorded outcomes in four
seeded disturbance conditions. That small check is not proof that correctly
implemented managers perform equally well.

We initially paused before changing simulator behavior. Since then, the approved
Step 3A repaired geometry and physical completion for bounded fixtures; the
remaining communication/disturbance/metric limitations still need work. Main PPO
training and final research comparisons remain pending.

## Roadmap from here

October 10 update: [Step 3A is implemented](STEP3A_PHYSICAL_MERGE.md) and checked
against bounded physical fixtures. 35 tests pass; the full validation gate is
still open. Step 3B now adds real message delivery/cache and cancellation handling;
see [the communication record](STEP3B_COMMUNICATION.md). The next implementation
task is Step 3C; 82 software tests currently pass.

The phases below summarize the detailed [TODO tracker](PROJECT_ROADMAP.md).
Check them only when their completion evidence exists. No fixed calendar dates
are assigned because the semester deadline and repair effort are not yet established.

### Phase 1 make the simulation trustworthy

**Current phase.** These tasks can be developed and checked on the laptop without a GPU.

- [x] **Step 3A: fix physical merging for the declared fixtures.** Keep the custom simulator,
  create valid moving gaps, represent vehicle sizes and lane positions, and define
  a merge as actually entering the intended lane/gap safely. Correct collision
  and vehicle-to-vehicle safety calculations.
- [x] **Step 3B: fix communication for the abstract fixtures.** Send timestamped messages, deliver or drop them,
  keep the last received state, and make information become older during outages.
  Define how agreement changes are acknowledged or expire.
- [ ] **Step 3C: fix disturbances and revised plans.** Make cut-ins and braking change
  actual motion. Give every proposed gap/timing change a real trajectory and bounded
  control response. Remove artificial gap bonuses.
- [ ] **Step 3D: fix measurement.** Record when decisions happen, when agreements
  become invalid, what messages are sent and when revised plans succeed. Define
  unnecessary cancellation using a separate evaluator, not future knowledge given
  to a manager.
- [ ] **Step 3E: validate the repairs.** Use small scenarios where we already know
  the correct result, then check different traffic and communication settings.

**Ready to move on when:** physically valid scenarios and independently checked
metrics pass the M2 gate. Passing the original seven tests alone is insufficient.

### Phase 2 establish strong non-learning comparisons

- [ ] Obtain instructor guidance on the proposed paper adaptation.
- [ ] Implement and test B2 separately from the current generic threshold rules.
- [ ] Build one shared menu of physically feasible revised plans.
- [ ] Implement B3 using that menu and documented decision/ranking rules.
- [ ] Run B1, B2 and B3 on the same small scenario set and inspect their decisions.

**Ready to move on when:** the baselines behave sensibly, the comparison is fair,
and there is a meaningful question left for learning. Do not weaken safety to
create an opportunity for PPO to look better.

### Phase 3 prepare reliable experiments

- [ ] Verify the desktop environment and dependencies. Reported hardware is a
  Ryzen 5 3600, RTX 3060 Ti and 32 GB RAM; actual setup remains to be checked.
- [ ] Define separate training, tuning and held-out testing scenarios.
- [ ] Fix scenario seeds and record configurations, code revisions and run IDs.
- [ ] Make evaluation save useful decision traces as well as episode summaries.
- [ ] Check analysis on examples with known answers; include condition-specific
  comparisons and uncertainty, not just overall averages.

This infrastructure can overlap baseline development after metric definitions
are reliable. The desktop is not a prerequisite for the current documentation
or small deterministic repairs.

### Phase 4 train and assess the learned manager

- [ ] Check that PPO sees the same relevant information and proposals as B3.
- [ ] Verify the reward cannot exploit simulation or measurement shortcuts.
- [ ] Run a short training/save/load test, then tune only on development data.
- [ ] Benchmark CPU versus GPU rather than assume GPU is faster for the small model.
- [ ] Train multiple independent runs and freeze the chosen settings before final testing.

**Ready to move on when:** training is repeatable and saved models can be evaluated
correctly. Beating the rules is an experimental outcome, not an implementation requirement.

### Phase 5 compare explain and finish

- [ ] Evaluate all managers on the same held-out scenarios, including traffic
  disturbances and delayed/lost communication.
- [ ] Compare safety first, then completion, agreement quality, time, comfort and messages.
- [ ] Report where learning wins, ties or loses, with sample counts and uncertainty.
- [ ] If time permits, add one bounded stronger-validation extension, such as a
  model-based comparator or targeted simulator transfer.
- [ ] Produce reproducible figures, example timelines, final documentation and
  the course-required GitHub/Canvas deliverables.

## What exactly should we do next?

**Review Step 3A/3B results, then scope Step 3C.** Define actual cut-in/braking
motion and how feasible revised plans are proposed, accepted and physically
executed. Communication is now meaningful, but disturbances and metrics still
need validation before the baseline comparison.

The overview was initially created as documentation only. The subsequent approved
Step 3A implementation is recorded separately; no PPO training, commit or push
has been performed in that implementation session.

## Where to find our project memory

- This document: simple explanation and phase-level roadmap.
- [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md): detailed TODOs and acceptance gates.
- [PROJECT_LOG.md](PROJECT_LOG.md): session history, decisions and current handoff.
- [SIMULATION_AND_METRIC_DEFINITIONS.md](SIMULATION_AND_METRIC_DEFINITIONS.md): audit evidence and required metric corrections.
- [BASELINE_REPRODUCTION_SPEC.md](BASELINE_REPRODUCTION_SPEC.md): source rules versus merge adaptations.

Research documents were pushed in `ce7d47c`; Step 3A and the audit/progress records
were then pushed in `9976057`. The owner has now authorized Step 3B publication;
see the project log and latest Git history for its scope and revision.
