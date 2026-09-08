# ReNe

**Learning When to Renegotiate in V2X Cooperative Merging**

## Team

- João **[add full name]** — project maintainer
- **[Add additional team member(s), if any]**

## Selected track

**Autonomous Agents / Multi-Agent Systems** **[replace with the course's exact track name]**

## Abstract

ReNe, short for **renegotiate**, studies how connected automated vehicles should manage freeway-merge agreements after acceptance. Most cooperative-driving work emphasizes reaching the initial agreement, but an agreement that was safe when accepted can become unsafe or inefficient after a human-driven vehicle cuts into the target gap, a participant brakes, or a V2X message becomes delayed or stale. We will train a compact, risk-aware policy that chooses whether to **continue**, **cancel**, or **renegotiate** an accepted merge agreement. Low-level vehicle motion will remain rule-based, and a separate safety shield will override unsafe decisions. In simulation, the learned manager will be compared with perception-only merging, one-shot negotiation, and fixed-threshold cancellation under changing traffic and communication conditions. The main hypothesis is that learned lifecycle management can shorten failed agreements and avoid unnecessary cancellations without increasing safety violations.

## Research question

Can a learned, risk-aware agreement manager outperform fixed lifecycle rules by preserving valid cooperative merge agreements, abandoning doomed agreements earlier, and issuing useful counter-proposals under uncertain traffic and V2X communication?

## Repository contents

- [`docs/literature_survey.md`](docs/literature_survey.md) — recent literature and state-of-the-art survey
- [`docs/project_proposal.md`](docs/project_proposal.md) — Canvas-ready proposal document
- [`docs/ai_novelty_feasibility_audit.md`](docs/ai_novelty_feasibility_audit.md) — AI critique, novelty boundary, and feasibility audit
- [`PROJECT_INTENT_NEGOTIATION.md`](PROJECT_INTENT_NEGOTIATION.md) — original concept note
- [`LITERATURE_NOVELTY_SCAN.md`](LITERATURE_NOVELTY_SCAN.md) — preliminary novelty scan

## Planned implementation

The minimum viable system will use `highway-env` or SUMO to simulate a freeway on-ramp merge. A learned high-level policy will observe traffic state, agreement state, and communication quality. It will select `continue`, `cancel`, or a bounded renegotiation action, while a rule-based safety layer enforces minimum gap and time-to-collision constraints. The project will evaluate safety, merge success, delay, comfort, agreement quality, communication cost, and generalization to unseen disturbances.

## Repository link

https://github.com/JoaoLucasVeras/ReNe
