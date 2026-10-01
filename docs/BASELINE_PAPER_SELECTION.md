# Step 1: Cancellation Baseline Paper Selection

Date: October 1, 2026

Status: Source selected for specification; implementation and simulator adaptation are pending.

## Selection

**When Cooperation Should End: Maneuver Coordination Cancellation for Connected Automated Driving**

Rafael Molina-Masegosa, Sergei S. Avedisov, Miguel Sepulcre, Javier Gozalvez, and Onur Altintas. IEEE VTC2026-Spring, June 9–13, 2026; author postprint submitted June 20, 2026.

- [Author record](https://arxiv.org/abs/2606.22052)
- [Full paper](https://arxiv.org/pdf/2606.22052)
- [Postprint DOI](https://doi.org/10.48550/arXiv.2606.22052) — this is an arXiv DOI, not the IEEE proceedings DOI.

The implemented trigger cancels when the host loses its lane-change incentive (Section III.B). The host repeats cancellation messages every 100 ms until the remote vehicle sends Intent or execution times out. The remote vehicle aborts on receipt and replies within 100 ms (III.A). Evaluation uses optional highway lane changes and ns-3, with five-second predictions (IV). Sections II–IV are the extraction targets. [Source](https://arxiv.org/pdf/2606.22052)

No official implementation repository was verified in this search. This does not establish that code is unavailable.

## Candidate comparison

| Candidate | Evidence inspected | Assessment for ReNe |
|---|---|---|
| Selected 2026 cancellation paper | Full-text decision and management sections | Best match to the requested cancellation baseline; specification must resolve maneuver adaptation. |
| [Negotiation in Cooperative Maneuvering using Conflict Analysis: Theory and Experimental Evaluation](https://public.websites.umich.edu/~orosz/articles/2024_IVS_Wang_Avedisov_Altintas_Orosz.pdf), Wang et al., IEEE IV 2024; DOI 10.1109/IV55156.2024.10588700 | Full-text mathematical negotiation criteria | Strong supporting source for a later model-based comparator; its main decision is initial request/response, not ongoing-agreement cancellation. |
| [Evaluation of a Negotiation Acceptance Scheme in Maneuver Coordination within a Congested Environment](https://www.jstage.jst.go.jp/article/ipsjjip/32/0/32_223/_article/-char/en), Iwashina, Kato, and Shigeno, 2024; DOI 10.2197/ipsjjip.32.223 | Full-text acceptance and agreement logic | Useful for utility-based acceptance and participant consistency; not the preferred cancellation source. |
| [Maneuver Coordination Service With Reliability and Relevance Enhancements](https://researchportal.ulisboa.pt/en/publications/maneuver-coordination-service-with-reliability-and-relevance-enha/), Figueiredo et al., 2025; DOI 10.1109/OJITS.2025.3613990 | Institutional publication record and abstract; full methods not verified from a primary host | Supporting communication-reliability source; insufficient verified decision detail to choose as B2. |

The 2024 conflict-analysis paper supplies explicit feasibility conditions based on bounded motion and conflict-zone timing. The other 2024 paper supplies acceptance utility and an agreement phase. Neither is a better direct fit to the professor's cancellation request. The 2025 paper focuses on acknowledgments and relevant-message filtering. These assessments are selection judgments, not claims that the papers lack other useful mechanisms.

## Why choose this source

Our selection criteria are explicit post-acceptance decisions, interpretable management rules, accessible methods, and semester feasibility. The selected source gives us a concrete reference against which to specify B2. It also allows us to separate a manager's decision from the protocol that executes cancellation.

Step 1 selects a source; it does not establish that the existing ReNe threshold manager reproduces it or that the paper proves PPO is needed.

## Adaptation issue to resolve in Step 2

The following is our engineering assessment: an on-ramp vehicle generally must merge before the ramp ends. A rule about losing the benefit of an optional lane change may therefore behave differently from a rule about abandoning a particular accepted merge agreement.

We must choose and document a defensible bridge:

1. **Reference scenario:** implement a small optional lane-change case to validate the source logic, then test a separately labeled merge adaptation.
2. **Merge adaptation:** retain ReNe's merge task and define when the particular agreed gap/time loses its benefit relative to fallback. Any new benefit function is a ReNe design choice, not an equation claimed to come from the paper.

Recommendation: specify a reference scenario plus the merge adaptation. If the simulator cannot support a credible reference case within scope, document that limitation and ask the instructor whether the adapted baseline satisfies the reproduction requirement.

## Required outputs of Step 2

Create `docs/BASELINE_REPRODUCTION_SPEC.md` with:

- [ ] Source section/page for each extracted behavior.
- [ ] Exact incentive calculation and prediction dependencies, including follow-up references where needed.
- [ ] Host/remote state transitions and cancellation acknowledgment/timeout semantics.
- [ ] Parameter provenance: published, adapted, or validation-tuned.
- [ ] Observable inputs versus privileged evaluation information.
- [ ] Explicit mapping from optional lane change to the accepted merge plan.
- [ ] Reference tests with expected actions and state transitions.
- [ ] Boundaries between manager cancellation and emergency shield intervention.
- [ ] Distinction between request time, message delivery, remote disengagement, and completed cancellation.
- [ ] Full reproduction versus component adaptation claims.

Keep B2, B3, and PPO on the same execution and safety layers in the eventual comparison. Record any protocol simplification equally across methods. Do not silently import the original paper's network-level or traffic-level results into ReNe.

## Completion record

- [x] Search and screen recent primary sources.
- [x] Identify and inspect explicit cancellation logic.
- [x] Compare a short list and choose a reference source.
- [x] Verify bibliographic details and check for public code.
- [x] Record the major implementation-fit limitation.
- [ ] Complete source-to-simulator reproduction specification (Step 2).
- [ ] Implement and validate B2 (later milestones).

Paper selection is complete. M1 as a whole remains open until the reproduction specification is finished.
