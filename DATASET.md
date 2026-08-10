# Dataset provenance and split policy

## Formal source

Wiafe, I., et al. (2026). *A Parallel English-Akan Maternal Health Dataset to Support Machine Translation and Text-to-Speech Systems*. **Data in Brief**. https://doi.org/10.1016/j.dib.2026.113088

Dataset deposit: *Parallel English–Akan Maternal Health Dataset*. Science Data Bank. https://doi.org/10.57760/sciencedb.32698

The article and deposit identify the resource as CC BY 4.0. Users must consult the current deposit record and its documentation before reuse.

## Corpus characteristics

- 3,487 unique English maternal-health phrases;
- 12,000 Akan text variants and 12,000 corresponding audio recordings;
- 32.313 hours of controlled studio audio;
- four linguistic experts, represented in the research files by speaker codes BT, HA, IM, and PT;
- question-and-answer material covering prenatal and postnatal themes;
- Twi, a major variety within the Akan language cluster;
- metadata fields include ID, English phrase, Akan transcription, theme, and audio path.

The corpus is scripted and controlled. It must not be described as spontaneous patient speech, naturally occurring clinical dialogue, broad Akan dialect coverage, or population-representative speaker diversity.

## Experiment split

The research split was created before adaptation using semantic content groups so that variants of the same underlying English phrase could not cross train/development/test boundaries. Speaker representation was stratified within each partition.

| Partition | Rows | Semantic groups | Notes |
|---|---:|---:|---|
| Train | 7,240 | 2,139 | 12.5935 hours; adaptation only |
| Development | 1,558 | 458 | model selection, screening, and development audits |
| Sealed test | 1,552 | recorded separately | not opened for the results in this release |

- split seed: `452`
- train/development semantic-group overlap: `0`
- speaker codes in all partitions: `BT`, `HA`, `IM`, `PT`
- speaker-disjoint: **no**

The four Akan variants aligned to one English phrase are not automatically treated as linguistically interchangeable at every level. Grouping prevents semantic leakage; it does not erase meaningful lexical, morphological, or pragmatic differences.

## Data access and non-redistribution

This repository does not mirror raw audio, row-level transcripts, or participant-linked audit material. Reproducers should obtain the published resource from the dataset DOI, construct the split locally, and verify all recorded hashes. This minimises unnecessary duplication of voice data and keeps this code repository focused on reproducibility metadata.

## Ethics

The dataset paper reports ethical approval identifier `ECBAS 029/24-25`. Reuse must remain within the dataset's consent, approval, licence, and local institutional requirements. Publication of code or model weights does not expand the scope of the original ethical approval.

