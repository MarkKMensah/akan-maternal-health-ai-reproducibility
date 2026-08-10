---
language:
- tw
- en
license: cc-by-nc-4.0
library_name: peft
pipeline_tag: translation
base_model: facebook/nllb-200-distilled-600M
tags:
- akan
- twi
- maternal-health
- translation
- nllb
- lora
- development-only
---

# Akan–English Maternal-Health NLLB-600M RNMT LoRA

This repository contains the selected LoRA adapter for Twi-to-English maternal-health translation. It adapts the pinned base model:

`facebook/nllb-200-distilled-600M@f8d333a098d19b4fd9a8b18f94170487ad3f821d`

Adapter SHA-256:

`209B17B08168DB35E02BD9CF2A5BE321A0175069DE51C0D8050AA565353C88E1`

## Model architecture and research record

This repository provides the trained LoRA adapter in a directly loadable form. The companion GitHub repository contains the training notebook, frozen protocols, aggregate statistics, figures, and checksums.

## Source data and split

The adapter used the *Parallel English–Akan Maternal Health Dataset*:

- article: Wiafe et al. (2026), [doi:10.1016/j.dib.2026.113088](https://doi.org/10.1016/j.dib.2026.113088);
- dataset: [doi:10.57760/sciencedb.32698](https://doi.org/10.57760/sciencedb.32698).

The parent corpus contains 3,487 unique English phrases and 12,000 Akan variants. Training used 7,240 rows from 2,139 semantic groups. Development used 1,558 rows from 458 non-overlapping semantic groups. A separate 1,552-row test partition remained sealed. Split seed: `452`.

The split is semantic-content-group-disjoint and speaker-stratified, not speaker-disjoint. It covers four expert speaker codes and scripted maternal-health question-and-answer content.

## Training configuration

- source/target: `twi_Latn` → `eng_Latn`;
- LoRA rank 16, alpha 32, dropout 0.1;
- target modules: `q_proj`, `v_proj`;
- AdamW, learning rate `2e-4`;
- per-device batch 16, gradient accumulation 2, effective batch 32;
- maximum 8 epochs with evaluation/checkpointing each epoch;
- group-balanced `WeightedRandomSampler`;
- seeds 17, 29, and 47 were run under the frozen protocol;
- seed 17 was selected by the prespecified highest development chrF++ rule on frozen MMS input, with documented tie-breakers.

## Development evidence under adapted ASR

In the V3-M9 causal-propagation experiment, the same frozen RNMT adapter was fed two ASR conditions on 1,558 development rows:

- D0: unadapted MMS transcription;
- D1: selected adapted-MMS transcription.

| Metric | D0 | D1 | D1 − D0 |
|---|---:|---:|---:|
| chrF++ | 25.4841 | 30.8636 | +5.3795 |
| SacreBLEU | 7.2029 | 10.9806 | +3.7777 |
| Macro token F1 | 0.2677 | 0.3359 | +0.0682 |
| Protected-concept recall | 0.3799 | 0.4575 | +0.0776 |

The semantic-group-clustered 95% interval for mean sentence chrF++ gain was `[5.1963, 6.7625]`; wins/losses/ties were 1,054/487/17; exact two-sided sign-test p = `3.35e-48`.

### Evidence scope

The comparison measures causal error propagation under the specified development-stage pipeline conditions. It does not assess clinical safety or sealed-test generalisation.

## Loading

Load the pinned NLLB base with Transformers, then attach this adapter with PEFT. Use `twi_Latn` as source language and force `eng_Latn` as target language. Exact package versions and decoding settings are in the companion frozen notebook.

## Full reproducibility record

`https://github.com/MarkKMensah/akan-maternal-health-ai-reproducibility`

## Limitations

The data are scripted and limited to four expert speakers, and the adapter was selected on the development partition. The sealed test was not used for the reported results. Automated lexical and protected-concept measures are screening proxies rather than clinical-safety assessments. The associated human audits used single-expert adjudication and do not provide independent inter-rater validation.

## Licence

The upstream NLLB model is licensed CC BY-NC 4.0; this LoRA adapter is released under the same upstream licence conditions. Dataset reuse remains subject to the dataset's CC BY 4.0 terms and ethics documentation.
