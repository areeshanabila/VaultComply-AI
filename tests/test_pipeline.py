from services.document_ingestion import parse_document
from services.requirement_engine import extract_requirements
from services.retrieval import retrieve
from services.audit_engine import audit_document, compliance_score
from services.models import DocumentRecord, DocumentChunk


def test_txt_ingestion_chunks_and_hash():
    rec = parse_document("policy.txt", b"Safety policy. PPE is required.\nDaily toolbox briefing is required.", "text/plain")
    assert rec.name == "policy.txt"
    assert rec.page_count == 1
    assert rec.sha256
    assert rec.chunks
    assert rec.chunks[0].page == 1


def test_requirement_fallback_extracts_explicit_rules():
    rec = parse_document(
        "rfp.txt",
        b"MANDATORY REQUIREMENTS:\nThe proposal must include a Company Credentials section.\n"
        b"The Sustainability Plan must state a minimum 70% waste-diversion target.\n"
        b"The Implementation Plan must commit to project completion within 12 weeks.",
        "text/plain",
    )
    reqs, engine = extract_requirements(rec, prefer_ollama=False)
    assert engine == "deterministic-fallback"
    assert len(reqs) == 3
    assert reqs[0].rule_type == "section_presence"
    assert reqs[1].minimum == 70
    assert reqs[2].maximum == 12


def test_lexical_retrieval_returns_relevant_source():
    a = parse_document("cyber.txt", b"Cybersecurity Incident Response Plan. Client notification within 60 minutes.", "text/plain")
    b = parse_document("safety.txt", b"Safety shoes and toolbox briefing for construction workers.", "text/plain")
    hits, mode = retrieve("cybersecurity incident client notification", [a, b], top_k=2, use_semantic=False)
    assert mode == "lexical"
    assert hits
    assert hits[0].chunk.document_name == "cyber.txt"


def test_compliance_score_is_derived_from_results():
    rfp = parse_document(
        "rfp.txt",
        b"The proposal must include a Company Credentials section.\n"
        b"The Sustainability Plan must state a minimum 70% waste-diversion target.\n"
        b"The Implementation Plan must commit to project completion within 12 weeks.",
        "text/plain",
    )
    reqs, _ = extract_requirements(rfp, prefer_ollama=False)
    compliant = "Company Credentials\nSustainability Plan\n75% waste-diversion target.\nImplementation Plan\nCompletion within 10 weeks."
    results = audit_document(compliant, reqs, use_ollama=False)
    assert compliance_score(results) == 100

    missing = "Company Credentials\nImplementation Plan\nCompletion within 10 weeks."
    results2 = audit_document(missing, reqs, use_ollama=False)
    assert compliance_score(results2) < 100
