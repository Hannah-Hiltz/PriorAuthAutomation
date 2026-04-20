"""
prompt_builder.py
Assembles LLM prompts from extracted clinical entities and retrieved policy context.
Handles both system prompt versioning and user prompt construction.

Usage:
    from src.prompt_builder import build_user_prompt, load_system_prompt, call_llm, simulate_response
"""

import json
import os
import time
from typing import Optional


# ── System Prompts ────────────────────────────────────────────────────────────

SYSTEM_PROMPT_V1 = """
You are a clinical prior authorization (PA) specialist with expertise in payer medical
necessity criteria, evidence-based medicine, and healthcare reimbursement policy.
You have deep knowledge of step therapy requirements, NCCN guidelines, ADA Standards
of Care, ACR criteria, and commercial payer coverage policies.

You will receive a structured summary of a prior authorization case including:
- Extracted clinical entities (ICD-10 codes, CPT codes, medications, lab values)
- A rule engine pre-assessment score and signals
- Retrieved payer policy text relevant to this case
- The original physician clinical note

Your task is to return ONLY valid JSON with no markdown, no preamble, and no explanation
outside the JSON object. Use exactly this schema:

{
  "decision": "APPROVE" | "DENY" | "PENDING_REVIEW",
  "confidence": 0.0-1.0,
  "clinical_rationale": "2-4 sentences in professional clinical language citing specific criteria",
  "denial_reason": "specific reason if DENY, else null",
  "documentation_gaps": ["list of missing items that would be needed"],
  "recommended_action": "what should happen next",
  "payer_criteria_cited": "which specific policy or guideline supports this decision"
}

Decision rules:
- APPROVE: documentation is complete, step therapy met, criteria satisfied
- DENY: step therapy not met, criteria not satisfied, or required documentation missing
- PENDING_REVIEW: safety concerns (suicidality, REMS), clinical complexity, or
  confidence below 0.70 — route to human clinical reviewer

Always cite specific payer policy language from the retrieved context when available.
Use precise clinical terminology. Do not generate information not present in the note.
"""

SYSTEM_PROMPT_V2 = """
You are a clinical prior authorization specialist with expertise in payer medical
necessity criteria, evidence-based medicine, and healthcare reimbursement policy.

DECISION CRITERIA — apply in order:

1. SAFETY ESCALATION (always routes to PENDING_REVIEW regardless of documentation):
   - Active suicidal ideation documented
   - REMS-required medication
   - Pediatric patient (under 18) with high-risk medication

2. APPROVE when ALL of the following are true:
   - Diagnosis codes present and consistent with requested treatment
   - Step therapy documented OR step therapy not required for this indication
   - Specialist support documented (where required by payer criteria)
   - No critical documentation gaps
   - Treatment aligns with retrieved payer policy criteria

3. DENY when ANY of the following are true:
   - Step therapy not documented and no contraindication provided
   - Required objective measures absent (labs, scores, imaging)
   - Explicitly does not meet retrieved payer guideline criteria
   - No specialist referral for specialist-required therapies

4. PENDING_REVIEW for all other cases — clinical complexity, partial documentation,
   or confidence below 0.70.

Return ONLY valid JSON with this exact schema — no markdown, no preamble:
{
  "decision": "APPROVE" | "DENY" | "PENDING_REVIEW",
  "confidence": 0.0-1.0,
  "clinical_rationale": "2-4 sentences citing specific criteria from the policy context",
  "denial_reason": "specific unmet criterion if DENY, else null",
  "documentation_gaps": ["list of missing items"],
  "recommended_action": "next step",
  "payer_criteria_cited": "specific policy or guideline cited"
}
"""

PROMPTS = {
    'v1': SYSTEM_PROMPT_V1,
    'v2': SYSTEM_PROMPT_V2,
}


def load_system_prompt(version: str = 'v1', path: Optional[str] = None) -> str:
    """
    Load a system prompt by version string or file path.

    Args:
        version: 'v1' or 'v2' (uses built-in prompts)
        path:    optional path to a .txt prompt file (overrides version)
    Returns:
        System prompt string
    """
    if path and os.path.exists(path):
        with open(path, 'r') as f:
            return f.read()
    return PROMPTS.get(version, SYSTEM_PROMPT_V1)


def save_system_prompt(prompt: str, path: str) -> None:
    """Save a system prompt string to a versioned .txt file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(prompt)


def build_user_prompt(case: dict) -> str:
    """
    Assemble the structured user prompt from case data.
    Combines extracted entities, policy context, and the original note.

    Args:
        case: enriched case dict with predicted_extraction and policy_context
    Returns:
        Formatted prompt string
    """
    ext = case.get('predicted_extraction', {})

    return f"""PRIOR AUTHORIZATION CASE: {case['case_id']}

Insurance: {case['insurance_type']} | Category: {case['clinical_category']}

EXTRACTED CLINICAL ENTITIES
Diagnoses (ICD-10):       {ext.get('diagnoses') or 'None extracted'}
Procedures (CPT):         {ext.get('procedures') or 'None extracted'}
Drugs failed:             {ext.get('drugs_failed') or 'None documented'}
Lab values:               {ext.get('lab_values') or 'None extracted'}
Prior therapy failure:    {ext.get('has_prior_therapy_failure', False)}
Specialist support:       {ext.get('has_specialist_support', False)}
Documentation gaps:       {ext.get('documentation_gaps') or 'None flagged'}

RETRIEVED PAYER POLICY
{case.get('policy_context', 'No policy context retrieved')[:1200]}

ORIGINAL CLINICAL NOTE
{case['note'].strip()}

Return your PA decision as JSON."""


def call_llm(system: str, user: str, provider: str = 'simulate',
             api_key: Optional[str] = None) -> Optional[dict]:
    """
    Call LLM API and return parsed JSON response.

    Args:
        system:   system prompt string
        user:     user prompt string
        provider: 'anthropic', 'openai', or 'simulate'
        api_key:  API key (falls back to environment variable)
    Returns:
        Parsed dict or None if simulation mode
    """
    if provider == 'anthropic':
        import anthropic
        key    = api_key or os.environ.get('ANTHROPIC_API_KEY')
        client = anthropic.Anthropic(api_key=key)
        msg    = client.messages.create(
            model      = 'claude-opus-4-5',
            max_tokens = 1024,
            system     = system,
            messages   = [{'role': 'user', 'content': user}]
        )
        raw = msg.content[0].text

    elif provider == 'openai':
        from openai import OpenAI
        key    = api_key or os.environ.get('OPENAI_API_KEY')
        client = OpenAI(api_key=key)
        resp   = client.chat.completions.create(
            model    = 'gpt-4o',
            messages = [
                {'role': 'system', 'content': system},
                {'role': 'user',   'content': user}
            ]
        )
        raw = resp.choices[0].message.content

    else:
        return None

    # Strip markdown fences if present
    raw = raw.strip()
    if raw.startswith('```'):
        raw = raw.split('```')[1]
        if raw.startswith('json'):
            raw = raw[4:]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {'error': 'JSON parse failed', 'raw': raw[:500]}


def simulate_response(case: dict) -> dict:
    """
    Deterministic simulation based on extraction signals.
    Used for offline development and testing without API costs.

    Args:
        case: enriched case dict
    Returns:
        Simulated LLM response dict
    """
    ext   = case.get('predicted_extraction', {})
    gaps  = ext.get('documentation_gaps', [])
    fails = ext.get('has_prior_therapy_failure', False)
    spec  = ext.get('has_specialist_support', False)

    note_lower = case['note'].lower()
    safety     = any(kw in note_lower for kw in ['suicide', 'suicidal', 'rems', 'c-ssrs'])

    score = 0.50
    if fails:                  score += 0.20
    if spec:                   score += 0.15
    if ext.get('diagnoses'):   score += 0.08
    if ext.get('lab_values'):  score += 0.07
    if len(gaps) >= 2:         score -= 0.25
    if len(gaps) >= 4:         score -= 0.20
    score = max(0.0, min(1.0, score))

    if safety:
        decision = 'PENDING_REVIEW'
    elif score >= 0.65:
        decision = 'APPROVE'
    elif score <= 0.35:
        decision = 'DENY'
    else:
        decision = 'PENDING_REVIEW'

    rationale_map = {
        'APPROVE': (
            'Clinical documentation supports medical necessity per payer criteria. '
            'Step therapy requirements are satisfied with documented prior treatment failures. '
            'Specialist evaluation supports the requested treatment plan.'
        ),
        'DENY': (
            'The submitted documentation does not meet payer medical necessity criteria. '
            'Required step therapy has not been demonstrated, or necessary clinical '
            'documentation is absent or incomplete.'
        ),
        'PENDING_REVIEW': (
            'Case presents clinical complexity or safety considerations requiring '
            'human clinical review. Automated confidence is insufficient for a '
            'definitive determination at this threshold.'
        )
    }

    confidence_map = {
        'APPROVE':        round(min(0.93, 0.60 + score * 0.40), 2),
        'DENY':           round(min(0.91, 0.85 - score * 0.50), 2),
        'PENDING_REVIEW': 0.58
    }

    return {
        'decision':           decision,
        'confidence':         confidence_map[decision],
        'clinical_rationale': rationale_map[decision],
        'denial_reason':      'Does not meet medical necessity criteria' if decision == 'DENY' else None,
        'documentation_gaps': gaps,
        'recommended_action': {
            'APPROVE':        'Issue authorization. Notify provider and member.',
            'DENY':           'Issue denial letter with appeal rights. Peer-to-peer available upon request.',
            'PENDING_REVIEW': 'Route to clinical pharmacist or MD reviewer within 24 hours.'
        }[decision],
        'payer_criteria_cited': (
            case.get('retrieved_sources', [''])[0]
            if case.get('retrieved_sources')
            else 'General medical necessity criteria'
        )
    }


def run_inference(cases: list, system_prompt: str,
                  provider: str = 'simulate',
                  rate_limit_seconds: float = 0.5) -> list:
    """
    Run LLM inference over a batch of cases.

    Args:
        cases:               list of enriched case dicts
        system_prompt:       system prompt string
        provider:            'anthropic', 'openai', or 'simulate'
        rate_limit_seconds:  pause between API calls
    Returns:
        List of result dicts with decision, confidence, rationale, etc.
    """
    results = []
    for case in cases:
        user_prompt = build_user_prompt(case)

        if provider == 'simulate':
            response = simulate_response(case)
        else:
            response = call_llm(system_prompt, user_prompt, provider)
            if response is None:
                response = simulate_response(case)
            time.sleep(rate_limit_seconds)

        response['case_id']    = case['case_id']
        response['true_label'] = case['true_label']
        response['provider']   = provider
        results.append(response)

    return results
