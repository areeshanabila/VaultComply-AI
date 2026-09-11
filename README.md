# VaultComply AI — Local Ollama + RAG Prototype

VaultComply AI is a local-first Streamlit prototype for **grounded business-document drafting and compliance auditing**.


- real PDF / DOCX / TXT / MD / CSV / XLSX parsing
- page-aware document chunking
- optional Ollama embeddings for Semantic Vault retrieval
- lexical retrieval fallback when embeddings are unavailable
- RFP/checklist requirement extraction with Ollama JSON output
- deterministic requirement-extraction fallback
- grounded drafting with local Ollama
- deterministic grounded drafting fallback if the chat model is unavailable
- citations taken from the retrieved file/page/chunk metadata — not invented by the model
- compliance results calculated from actual extracted requirements
- optional Ollama semantic verification for ambiguous requirements
- human approval separated from compliance scoring
- DOCX / PDF / ZIP exports from the reviewed draft

> This is a prototype. It demonstrates local processing and workflow controls; it does not itself prove production VPC isolation, KMS custody, external certifications, or independently attested Zero Data Retention.

---

## 1. Requirements

- Python 3.11+
- Ollama installed locally

Recommended Ollama models:

```powershell
ollama pull qwen3:1.7b
ollama pull nomic-embed-text
```

The default local endpoint is:

```text
http://127.0.0.1:11434
```

The application does not require a cloud AI API.

---

## 2. Windows setup

From PowerShell:

```powershell
cd VaultComply-AI-main

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

Check that Ollama is running and the configured models are available:

```powershell
ollama list
python ollama_check.py
```

Start VaultComply:

```powershell
streamlit run main.py
```

Open:

```text
http://localhost:8501
```

---

## 3. Ollama configuration

Defaults:

```text
OLLAMA_CHAT_MODEL=qwen3:1.7b
OLLAMA_EMBED_MODEL=nomic-embed-text
```

For CPU-only testing, `qwen3:1.7b` is the recommended default in this build.

---

## 4. Real workflow

### A. Index the Semantic Vault

Open Proposal, Tender, or Report Workspace.

In the left column, upload historical company documents.

VaultComply:

1. parses the file locally
2. preserves PDF page numbers
3. chunks the extracted text
4. hashes each chunk
5. generates local embeddings if `nomic-embed-text` is available
6. otherwise keeps a lexical index

The filenames that ship with the old prototype remain visible as **reference-only placeholders** until the actual files are uploaded and parsed.

### B. Upload the RFP / checklist

In the centre column, upload the client requirements document.

VaultComply attempts:

```text
RFP / checklist
      ↓
Ollama structured extraction
      ↓
Requirement objects
```

Every Ollama-extracted requirement must include an exact source quote that exists in the uploaded document. Unsupported model-generated requirements are rejected.

If Ollama is unavailable, explicit `must`, `shall`, `required`, minimum/maximum, and section-presence rules are extracted deterministically.

### C. Verify an existing document

Under **Verify Existing Document**, upload the document you want to audit.

VaultComply runs deterministic checks first:

- required section / concept presence
- expected concept coverage
- percentage thresholds
- week / hour / minute thresholds

For genuinely semantic requirements, you can enable:

```text
Use Ollama for ambiguous semantic requirements
```

This is optional because CPU inference may be slower.

### D. Draft a missing clause from the vault

Under **Draft a Clause**:

1. choose a failed requirement or type an instruction
2. retrieve the most relevant local vault chunks
3. use hybrid embedding + lexical retrieval when embeddings exist
4. pass only the top grounded passages to Ollama
5. create a provisional draft
6. attach the real source filename, page, chunk ID, retrieval score and hash

If no relevant source is found, the system stops with:

```text
No grounded source found
```

It does not fabricate a citation.

### E. Human approval and re-audit

Approval means:

> The reviewer accepts the proposed wording.

Approval does **not** mean:

> The document is automatically compliant.

When a revision is approved, VaultComply combines it with the document under test and recalculates the audit deterministically.

### F. Export

- reviewed Word draft: available after human approval
- audit PDF and submission bundle: available only when all extracted mandatory requirements PASS

---

## 5. Architecture

```text
Streamlit UI
    │
    ├── views/workspace/vault.py
    │       │
    │       ├── document_ingestion.py
    │       └── retrieval.py ─────────────► Ollama embeddings (optional)
    │
    ├── views/workspace/studio.py
    │       │
    │       ├── requirement_engine.py ────► Ollama chat / JSON
    │       ├── retrieval.py
    │       ├── drafting.py ──────────────► Ollama grounded drafting
    │       └── audit_engine.py ──────────► optional Ollama semantic check
    │
    └── views/workspace/auditor.py
            │
            └── deterministic compliance score
```

Service modules:

```text
services/
├── models.py
├── ollama_client.py
├── document_ingestion.py
├── retrieval.py
├── requirement_engine.py
├── drafting.py
├── audit_engine.py
└── exporters.py
```

---

## 6. Ollama failure behaviour

If Ollama is offline or a model is missing:

| Capability | Fallback |
|---|---|
| Vault ingestion | still works |
| PDF/DOCX parsing | still works |
| Retrieval | lexical search |
| Requirement extraction | deterministic rule extraction |
| Drafting | grounded extractive fallback |
| Deterministic audit | still works |
| Semantic-only audit | REVIEW instead of a fabricated PASS/FAIL |

The Settings page shows the current Ollama endpoint and whether the configured chat and embedding models were detected.

---

## 7. Tests

Run:

```powershell
python doctor.py
pytest -q
```

`doctor.py` checks the internal module/import graph. The service tests verify parsing, requirement fallback extraction, local retrieval and score derivation.

---

## 8. Important current limitations

This implementation intentionally does not pretend to provide features that are not yet production-ready:

- session state is not a durable database
- no multi-user persistence
- no immutable audit ledger
- no production tenant isolation / VPC orchestration
- no external KMS integration
- no OCR for scanned image-only PDFs
- numeric compliance checks are generic and should be expanded by domain
- semantic verification quality depends on the selected Ollama model
- cross-lingual BM ↔ English semantic matching uses the optional local model rather than a dedicated translation/alignment model
- deep contradiction checking against authoritative vault versions is a recommended next phase


