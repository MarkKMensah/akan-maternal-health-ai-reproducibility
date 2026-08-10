from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "V3_M14_END_TO_END_REVERSE_MT_GATE_COLAB_2026-08-09.ipynb"


def markdown(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip() + "\n"}


def code(text: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": text.strip() + "\n"}


cells = [
    markdown("""
# V3-M14 end-to-end reverse English→Twi gate

This notebook runs the frozen 72-case B1-versus-B3 experiment. The adapted-MMS, forward RNMT and SBLLM English responses are immutable; only the reverse translator changes. It requires an A100 GPU, does not open the sealed test, does not train any model and does not change production.
"""),
    code("""
# Mount the persistent Drive archive and verify the frozen package before installing or executing anything.
from google.colab import drive, userdata
drive.mount('/content/drive', force_remount=False)

import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path('/content/drive/MyDrive/Akan_ASR_PhD_Experiments/03_Adaptation/nllb_v3_m14_end_to_end_reverse_mt_2026-08-09')
PRECOMMIT = ROOT / 'V3_M14_EXECUTION_PRECOMMIT_2026-08-09.json'
EXPECTED_PRECOMMIT_SHA256 = 'DD8CDB873FFCA48594F5E9BF8AF31DBDC4FCC4C51A07BCCF74A9ACE892779786'

def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest().upper()

assert ROOT.is_dir(), f'Frozen V3-M14 Drive folder not found: {ROOT}'
assert PRECOMMIT.is_file(), f'Missing precommit: {PRECOMMIT}'
assert sha256_file(PRECOMMIT) == EXPECTED_PRECOMMIT_SHA256, 'Stop: V3-M14 precommit hash changed.'
precommit = json.loads(PRECOMMIT.read_text(encoding='utf-8'))
assert precommit['frozen_before_execution'] is True
assert precommit['stop_boundaries']['sealed_test_opened'] is False
assert precommit['stop_boundaries']['production_changed'] is False

# Require the prespecified accelerator; this prevents silent execution on an unsuitable runtime.
gpu_text = subprocess.run(['nvidia-smi', '-L'], check=True, capture_output=True, text=True).stdout.strip()
print(gpu_text)
assert 'A100' in gpu_text, 'Stop: choose an A100 GPU runtime before running V3-M14.'

# Use a Hugging Face token from Colab Secrets when present and persist model downloads in Drive.
try:
    hf_token = userdata.get('HF_TOKEN')
except Exception:
    hf_token = None
if hf_token:
    os.environ['HF_TOKEN'] = hf_token
os.environ['HF_HOME'] = '/content/drive/MyDrive/Akan_ASR_PhD_Experiments/.cache/huggingface'
os.environ['TRANSFORMERS_CACHE'] = os.path.join(os.environ['HF_HOME'], 'hub')
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
print({'root': str(ROOT), 'precommit_sha256': EXPECTED_PRECOMMIT_SHA256, 'hf_token_available': bool(hf_token)})
"""),
    code("""
# Install the exact research libraries used by the successful V3-M13 benchmark.
%pip install -q transformers==4.57.1 accelerate==1.11.0 sentencepiece==0.2.1 pysbd==0.3.4
"""),
    code("""
# Execute the precommitted script. Candidate outputs are written atomically and can safely resume by completed model.
%run /content/drive/MyDrive/Akan_ASR_PhD_Experiments/03_Adaptation/nllb_v3_m14_end_to_end_reverse_mt_2026-08-09/v3_m14_execute.py
"""),
    code("""
# Verify and display only execution metadata; do not inspect candidate translations before the blinded workbook is created.
import pandas as pd

completion_path = ROOT / 'execution_outputs' / 'V3_M14_EXECUTION_COMPLETION.json'
translations_path = ROOT / 'execution_outputs' / 'V3_M14_ALL_TRANSLATIONS.csv'
assert completion_path.is_file() and translations_path.is_file()
completion = json.loads(completion_path.read_text(encoding='utf-8'))
translations = pd.read_csv(translations_path)
assert completion['paired_case_count'] == 72
assert len(translations) == 144
assert translations.groupby('audit_id')['candidate_id'].nunique().eq(2).all()
print(json.dumps({
    'paired_case_count': completion['paired_case_count'],
    'row_count': completion['row_count'],
    'candidate_completions': completion['candidate_completions'],
    'repetition_detector_positive_counts': completion['repetition_detector_positive_counts'],
    'output_sha256': completion['sha256']['all_translations'],
    'sealed_test_opened': completion['sealed_test_opened'],
    'production_changed': completion['production_changed'],
}, indent=2, ensure_ascii=False))
"""),
]

notebook = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {"gpuType": "A100", "provenance": []},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.x"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}
OUT.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(OUT)
