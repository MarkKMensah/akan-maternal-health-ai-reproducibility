# V3-M9 adapted-ASR causal propagation protocol

**Protocol ID:** `nllb-v3-m9-adapted-asr-causal-propagation-dev-v1`  
**Freeze date:** 2026-08-07  
**Scope:** development-only automatic eligibility experiment  
**Sealed test:** closed; 0 test rows may be read  
**Downstream SBLLM and production:** not run and not changed

## Research question

Does the representative, train-only maternal-health MMS adapter improve the
quality and protected-meaning preservation of English translations produced by
the unchanged V3-M1 seed-17 RNMT system, relative to the original public-MMS
development transcripts?

This experiment isolates the ASR intervention. It changes no RNMT weight,
decoder, prompt, threshold, memory, selector, reference, partition or SBLLM
component.

## Frozen systems and conditions

The 1,558-row development partition contains 458 semantic content groups. The
partition is semantic-content-group-disjoint from training and
speaker-stratified; BT, HA, IM and PT occur in both training and development.
It is not an unseen-speaker experiment.

The three paired input conditions are:

- `G` (diagnostic only): validated gold Twi input and the already preserved
  V3-M1 seed-17 English output;
- `D0` (deployable baseline): original public-MMS Twi hypothesis and the
  already preserved V3-M1 seed-17 English output; and
- `D1` (experimental): representative adapted-MMS Twi hypothesis translated
  once by the same V3-M1 seed-17 RNMT model and decoding configuration.

`G` is an input-quality diagnostic, not a deployable system. `D0` and `D1` are
paired by `record_uid` and share the same English reference, semantic group and
speaker code.

## Immutable model bindings

### Adapted ASR source

- base: `facebook/mms-1b-all`;
- base revision: `3d33597edbdaaba14a8e858e2c8caa76e3cec0cd`;
- representative seed: `20260809`;
- selected epoch: `4`;
- selection rule: development WER closest to the three-seed mean, fixed before
  downstream outcomes;
- adapter SHA-256:
  `F9B87F0ACD73BB8703ED936EB79117699FA9988B05B13ADB9D5288E0994B496B`;
- full paired development predictions SHA-256:
  `0D0120327BB58CE505C81C0F4563D929A8204E717E89C16F67AA4D61A0A71BD2`.

The preserved adapted-ASR prediction table is reused; ASR inference is not
rerun or reselected inside V3-M9.

### Frozen RNMT

- base: `facebook/nllb-200-distilled-600M`;
- base revision: `f8d333a098d19b4fd9a8b18f94170487ad3f821d`;
- adapter: V3-M1 seed 17;
- adapter SHA-256:
  `209B17B08168DB35E02BD9CF2A5BE321A0175069DE51C0D8050AA565353C88E1`;
- source/target language tags: `twi_Latn` to `eng_Latn`;
- decoding: beam size 6, early stopping, length penalty 1.0, maximum 192 new
  tokens, no source truncation;
- preserved V3-M1 prediction-table SHA-256:
  `39DC9919C283FD59C1D4CDB3D878AA6D987C26D1AD993443FE246830F9C0E1C4`.

## Outcomes

### Primary automatic outcome

The primary outcome is the paired `D1 - D0` difference in corpus chrF++.
Uncertainty is the 95% percentile interval from 20,000 paired bootstrap draws
over semantic content groups. Each group contributes its mean record-level
chrF++ difference, so multivariant rows from one semantic item are not treated
as independent. A two-sided exact sign test over non-tied record-level chrF++
differences is supporting evidence.

### Supporting outcomes

- SacreBLEU with `13a` tokenization and effective order;
- macro token F1;
- corpus chrF++, SacreBLEU and macro token F1 by speaker code;
- recovery toward `G`, reported descriptively as the fraction of the positive
  `G-D0` chrF++ gap recovered by `D1`;
- high-recall protected English-category recall and precision using the
  previously frozen clinical lexicon;
- exact number/timing marker-set agreement with the English reference;
- English negation-presence agreement with the reference; and
- empty or malformed output failures.

Lexicon, number and negation checks are automatic screening proxies, not human
clinical-safety judgments. WER/CER remain upstream ASR measures and are not
treated as sufficient evidence of downstream meaning preservation.

## Precommitted automatic eligibility gate

V3-M9 advances to a separately frozen fresh blinded human development audit
only when every condition below is true:

1. all input hashes, row identities, paired references and split boundaries
   verify, with exactly 1,558 rows and 458 semantic groups;
2. `D1` has no empty output;
3. `D1-D0` corpus chrF++ is at least +1.00 point;
4. the lower limit of the group-clustered 95% interval for mean record-level
   chrF++ difference is greater than 0;
5. the paired exact sign test is below 0.05 and wins exceed losses;
6. `D1-D0` SacreBLEU is no worse than -0.50 point;
7. `D1-D0` macro token F1 is no worse than -0.005;
8. protected-category recall is no worse than -0.005;
9. reference-number agreement is no worse than -0.01;
10. reference-negation agreement is no worse than -0.01;
11. no speaker code loses more than 1.00 chrF++ point; and
12. the sealed test remains unopened, zero test rows are read, no human outcome
    is read, no SBLLM call is made and no production component is changed.

A failure is preserved as a valid negative causal result. Thresholds, models or
inputs may not be changed after outcomes are observed within this protocol.

## If the automatic gate passes

The pass authorizes only a new, separately frozen, blinded audit of 72
previously unreviewed development records, balanced 18 per speaker code and
challenge-enriched for `D0/D1` disagreements. It does not authorize the sealed
test, SBLLM evaluation or deployment. The human audit must rate candidate
identity blindly using the existing intent-preservation and critical-error
codebook and must be locked and hashed before reveal.

## Stop and claim boundaries

- sealed test opened: **false**;
- test rows read: **0**;
- prior human outcomes used to fit or select D1: **false**;
- SBLLM run: **false**;
- RunPod/backend/frontend/API changed: **false**.

Any positive result applies only to controlled, scripted maternal-health Twi
from the four recorded speaker codes. It does not establish clinical safety,
spontaneous patient-speech performance, unseen-speaker generalisation or
population-level Akan performance.
