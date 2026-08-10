# MMS maternal-health adapter screening — frozen protocol

**Protocol ID:** `mms-maternal-adapter-screen-dev-v1`  
**Freeze date:** 2026-08-06 (America/New_York)  
**Scope:** one-seed train/development feasibility screen; sealed test closed

## Research question

Does train-only maternal-health adapter training of the frozen MMS-1B model
improve recognition on semantic-group-disjoint maternal-health development
speech relative to the immutable public Akan MMS baseline?

This is the first upstream intervention after V3-M4 to V3-M8 established that
the MMS-conditioned downstream candidate set was the primary bottleneck and
that selector, threshold and train-memory retrieval changes could not provide
adequate general coverage.

## Literature-supported method

The experiment follows the MMS language-adapter design rather than full-model
fine-tuning. The official MMS work uses small language-specific adapters over a
shared multilingual speech encoder (Pratap et al., 2023:
<https://ai.meta.com/research/publications/scaling-speech-technology-to-1000-languages/>).
The official Hugging Face guide recommends adapter training for low-resource
ASR and describes reinitializing the output vocabulary and adapter layers from
train-only text (<https://huggingface.co/blog/mms_adapters>). Independent
low-resource studies also report competitive or superior adapter performance
with limited labelled speech (Mainzinger and Levow, 2024:
<https://aclanthology.org/2024.acl-srw.16/>; Liang and Levow, 2025:
<https://aclanthology.org/2025.fieldmatters-1.3/>).

## Frozen data

- Training manifest SHA-256:
  `1EBC4FF1D7F668AD28BA7262DD4CB143264F39906CF98B3B11806A9BCCDB5633`.
- Training: 7,240 records, 2,139 semantic groups, 12.5935 hours; BT, HA,
  IM and PT; all 7,240 audio paths verified present.
- Development source SHA-256:
  `30C202E8490BE242A411B1547712527546D3355237072CB29C09CB301FACFA4F`.
- Development: 1,558 records, 458 semantic groups; BT 377, HA 429,
  IM 372 and PT 380.
- Train/development semantic-group overlap: zero.
- Split terminology: semantic-group-disjoint and speaker-stratified, not
  speaker-disjoint.

## Frozen models and outputs

- Baseline: `facebook/mms-1b-all` revision
  `3d33597edbdaaba14a8e858e2c8caa76e3cec0cd`, public Akan adapter `aka`.
- Immutable baseline development predictions:
  `mms_1b_akan_base__3d33597edbda__full_dev.csv`.
- Screening candidate: the same immutable MMS-1B base, with a new train-only
  character vocabulary, reinitialized language-adapter layers and CTC output
  layer. The shared base encoder remains frozen.

## Target and scoring normalization

Train targets use the frozen `source_gold_normalized` field. Evaluation follows
the previously frozen primary scoring policy:

- Unicode NFC;
- Unicode casefold;
- diacritics preserved;
- punctuation and symbols replaced by spaces;
- whitespace collapsed and stripped;
- primary WER on normalized words;
- primary CER on normalized characters with spaces excluded.

The train-only character vocabulary may not be extended from development
references. Development out-of-vocabulary characters must be reported.
Because primary targets exclude punctuation, this experiment does not claim to
solve punctuation restoration; punctuation remains a separate limitation.

## Frozen screening configuration

- seed: `20260806`;
- epochs: `4`;
- adapter-only trainable parameters; shared encoder frozen;
- optimizer: AdamW, learning rate `1e-3`, beta1 `0.9`, beta2 `0.999`,
  epsilon `1e-8`, weight decay `0`;
- linear schedule with 10% warm-up;
- record-uniform sampling, length-bucketed batches;
- device batch size `8`, gradient accumulation `4` (effective batch 32);
- bfloat16 on supported A100 hardware;
- dynamic input/label padding, 16 kHz mono audio;
- gradient checkpointing and maximum gradient norm `1.0`;
- greedy CTC decoding, matching the immutable MMS baseline;
- best epoch selected by normalized development WER, with CER as tie-breaker.

This is one precommitted feasibility configuration, not a hyperparameter grid.
All four epoch results must be retained.

## Outcomes and uncertainty

Report:

1. normalized corpus WER and space-excluded CER for baseline and candidate;
2. paired candidate-minus-baseline WER and CER differences with 5,000-draw
   semantic-group-clustered bootstrap 95% intervals;
3. per-speaker WER/CER and paired deltas;
4. output failure rate, development OOV-character rate, epoch loss, runtime,
   trainable parameter count and peak GPU memory;
5. raw predictions, normalized predictions and references for every
   development record.

## Automatic advancement gate

Advance to a separately frozen three-seed confirmation only if all conditions
hold for the selected epoch:

1. candidate WER is at least 5% relatively lower than baseline WER;
2. candidate CER is no worse than baseline CER;
3. the upper bound of the clustered 95% interval is below zero for at least
   one of WER or CER difference;
4. no speaker-code WER regresses by more than 0.03 absolute;
5. no speaker-code CER regresses by more than 0.02 absolute;
6. output failure rate is at most 1%; and
7. no integrity assertion fails.

If the gate fails, preserve the negative result and do not tune the same
development set retrospectively. If it passes, do not yet open the sealed test:
freeze three confirmation seeds, a protected-meaning evaluation and a single
final model-selection rule first.

## Stop-state and claim boundary

Throughout screening:

- sealed test opened: `false`;
- test rows read: `0`;
- RNMT human outcomes read: `false`;
- SBLLM run: `false`;
- production changed: `false`.

This study concerns controlled, scripted maternal-health Twi from four speaker
codes. It does not establish clinical safety, spontaneous-patient-speech
performance, unseen-speaker generalisation, clinical-environment performance
or population-level Akan generalisation.

