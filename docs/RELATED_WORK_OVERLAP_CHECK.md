# Related-work overlap check before Step 2

Date: October 1, 2026

## Evidence

Paper: **AI-Assisted Maneuver Coordination for Connected and Automated Vehicles**, Gasco et al., VTC 2026 author manuscript.

- [Institutional record](https://iris.polito.it/handle/11583/3008889)
- [Full manuscript](https://iris.polito.it/retrieve/df3a71f2-389c-42a6-ac2c-6c1de47e3fe3/ManeuverCoordination.pdf)

Section III.B (printed page 4; PDF page 5 including the repository cover) describes an XGBoost binary filter that suppresses predicted failures before coordination initiation. Section IV trains it from labeled deterministic-simulation outcomes. The described AI does not select repeated post-acceptance continue/cancel/renegotiate actions. References to execution monitoring elsewhere do not establish an AI lifecycle policy. [Source](https://iris.polito.it/retrieve/df3a71f2-389c-42a6-ac2c-6c1de47e3fe3/ManeuverCoordination.pdf)

## Assessment for ReNe

This is a close related source and belongs in the literature survey. Our proposed decision point remains distinct from its described AI filter. That observation is evidence of a difference from this paper, not proof that ReNe is the first project to address the problem.

Preserve the central question: when does learned management of an already accepted agreement improve outcomes compared with literature-derived cancellation and matched heuristic renegotiation?

Avoid claiming novelty merely from using AI or PPO. A useful contribution would be a fair, reproducible measurement of learning's incremental value across traffic and communication conditions.

## Implications for the experiment

- Keep the initial accepted agreement and scenario conditions comparable across managers.
- Separate benefits of selecting good initial agreements from benefits of managing them later.
- If adding an initial AI filter later, apply it consistently or evaluate it as a separate experimental factor.
- Consider a simpler learned classifier as an optional later comparator, adapted and labeled for the new task. Different learning algorithms alone do not establish a new research problem.
- Further related-work searches remain necessary before a publication-level priority claim.

## Step status

- [x] Read the closest identified AI paper's full method.
- [x] Check whether its AI operates at initiation or after acceptance.
- [x] Record the supported distinction and its limits.
- [ ] Step 2: create `BASELINE_REPRODUCTION_SPEC.md` for the selected cancellation source.

Step 2 will extract the cancellation rule, required inputs, timing and protocol parameters, reference tests, and explicit lane-change-to-merge adaptations. This overlap check informs that specification but does not complete it.
