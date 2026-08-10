# Domain-Adapted NLLB RNMT v3 Protocol — Frozen

**Protocol version:** `nllb-v3-lora-dev-v1`  
**Frozen:** 4 August 2026, before any v3 model training or v3 output inspection  
**Status:** development-only experiment authorised; final test remains sealed  
**Production:** unchanged; the existing NLLB top-1 path remains operational  

## 1. Research question

Does parameter-efficient, train-only adaptation of the pinned NLLB model improve
maternal-health Twi-to-English translation when the source is the deployed MMS
ASR transcript, without degrading gold-input translation or introducing new
clinically important semantic redirections?

This experiment addresses a failure demonstrated by the declared live
diagnostic `HA_0108`: the gold Twi itself was translated incorrectly by the
baseline NLLB model, so the error could not be attributed only to ASR. The
experiment does not claim clinical efficacy, population generalisation, or
independent clinical validation.

## 2. Immutable provenance

### 2.1 Base translation model

- repository: `facebook/nllb-200-distilled-600M`
- immutable revision: `f8d333a098d19b4fd9a8b18f94170487ad3f821d`
- source language: `twi_Latn`
- target language: `eng_Latn`
- licence recorded by the model repository: `CC-BY-NC-4.0`
- research use only unless a separate licence review authorises another use

### 2.2 ASR model used for the primary input condition

- repository: `facebook/mms-1b-all`
- immutable revision: `3d33597edbdaaba14a8e858e2c8caa76e3cec0cd`
- recorded experiment label: `mms_1b_akan_base`

### 2.3 Frozen train/development materialisation

Directory: `02_Data/Derived/nllb_v3_2026-08-04`

- `train_pairs_group_balanced_v1.csv`
  - SHA-256: `6672887fe9117e9f14ec085ef79533b5c148b85d10043d449b811d4a06a1bc37`
  - 7,240 Twi-English rows from 2,139 train-only semantic groups
- `dev_pairs_gold_and_mms_v1.csv`
  - SHA-256: `cb202d42d8a0d079f68515a4effd536be2ee91cea5e4689e2f55251a5c67626a`
  - 1,558 development records from 458 original semantic groups
- `DATASET_MANIFEST_v1.json`
  - SHA-256: `c86ee991c6d588e2dd568381a2e6a366964338b3fda2c23300713da6a2462c47`
  - train/development group overlap: 0
  - development gold sources exactly seen in train: 0
  - development MMS sources exactly seen in train: 0
  - test rows exported: 0
  - test predictions read: 0
- `NLLB_V3_FROZEN_CLINICAL_LEXICON_v1.json`
  - SHA-256: `a0532f1a5124dd48e90f9f4697cc8a9ddb7ac99048244c2c70dcb6a7727b23aa`
  - high-recall review-queue trigger only; it is not represented as a
    clinical ontology or as a translation component

Development groups `CG01858` and `CG02330` contain two adjudicated English
targets. They retain their original group identifiers for cluster resampling,
while target-specific effective group identifiers are used for scoring. The
targets must not be normalised as equivalent.

The four ambiguity/duplicate records quarantined by the Human Canonical Gate
(`PT_1334`, `PT_1411`, `BT_0937`, and `HA_0552`) remain excluded from v3.

## 3. Systems and conditions

- **V3-M0:** the pinned, unadapted NLLB baseline.
- **V3-M1-S17:** LoRA adaptation with seed 17.
- **V3-M1-S29:** LoRA adaptation with seed 29.
- **V3-M1-S47:** LoRA adaptation with seed 47.

Every system is evaluated on the same development records under two paired
input conditions:

1. `gold`: validated Twi reference transcription, an ASR-error-free upper
   bound;
2. `mms`: frozen raw MMS transcription, the primary deployed-path condition.

No development source or target may be used for training, prompt construction,
retrieval, lexicon expansion, threshold tuning, or manual correction.

## 4. Frozen adaptation configuration

### 4.1 LoRA

- PEFT task type: `SEQ_2_SEQ_LM`
- target modules: `q_proj`, `v_proj`
- rank `r`: 16
- alpha: 32
- dropout: 0.10
- bias: `none`
- base-model weights remain frozen
- trainable parameter count and proportion must be logged

### 4.2 Tokenisation and decoding

- maximum source length: 192 tokens
- maximum target length: 192 tokens
- a pre-training tokenizer audit must report zero truncated train and
  development sequences; otherwise the run aborts before optimisation
- development generation: six beams, `early_stopping=true`,
  `length_penalty=1.0`, `max_new_tokens=192`
- target language is forced with the `eng_Latn` BOS token
- the same decoding configuration is used for M0 and every M1 seed

### 4.3 Optimisation

- precision: bfloat16 on an NVIDIA A100 or H100; any other accelerator aborts
- optimizer: AdamW
- learning rate: `2e-4`
- betas: `(0.9, 0.999)`
- epsilon: `1e-8`
- weight decay: `0.01`
- scheduler: linear
- warm-up ratio: `0.10`
- gradient clipping: `1.0`
- label smoothing: `0.10`
- per-device train batch: 16
- gradient accumulation: 2
- effective single-GPU batch: 32
- maximum epochs: 8
- evaluate and checkpoint at the end of every epoch
- early stopping patience: 2 completed evaluations
- best checkpoint criterion: development-gold corpus chrF++

The gold condition is used for checkpoint selection because it isolates the
translation model from stochastic ASR corruption. The primary promotion
endpoint remains the frozen MMS condition.

### 4.4 Group-balanced sampling

Each train row has weight `1 / group_variant_count`. A single-GPU
`WeightedRandomSampler` draws `len(train)` samples with replacement per epoch.
This gives each semantic group equal expected contribution despite differing
numbers of surface variants. The sampler generator is seeded with the arm's
fixed seed. Distributed training is prohibited for v1 so sampler semantics
remain unambiguous.

### 4.5 Software environment

The notebook installs and records these packages:

- `transformers==4.57.1`
- `peft==0.17.1`
- `accelerate==1.11.0`
- `datasets==4.3.0`
- `evaluate==0.4.6`
- `sacrebleu==2.5.1`
- `sentencepiece==0.2.1`
- `scikit-learn==1.7.2`

The Colab-provided PyTorch/CUDA stack is not silently replaced. Its exact
versions, GPU identity, driver, Python version, package freeze and environment
variables relevant to determinism are captured before training. A mismatch
between the installed and declared package versions aborts the run.

## 5. Frozen metrics and statistical analysis

For every record, input condition and system, retain source, reference,
hypothesis, seed, group identifiers and hashes.

Report:

- corpus chrF++ (`word_order=2`), the primary automatic metric;
- corpus sacreBLEU;
- normalized whitespace-token F1, macro-averaged by record;
- per-record chrF++ for paired error analysis;
- improvement, unchanged, degradation and material-regression counts;
- results by theme, speaker code and input condition;
- adapter size, peak GPU memory, train/evaluation time and generation latency.

`Material regression` is frozen as a paired per-record chrF++ change of no more
than `-5.0` points relative to M0.

Uncertainty is estimated with 20,000 paired bootstrap replicates clustered by
the original `content_group_id`, using bootstrap seed `20260804`. Each
replicate samples the 458 original groups with replacement and retains all
records and target-specific effective subgroups belonging to each sampled
group. For the primary multi-seed estimate, the statistic is the mean of the
three seed-specific corpus-score differences within each replicate. Report
two-sided percentile 95% intervals; do not substitute an unclustered row-level
interval.

## 6. Pre-specified semantic-safety review

Automatic scores cannot establish clinical meaning preservation. Before a v3
arm is promoted, the principal investigator reviews a blinded paired queue
containing, for both gold and MMS conditions:

- every material regression;
- every M0/M1 disagreement involving a negation, number, temporal expression,
  participant, requested action, urgency/referral term, medicine, symptom,
  pregnancy stage, infant-care term or other frozen maternal-health lexicon
  item;
- every output with a source-side clinical term but no corresponding concept
  in the hypothesis;
- every M1 concept absent from both the source-aligned reference and M0;
- a fixed, seed-derived 10% sample of remaining changed outputs, stratified by
  theme and input condition.

The reviewer records at least: intent preservation, question/statement form,
participant, requested action, negation, number, critical concept, severity,
preferred output and adjudication note. The reviewer is the author/native
Akan speaker, not an independent clinician; the dissertation must state this
limitation explicitly.

## 7. Frozen development promotion gates

V3-M1 may advance to paired downstream SBLLM evaluation only if every condition
below is satisfied:

1. **Primary MMS benefit:** the three-seed mean MMS chrF++ difference is
   positive and its clustered 95% lower confidence limit is at least `0.0`.
2. **Gold non-inferiority:** the three-seed mean gold chrF++ difference has a
   clustered 95% lower confidence limit of at least `-0.5` points.
3. **Seed stability:** each of the three seeds has a positive mean MMS chrF++
   difference; the range between seed-specific MMS differences is at most
   `2.0` points.
4. **Safety:** no reviewed M1 output introduces a new confirmed critical
   semantic redirection, harmful negation reversal, unsupported high-risk
   clinical instruction or urgency/referral loss that is absent from M0.
5. **Unsafe-rate non-inferiority:** on the identical blinded review queue, the
   confirmed unsafe rate for M1 must not exceed M0. Exact paired counts and a
   two-sided McNemar test are reported descriptively; the safety rule is not
   waived for lack of statistical significance.
6. **Regression control:** material regressions may affect no more than 5% of
   development records in either condition for any seed, and every such record
   is included in the human review queue.
7. **Completeness:** all hashes, checkpoints, adapters, logs, training curves,
   row-level predictions, bootstrap draws, review queue and environment
   records are present in the immutable Drive run folder.

If any gate fails, retain V3-M0, report v3 as a negative or mixed result, and do
not open the final test.

## 8. Downstream and final-test rule

If all development translation gates pass, select the deployment candidate as
the seed with the highest MMS development chrF++ (ties resolved by the smaller
gold material-regression count, then the lower seed number). Freeze its adapter
and decoding hashes before running a paired downstream comparison:

- M0 translation → unchanged SBLLM;
- selected M1 translation → the same SBLLM model, prompt, memory, temperature
  and seed.

Any new unsafe SBLLM response, material intent loss, or urgency/referral loss
blocks test release. Only after a signed downstream release record may the
sealed test partition be opened once. No weight, threshold, prompt,
normalisation rule, lexicon, decoder or selector may change after opening it.

## 9. Human Canonical Gate relationship

The versioned train-only canonical index remains a separate diagnostic:

- normalized exact lookup (`HC1`) may later be evaluated as a narrow runtime
  safety layer for already validated train variants;
- fuzzy retrieval (`HC2-D`) is prohibited from production because 62 of 540
  accepted closed-set leave-one-out decisions were semantically wrong;
- `HA_0108` correctly abstains under HC1 and HC2-D and therefore remains an
  out-of-memory diagnostic for v3;
- adding `HA_0108` after observing the failure would be an operational patch,
  not evidence of unseen generalisation.

## 10. Stop conditions and transparency

The notebook must stop immediately for a hash mismatch, train/development
overlap, tokenizer truncation, unavailable required GPU, non-finite loss,
missing output, incomplete seed, or attempted access to any sealed-test file.
The final cell writes `RUN_COMPLETE.json` only after all three development seeds
and their artifacts are complete. A failure writes `RUN_FAILED.json` with the
exception and environment snapshot.

## 11. Methodological sources

- NLLB Team et al. (2022), *No Language Left Behind: Scaling Human-Centered
  Machine Translation*, arXiv:2207.04672, https://arxiv.org/abs/2207.04672
- Costa-jussà et al. (2024), *Scaling neural machine translation to 200
  languages*, Nature 630, 841–846,
  https://doi.org/10.1038/s41586-024-07335-x
- Hu et al. (2022), *LoRA: Low-Rank Adaptation of Large Language Models*,
  ICLR 2022, https://openreview.net/forum?id=nZeVKeeFYf9
- Koehn (2004), *Statistical Significance Tests for Machine Translation
  Evaluation*, EMNLP 2004, https://aclanthology.org/W04-3250/
- Efron and Tibshirani (1993), *An Introduction to the Bootstrap*, Chapman &
  Hall/CRC.

