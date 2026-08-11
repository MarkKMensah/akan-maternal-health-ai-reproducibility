# TTS Stage-B Final Development Results

**Protocol:** `tts-closure-dev-v1`
**Run:** `20260811T014117Z_tts_closure_dev_v1`
**Completed:** 2026-08-11
**Decision:** promote **T3, EveryVoice-OpenBible-Twi-Asante**, as the TTS deployment candidate; production remains unchanged pending reversible integration and an operational smoke test.

## Integrity and scope

- The 32-case, 96-clip audit was completed while the arm mapping remained private.
- The source Google Sheet was preserved without analysis-time edits.
- Only after completion was the mapping opened. Its SHA-256 was independently verified as `450F8F6B59A5158DCB135913ABAC02E5363D4DFD2D5938A5A5522B19C654EF99`, exactly matching the preregistered manifest.
- A single deterministic consistency recode was declared before model unblinding and applied only to the analysis copy: TTSB-021/C changed from critical-concept `YES` to `NO`, because the adjudication note explicitly states that all three clips omitted the protected term “HIV”. The raw sheet remains unchanged and the correction is preserved in the correction ledger.
- The sealed test partition remained unopened; zero test rows were read. This is development component-selection evidence only.

## Primary human-screen definition

A clip counted as a **useful-and-safe rendering** only when all four conditions held:

1. intelligibility was `FULLY_INTELLIGIBLE` or `MOSTLY_INTELLIGIBLE`;
2. the critical/protected concept was preserved;
3. no truncation or repetition occurred; and
4. there was no meaning-changing tonal or segmental ambiguity.

Naturalness was retained as a descriptive 1–5 ordinal score. It is not MOS.

## Results

| Arm | System | Useful-and-safe | Wilson 95% CI | Critical concept preserved | Fully/mostly intelligible | Mean naturalness |
|---|---|---:|---:|---:|---:|---:|
| T0 | HCI legacy baseline | 0/32 (0.0%) | 0.0–10.7% | 3/32 (9.4%) | 0/32 (0.0%) | 1.38 |
| T1 | MMS-TTS-Akan | 13/32 (40.6%) | 25.5–57.7% | 17/32 (53.1%) | 15/32 (46.9%) | 3.28 |
| T3 | EveryVoice-Twi-Asante | 29/32 (90.6%) | 75.8–96.8% | 29/32 (90.6%) | 31/32 (96.9%) | 4.59 |

Against T0, T1 produced 13 paired useful-and-safe gains, no losses and 19 ties: rate difference +40.6 percentage points, paired bootstrap 95% interval +25.0 to +59.4, exact two-sided sign p = 0.000244, Holm-adjusted p = 0.000244.

Against T0, T3 produced 29 paired useful-and-safe gains, no losses and three ties: rate difference +90.6 percentage points, paired bootstrap 95% interval +78.1 to +100.0, exact two-sided sign p = 3.73×10⁻⁹, Holm-adjusted p = 7.45×10⁻⁹.

The three-way best-overall judgement included T3 in the selected best set for 28 of 32 cases, T1 for six cases and T0 for none; four cases were either explicit `NEITHER` decisions or did not select the arm in the relevant pairwise summary. This preference count is descriptive because the sheet recorded one three-way best choice, not two independent candidate-versus-baseline preferences.

## Subgroup stress screen

- Questions: T3 useful-and-safe 16/16; T1 8/16; T0 0/16.
- Responses: T3 13/16; T1 5/16; T0 0/16.
- Protected-category cases: T3 13/14; T1 3/14; T0 0/14.
- T3 remained useful-and-safe in 10/11 long, 9/10 medium and 10/11 short cases.

These are challenge-balanced conditional development rates, not population prevalence estimates.

## Automatic and operational gates

Both finalists achieved 48/48 successful Stage-A generations and real-time factors below 1.0. T3 and T1 were non-inferior to T0 on both recorded round-trip ASR-CER proxies; in fact, mean row CER was 0.0652/0.1048 for T3 and 0.0845/0.1168 for T1, compared with 0.3395/0.3683 for T0 under the adapted-MMS and Farmerline evaluators. These ASR-mediated scores remain proxies, not human speech-quality measures.

Both T1 and T3 passed all prespecified promotion gates. T3 was selected by the frozen evidence hierarchy: highest Stage-B useful-and-safe rate, then critical-concept preservation, then the two-evaluator Stage-A CER ranking.

## Decision and dissertation claim

EveryVoice-Twi-Asante at revision `756fa212153a578000ba4ef45946bb6a0b111f23` is the selected **deployment candidate**. This authorizes a reversible integration and technical smoke test; it does not itself authorize a production replacement claim until that integration passes.

The dissertation may state that a revision-pinned public Twi-Asante TTS checkpoint substantially improved blinded native-speaker development-screen intelligibility and protected-concept rendering relative to the undocumented HCI operational baseline under the frozen 32-case protocol.

The dissertation must not describe this as MOS, inter-rater reliability, population preference, clinical validation, patient evidence, or state-of-the-art performance. The single expert was the Akan-speaking principal investigator; positionality, corpus familiarity and lack of independent raters must remain explicit limitations.

## Artifacts

- `TTS_STAGE_B_ANALYSIS_FINAL_2026-08-11.json`
- `TTS_STAGE_B_CLIP_LEVEL_UNBLINDED_2026-08-11.csv`
- `TTS_STAGE_B_SUBGROUP_RESULTS_2026-08-11.csv`
- `TTS_STAGE_B_CORRECTION_LEDGER_2026-08-11.json`
- `TTS_STAGE_B_USEFUL_SAFE_2026-08-11.svg`
- `TTS_STAGE_B_OUTCOME_PROFILE_2026-08-11.svg`
