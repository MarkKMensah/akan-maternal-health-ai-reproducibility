"""Build the V3-M9 Colab execution notebook without embedding study outcomes."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "V3_M9_ADAPTED_ASR_CAUSAL_PROPAGATION_DEV_COLAB_2026-08-07.ipynb"
PROTOCOL_SHA256 = "830446ACC3C4CBA741B05E0F65565CA3DB8753DE9E5C0C1050B8EAB1B6A20D54"
SCRIPT_SHA256 = "459A5ADE42C9DBD06B17A95C05A8BF317B48364AC13247C46B7D847A9F139CC3"


def markdown(source: str) -> dict:
    """Create one notebook markdown cell."""
    return {"cell_type": "markdown", "metadata": {}, "source": source}


def code(source: str) -> dict:
    """Create one unexecuted notebook code cell."""
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source,
    }


cells = [
    markdown(
        """# V3-M9 — adapted-ASR causal propagation through frozen RNMT

This notebook runs the precommitted development-only comparison `G / D0 / D1`.
It changes only the ASR source supplied to the unchanged V3-M1 seed-17 RNMT
model. The 1,552-row sealed test, prior human outcomes, SBLLM and production are
not accessed.

Automatic success authorizes only a separately frozen 72-case blinded
development audit."""
    ),
    code(
        """# Mount the versioned project Drive and display the active accelerator.
from google.colab import drive
drive.mount('/content/drive', force_remount=False)

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path('/content/drive/MyDrive/Akan_ASR_PhD_Experiments/03_Adaptation/nllb_v3_m9_2026-08-07')
SCRIPT = ROOT / 'v3_m9_execute.py'
PROTOCOL = ROOT / 'RNMT_V3_M9_ADAPTED_ASR_CAUSAL_PROPAGATION_PROTOCOL_FROZEN_2026-08-07.md'
PRECOMMIT = ROOT / 'V3_M9_EXECUTION_PRECOMMIT_2026-08-07.json'

def sha256_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest().upper()

assert SCRIPT.is_file() and PROTOCOL.is_file() and PRECOMMIT.is_file()
precommit = json.loads(PRECOMMIT.read_text(encoding='utf-8'))
assert precommit['artifact'] == 'v3_m9_execution_precommit_v1'
assert sha256_file(PROTOCOL) == precommit['sha256']['protocol'] == '"""
        + PROTOCOL_SHA256
        + """'
assert sha256_file(SCRIPT) == precommit['sha256']['execution_script'] == '"""
        + SCRIPT_SHA256
        + """'
subprocess.run(['nvidia-smi'], check=True)
print({'root': str(ROOT), 'protocol': precommit['protocol_id']})"""
    ),
    code(
        """# Create an isolated, version-checked environment without modifying the scientific protocol.
VENV = Path('/content/v3m9-venv')
if VENV.exists():
    shutil.rmtree(VENV)
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'virtualenv==20.35.3'], check=True)
subprocess.run([sys.executable, '-m', 'virtualenv', '--system-site-packages', str(VENV)], check=True)
PY = VENV / 'bin' / 'python'
subprocess.run([
    str(PY), '-m', 'pip', 'install', '-q', '--upgrade',
    'numpy==1.26.4', 'pandas==2.2.3', 'scipy==1.15.2',
    'matplotlib==3.10.0', 'transformers==4.57.1', 'peft==0.17.1',
    'accelerate==1.11.0', 'sacrebleu==2.5.1', 'sentencepiece==0.2.1',
    'safetensors==0.4.5'
], check=True)
subprocess.run([
    str(PY), '-c',
    "import torch, transformers, peft, pandas, numpy; "
    "assert torch.cuda.is_available(); "
    "assert 'A100' in torch.cuda.get_device_name(0).upper(); "
    "print({'gpu':torch.cuda.get_device_name(0),'torch':torch.__version__,"
    "'transformers':transformers.__version__,'peft':peft.__version__,"
    "'pandas':pandas.__version__,'numpy':numpy.__version__})"
], check=True)"""
    ),
    code(
        """# Recheck the frozen hashes immediately before the single V3-M9 execution.
precommit = json.loads(PRECOMMIT.read_text(encoding='utf-8'))
assert sha256_file(PROTOCOL) == precommit['sha256']['protocol']
assert sha256_file(SCRIPT) == precommit['sha256']['execution_script']
assert precommit['stop_boundaries'] == {
    'sealed_test_opened': False,
    'test_rows_read': 0,
    'human_outcomes_read': False,
    'sbllm_run': False,
    'production_changed': False,
}
subprocess.run([str(PY), '-u', str(SCRIPT)], check=True)"""
    ),
    code(
        """# Read only the completed automatic gate and render its fixed development figures.
from IPython.display import Image, display
import pandas as pd

RUN = ROOT / 'runs/20260807_v3_m9_adapted_asr_causal_propagation_dev_v1'
DECISION = RUN / 'outputs/V3_M9_AUTOMATIC_GATE_DECISION.json'
decision = json.loads(DECISION.read_text(encoding='utf-8'))
print(json.dumps(decision, ensure_ascii=False, indent=2))
display(pd.read_csv(RUN / 'outputs/V3_M9_OVERALL_METRICS.csv'))
display(pd.read_csv(RUN / 'outputs/V3_M9_SPEAKER_METRICS.csv'))
for name in [
    'V3_M9_FIGURE_1_OVERALL_METRICS.png',
    'V3_M9_FIGURE_2_SPEAKER_CHRF.png',
    'V3_M9_FIGURE_3_PAIRED_CHRF_DELTAS.png',
]:
    display(Image(filename=str(RUN / 'figures' / name)))
assert decision['sealed_test_opened'] is False and decision['test_rows_read'] == 0
assert decision['human_outcomes_read'] is False and decision['sbllm_run'] is False
assert decision['production_changed'] is False"""
    ),
]

notebook = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {"name": OUTPUT.name, "provenance": []},
        "kernelspec": {"display_name": "Python 3", "name": "python3"},
        "language_info": {"name": "python"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}
OUTPUT.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(OUTPUT)
