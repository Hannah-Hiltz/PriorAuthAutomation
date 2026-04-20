"""
letter_generator.py
Formats LLM classification results into PA determination letters,
decision summaries, and documentation gap reports.

Usage:
    from src.letter_generator import generate_pa_letter, generate_gap_report, generate_decision_summary
"""

from datetime import date
from typing import List
import pandas as pd


def generate_pa_letter(case: dict) -> str:
    """
    Generate a structured PA determination letter from LLM output.
    Mirrors the format of real payer determination notices.

    Args:
        case: classified case dict containing llm_result and predicted_extraction
    Returns:
        Formatted letter string
    """
    llm       = case.get('llm_result', {})
    ext       = case.get('predicted_extraction', {})
    decision  = llm.get('decision', 'PENDING_REVIEW')
    today     = date.today().strftime('%B %d, %Y')
    ref_num   = f'AUTH-{case["case_id"]}-{date.today().strftime("%Y%m%d")}'

    icd_str   = ', '.join(ext.get('diagnoses', [])) or 'See clinical note'
    cpt_str   = ', '.join(ext.get('procedures', [])) or 'See clinical note'
    gaps      = llm.get('documentation_gaps', [])
    rationale = llm.get('clinical_rationale', '')
    criteria  = llm.get('payer_criteria_cited', 'Standard medical necessity criteria')

    header_map = {
        'APPROVE':        'PRIOR AUTHORIZATION — APPROVED',
        'DENY':           'PRIOR AUTHORIZATION — DENIED',
        'PENDING_REVIEW': 'PRIOR AUTHORIZATION — UNDER CLINICAL REVIEW'
    }

    if decision == 'APPROVE':
        body = f"""We are pleased to inform you that the requested service has been approved
based on our review of the submitted clinical documentation.

Authorization Number: {ref_num}
Valid Period:         {today} — 90 days from date of issue
Diagnosis Codes:      {icd_str}
Procedure Codes:      {cpt_str}
Policy Reference:     {criteria}

CLINICAL BASIS FOR APPROVAL:
{rationale}"""

    elif decision == 'DENY':
        gap_text = '\n'.join(f'  • {g}' for g in gaps) if gaps else '  • See clinical policy for requirements'
        body = f"""Following review of the submitted clinical information, we are unable to
approve the requested service at this time.

Reason for Denial:    {llm.get('denial_reason', 'Does not meet medical necessity criteria')}
Diagnosis Codes:      {icd_str}
Procedure Codes:      {cpt_str}
Policy Reference:     {criteria}

CLINICAL BASIS FOR DENIAL:
{rationale}

DOCUMENTATION REQUIRED FOR RECONSIDERATION:
{gap_text}

APPEAL RIGHTS:
You have the right to appeal this decision within 60 calendar days of this notice.
To request a peer-to-peer review with our Medical Director, contact Medical Management
within 14 business days. To submit an appeal, include updated clinical documentation
addressing the items listed above."""

    else:  # PENDING_REVIEW
        body = f"""Your prior authorization request is currently under clinical review
by our medical management team.

Reference Number:     {ref_num}
Expected Resolution:  Within 3 business days (standard) or 72 hours (urgent)
Diagnosis Codes:      {icd_str}

REASON FOR REVIEW:
{rationale}

If this request is clinically urgent, please contact our Clinical Review team
directly and reference the number above."""

    return f"""{'='*65}
{header_map[decision]}
{'='*65}

Date:              {today}
Case Reference:    {case['case_id']}
Health Plan:       {case['insurance_type']}
Clinical Category: {case['clinical_category']}

{body}

{'-'*65}
Recommended Action: {llm.get('recommended_action', '')}
AI Confidence:      {llm.get('confidence', 0):.0%}
                    (Cases below 70% confidence are routed to human review)

IMPORTANT: This determination was generated with AI assistance and is subject
to clinical oversight review per organizational policy. All denials require
human clinical reviewer sign-off before issuance.
{'='*65}
"""


def extract_rationale(text: str) -> str:
    """
    Extract the clinical rationale section from a letter or gold standard.
    Used for rationale-only BERTScore evaluation.

    For generated letters: pulls the CLINICAL BASIS section.
    For gold standard prose: pulls the first substantive paragraph.
    """
    if 'CLINICAL BASIS' in text:
        start = text.find('CLINICAL BASIS')
        start = text.find('\n', start) + 1
        end   = text.find('\n\n', start)
        if end == -1:
            end = start + 500
        return text[start:end].strip()

    paragraphs = [p.strip() for p in text.split('\n') if len(p.strip()) > 80]
    return paragraphs[0] if paragraphs else text[:400].strip()


def generate_gap_report(cases: list) -> pd.DataFrame:
    """
    Aggregate documentation gaps across all cases.
    Useful for identifying systemic documentation issues at a provider level.

    Args:
        cases: list of classified case dicts
    Returns:
        DataFrame with one row per case
    """
    rows = []
    for case in cases:
        llm  = case.get('llm_result', {})
        gaps = llm.get('documentation_gaps', [])
        rows.append({
            'case_id':           case['case_id'],
            'decision':          llm.get('decision', ''),
            'true_label':        case['true_label'],
            'clinical_category': case['clinical_category'],
            'doc_quality':       case['documentation_quality'],
            'n_gaps':            len(gaps),
            'gaps':              '; '.join(gaps) if gaps else 'None',
            'confidence':        llm.get('confidence', 0),
        })
    return pd.DataFrame(rows)


def generate_decision_summary(cases: list) -> pd.DataFrame:
    """
    Flat decision summary table for all cases.

    Args:
        cases: list of classified case dicts
    Returns:
        DataFrame with one row per case
    """
    rows = []
    for case in cases:
        llm = case.get('llm_result', {})
        rows.append({
            'Case ID':      case['case_id'],
            'Category':     case['clinical_category'],
            'Insurance':    case['insurance_type'].split('(')[0].strip(),
            'Decision':     llm.get('decision', ''),
            'True Label':   case['true_label'],
            'Match':        'YES' if llm.get('decision') == case['true_label'] else 'NO',
            'Confidence':   f"{llm.get('confidence', 0):.0%}",
            'Doc Quality':  case['documentation_quality'],
            'Gaps':         len(llm.get('documentation_gaps', [])),
            'Next Action':  llm.get('recommended_action', '')[:50],
        })
    return pd.DataFrame(rows)


def generate_all_letters(cases: list) -> List[dict]:
    """
    Generate letters for all cases and return as a list of dicts.

    Args:
        cases: list of classified case dicts
    Returns:
        List of dicts with case_id, decision, true_label, letter, gold_standard
    """
    return [{
        'case_id':       case['case_id'],
        'decision':      case.get('llm_result', {}).get('decision', ''),
        'true_label':    case['true_label'],
        'letter':        generate_pa_letter(case),
        'gold_standard': case.get('gold_standard_letter', ''),
    } for case in cases]
