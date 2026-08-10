# MMS maternal-health adapter screening: positive development result

Date completed: 2026-08-07  
Protocol: `mms-maternal-adapter-screen-dev-v1`  
Seed: `20260806`  
Selected epoch: `4`  
Automatic gate: **PASS**

## Result

On the frozen 1,558-record, 458-content-group development partition, the
selected train-only maternal-health MMS adapter reduced WER from `0.5068335`
to `0.2987706` (absolute delta `-0.2080629`; relative reduction `41.05%`) and
CER from `0.1457793` to `0.0785546` (absolute delta `-0.0672246`; relative
reduction `46.11%`).  There were zero output failures.

The 5,000-draw content-group-clustered 95% intervals were wholly below zero:

- WER delta: `[-0.2177472, -0.1987818]`
- CER delta: `[-0.0704792, -0.0641284]`

All four recorded speaker codes improved:

| Speaker code | Rows | Baseline WER | Adapted WER | WER delta | Baseline CER | Adapted CER | CER delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| BT | 377 | 0.47168 | 0.26873 | -0.20295 | 0.13882 | 0.07153 | -0.06729 |
| HA | 429 | 0.48317 | 0.31268 | -0.17049 | 0.15057 | 0.09365 | -0.05692 |
| IM | 372 | 0.48289 | 0.28233 | -0.20056 | 0.13526 | 0.07465 | -0.06062 |
| PT | 380 | 0.58342 | 0.33287 | -0.25056 | 0.15860 | 0.07703 | -0.08157 |

Every precommitted gate passed: relative WER improvement at least 5%, CER no
worse, a clustered CI upper bound below zero, no speaker-code WER regression
greater than 0.03, no speaker-code CER regression greater than 0.02, output
failure at most 1%, and integrity pass.

## Provenance and execution

- Base model: `facebook/mms-1b-all`
- Base revision: `3d33597edbdaaba14a8e858e2c8caa76e3cec0cd`
- Trainable parameters: `2,203,689` of `964,701,097`
- Training time: `1,193.37` seconds for four epochs
- Selected adapter SHA-256:
  `3DABE79C0569375A862635D14E0F32ABECBC619387012FE9E1179B1593AADF0E`
- Paired development predictions SHA-256:
  `64B2A0B58EBDCD3AE19A91DC8AC5EE630FC0A48B09562F4C15C3C5D558FAD0A2`
- Decision SHA-256:
  `C5E73B4A2E71340186C35A673A36E609B364933DEDC1A6EFDFEF2465F7DEBADB`
- SHA-256 manifest SHA-256:
  `F9B6112E8BC7A1249AED72F1BC9AF668FD2A158E9CE4282CD3381F110A63CD06`
- Drive run folder:
  https://drive.google.com/drive/folders/1IfaOwchMZB4HIGBr1WoR5NmSPJNujUT4
- Full paired predictions:
  https://drive.google.com/file/d/1p4OmoIEGngQlb0d8ob_Km1ayBkjhI4NJ/view

Execution amendment 01 changed only `low_cpu_mem_usage=True` to `False` after
the first loader attempt failed on meta-device tensors before epoch 1.  No
development prediction had been produced or read.  The amendment, old and new
script hashes, and unchanged scientific settings were recorded before rerun.

## Interpretation boundary

This is a strong one-seed development result on controlled scripted
maternal-health Twi from the same four speaker codes represented in training.
The split is semantic-content-group-disjoint and speaker-stratified, not
unseen-speaker-disjoint.  The result does not establish clinical safety,
spontaneous-speech performance, population-level Akan generalisation, or a
final test-set result.  The sealed test was not opened; test rows read were
zero.  RNMT human outcomes, SBLLM, RunPod, frontend and production were not
changed.

## Decision

Advance the selected configuration to a separately frozen three-seed
development confirmation.  Do not open the sealed test, run downstream SBLLM,
or change production until the multi-seed result and release gate are complete.
