# SHA-256 manifest policy

`SHA256SUMS.txt` uses a platform-independent canonical byte policy:

- UTF-8 text files are normalized to LF line endings before hashing.
- Binary files are hashed byte-for-byte.
- `.git/` and `provenance/SHA256SUMS.txt` are excluded.
- paths are repository-relative POSIX paths and sorted lexicographically.

Run `python provenance/build_sha256_manifest.py` from the repository root to
regenerate the manifest. Run it with `--check` to verify every entry and detect
unlisted files. This policy avoids Windows CRLF versus Git LF mismatches.
