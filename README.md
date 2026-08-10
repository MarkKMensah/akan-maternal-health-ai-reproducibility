# Reproducibility records for an Akan maternal-health voice pipeline

This repository preserves the public-safe research record for three linked components of an Akan (Twi) maternal-health voice pipeline:

1. **ASR:** parameter-efficient adaptation of `facebook/mms-1b-all` to the maternal-health speech domain;
2. **forward MT / RNMT:** LoRA adaptation of `facebook/nllb-200-distilled-600M` for Twi-to-English translation, including evaluation under raw and adapted-ASR input;
3. **reverse MT:** a zero-shot benchmark of unmodified `facebook/nllb-200-3.3B` for English-to-Twi response translation.

The repository contains protocols, code, model/data revision identifiers, aggregate results, statistical tests, figures, and SHA-256 manifests. It intentionally does **not** redistribute participant audio, full transcripts, human-audit workbooks, reveal keys, credentials, or proprietary application configuration.

## What was trained—and what was not

| Component | Upstream model | Modification | Public record |
|---|---|---|---|
| Maternal-health ASR | `facebook/mms-1b-all@3d33597edbdaaba14a8e858e2c8caa76e3cec0cd` | Adapter training | Hugging Face weights + this repository |
| Forward RNMT | `facebook/nllb-200-distilled-600M@f8d333a098d19b4fd9a8b18f94170487ad3f821d` | LoRA training | Separate Hugging Face adapter + this repository |
| Reverse MT | `facebook/nllb-200-3.3B@a2814a8c92847d0d6aaf7afc9eac24ab57f26151` | **None**; zero-shot benchmark only | This repository; no derived model repository |

Creating a new model repository for NLLB-3.3B would incorrectly imply that its parameters were changed. Its pinned upstream revision, decoding protocol, and benchmark evidence therefore live here instead.

Model records:

- MMS ASR adapter: [`hci-lab-dcug/akan-maternal-health-mms-1b-adapter-dev-v1`](https://huggingface.co/hci-lab-dcug/akan-maternal-health-mms-1b-adapter-dev-v1)
- forward-RNMT LoRA: [`GiftMark/akan-maternal-health-nllb-600m-rnmt-lora-v1`](https://huggingface.co/GiftMark/akan-maternal-health-nllb-600m-rnmt-lora-v1) (initially private pending an explicit public-weight release decision)

## Dataset and split boundary

The source corpus is the *Parallel English–Akan Maternal Health Dataset* described by Wiafe et al. (2026):

- article DOI: [10.1016/j.dib.2026.113088](https://doi.org/10.1016/j.dib.2026.113088)
- dataset DOI: [10.57760/sciencedb.32698](https://doi.org/10.57760/sciencedb.32698)
- repository: [Science Data Bank](https://www.scidb.cn/en/detail?dataSetId=c633d8fdee6447a28c2ae2ea33ab2d73)

The published resource contains 3,487 unique English maternal-health phrases, 12,000 Akan text variants, and 12,000 studio recordings (32.313 hours) from four linguistic experts. It is a controlled, scripted, question-and-answer corpus—not spontaneous patient speech or a clinical encounter corpus.

The experiments used a fixed **semantic-content-group-disjoint, speaker-stratified** split:

- training: 7,240 rows, 2,139 semantic groups, 12.5935 hours;
- development: 1,558 rows, 458 semantic groups;
- sealed test: 1,552 rows;
- split seed: 452;
- speaker codes BT, HA, IM, and PT occur in each split.

The split is not speaker-disjoint. Reported results therefore do not establish unseen-speaker or population-level generalisation. See [DATASET.md](DATASET.md).

## Principal development results

### MMS ASR adaptation

Across three confirmation seeds, the unadapted MMS baseline had WER 0.5068 and CER 0.1458. Adapted development WER was 0.3029, 0.2838, and 0.3012; adapted CER was 0.0802, 0.0739, and 0.0774. Mean relative improvements were 41.61% WER and 47.05% CER. Hierarchical bootstrap 95% intervals for adapted-minus-baseline deltas were [-0.2225, -0.2009] for WER and [-0.0719, -0.0653] for CER.

### Forward RNMT under adapted-ASR input

On 1,558 development rows, replacing the original public-MMS transcription with adapted-MMS transcription before the frozen RNMT adapter increased corpus chrF++ from 25.4841 to 30.8636 (+5.3795) and SacreBLEU from 7.2029 to 10.9806. The semantic-group-clustered 95% interval for mean sentence chrF++ gain was [5.1963, 6.7625]; exact sign-test p = 3.35e-48.

### Reverse MT with unmodified NLLB-3.3B

In a 72-case, challenge-enriched, paired development audit, the NLLB-3.3B arm achieved safe final-Twi fidelity in 75.0% of cases versus 55.6% for the smaller anchor (+19.4 percentage points; 95% CI [6.9, 31.9]; exact McNemar p = 0.00661). Among 34 upstream-English cases rated useful and safe, end-to-end useful-and-safe output was 82.4% versus 50.0% (+32.4 points; exact p = 0.000977).

These are development and challenge-set findings, not sealed-test, clinical-effectiveness, or deployment-safety claims.

## Repository map

- `mms_asr/` — frozen protocols, training/analysis scripts, aggregate development evidence, and the Hugging Face card source.
- `rnmt_forward/` — frozen RNMT notebook/protocols, LoRA configuration, evaluation code, and causal-propagation results.
- `reverse_mt/` — NLLB-3.3B zero-shot benchmark and paired end-to-end audit.
- `docs/` — release, claim-boundary, and reproducibility notes.
- `provenance/` — immutable file checksums and source identifiers.

## Reproduction order

1. Obtain the dataset from its DOI and verify its terms and ethics documentation.
2. Recreate the frozen semantic-group split using the recorded seed and group policy; do not inspect the sealed test partition.
3. Run the MMS preflight and three-seed adapter protocol.
4. Run the forward-RNMT frozen notebook on gold and frozen ASR development inputs.
5. Reproduce the adapted-ASR causal-propagation evaluation.
6. Run the reverse-MT zero-shot benchmark at the pinned NLLB-3.3B revision.
7. Verify repository files against `provenance/SHA256SUMS.txt`.

Exact software versions are recorded in the notebooks and environment manifests. Data files are intentionally not committed.

## Responsible-use boundary

This is a research artefact. It is not a medical device, diagnostic system, or substitute for a qualified health professional. The recorded ethics approval covered the source project described by the dataset paper; this repository does not claim a new clinical trial or patient-user evaluation.

## Citation

Please cite both this software record (see `CITATION.cff`) and the source dataset article. Model-specific cards contain the relevant upstream model citations and licences.
