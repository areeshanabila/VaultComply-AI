from __future__ import annotations

import re

from services.models import RetrievalHit
from services.ollama_client import OllamaError, chat, status


def _fallback_draft(instruction: str, hits: list[RetrievalHit]) -> str:
    heading = instruction.strip().rstrip(".") or "Grounded Draft Section"
    if len(heading) > 110:
        heading = "Grounded Draft Section"
    lines = [heading, ""]
    for hit in hits[:3]:
        excerpt = re.sub(r"\s+", " ", hit.chunk.text).strip()
        sentences = re.split(r"(?<=[.!?])\s+", excerpt)
        chosen = " ".join(sentences[:2]).strip()
        if chosen:
            lines.append(chosen)
    lines.append("")
    lines.append("[Deterministic grounded fallback — review before approval]")
    return "\n\n".join(x for x in lines if x is not None).strip()


def generate_grounded_draft(instruction: str, hits: list[RetrievalHit]) -> tuple[str, str]:
    if not hits:
        raise ValueError("No grounded source found in the Semantic Vault for this instruction.")

    st = status()
    if st.online and st.chat_model_ready:
        sources = []
        for i, hit in enumerate(hits, start=1):
            sources.append(
                f"SOURCE {i}\nDocument: {hit.chunk.document_name}\nPage: {hit.chunk.page}\n"
                f"Excerpt:\n{hit.chunk.text}"
            )
        system = (
            "You are the grounded drafting component of VaultComply AI. Draft professional business/compliance text using ONLY "
            "the supplied source excerpts. Do not invent dates, certifications, legal claims, SLA values, company facts, or citations. "
            "Do not mention sources inline; citation metadata will be attached by the application. If evidence is insufficient, say "
            "INSUFFICIENT GROUNDED EVIDENCE. Keep the output concise and ready for human review."
        )
        try:
            content = chat([
                {"role": "system", "content": system},
                {"role": "user", "content": f"INSTRUCTION:\n{instruction}\n\n" + "\n\n".join(sources)},
            ], timeout=600, num_predict=1200)
            if "INSUFFICIENT GROUNDED EVIDENCE" in content.upper():
                raise ValueError("The local model found insufficient grounded evidence for this draft.")
            return content.strip(), "ollama"
        except OllamaError:
            pass

    return _fallback_draft(instruction, hits), "deterministic-grounded-fallback"
