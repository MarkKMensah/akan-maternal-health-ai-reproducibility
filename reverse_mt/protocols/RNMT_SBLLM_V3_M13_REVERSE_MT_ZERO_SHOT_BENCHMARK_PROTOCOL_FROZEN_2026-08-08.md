# V3-M13 reverse-MT zero-shot benchmark protocol

**Protocol ID:** `rnmt-sbllm-v3-m13-reverse-mt-zeroshot-dev-v1`  
**Freeze date:** 2026-08-08 (America/New_York)  
**Scope:** development-only English-to-Twi model and decoding benchmark  
**Sealed test:** closed; no sealed-test row, reference, metric, or label may be read  
**Production:** unchanged  
**Adaptation:** prohibited in this stage

## 1. Rationale and scientific question

V3-M12 established that sentence-segmented translation with the current
`facebook/nllb-200-distilled-600M` checkpoint removed observed repetition and
won all six decided blind preferences, but it introduced two T1-only protected
clinical errors (`SYMPTOM` and `BODY_PART`). V3-M12 therefore failed its
zero-tolerance protected-error gate and cannot advance.

V3-M13 asks: **under identical development data and decoding conditions, does
a larger NLLB checkpoint or the independently trained MADLAD-400 architecture
offer a safer and more faithful English-to-Twi base for later maternal-health
adaptation than the current 600M NLLB checkpoint?**

This stage is a model-screening experiment. It cannot authorize deployment,
sealed-test access, or a claim of clinical safety.

## 2. Frozen data

### 2.1 Multi-reference development benchmark

The benchmark is derived from the previously frozen 1,558-row, 458-content-
group development partition. It contains no training or sealed-test rows.

Rows are collapsed only when both the original content-group identifier and
the Unicode-NFC, whitespace-normalized English source are identical. Every
distinct Twi rendering for that exact English source remains a valid reference.
Two original groups contain two distinct English meanings; these meanings are
kept as separate evaluation units and are not normalized as equivalent. The
result is 460 evaluation units clustered in 458 original content groups.

The 7,240-row, 2,139-group training-only multivariant index is included solely
for leakage verification and provenance in this stage. No training row is
passed to a model. Exact normalized-English and content-group overlap between
the training and development inputs must both be zero before inference begins.

### 2.2 Response-distribution diagnostic set

The frozen V3-M12 file `V3_M12_ALL_95_CASE_OUTPUTS.csv`, SHA-256
`EF50378C45C31E6FF1474D0FE0EC9E80863A58582ABA2EFFAD4C6293F01F2821`,
provides 95 previously generated English SBLLM responses from fresh development
groups. Runtime access is restricted to identifiers, provenance, and
`source_english_response`. Prior candidate translations, selector actions,
audit membership, human labels, and post-review outcomes are forbidden inputs.

These 95 responses have no gold Twi response references. They are used only
for output-integrity, repetition, length, punctuation, and latency diagnostics.

## 3. Frozen candidates

All candidates use deterministic beam decoding with beam size 6, early
stopping, length penalty 1.0, and at most 192 new tokens per segment. Source
sentences are segmented with `pysbd` English sentence boundaries and
reassembled in original order, except the historical paragraph baseline.

| ID | Checkpoint and immutable revision | Mode | Role |
|---|---|---|---|
| B0 | `facebook/nllb-200-distilled-600M@f8d333a098d19b4fd9a8b18f94170487ad3f821d` | paragraph | historical baseline |
| B1 | same checkpoint/revision | sentence | V3-M12 mechanism anchor |
| B2 | `facebook/nllb-200-distilled-1.3B@7be3e24664b38ce1cac29b8aeed6911aa0cf0576` | sentence | NLLB capacity arm |
| B3 | `facebook/nllb-200-3.3B@a2814a8c92847d0d6aaf7afc9eac24ab57f26151` | sentence | larger NLLB ceiling |
| B4 | `google/madlad400-3b-mt@fa184c675da0b5c9e1c8694fccd4e12e2d422094` | sentence | independent architecture |

NLLB uses source `eng_Latn` and target `twi_Latn`. MADLAD uses the published
`<2ak>` target prefix. The broader MADLAD `ak` macro-code includes Akan/Twi and
Fante, so B4 is a comparator rather than a presumed replacement.

Models run sequentially on one A100 GPU. No quantized checkpoint, model
ensemble, prompt repair, glossary insertion, retrieval, reranking, human edit,
or stochastic sampling is permitted.

## 4. Frozen outcomes

### 4.1 Reference-based development outcomes

Reported for all 460 evaluation units:

- corpus multi-reference chrF++ (`word_order=2`);
- corpus multi-reference sacreBLEU;
- macro mean best-reference sentence chrF++;
- macro mean best-reference multiset-token F1;
- reference-grounded target-side protected-concept recall and F1 using the
  pre-existing frozen Twi concept schema;
- exact number-marker agreement;
- exact temporal-marker agreement;
- question-mark retention for English questions; and
- empty-output count and output/source length ratio.

Metric values are screening evidence, not clinical judgments. Neural learned
metrics are excluded from the primary decision because English-Twi calibration
is insufficiently established.

### 4.2 Response-distribution outcomes

Reported on all 95 English SBLLM responses:

- detector-positive repetition count under the frozen V3-M12 detector;
- repeated four-gram proportion;
- maximum identical-token run;
- exact repeated-sentence count;
- empty-output count;
- output/source token ratio; and
- total generation time and peak allocated GPU memory.

## 5. Frozen statistical analysis

B1 is the primary comparison anchor. For every alternative, report paired
unit-level differences and 95% cluster-bootstrap percentile intervals using
20,000 deterministic resamples of the 458 original content groups. Response
repetition discordance is reported with a two-sided exact paired sign test.

The two split evaluation units inside one original group remain in the same
bootstrap cluster. No row is treated as an independent speaker or patient.

## 6. Frozen shortlist rule

B0 is retained as historical context and is not eligible for adaptation.
Each of B2, B3, and B4 is eligible only if:

1. all 460 development and 95 response outputs are non-empty;
2. response detector-positive repetition count is no greater than B1;
3. mean reference-grounded protected-concept recall is no more than 0.01
   below B1; and
4. question-mark retention is no more than 0.02 below B1.

Eligible alternatives are ordered lexicographically by:

1. higher corpus multi-reference chrF++;
2. higher protected-concept recall;
3. higher corpus sacreBLEU; and
4. lower response-generation time.

The leading two eligible alternatives form the automatic shortlist. B1 is
always retained as the blinded-audit anchor. If fewer than two alternatives
are eligible, the result is `INSUFFICIENT_ALTERNATIVES`, and no threshold may
be changed after inspecting outcomes.

The shortlist is not a winner. It authorizes only a separately frozen blind
native-speaker audit and, after that audit, a separately frozen train-only
adaptation experiment.

## 7. Integrity, resumability, and stop boundaries

- Every input, script, registry, notebook, model revision, environment, raw
  output, summary, figure, and decision file receives an SHA-256 record.
- Candidate outputs are saved atomically after each model and may be resumed
  only when their row identities and recorded hashes validate.
- A failed model is recorded; it may not be silently replaced.
- The sealed test remains closed.
- No human audit label is read.
- No model is fine-tuned.
- No RunPod, GitHub, frontend, API documentation, or production setting is
  changed.

## 8. Claim boundary

A successful screen supports only the claim that specified pretrained
English-to-Twi candidates were compared reproducibly on a validated
maternal-health development benchmark and a previously frozen English-response
distribution. It does not establish spontaneous-speaker performance,
population prevalence, clinical safety, autonomous medical advice, or final
test performance.

## 9. Primary sources

1. NLLB model card: https://huggingface.co/facebook/nllb-200-distilled-600M
2. NLLB paper: https://arxiv.org/abs/2207.04672
3. FLORES-200 Twi code: https://github.com/facebookresearch/flores/blob/main/flores200/README.md
4. NLLB 1.3B checkpoint: https://huggingface.co/facebook/nllb-200-distilled-1.3B
5. NLLB 3.3B checkpoint: https://huggingface.co/facebook/nllb-200-3.3B
6. MADLAD-400 paper: https://papers.nips.cc/paper_files/paper/2023/file/d49042a5d49818711c401d34172f9900-Paper-Datasets_and_Benchmarks.pdf
7. MADLAD-400 3B checkpoint: https://huggingface.co/google/madlad400-3b-mt
8. English-Twi metric limitations: https://aclanthology.org/2024.wmt-1.36/

