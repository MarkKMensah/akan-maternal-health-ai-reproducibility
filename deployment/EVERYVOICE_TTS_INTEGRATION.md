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

Live technical acceptance completed on 11 August 2026. The accepted backend is
commit `cfe3bf6d1859c3bcb59bd2a431961f4289e831a1`, image
`sha-cfe3bf6d1859c3bcb59bd2a431961f4289e831a1`, manifest digest
`sha256:5d7c69a9cefe57972f16da9f284c02af18da06a394561fc77f65f35819ce5598`.
Health, direct `/tts/`, the full public WebSocket audio path, API docs, public
demos and the Vercel frontend all passed. See
`RUNPOD_EVERYVOICE_TTS_ACCEPTANCE_2026-08-11.md` and its machine-readable JSON.

The rollback anchors were verified but not exercised after acceptance, because
doing so would interrupt the accepted public deployment. A development
selection and technical smoke test remain distinct from clinical or production
safety evidence.
