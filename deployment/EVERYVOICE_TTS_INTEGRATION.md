# EveryVoice TTS reversible integration

The application selects EveryVoice through `TTS_BACKEND=everyvoice`. The exact
checkpoint is code-pinned to
`multilingual-tts/EveryVoice-OpenBible-Twi-Asante@756fa212153a578000ba4ef45946bb6a0b111f23`.

EveryVoice 0.4.1 requires PyTorch 2.7.1 and a Pydantic/protobuf dependency
family that conflicts with the previously accepted API runtime. The deployment
therefore runs EveryVoice in a private localhost worker environment. The public
API contract and port remain unchanged; the worker is not exposed outside the
container.

There is no silent runtime fallback. `TTS_BACKEND=hci` is the explicit rollback
switch, and Git tag `rollback/pre-everyvoice-tts-2026-08-11` preserves the
pre-integration source at commit
`6ea52915bc5d5352e7fc14cfa72d6f2620e7b349`.

Operational acceptance requires the immutable candidate image digest, live
health metadata, one direct `/tts/` WAV response, one complete WebSocket audio
response, browser playback, latency/GPU observations and a rollback check. A
development-selection result alone is not production-safety evidence.
