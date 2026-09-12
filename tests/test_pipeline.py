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
    assert engine == "deterministic-scoped-fallback"
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



def test_structured_assessment_scopes_and_flexible_section_matching():
    brief = parse_document(
        "requirements.txt",
        b"Report Formatting Requirements: Font: Arial, Font Size: 12, Line Spacing: 1.5 and Page Number: Bottom centre.\n"
        b"No plagiarism (not more than 20% similarity index).\n"
        b"PART 1: ORGANISATIONAL PROBLEM IDENTIFICATION & CONTEXT\n"
        b"PART 2: REQUIREMENT ANALYSIS FOR THE AI-POWERED TM SYSTEM\n"
        b"PART 3: SYSTEM DESIGN & WORKFLOW DEVELOPMENT\n"
        b"PART 4: AI VALUE, IMPACT & ETHICAL CONSIDERATIONS\n"
        b"PART 5: CONCLUSION\n"
        b"SECTION B: PRESENTATION\nStudents are required to present their project.",
        "text/plain",
    )
    reqs, engine = extract_requirements(brief, prefer_ollama=False)
    assert engine == "structured-assessment"
    content = [r for r in reqs if r.scope == "report_content"]
    assert len(content) == 5
    assert any(r.scope == "report_format" for r in reqs)
    assert any(r.scope == "academic_integrity" for r in reqs)
    assert any(r.scope == "presentation" for r in reqs)

    # Numbering differs from PART labels on purpose; semantic heading matching
    # should still recognise Parts 1, 2, 3 and 5 while correctly failing Part 4.
    existing = (
        "1.0 ORGANISATIONAL PROBLEM IDENTIFICATION & CONTEXT\n"
        "2.0 REQUIREMENT ANALYSIS FOR THE AI-POWERED TALENT MANAGEMENT SYSTEM\n"
        "3.0 SYSTEM DESIGN & WORKFLOW DEVELOPMENT\n"
        "5.0 CONCLUSION\n"
    )
    results = audit_document(existing, reqs, use_ollama=False)
    content_results = [r for r in results if r.requirement.scope == "report_content"]
    assert [r.status for r in content_results] == ["PASS", "PASS", "PASS", "FAIL", "PASS"]
    assert compliance_score(results) == 80

    formatting = next(r for r in results if r.requirement.scope == "report_format")
    plagiarism = next(r for r in results if r.requirement.scope == "academic_integrity")
    presentation = next(r for r in results if r.requirement.scope == "presentation")
    assert formatting.status == "REVIEW"
    assert plagiarism.status == "REVIEW"
    assert presentation.status == "N/A"
