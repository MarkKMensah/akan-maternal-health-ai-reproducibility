---
language:
- tw
license: cc-by-nc-4.0
library_name: transformers
pipeline_tag: automatic-speech-recognition
base_model: facebook/mms-1b-all
datasets:
- doi:10.57760/sciencedb.32698
tags:
- akan
- twi
- maternal-health
- asr
- adapter
- development-only
model-index:
- name: Akan maternal-health MMS-1B adapter (development v1)
  results:
  - task:
      type: automatic-speech-recognition
    dataset:
      name: Parallel English-Akan Maternal Health Dataset — development split
      type: doi:10.57760/sciencedb.32698
    metrics:
    - name: WER
      type: wer
      value: 0.3011732401
    - name: CER
      type: cer
      value: 0.0774433283
---

# Akan maternal-health MMS-1B adapter — development v1

This repository contains the selected epoch-4 adapter and processor for maternal-health Twi automatic speech recognition. It adapts the pinned base model `facebook/mms-1b-all@3d33597edbdaaba14a8e858e2c8caa76e3cec0cd`.

The selected checkpoint is seed `20260809`, epoch `4`, with adapter SHA-256:

`F9B87F0ACD73BB8703ED936EB79117699FA9988B05B13ADB9D5288E0994B496B`

## Source data

Training and development data were derived from the *Parallel English–Akan Maternal Health Dataset*:

- Wiafe, I., et al. (2026), *A Parallel English-Akan Maternal Health Dataset to Support Machine Translation and Text-to-Speech Systems*, **Data in Brief**, [doi:10.1016/j.dib.2026.113088](https://doi.org/10.1016/j.dib.2026.113088).
- dataset deposit: [doi:10.57760/sciencedb.32698](https://doi.org/10.57760/sciencedb.32698), [Science Data Bank record](https://www.scidb.cn/en/detail?dataSetId=c633d8fdee6447a28c2ae2ea33ab2d73).

The parent resource reports 3,487 unique English maternal-health phrases, 12,000 Akan text variants, 12,000 controlled studio recordings, and 32.313 hours of audio from four linguistic experts. It is a scripted question-and-answer corpus, not spontaneous patient speech or natural clinical dialogue.

## Split construction

The fixed split was semantic-content-group-disjoint and speaker-stratified:

| Partition | Rows | Semantic groups | Additional detail |
|---|---:|---:|---|
| Train | 7,240 | 2,139 | 12.5935 hours |
| Development | 1,558 | 458 | model selection and confirmation |
| Sealed test | 1,552 | separately held | not opened for these results |

- split seed: `452`
- train/development semantic-group overlap: `0`
- speaker codes BT, HA, IM, and PT occur in every partition
- the split is **not speaker-disjoint**

Variants of the same underlying English phrase were kept in one partition to reduce semantic leakage.

## Training

- adapter-only trainable subset;
- four epochs;
- AdamW, learning rate `1e-3`;
- 10% warm-up;
- device batch size 8, gradient accumulation 4 (effective batch 32);
- 16 kHz verified audio cache and length-bucketed batches;
- gradient checkpointing and maximum gradient norm 1.0;
- epoch selected by development WER, with CER as the tie-breaker.

Three prespecified confirmation seeds (`20260807`, `20260808`, `20260809`) used the same settings.

## Development results

The frozen unadapted MMS baseline was WER `0.5068335`, CER `0.1457793` on 1,558 development rows.

| Seed | Selected epoch | WER | CER |
|---:|---:|---:|---:|
| 20260807 | 4 | 0.302921 | 0.080196 |
| 20260808 | 4 | 0.283793 | 0.073918 |
| 20260809 | 4 | 0.301173 | 0.077443 |
| Mean | — | 0.295962 | 0.077186 |

Mean relative improvement was 41.61% for WER and 47.05% for CER. A hierarchical bootstrap across seeds and 458 semantic groups gave 95% intervals of `[-0.222459, -0.200865]` for the WER delta and `[-0.071939, -0.065255]` for the CER delta. All four speaker codes improved in every confirmation seed.

These are development results. They are not a sealed-test or unseen-speaker claim.

## Files and integrity

- `adapter_epoch_04.safetensors` — selected adapter weights;
- `processor/` — processor/tokenizer files required by the adapter;
- `adapter_metadata.json` — frozen provenance, split, training, and result metadata.

The full public-safe protocols, scripts, aggregate results, and hashes are archived at:

`https://github.com/MarkKMensah/akan-maternal-health-ai-reproducibility`

## Intended use

Research on controlled Twi maternal-health speech and investigation of error propagation in a staged ASR–translation–response pipeline.

## Limitations and out-of-scope uses

This model has not established performance for unseen speakers, broad Akan dialects, spontaneous patient speech, noisy clinical environments, population-level diversity, or clinical safety. It must not be used as a diagnostic or treatment system. The four-speaker, scripted development evidence and single-project domain are material limitations.

## Licence

The upstream MMS model is licensed CC BY-NC 4.0; this derived adapter is released under the same upstream licence conditions. Dataset reuse remains subject to the dataset's own CC BY 4.0 terms and ethics documentation.

