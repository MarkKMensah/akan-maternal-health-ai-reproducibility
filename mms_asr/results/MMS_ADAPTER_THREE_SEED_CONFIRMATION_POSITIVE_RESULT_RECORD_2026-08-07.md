# MMS maternal-health adapter: positive three-seed development confirmation

Date completed: 2026-08-07  
Protocol: `mms-maternal-adapter-confirm-dev-v1`  
Decision: **PASS on development; eligible only for a separately frozen one-time sealed-test release protocol**

## Research question

Does the train-only maternal-health MMS adapter configuration selected by the
one-seed screen reproduce across three new random seeds under the identical,
precommitted development protocol?

## Frozen design

- Seeds: `20260807`, `20260808`, `20260809`; screening seed `20260806` was
  excluded from the confirmation.
- Immutable inputs: 7,240 train rows from 2,139 semantic groups and 1,558
  development rows from 458 non-overlapping semantic groups.
- Frozen base: `facebook/mms-1b-all` at revision
  `3d33597edbdaaba14a8e858e2c8caa76e3cec0cd`.
- Adapter-only training: 2,203,689 trainable parameters out of 964,701,097;
  four epochs; effective batch 32; learning rate 0.001; 10% warm-up; fixed
  best-WER-then-CER selection; greedy CTC decoding.
- Uncertainty: 5,000 content-group-clustered draws per seed and a separately
  precommitted 5,000-draw hierarchical bootstrap over seeds and semantic
  content groups.

The partition is **semantic-content-group-disjoint and speaker-stratified**.
BT, HA, IM and PT occur in train and development; this is not an
unseen-speaker experiment.

## Transparent execution amendment

The first launch of seed `20260807` stopped before model loading because three
terminal-status lines had accidentally been prepended to the Python file.
Only those three non-Python lines were removed. No model, data, split, seed,
hyperparameter, epoch, metric, selection rule, gate or stop boundary changed.
No training or development prediction had occurred. The invalid and corrected
script hashes and the updated precommit were recorded before relaunch in
`MMS_ADAPTER_THREE_SEED_CONFIRMATION_EXECUTION_AMENDMENT_01_2026-08-07.md`.

## Seed-wise development results

The immutable public MMS baseline was WER `0.5068335` and CER `0.1457793` for
all comparisons. Every seed selected epoch 4 and had zero output failures.

| Seed | WER | CER | Relative WER improvement | Relative CER improvement | WER delta 95% clustered CI | CER delta 95% clustered CI | Training seconds |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20260807 | 0.302921 | 0.080196 | 40.23% | 44.99% | [-0.213189, -0.194423] | [-0.068718, -0.062346] | 1186.92 |
| 20260808 | 0.283793 | 0.073918 | 44.01% | 49.29% | [-0.232172, -0.214031] | [-0.075144, -0.068575] | 1183.27 |
| 20260809 | 0.301173 | 0.077443 | 40.58% | 46.88% | [-0.214860, -0.196472] | [-0.071553, -0.065224] | 1194.61 |

## Three-seed summary

- Mean WER: `0.295962`; sample SD `0.010575`; range
  `0.283793`–`0.302921`.
- Mean CER: `0.077186`; sample SD `0.003146`; range
  `0.073918`–`0.080196`.
- Mean relative WER improvement: `41.61%`; sample SD `2.09` percentage
  points; range `40.23%`–`44.01%`.
- Mean relative CER improvement: `47.05%`; sample SD `2.16` percentage
  points; range `44.99%`–`49.29%`.
- Mean WER delta: `-0.210871`; hierarchical 95% CI
  `[-0.222459, -0.200865]`.
- Mean CER delta: `-0.068593`; hierarchical 95% CI
  `[-0.071939, -0.065255]`.
- Mean training time: `1188.27` seconds; sample SD `5.79` seconds.
- Peak allocated GPU memory was approximately `11.81` GB in every seed.

The hierarchical intervals are wholly below zero. The gain is therefore not
dependent on the single screening seed.

## Speaker-code robustness

Every seed improved both WER and CER for BT, HA, IM and PT. Across seeds:

- BT WER was `0.2541`–`0.2722`, versus baseline `0.4717`.
- HA WER was `0.3005`–`0.3179`, versus baseline `0.4832`.
- IM WER was `0.2653`–`0.2864`, versus baseline `0.4829`.
- PT WER was `0.3172`–`0.3410`, versus baseline `0.5834`.

No precommitted speaker-code regression threshold was approached.

## Gate decision

All joint gates passed:

1. all three per-seed decisions passed;
2. WER and CER improved in every seed;
3. mean relative WER improvement exceeded 5%;
4. no speaker-code WER or CER regression breached its limit;
5. all output-failure rates were 0% and all integrity checks passed;
6. the hierarchical WER and CER upper confidence limits were below zero; and
7. every selected adapter, prediction file, decision and manifest has a
   recorded SHA-256 value.

## Reproducibility identifiers

- Joint evidence bundle: preserved in controlled research storage and not
  redistributed in this repository.
- Joint decision SHA-256:
  `FA446575F4A1A2C7A58B9FE4691D580BE881B42D63F1E3CCC62CB9A60C333AC9`
- Joint manifest SHA-256:
  `C0C027B657F886200AFBC09C5A5B730167B2AA8A221E3D73B2E5973B92289675`
- Selected adapter hashes:
  - seed 20260807: `2C69EDCD094924EC687C9CA2A610F873A54FD54B985EA5816EA810747C131DA7`
  - seed 20260808: `5D8A7CEE21D660CBD34C5F3FC414EA375B662220BBA7C8177D3CD12D19B443AA`
  - seed 20260809: `F9B87F0ACD73BB8703ED936EB79117699FA9988B05B13ADB9D5288E0994B496B`

The exact seed decisions, environments, epoch metrics and manifests are also
preserved under `work_products/mms_maternal_adaptation/execution_outputs/`.
Twenty-two local-to-Drive hash comparisons passed with zero mismatch.

## Boundary audit and interpretation

- Sealed test opened: **no**.
- Test rows read: **0**.
- RNMT human outcomes read during training/analysis: **no**.
- SBLLM run: **no**.
- RunPod/frontend/production changed: **no**.

This is strong development evidence that train-only maternal-health adaptation
substantially and reproducibly improves MMS recognition on controlled scripted
maternal-health Twi from the four recorded speaker codes. It does **not** prove
clinical safety, spontaneous patient-speech performance, unseen-speaker
generalisation, population-level Akan performance, or end-to-end downstream
benefit.

The pass authorizes only the freezing of a separate one-time sealed-test
release protocol. Test data must not be opened until the test container,
selected checkpoint rule, baseline, normalization, metrics, subgroup analyses,
confidence intervals, failure criteria and no-tuning rule are all fully
identified and hash-locked.
