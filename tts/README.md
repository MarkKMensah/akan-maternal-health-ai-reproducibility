# Twi text-to-speech component selection

This directory records the frozen development-only comparison used to select
the spoken-output component of the Akan maternal-health demonstrator.

## Selected deployment candidate

`multilingual-tts/EveryVoice-OpenBible-Twi-Asante` at immutable Hugging Face
revision `756fa212153a578000ba4ef45946bb6a0b111f23` was selected. It is an
EveryVoice FastSpeech2 acoustic model with a HiFi-GAN vocoder and 22,050 Hz
output. The model card declares CC-BY-SA-4.0.

The choice was prospective and evidence-based: EveryVoice was the public
Twi-Asante system with the strongest documented intelligibility result in the
same OpenBibleTTS comparison, and it provided a different architecture and
provenance path from the undocumented HCI operational baseline. Prior results
motivated inclusion; they did not determine the local winner.

## Frozen local evidence

- Stage A: 48 validated development texts; automatic, operational and
  two-ASR round-trip proxy measures.
- Stage B: 32 cases and 96 anonymized clips; blinded single-expert native-Akan
  screen.
- Useful-and-safe required intelligibility, protected-concept preservation, no
  truncation/repetition and no meaning-changing tonal/segmental ambiguity.
- EveryVoice: 29/32 (90.6%, Wilson 95% CI 75.8–96.8%).
- HCI baseline: 0/32 (0.0%, Wilson 95% CI 0.0–10.7%).
- Paired comparison: 29 gains, 0 losses, 3 ties; Holm-adjusted exact sign-test
  p = 7.45e-9.
- The sealed test partition remained unopened.

## Claim boundary

This is a challenge-balanced development component-selection result. It is not
MOS, inter-rater reliability, patient evaluation, clinical validation,
population prevalence or a state-of-the-art claim. The reviewer was the
Akan-speaking principal investigator. The checkpoint is Bible-domain, so
domain shift remains an explicit limitation despite the local maternal-health
text screen.

The HCI path is retained only as an explicit operational rollback. The runtime
must not silently switch voices following an error.

See `references.bib`, the frozen protocol, aggregate result files and figures
in this directory.
