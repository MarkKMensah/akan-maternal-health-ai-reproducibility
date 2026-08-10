# MMS maternal-health adapter: frozen three-seed development confirmation

Frozen: 2026-08-07  
Protocol: `mms-maternal-adapter-confirm-dev-v1`

## Purpose

Confirm that the selected MMS maternal-health adapter configuration is stable
across three new random seeds before any sealed-test release decision.  This is
a development confirmation, not a new hyperparameter search.

## Frozen seeds

`20260807`, `20260808`, `20260809`.

The prior screening seed `20260806` is reported separately and is not counted
among the three confirmatory seeds.

## Fixed inputs and configuration

Use the same immutable 7,240-row train manifest, 1,558-row development source,
baseline predictions, train-only vocabulary construction, MMS base revision,
adapter-only trainable subset, four epochs, per-device batch 8, gradient
accumulation 4, learning rate 0.001, 10% warm-up, AdamW settings, length
bucketing, 16 kHz verified cache, best-WER-then-CER epoch rule, and 5,000-draw
content-group-clustered bootstrap as the passed screen.

The model loader uses execution amendment 01
(`low_cpu_mem_usage=False`) for all seeds.  No outcome-contingent setting may
change.

## Per-seed outputs

Preserve all four epoch metrics and adapter checkpoints, full paired
development predictions, speaker-code results, bootstrap intervals,
environment, decision and SHA-256 manifest.

## Joint confirmation gate

Advance only if:

1. all three seed decisions pass every one-seed gate;
2. WER and CER improve versus baseline in every seed;
3. mean relative WER improvement is at least 5%;
4. no seed/speaker-code WER regression exceeds 0.03 and no CER regression
   exceeds 0.02;
5. every seed has output-failure rate at most 1% and passes integrity;
6. a 5,000-draw hierarchical bootstrap over seeds and semantic content groups
   has an upper 95% bound below zero for WER or CER delta; and
7. all three selected adapters, paired predictions, decisions and manifests
   have recorded SHA-256 values.

Report seed-wise values, mean, sample standard deviation, range, selected
epochs, runtime and memory.  Do not tune from these outcomes.

## Stop boundaries

The split is semantic-content-group-disjoint and speaker-stratified, not
unseen-speaker-disjoint.  Keep the sealed test closed, test rows read at zero,
RNMT human outcomes unread, SBLLM unrun, and RunPod/frontend/production
unchanged.  A pass authorizes only a separately frozen one-time test-release
protocol.
