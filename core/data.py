"""
Domain content — section 4 of the original app.py.

Per-category vault listings, preset prompts, statutory checklists and the
boilerplate clause text. This is the file to edit when you want to change what
the prototype *says*; nothing here touches Streamlit or application state.

Swapping this module for a real retrieval backend is the main seam for turning
the prototype into a working product.
"""

from __future__ import annotations

SLA_HEADERS = ["Service Tier", "Recovery Time Objective (RTO)",
               "Recovery Point Objective (RPO)", "Guaranteed Availability"]


SLA_ROWS = [
    ["Tier 1 — Critical", "15 minutes", "5 minutes", "99.99%"],
    ["Tier 2 — High", "4 hours", "1 hour", "99.90%"],
    ["Tier 3 — Standard", "24 hours", "12 hours", "99.50%"],
]


DR_BODY = """4.2  DISASTER RECOVERY & BUSINESS CONTINUITY FRAMEWORK

4.2.1  Statement of Commitment
The Contractor shall establish, maintain and annually test a Disaster Recovery (DR) and Business Continuity Management (BCM) framework that is certified to ISO/IEC 27001:2022 and ISO 22301:2019, and which remains fully aligned with the Malaysian Cyber Security Act 2024 and the Personal Data Protection Act 2010 (as amended 2024). All primary and secondary processing shall remain within Malaysian sovereign territory.

4.2.2  Recovery Architecture
Production workloads shall operate in an active-active configuration across two geographically separated Tier-III datacentres located in Cyberjaya (primary) and Kuala Lumpur (secondary), with a minimum physical separation of 35 kilometres. Continuous asynchronous block-level replication shall be maintained between sites, with automated failover orchestration validated on a quarterly basis.

4.2.3  Service Level Commitments
Recovery objectives are stratified by service criticality tier as set out in the table below. These objectives are contractually binding and subject to the liquidated damages regime in Section 9.4.

4.2.4  Testing, Assurance and Reporting
A full DR invocation exercise shall be conducted no less than twice per calendar year, with an independent observer nominated by the Client entitled to attend. A signed test report, including recovery timings measured against the committed objectives, shall be submitted to the Client within fourteen (14) working days of each exercise.

4.2.5  Notification and Escalation
The Contractor shall notify the Client's nominated Compliance Lead within thirty (30) minutes of declaring a disaster event, and shall provide written incident notification to the National Cyber Security Agency (NACSA) within the statutory period prescribed under the Cyber Security Act 2024."""


CATEGORIES: dict[str, dict] = {
    "Proposal": {
        "route": "Proposal Generation",
        "blurb": "Commercial and technical proposal drafting and statutory verification, "
                 "grounded in your proposal registry.",
        "vault": [
            "2024_Corporate_Capability_Statement.pdf",
            "Client_Reference_Portfolio_v6.pdf",
            "ISO_27001_Compliance.pdf",
            "Pricing_Schedule_Master.xlsx",
            "PDPA_Data_Processing_Addendum.pdf",
        ],
        "intake": "Client_RFP_Requirements.pdf",
        "prompts": [
            "Draft Section 4.2 Disaster Recovery SLA for banking tender",
            "Generate MOF-compliant statutory declaration",
            "Create Executive Summary highlighting ISO 27001",
        ],
        "doc_title": "Technical & Commercial Proposal — Managed Services",
        "doc_ref": "VC-PRO-2026-0417",
        "citation": ("2024_Master_Tender.pdf", 18),
        "audit_basis": "MOF_ePerolehan_Template.pdf + 2024_Master_Tender.pdf",
        "passed": [
            "Corporate profile & SSM registration particulars present",
            "MOF registration certificate referenced and valid",
            "ISO/IEC 27001:2022 certification evidence attached",
            "PDPA 2010 (Amd. 2024) data processing clauses included",
            "Pricing schedule format matches Treasury benchmark",
            "Authorised signatory block complete",
        ],
        "missing": "Section 4.2 Disaster Recovery SLA",
    },
    "Tender": {
        "route": "Tender Generation",
        "blurb": "Tender response drafting and statutory verification against the MOF and "
                 "ePerolehan baselines.",
        "vault": [
            "2024_Master_Tender.pdf",
            "ISO_27001_Compliance.pdf",
            "MOF_ePerolehan_Template.pdf",
            "Treasury_Circular_PK_2.3.pdf",
            "Bumiputera_Status_Certificate.pdf",
            "Statutory_Declaration_Borang_A.docx",
        ],
        "intake": "Client_RFP_Requirements.pdf",
        "prompts": [
            "Draft Section 4.2 Disaster Recovery SLA for banking tender",
            "Generate MOF-compliant statutory declaration",
            "Create Executive Summary highlighting ISO 27001",
        ],
        "doc_title": "Tender Response — Core Banking Infrastructure Services",
        "doc_ref": "VC-TDR-2026-0088",
        "citation": ("2024_Master_Tender.pdf", 18),
        "audit_basis": "MOF_ePerolehan_Template.pdf + 2024_Master_Tender.pdf",
        "passed": [
            "Borang A statutory declaration executed and witnessed",
            "MOF & CIDB registration codes verified against ePerolehan",
            "Bumiputera status certificate current and attached",
            "ISO/IEC 27001:2022 scope statement covers tendered services",
            "Treasury Circular PK 2.3 pricing format observed",
            "Anti-bribery & integrity pact signed",
        ],
        "missing": "Section 4.2 Disaster Recovery SLA",
    },
    "Report": {
        "route": "Report Generation",
        "blurb": "Regulatory, board and audit reporting — drafted and verified against "
                 "validated internal evidence.",
        "vault": [
            "Q3_2026_Internal_Audit_Findings.pdf",
            "ISO_27001_Compliance.pdf",
            "BNM_RMiT_Control_Mapping.xlsx",
            "Incident_Register_2026.csv",
            "Board_Reporting_Template_v4.docx",
        ],
        "intake": "Client_RFP_Requirements.pdf",
        "prompts": [
            "Draft Section 4.2 Disaster Recovery SLA for banking tender",
            "Generate MOF-compliant statutory declaration",
            "Create Executive Summary highlighting ISO 27001",
        ],
        "doc_title": "Annual Compliance & Resilience Assurance Report",
        "doc_ref": "VC-RPT-2026-0231",
        "citation": ("2024_Master_Tender.pdf", 18),
        "audit_basis": "MOF_ePerolehan_Template.pdf + 2024_Master_Tender.pdf",
        "passed": [
            "Control ownership matrix complete for all 14 domains",
            "BNM RMiT control mapping reconciled",
            "ISO/IEC 27001:2022 surveillance audit outcome recorded",
            "Incident register reconciled to statutory notification log",
            "Board attestation page prepared",
            "Retention schedule aligned to PDPA 2010 (Amd. 2024)",
        ],
        "missing": "Section 4.2 Disaster Recovery SLA",
    },
}


PROVENANCE_QUOTE = (
    "“The Contractor shall maintain an active-active disaster recovery posture across two "
    "geographically separated Tier-III facilities within Malaysia, achieving a Recovery Time "
    "Objective of not more than fifteen (15) minutes and a Recovery Point Objective of not "
    "more than five (5) minutes for all Tier 1 Critical services, with guaranteed availability "
    "of 99.99% measured on a rolling calendar-month basis.”"
)