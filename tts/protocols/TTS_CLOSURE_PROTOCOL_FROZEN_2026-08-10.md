# Akan/Twi TTS Component-Selection Protocol — Frozen Development Benchmark

**Protocol ID:** `tts-closure-dev-v1`
**Frozen:** 2026-08-10, before synthesis or outcome inspection
**Scope:** component selection for the research demonstrator; no TTS training; sealed ASR/MT test remains unopened

## Research question

Does a documented public Akan/Twi TTS checkpoint provide a more useful and safe spoken rendering of validated maternal-health Twi than the operational HCI legacy voice, without increasing protected-concept loss, truncation, synthesis failure or unacceptable latency?

## Prospective systems

| Arm | System and immutable revision | Scientific role |
|---|---|---|
| T0 | `hci-lab-dcug/ugtts-multispeaker-max42secs-total7hrs-sr22050`; deployment speaker `PT`; runtime snapshot required | operational baseline; provenance-limited |
| T1 | `facebook/mms-tts-aka@c20caea1cb234579cb5e3338b117a67d8235db1c` | official MMS/VITS Akan anchor |
| T2 | `UBC-NLP/Simba-TTS-twi-asanti@b109f57c084cfa435520c117e31d52734c930ee0` | published MMS adaptation / same-family control |
| T3 | `multilingual-tts/EveryVoice-OpenBible-Twi-Asante@756fa212153a578000ba4ef45946bb6a0b111f23` | strongest documented OpenBible same-protocol public comparator |
| T4 | `ghananlpcommunity/stable-twi-tts@b6d42942c79e9a3699d2fab85c1a592dfdfd7ca5` | modern Ghanaian/code-switch/CPU-efficiency comparator |
| T5 | `neriqlabs/kasanoma-tts-twi-v0.4@9ef4b2dde5fb4029ec019928725abae7d8eeae6d` | multi-domain, multi-speaker CosyVoice-family comparator |

Each arm has a 45-minute installation/load cap. A failure is retained as a preflight exclusion and cannot silently trigger an unplanned substitute. F5-TTS, VieNeu, Nano-Twi and recent opaque checkpoints remain documented literature exclusions; no post-outcome candidate may be added.

## Frozen material

- 48 development texts only, one deterministic representative per semantic group.
- Six equal strata: question/response × short/medium/long.
- Preserve original validated Twi orthography and punctuation.
- Record speaker/theme only as provenance; synthesized voices are not claims about those speakers.
- The selection script and resulting CSV are hashed before synthesis.

## Synthesis controls

- One main deterministic seed (`20260810`) where the model permits it.
- HCI uses the deployed `PT` speaker.
- Fixed-voice systems use their published fixed voice.
- Reference-conditioned systems use one fixed, licensed, non-evaluation prompt plus its exact transcript; if no defensible prompt is available, the arm is blocked rather than given a test-row reference.
- One retry after a technical failure. Retain waveform SHA-256, sample rate, duration, generation latency, real-time factor, peak VRAM, silence/clipping and repetition/truncation screens.

## Automatic evidence

Primary proxy: round-trip CER, reported separately through:

1. the frozen adapted MMS evaluator (`facebook/mms-1b-all` base plus the public maternal-health adapter); and
2. `FarmerlineML/w2v-bert-2.0_twi_alpha_v1@0ed71b2ead0aedd92571178eeef11733d95cdfb6`.

Also report WER, protected-concept/negation/timing retention, synthesis success, duration ratio and latency/RTF. ASR-based scores are evaluator-dependent proxies, not human fidelity. UTMOS is descriptive only if its frozen implementation loads within the cap.

## Stage A and Stage B

Stage A synthesizes all 48 texts for every successfully loaded arm. A candidate cannot advance if success is below 99%, it adds a candidate-only protected-concept failure, it is materially worse on both ASR-CER evaluators, or it is operationally infeasible.

At most two challengers advance. Stage B contains T0 plus those two challengers on a frozen balanced 32-text subset. Audio is randomly renamed and model-blinded. The native Akan-speaking principal investigator records intelligibility (`fully`, `mostly`, `partial`, `unintelligible`), critical concept preserved (`yes/no`), truncation/repetition, tonal or segmental ambiguity, naturalness ordinal and paired preference versus T0. This is a **blinded single-expert development screen**, not MOS, inter-rater reliability, clinical validation or population preference.

## Statistics and promotion

- Clustered paired bootstrap (10,000 replicates; semantic group) for CER/WER and runtime deltas.
- Exact paired binary/sign evidence for Stage-B useful-and-safe rendering.
- Holm adjustment across the prespecified candidate-versus-T0 primary family.
- Promotion requires at least 99% successful generations, no increase in critical protected-concept failure, non-inferiority across both ASR evaluators, and acceptable runtime. A human-screen improvement is required for a replacement claim.

No sealed test is opened. No clinical-effectiveness, population, speaker-similarity or state-of-the-art claim is authorized.

## Primary evidence

- Pratap et al. (2023), *Scaling Speech Technology to 1,000+ Languages*, arXiv:2305.13516.
- Elmadany et al. (2025), *Voice of a Continent*, EMNLP 2025, ACL 2025.emnlp-main.559.
- Meyer et al. (2022), *BibleTTS*, arXiv:2207.03546.
- OpenBibleTTS (2026), arXiv:2606.09553.
- Du et al. (2025), *CosyVoice 3*, arXiv:2505.17589.
- ITU-T P.808 (2021); Cooper et al. (2023), arXiv:2306.02044.
