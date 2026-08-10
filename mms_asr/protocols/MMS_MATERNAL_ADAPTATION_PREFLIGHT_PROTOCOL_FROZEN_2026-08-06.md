# MMS maternal-health adaptation preflight — frozen protocol

**Protocol ID:** `mms-maternal-asr-adaptation-preflight-v1`  
**Freeze date:** 2026-08-06 (America/New_York)  
**Scope:** train/development integrity inspection only; no model fitting and no
sealed-test access

## Decision context

The frozen MMS base model is the most defensible upstream adaptation target.
On the completed development benchmark, `facebook/mms-1b-all` was a close
finalist: compared with Farmerline, MMS had slightly worse WER but better CER.
The subsequent RNMT sequence established that inadequate MMS-conditioned
candidates, rather than ranking alone, were the binding downstream limitation.
V3-M8 closed the current selector/retrieval loop after its strongest retrieval
configuration reached only 3.55% coverage.

The next causal intervention is therefore domain adaptation of MMS using only
the already frozen maternal-health training audio.

## Literature basis

- The MMS project uses language-specific adapters to scale ASR across more
  than one thousand languages (Pratap et al., 2023):
  <https://ai.meta.com/research/publications/scaling-speech-technology-to-1000-languages/>.
- The official Hugging Face MMS adaptation guide recommends adapter training
  for low-resource ASR because it trains only a small language-specific subset
  of the model and is more memory efficient than full fine-tuning:
  <https://huggingface.co/blog/mms_adapters>.
- Controlled low-resource evidence found MMS particularly suitable when
  labelled speech is extremely limited (Liang and Levow, 2025):
  <https://aclanthology.org/2025.fieldmatters-1.3/>.
- Adapter training has also been reported as parameter-efficient and accurate
  for very-low-resource ASR (Mainzinger and Levow, 2024):
  <https://aclanthology.org/2024.acl-srw.16/>.

These sources motivate an adapter-first experiment. They do not guarantee a
gain on controlled maternal-health Twi and do not establish clinical safety.

## Immutable inputs

1. **Base model:** `facebook/mms-1b-all` at full revision
   `3d33597edbdaaba14a8e858e2c8caa76e3cec0cd`, Akan adapter language code
   `aka`.
2. **Training manifest:** `V3_M5_TRAIN_AUDIO_MANIFEST_v1.csv`, SHA-256
   `1EBC4FF1D7F668AD28BA7262DD4CB143264F39906CF98B3B11806A9BCCDB5633`.
   It contains 7,240 train-only records, 2,139 semantic groups, four speaker
   codes and 12.5935 hours of audio.
3. **Development source:** the immutable `evaluated_records_full_dev.csv` from
   the completed even-ground baseline benchmark. The preflight may read its
   schema and development rows but may not join or inspect any sealed-test
   artifact.

## Preflight checks

The preflight must:

1. verify the training-manifest hash before reading it;
2. assert that every training row has `split=train`;
3. confirm row, unique-record, semantic-group and speaker counts;
4. confirm that all frozen training audio paths exist and that recorded byte
   counts are positive;
5. record duration and per-speaker distributions;
6. locate the immutable full-development baseline input and hash it;
7. record its columns and non-sensitive partition counts so a dedicated
   adaptation development manifest can be materialized without guessing field
   names;
8. assert zero semantic-group overlap between train and development whenever
   the shared group key is present;
9. write a machine-readable report and hashes to the experiment folder.

The preflight must not:

- open a path containing a sealed-test or primary-test artifact;
- fit, update or evaluate model parameters;
- read RNMT human outcomes;
- run SBLLM;
- change RunPod, the backend, frontend, API documentation or production.

## Split and claim boundary

The data are **semantic-group-disjoint and speaker-stratified**, not
speaker-disjoint. BT, HA, IM and PT occur in more than one partition. The study
concerns controlled, scripted maternal-health Twi. It cannot establish
spontaneous-patient-speech performance, unseen-speaker generalisation,
clinical-environment performance, population-level Akan generalisation or
clinical safety.

## Advancement rule

Training may be frozen only if the preflight confirms:

- the exact training-manifest hash;
- 7,240 training records and 2,139 semantic groups;
- all four expected speaker codes;
- no missing training audio;
- a development-only source whose schema permits an immutable, non-test
  evaluation manifest;
- zero train/development semantic-group overlap.

Any failure stops the experiment for data repair. Passing authorizes only the
creation of a separately frozen adapter-training protocol and notebook; it
does not authorize opening the sealed test or changing production.

