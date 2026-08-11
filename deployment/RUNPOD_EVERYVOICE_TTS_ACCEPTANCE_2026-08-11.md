# EveryVoice Twi-Asante live technical acceptance

Recorded: 11 August 2026 (UTC)

## Outcome

The evidence-selected `multilingual-tts/EveryVoice-OpenBible-Twi-Asante` checkpoint is running in the public research demonstrator and passed live technical acceptance.

This record establishes component identity, route availability and valid audio delivery. It does **not** establish clinical effectiveness, clinical production safety, MOS, population preference, patient acceptability or global state of the art.

## Selection evidence

The frozen, blinded single-expert development screen selected EveryVoice at revision `756fa212153a578000ba4ef45946bb6a0b111f23`:

- useful-and-safe spoken rendering: 29/32, versus 0/32 for HCI-LEGACY and 13/32 for MMS-TTS-Akan;
- EveryVoice versus HCI: 29 gains, 0 losses and 3 ties;
- Holm-adjusted paired p-value: 7.45e-9;
- protected-concept preservation: 13/14;
- sealed test opened: no.

These are challenge-enriched development results and are not prevalence estimates.

## Immutable implementation

- Backend commit: `cfe3bf6d1859c3bcb59bd2a431961f4289e831a1`
- Successful build: https://github.com/Akan-ASR-for-Health/asr-app-backend/actions/runs/31464496442
- Image: `ghcr.io/akan-asr-for-health/asr-app-backend:sha-cfe3bf6d1859c3bcb59bd2a431961f4289e831a1`
- Image manifest: `sha256:5d7c69a9cefe57972f16da9f284c02af18da06a394561fc77f65f35819ce5598`
- Image configuration: `sha256:8d9997ce9c17ed92d4a2f0b0bf7bbd54cde71eded5431da273fc1ed80ba09224`
- Pod: `5sewxdw6wiqh7w`, RTX 4000 Ada, `/workspace` persistent network volume
- Public base: https://5sewxdw6wiqh7w-9090.proxy.runpod.net
- Frontend: https://asr-web-frontend-blue.vercel.app/

EveryVoice runs in a dependency-isolated localhost worker. The versioned environment is persisted at `/workspace/.venvs/everyvoice-0.4.1-cu118`; the worker is not publicly exposed. The accepted environment pins `EveryVoice==0.4.1`, `torch==2.7.1+cu118` and `torchaudio==2.7.1+cu118`.

## Live checks

The health endpoint reported `healthy`, the exact model revision, `SPEAKER_00_Twi (Asante)`, `cuda:0`, `model_loaded=true`, `worker_status=healthy` and `runtime_fallback=false`.

Direct synthesis returned HTTP 200 `audio/wav`, a valid 112,684-byte RIFF/WAVE file in 3.397 seconds, SHA-256 `94352D7A7470DC0F0557FF3E6764D295297CE718F99720CA9BC2D2727C8098C7`.

The full public WebSocket route returned a second valid 683,052-byte RIFF/WAVE response, SHA-256 `A46C3A61F5D009CD58E138A83506AEE8FA2A53FE0C4D2C0B626D48F2032A097B`. The check used typed Twi, so it correctly observed the B1 typed-text forward route; the D1 seed-17 route remains scoped to adapted-MMS audio. Reverse translation was B3 segmented NLLB-3.3B.

The public API documentation, demo page and Vercel frontend each returned HTTP 200.

## Build incident and rollback

The first build (Actions run `31462854017`) exhausted the GitHub-hosted runner disk while baking a second CUDA environment. No image from that run was deployed. The accepted correction bootstraps the pinned worker on the persistent volume.

The rollback tag `rollback/pre-everyvoice-tts-2026-08-11` points to backend commit `6ea52915bc5d5352e7fc14cfa72d6f2620e7b349`. The prior image digest is `sha256:277a27597f6e5fc16d1677eb7b431a76f169b855f753cdb60982ad94150581a7`. Provider-only rollback is explicit via `TTS_BACKEND=hci`; no silent fallback is permitted. The rollback was not exercised after acceptance because that would interrupt the accepted deployment.
