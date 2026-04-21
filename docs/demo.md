---
layout: default
title: Demo — Prior Authorization Automation
description: Live pipeline walkthrough, sample outputs, and business impact
---

# Pipeline Demo
### Prior Authorization Automation · Hannah Hiltz

[← Back to Project Overview](index.md) · [GitHub Repository](https://github.com/Hannah-Hiltz/PriorAuthAutomation) · [Run in Colab](https://colab.research.google.com/github/Hannah-Hiltz/PriorAuthAutomation/blob/main/notebooks/00_end_to_end.ipynb)

---

## What the Pipeline Does in 3 Steps

A physician finishes a clinical note. Instead of a staff member spending 45 minutes reformatting it into a payer's prior authorization form, the pipeline reads it in seconds and produces a complete, policy-grounded justification letter — along with a decision and a list of anything that's missing.

**Input:** Unstructured physician clinical note (free text)  
**Output:** PA justification letter + Approve/Deny/Pending decision + documentation gap report

---

## Live Walkthrough — Input to Output

### The Clinical Note (Input)

This is the raw input the pipeline receives — exactly as a physician would dictate or type it:

```
58-year-old male with Type 2 Diabetes Mellitus (E11.9), stage 3a CKD (N18.3),
and established CAD (I25.10) post-NSTEMI 2021. HbA1c 9.1% on current regimen.
Failed metformin 1000mg BID x 6 months (GI intolerance — nausea and diarrhea,
documented). Failed glipizide 10mg daily x 4 months — three hypoglycemic episodes
requiring glucose administration, discontinued 01/2024. Endocrinology recommends
GLP-1 agonist given cardiovascular risk profile and renal considerations.
UACR 85 mg/g. eGFR 48.
```

**Insurance:** BlueCross PPO  
**Drug requested:** Semaglutide 0.5mg SC weekly (Ozempic)

---

### Step 1 — NLP Extraction

The pipeline reads the note and pulls out structured clinical signals:

| Field | Extracted Value |
|---|---|
| ICD-10 codes | E11.9, N18.3, I25.10 |
| Lab values | HbA1c: 9.1%, eGFR: 48, UACR: 85 mg/g |
| Drugs failed | metformin 1000mg (GI intolerance), glipizide 10mg (hypoglycemia x3) |
| Prior therapy failure | ✅ True |
| Specialist support | ✅ True (endocrinology) |
| Documentation gaps | None flagged |

This structured object — not the raw note — feeds into the rule engine and LLM. It's what makes the output clinically specific rather than generic.

---

### Step 2 — Policy Retrieval (RAG)

The pipeline queries a vector store of CMS LCD documents and commercial payer criteria. For this case it retrieves the GLP-1 coverage policy:

> *"For patients with established ASCVD, heart failure, or CKD stage 3+, GLP-1 receptor agonists with demonstrated cardiovascular benefit (semaglutide, liraglutide, dulaglutide) may be authorized earlier in the treatment algorithm consistent with ADA Standards of Care and ACC/AHA guidelines."*
> — CMS LCD L38956 — GLP-1 Agonists for T2DM

This retrieved text is injected directly into the LLM prompt. The model cites it in the output.

---

### Step 3 — Generated PA Letter (Output)

```
=================================================================
PRIOR AUTHORIZATION — APPROVED
=================================================================

Date:              April 21, 2026
Case Reference:    PA-2024-002
Health Plan:       BlueCross PPO
Clinical Category: GLP-1 Diabetes

We are pleased to inform you that the requested service has been
approved based on our review of the submitted clinical documentation.

Authorization Number: AUTH-PA-2024-002-20260421
Valid Period:         April 21, 2026 — 90 days from date of issue
Diagnosis Codes:      E11.9, N18.3, I25.10
Policy Reference:     CMS LCD L38956 — GLP-1 Agonists for T2DM

CLINICAL BASIS FOR APPROVAL:
This 58-year-old male carries diagnoses of Type 2 Diabetes Mellitus
(E11.9), stage 3a chronic kidney disease (N18.3), and established
coronary artery disease with prior NSTEMI (I25.10), representing a
high-cardiovascular-risk phenotype for which GLP-1 receptor agonist
therapy has demonstrated superior outcomes. Step therapy requirements
have been met: metformin discontinued for GI intolerance and glipizide
discontinued following three documented hypoglycemic episodes. Per CMS
LCD L38956, the documented cardiorenal indication supports GLP-1
authorization consistent with ADA Standards of Care 2024.

-----------------------------------------------------------------
Recommended Action: Issue authorization. Notify provider and member.
AI Confidence:      93%

IMPORTANT: This determination was generated with AI assistance and
is subject to clinical oversight review per organizational policy.
All denials require human clinical reviewer sign-off before issuance.
=================================================================
```

**Processing time:** < 3 seconds  
**Manual equivalent:** 30–45 minutes of staff time

---

## All Three Decision Types

The pipeline handles every outcome. Here's a real example of each from the synthetic dataset.

---

### APPROVE — Oncology (Pembrolizumab)

**Case:** 74-year-old male, stage IV NSCLC, PD-L1 TPS 82%, ECOG 1, tumor board reviewed.

**Why approved:** PD-L1 ≥ 50% meets KEYNOTE-024 threshold. No EGFR/ALK alterations. First-line monotherapy is NCCN Category 1. Step therapy explicitly waived for guideline-concordant oncology agents.

**Confidence:** 92%

---

### DENY — Asthma Biologic (Dupilumab)

**Case:** 29-year-old female, severe persistent asthma, requesting dupilumab. Currently on albuterol PRN only. No ICS trial documented. No eosinophil count. No pulmonology referral.

**Why denied:** Aetna criteria require inadequate response to ICS/LABA combination for ≥ 3 months, documented eosinophil count ≥ 150 cells/μL or FeNO ≥ 25 ppb, and pulmonology evaluation. None are present.

**Generated gap report:**
- No ICS trial documented
- No ICS/LABA combination trial documented
- FEV1 not documented
- Eosinophil count absent
- No pulmonology referral on file

**Confidence:** 88%

---

### PENDING REVIEW — Esketamine (Treatment-Resistant MDD)

**Case:** 49-year-old female, PHQ-9 of 21, failed three antidepressants, REMS-certified clinic, C-SSRS moderate ideation documented.

**Why escalated:** Documentation fully meets criteria for esketamine authorization. However, documented suicidal ideation and REMS-required medication trigger automatic escalation to human clinical review regardless of documentation quality or confidence score.

**Confidence:** 58% (safety flag overrides automated resolution)

---

## Before and After — What Changes

| | Manual Process | Automated Pipeline |
|---|---|---|
| Who does the work | Clinical staff, billing team | Pipeline + human reviewer (denials only) |
| Information source | Staff reads the note manually | NLP extracts structured entities |
| Policy lookup | Staff checks payer website | RAG retrieves relevant criteria automatically |
| Letter language | Variable — depends on who wrote it | Consistent, policy-grounded, clinical |
| Turnaround | 3.5 business days average | < 3 minutes |
| Cost per PA | ~$45 (fully loaded) | ~$2.50 |
| Denial rate | ~22% (documentation gaps) | ~15% (projected) |
| Human touchpoints | Every case | Denials + low-confidence cases only (~30%) |

---

## Evaluation Results

### Decision Accuracy

The pipeline was evaluated against 25 hand-labeled synthetic PA cases across 13 clinical categories.

| Class | Precision | Recall | F1 |
|---|---|---|---|
| APPROVE | — | — | — |
| DENY | — | — | — |
| PENDING_REVIEW | — | — | — |
| **Overall accuracy** | | | **see notebook 06** |

> Run `notebooks/06_evaluation_roi.ipynb` to generate your own classification report with live results.

---

### Letter Quality — BERTScore

BERTScore measures semantic similarity between generated letters and hand-written gold standard letters using contextual embeddings.

| Scoring Method | Mean F1 |
|---|---|
| Full letter | 0.687 |
| Rationale sections only | 0.757 |
| Improvement | +0.071 |

**Why two scores?** The generated letters use a structured template (section headers, authorization numbers, appeal rights language). The gold standards are free-form clinical prose. BERTScore penalizes formatting differences even when clinical reasoning is identical. Scoring only the rationale section — the clinically meaningful part — produces a fairer measurement. The +0.181 precision improvement confirms the generated language closely matches gold standard clinical terminology.

---

## Business Impact

For a health system processing 5,000 PA requests per month:

| Driver | Monthly | Annual |
|---|---|---|
| Labor cost reduction | ~$130K | **~$1.6M** |
| Revenue recovery (fewer denials) | ~$100K | **~$1.2M** |
| **Combined value** | **~$230K** | **~$2.8M** |

**Break-even:** approximately 4–5 months post-implementation  
**FTEs freed:** ~2.25 per month (redirected to direct patient care)  
**Denial rate improvement:** 22% → 15% (documentation completeness)

*All figures based on AMA and CAQH published benchmarks. Validate against organizational actuals before business case development.*

---

## Try It Yourself

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Hannah-Hiltz/PriorAuthAutomation/blob/main/notebooks/00_end_to_end.ipynb)

The end-to-end notebook runs the complete pipeline — no API key required. Simulation mode produces realistic outputs using the rule engine and extraction signals. Swap `LLM_PROVIDER = 'anthropic'` or `'openai'` and add your key to use live inference.

---

## Compliance Note

All data shown on this page is entirely synthetic. No real patient information was used at any stage of this project. In a production deployment, all PHI must be de-identified per HIPAA standards, LLM API calls require a signed Business Associate Agreement, and all denial determinations require human clinical reviewer sign-off before issuance.

---

**Hannah Hiltz** · Healthcare AI & Data Science  
[LinkedIn](https://www.linkedin.com/in/hannah-hiltz/) · [GitHub](https://github.com/Hannah-Hiltz/PriorAuthAutomation) · [Project Overview](index.md)
