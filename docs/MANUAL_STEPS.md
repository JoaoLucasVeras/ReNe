# ReNe Manual Research Steps

These tasks require the project owner's judgment or direct verification. They should not be delegated entirely to generated code.

## 1. Install and verify the development machine

- Install Python 3.11 or 3.12 and Git on the desktop computer.
- Update the NVIDIA driver for the RTX 3060 Ti.
- Create a fresh virtual environment and install the project.
- If CUDA training is desired, install the PyTorch build recommended by the official selector: https://pytorch.org/get-started/locally/
- Run `python -c "import torch; print(torch.cuda.is_available())"`.
- Run the worker benchmark on the Ryzen 5 3600 and compare CPU versus CUDA PPO before choosing a device.

## 2. Review the research definitions

Before final training, approve and document:

- Minimum target gap
- Minimum time-to-collision
- Minimum time headway
- Acceleration and deceleration limits
- Agreement-invalidation persistence window
- Offline-oracle look-ahead horizon
- Meaning of an unnecessary cancellation
- Meaning of successful renegotiation
- Maximum renegotiation attempts

The values currently in YAML are implementation starting points, not validated final research thresholds.

## 3. Validate the simulation behavior

- Run the no-disturbance scenario and confirm that the agreement normally completes.
- Run every disturbance under a fixed seed and inspect its decision log.
- Confirm that disturbances used for the primary experiments begin after agreement acceptance.
- Render representative scenes and confirm vehicle positions and events are plausible.
- Verify that an obviously unsafe continuation is overridden.
- Verify that a feasible alternative gap can be accepted.
- Verify that infeasible renegotiation is rejected.
- Compare selected custom-environment behaviors with HighwayEnv `merge-v1`.

## 4. Review the generated implementation

- Read code changes and test output before committing them.
- Confirm that every manager uses the same scenario, low-level dynamics, feasibility checker, and shield.
- Inspect raw CSV rows rather than relying only on summary plots.
- Preserve a research log explaining configuration and design changes.
- Commit reviewed milestones using the project owner's Git identity.

## 5. Freeze the experiment

Before using the final test set:

- Finish tuning on training and validation seeds.
- Freeze the Git commit, dependency versions, YAML configurations, reward weights, thresholds, and selected policies.
- Decide the final number of training seeds. Five is preferred; three is the minimum fallback.
- Decide the final episode count based on measured runtime. The proposal target is 1,000 episodes per major condition when feasible.
- Define the exact held-out disturbance combinations.
- Do not use final-test results for additional tuning.

## 6. Supervise final runs

- Ensure adequate disk space and uninterrupted runtime.
- Monitor CPU temperature, memory use, and failures.
- Do not delete or silently rerun failed seeds without recording why.
- Save console output, configurations, checkpoints, and raw result files.
- Back up the frozen code and final raw data.

## 7. Validate the analysis

- Manually calculate metrics for several episodes and compare them with the generated CSV values.
- Investigate every collision and a sample of shield overrides.
- Check plots against the underlying CSV data.
- Report sample sizes, confidence intervals, variability, and effect sizes.
- Do not interpret a nonsignificant result as proof of equivalence.
- Obtain instructor guidance before making a formal safety non-inferiority claim.

## 8. Complete the academic work

- Read and verify the cited papers, author lists, years, and DOIs.
- Confirm that the claimed research gap is supported by the literature.
- Write the final interpretation and limitations in the student's own voice.
- Disclose AI assistance according to course policy.
- Avoid claiming that cancellation, reinforcement learning for merging, or safety shielding is independently novel.
- Describe safety results as empirical unless a formal guarantee is actually established.

## 9. Final repository and submission check

- Test setup, smoke test, and a small evaluation from a clean clone.
- Remove credentials, temporary files, caches, local environments, and unnecessary large models.
- Confirm the README contains exact reproduction commands.
- Confirm required GitHub deliverables are visible.
- Upload the proposal document to Canvas separately if required.
- Review the final repository diff before pushing.
