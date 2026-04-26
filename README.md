# Prior Authorization Automation
### Clinical NLP + LLM Pipeline for Healthcare Revenue Cycle
*by [Hannah Hiltz](https://www.linkedin.com/in/hannah-hiltz/) — Healthcare AI & Data Science*

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/v1.0-Updates%20Coming!-yellow)
![Domain](https://img.shields.io/badge/Domain-Healthcare%20AI-purple)
![Made with Colab](https://img.shields.io/badge/Made%20with-Colab-orange?logo=googlecolab)


End-to-end NLP + LLM pipeline that automates prior authorization decisions and generates justification letters — with a live interactive dashboard!

[Full Write-Up (GitPages)](https://github.com/Hannah-Hiltz/PriorAuthAutomation/blob/main/docs/index.md) | [Open End-to-End Pipeline in Colab](https://colab.research.google.com/github/Hannah-Hiltz/PriorAuthAutomation/blob/main/notebooks/00_full_pipeline_demo.ipynb) | [![Live Dashboard](https://img.shields.io/badge/▶_Live_Demo-Interactive_Dashboard-2563eb?style=for-the-badge)](https://hannah-hiltz.github.io/PriorAuthAutomation/) 

---

## The Problem
 
Prior authorization (PA) is one of the most administratively burdensome processes in U.S. healthcare and it's getting worse, not better.
 
Physicians spend an average of **16 hours per week** on PA paperwork. That's two full workdays every week spent filling out forms instead of aiding patients. The American Medical Association reports that **94% of physicians** say PA delays have led to patients abandoning recommended treatment. Health systems lose an estimated **$528 million annually** to write-offs and rework from denied or delayed authorizations.
 
The manual PA process is slow, inconsistent, and expensive on both sides. Providers submit incomplete documentation and claims get denied. Payers receive unstructured notes and have to manually map clinical language to coverage criteria. The average PA takes **3.5 business days** to resolve. For time-sensitive treatments such as cancer immunotherapy, biologics for severe disease, mental health medications that delay has clinical consequences that ultimately prevent patient from receiving top and timely care.
 
This is a solvable problem. The information needed to make a PA decision is already in the clinical note. It just isn't structured.
 
| Metric | Manual Process | Automated Pipeline |
|---|---|---|
| Turnaround time | 3–5 business days | < 3 minutes |
| Cost per PA | ~$45 (fully loaded) | ~$2.50 |
| Physician time/week | 16 hours | < 1 hour (review only) |
| Denial rate (documentation gaps) | ~22% | ~14% (projected) |
| Documentation completeness | Variable | Structured + flagged |

---

## What This Project Does
 
This project builds an end-to-end pipeline that reads an unstructured physician clinical note and produces three outputs:
 
**1. A PA justification letter draft** — professionally written, payer-compliant clinical rationale that cites specific coverage criteria. Ready for provider review and submission.
 
**2. A decision classification** — Approve, Deny, or Pending Review, with a confidence score. Cases below 70% confidence route to human clinical review automatically.
 
**3. A documentation gap report** — a structured list of what's missing from the submission and what would be needed for approval. Actionable feedback for the provider before resubmission.
 
---
 
## Key Results
 
| Metric | Value |
|---|---|
| BERTScore F1 (full letter) | 0.687 |
| BERTScore F1 (rationale only) | 0.757 |
| Auto-resolution rate | ~70% |
| Turnaround time | 3.5 days → 3 minutes |
| Estimated annual value | $2M+ at 5,000 PA/month |
 
---
 
## Pipeline Architecture
 
![Pipeline Diagram](pipeline_diagram.png)
 
*End-to-end pipeline: clinical note → NLP extraction → rule engine + RAG → LLM → structured outputs*
 
---
 
## How It Works
 
The pipeline has four stages:
 
**Stage 1 — NLP Extraction** (`src/extractor.py`)
Extracts structured clinical signals using scispaCy and regex: ICD-10 and CPT codes, lab values (HbA1c, BMI, PASI, etc.), medication history, and step therapy indicators.
 
**Stage 2 — Rule Engine** (`src/rule_engine.py`)
Applies payer-aligned deterministic logic: documentation completeness scoring, step therapy validation, and clinical severity scoring. Surfaces gaps *before* the LLM ever sees the case.
 
**Stage 3 — RAG Retrieval** (`src/rag.py`)
Embedding-based lookup over payer policies stored in ChromaDB. The LLM reasons against the right policy clause, not the whole manual. Covers CMS LCDs/NCDs and major payer criteria.
 
**Stage 4 — LLM Reasoning + Letter** (`src/prompt_builder.py`, `src/letter_generator.py`)
Classifies APPROVE / DENY / PENDING with a confidence score, cites specific policy criteria, and produces a formatted justification letter ready for payer review.
 
---
 
## Repository Structure
 
```
PriorAuthAutomation/
│
├── data/
│   ├── pa_synthetic_dataset.json       # 25 labeled synthetic PA cases
│   ├── ground_truth_labels.csv         # Decision labels for evaluation
│   └── payer_policies/
│       └── README.md                   # Which CMS LCDs to download
│
├── notebooks/
│   ├── 00_full_pipeline_demo.ipynb     # Full pipeline in one notebook
│   ├── 01_data_exploration.ipynb       # Dataset analysis and visualization
│   ├── 02_nlp_extraction.ipynb         # scispaCy entity extraction pipeline
│   ├── 03_rag_pipeline.ipynb           # Embedding, vector store, retrieval
│   ├── 04_prompt_engineering.ipynb     # LLM prompt development and testing
│   ├── 05_output_generation.ipynb      # Letter generation and formatting
│   └── 06_evaluation_roi.ipynb         # BERTScore, F1, ROI model
│
├── src/
│   ├── __init__.py
│   ├── extractor.py                    # scispaCy + regex NLP pipeline
│   ├── rule_engine.py                  # Step therapy and documentation scoring
│   ├── rag.py                          # Embedding + ChromaDB retrieval
│   ├── prompt_builder.py               # System/user prompt assembly + LLM calls
│   └── letter_generator.py             # PA letter and report formatting
│
├── prompts/
│   ├── pa_system_prompt_v1.txt         # General role + schema
│   └── pa_system_prompt_v2.txt         # Ordered decision criteria (improved)
│
├── evaluation/
│   ├── classification_report.json
│   ├── bertscore_results.json
│   ├── decision_summary.csv
│   └── gap_report.csv
│
├── docs/
│   └── index.html                      # GitHub Pages interactive dashboard
│
├── pipeline_diagram.png
├── requirements.txt
└── README.md
```
 
---
 
## The Dataset
 
All development used a hand-crafted synthetic dataset of 25 labeled prior authorization cases. **No real patient data was used at any stage.** This is both a practical necessity (HIPAA) and a design choice — synthetic data lets us control documentation quality, clinical category mix, and label distribution in ways that real data doesn't.
 
The 25 cases span 13 clinical categories chosen to represent the highest-volume PA scenarios in practice: biologics for rheumatology, dermatology, gastroenterology, and pulmonology; GLP-1 agonists for diabetes and obesity; oncology immunotherapy; mental health medications; imaging; bariatric surgery; specialty infusions; and genetic testing.
 
### Clinical Coverage
 
| Category | Cases | Notes |
|---|---|---|
| Biologics (RA, dermatology, GI, pulmonology) | 7 | Step therapy complexity varies |
| Imaging (MRI, CT) | 4 | Rule-based; good pipeline stress test |
| Mental health (esketamine, TMS, LAI antipsychotics) | 4 | Safety escalation cases included |
| GLP-1 agonists (diabetes + obesity) | 4 | Highest denial rate in current market |
| Oncology (pembrolizumab, olaparib) | 2 | Biomarker-driven; step therapy N/A |
| Bariatric surgery | 1 | Multi-criteria documentation check |
| Specialty infusions (IVIG, eculizumab) | 2 | Rare disease, strong documentation |
| Genetic testing | 1 | Classic over-request scenario |
 
### Label Distribution
 
| Decision | Count | % |
|---|---|---|
| APPROVE | 15 | 60% |
| DENY | 7 | 28% |
| PENDING_REVIEW | 3 | 12% |
 
Each case was hand-labeled with a ground truth decision and documentation quality rating (strong / partial / weak). Every case includes a gold standard justification letter written by hand, used for BERTScore evaluation. The dataset was deliberately designed to include edge cases: oncology cases where step therapy doesn't apply, safety escalation cases (suicidal ideation, REMS medications), partial-documentation cases that land in the pending review bucket, and weak-documentation cases that should be denied.
 
---
 
## Key Findings
 
**Documentation quality is the strongest predictor of denial.** Every weak-documentation case resulted in a DENY or PENDING_REVIEW decision. This matches real-world data — the AMA reports that 56% of PA denials are documentation-related, not clinical. The pipeline correctly identifies documentation gaps as the primary driver.
 
**RAG meaningfully improves output quality.** Without retrieved payer policy, the LLM produces plausible but generic rationale ("patient has failed prior therapy and meets clinical criteria"). With RAG, it produces specific, policy-grounded language ("per CMS LCD L37209, adequate trial of two csDMARDs including methotrexate is required, which has been documented with a DAS28 of 5.9"). The difference is what actually gets authorizations approved.
 
**BERTScore requires domain-aware evaluation.** Full-letter BERTScore F1 was 0.687, below the 0.85 target. Rationale-section-only F1 was 0.757 — a +7.1 point improvement. The gap reflects structural formatting differences between template-generated letters and free-form gold standard prose, not clinical content quality. The precision jump (+0.181) confirms the generated rationale language closely matches gold standard clinical terminology. This finding shaped a more rigorous evaluation methodology: score the reasoning, not the template.
 
**Human-in-the-loop is a design feature, not a limitation.** Cases below 70% confidence route to human review automatically. Safety flags — suicidal ideation, REMS medications — always escalate regardless of documentation quality or confidence score. This architecture is compliant with CMS regulations requiring human review for PA denials and reflects how responsible AI-assisted clinical decision support should be designed.
 
---
 
## Business Impact
 
For a health system processing 5,000 PA requests per month, the modeled annual impact is approximately $2M in combined cost savings and revenue recovery.
 
| Metric | Manual Process | Automated Pipeline |
|---|---|---|
| Cost per PA | ~$45 | ~$2.50 |
| Turnaround time | 3.5 business days | 3 minutes |
| Auto-resolution rate | 0% | ~70% |
| Annual labor savings | — | ~$1.6M |
| Annual revenue recovery | — | ~$1.2M |
| **Combined annual value** | — | **~$2.8M** |
| FTE hours freed per month | — | ~360 hrs (~2.25 FTEs) |
| Break-even | — | ~4–5 months |
 
These figures are based on published AMA and CAQH benchmarks and should be validated against organizational actuals before business case development. The auto-resolution rate comes directly from the pipeline's confidence scoring — only cases above 70% confidence are resolved without human review.
 
The most underappreciated number is turnaround time. Three and a half days to three minutes doesn't just save money — it means patients with time-sensitive diagnoses get treatment decisions faster. For a patient awaiting authorization for cancer immunotherapy or a biologic for severe disease, that delta is clinically meaningful.
 
---
 
## Tech Stack
 
| Component | Technology |
|---|---|
| Biomedical NLP | scispaCy, spaCy |
| LLM inference | Anthropic Claude, OpenAI GPT-4o |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector store | ChromaDB |
| Evaluation | bert-score, scikit-learn |
| Data | pandas, numpy |
| Environment | Google Colab / Jupyter |
 
---
 
## Getting Started
 
```bash
git clone https://github.com/Hannah-Hiltz/PriorAuthAutomation.git
cd PriorAuthAutomation
 
pip install scispacy spacy sentence-transformers chromadb
pip install anthropic openai bert-score pandas scikit-learn matplotlib seaborn
python -m spacy download en_core_web_sm
 
# Optional: set LLM API key (notebooks run in simulation mode without it)
export ANTHROPIC_API_KEY="your-key-here"
```
 
Open `notebooks/00_full_pipeline_demo.ipynb` for the full pipeline in one notebook, or start with `01_data_exploration.ipynb` to walk through each stage individually.
 
### Reproducibility
 
All outputs are generated by running the notebooks in order. No precomputed artifacts are required. The pipeline runs in full simulation mode without an API key — swap `LLM_PROVIDER = 'simulate'` to `'anthropic'` or `'openai'` in notebook 04 to use live inference.
 
---
 
## Scope & Limitations
 
This repository reports results on 25 synthetic cases evaluated without a held-out test set and without baseline comparisons. The headline numbers (BERTScore F1 0.687 on full letters, 0.757 on the rationale section) should be read as a working demonstration of the pipeline, not a validated benchmark. The roadmap below addresses this directly.
 
---
 
## Roadmap
 
### 1. Expand the dataset to 250 stratified cases
The current n=25 distribution is too small for stable Macro F1 on the minority classes. The expansion will be stratified on `true_label`, `documentation_quality`, and `clinical_category`. The synthetic-data generation protocol will be documented in `docs/` so readers can assess provenance.
 
### 2. Introduce a train/test split
A seeded stratified split — 200 dev / 50 held-out test — with the test IDs committed to `data/splits/test_ids.json`. Prompt engineering, few-shot example selection, and RAG index construction will be restricted to the dev set so test-set results are not contaminated.
 
### 3. Publish a baseline comparison table
 
| System | Accuracy | Macro F1 | BERTScore F1 (letter) | Gap Detection F1 |
|---|---|---|---|---|
| Majority class | 60% | 0.25 | 0.41 | — |
| LLM zero-shot | ?? | ?? | ?? | ?? |
| Rule engine only | ?? | ?? | — | ?? |
| Full pipeline | ?? | ?? | 0.687 | ?? |
 
Classification metrics will include 1000-sample bootstrap 95% confidence intervals.
 
---
 
## What I'd Build Next
 
**Fine-tune on labeled PA decisions.** The current pipeline uses zero-shot prompting with a structured system prompt. A fine-tuned BioClinicalBERT or Llama-3-8B on a labeled PA decision dataset would produce higher classification accuracy, more consistent clinical language, and better calibrated confidence scores. The synthetic dataset built here is a starting point for that training data.
 
**Ingest real CMS LCDs.** The RAG pipeline is built to accept real PDF documents — the ingestion code is in `src/rag.py` and `data/payer_policies/README.md` lists exactly which documents to download and how to name them. Swapping synthetic policy text for real LCDs would validate retrieval quality against actual payer criteria and produce more defensible letter language.
 
**Build a FHIR R4 integration layer.** The CMS Prior Authorization Final Rule (CMS-0057-F, effective 2026) requires payers to implement real-time PA APIs using HL7 FHIR R4. The pipeline architecture maps cleanly to FHIR's `CoverageEligibilityRequest` and `ClaimResponse` resources. Building this integration layer would make the pipeline deployable against real payer systems.
 
**Expand the dataset.** 25 cases is enough for development and demonstration. Production-grade evaluation requires 200+ cases covering the full distribution of PA types, denial reasons, and payer criteria variations.
 
---
 
## Compliance & Ethics
 
This project was built with healthcare compliance as a design constraint, not an afterthought.
 
**Data privacy.** All development uses fully synthetic data. No real patient data was used at any stage. In any production deployment, clinical notes must be de-identified per HIPAA Safe Harbor or Expert Determination standards before processing. PHI must never be transmitted to external LLM APIs without a signed Business Associate Agreement.
 
**Human in the loop.** Automated PA decisions are decision-support tools, not final determinations. All denial decisions and safety-escalated cases require human clinical reviewer sign-off before issuance. This is both the ethically appropriate design and the legally required one under current CMS regulations and most state-level PA laws.
 
**Explainability.** Every pipeline output includes an auditable rationale trace — extracted entities, rule signals, retrieved policy, and LLM reasoning are all preserved and logged. No black-box outputs.
 
**CMS 2026 PA Final Rule.** The pipeline architecture is designed for compatibility with the CMS Prior Authorization Final Rule (CMS-0057-F) requiring payers to implement real-time PA APIs via HL7 FHIR R4 by 2026.
 
---
 
## References
 
- AMA Prior Authorization Physician Survey (2022)
- CAQH Index: Automating Healthcare (2023)
- CMS Prior Authorization Final Rule CMS-0057-F (2024)
- Neumann et al., "Automated Prior Authorization" — NEJM Catalyst (2023)
- Da Vinci Project: Prior Authorization Support FHIR IG
- scispaCy: Neumann et al., ACL (2019)
- KEYNOTE-024, OlympiAD, and referenced clinical trials per case
---
 
## About the Author
 
**Hannah Hiltz** — Healthcare AI & Data Science  
[LinkedIn](https://www.linkedin.com/in/hannah-hiltz/) · [GitHub](https://github.com/Hannah-Hiltz) · [Live Demo](https://hannah-hiltz.github.io/PriorAuthAutomation/)
 
---
 
*This project uses entirely synthetic data. It is not intended for clinical use, does not constitute medical advice, and should not be deployed in a patient care setting without appropriate clinical validation, compliance review, and regulatory clearance.*
