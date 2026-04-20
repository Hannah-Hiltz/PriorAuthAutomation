"""
rule_engine.py
Heuristic rule engine that pre-scores PA cases on medical necessity signals
before LLM classification. Reduces LLM hallucination by providing structured
signal anchors in the prompt.

Usage:
    from src.rule_engine import PARuleEngine
    engine = PARuleEngine()
    result = engine.evaluate(extraction, case)
"""

from dataclasses import dataclass, field
from typing import List, Dict
import re


@dataclass
class RuleEngineResult:
    """Output of the rule engine for one PA case."""
    case_id:       str
    score:         float
    rule_signals:  Dict[str, bool] = field(default_factory=dict)
    decision_hint: str             = 'PENDING_REVIEW'
    reasoning:     List[str]       = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'case_id':       self.case_id,
            'score':         self.score,
            'rule_signals':  self.rule_signals,
            'decision_hint': self.decision_hint,
            'reasoning':     self.reasoning,
        }


class PARuleEngine:
    """
    Weighted scoring model encoding common payer medical necessity criteria.

    Scoring:
        score >= 0.65  →  APPROVE hint
        score <= 0.35  →  DENY hint
        between        →  PENDING_REVIEW (routes to human)

    Positive signals push toward APPROVE; negative signals push toward DENY.
    Safety flags always route to PENDING_REVIEW regardless of score.
    """

    APPROVE_THRESHOLD = 0.65
    DENY_THRESHOLD    = 0.35

    SAFETY_KEYWORDS = ['suicide', 'suicidal', 'rems', 'c-ssrs']
    SEVERITY_TERMS  = ['metastatic', 'stage iv', 'severe', 'treatment-resistant', 'nstemi']

    def evaluate(self, ext, case: dict) -> RuleEngineResult:
        """
        Evaluate a single PA case using extraction signals.

        Args:
            ext:  PAExtraction dataclass instance
            case: original case dict
        Returns:
            RuleEngineResult with score, hint, and reasoning
        """
        score     = 0.50
        signals   = {}
        reasoning = []
        note      = case['note'].lower()

        # ── Positive signals ──────────────────────────────────────────────────

        signals['prior_therapy_failure'] = ext.has_prior_therapy_failure
        if ext.has_prior_therapy_failure:
            score += 0.20
            reasoning.append('Step therapy: prior treatment failure documented')

        signals['specialist_support'] = ext.has_specialist_support
        if ext.has_specialist_support:
            score += 0.15
            reasoning.append('Specialist consulted and supports treatment plan')

        signals['has_diagnosis_codes'] = len(ext.diagnoses) > 0
        if ext.diagnoses:
            score += 0.10
            reasoning.append(f'ICD-10 codes documented: {", ".join(ext.diagnoses)}')

        signals['has_labs'] = len(ext.lab_values) > 0
        if ext.lab_values:
            score += 0.10
            reasoning.append(f'Objective lab values present: {ext.lab_values}')

        has_severity = any(t in note for t in self.SEVERITY_TERMS)
        signals['high_severity'] = has_severity
        if has_severity:
            score += 0.05
            reasoning.append('High-severity diagnosis documented')

        # ── Negative signals ──────────────────────────────────────────────────

        no_prior = any(f in ext.documentation_gaps for f in ['no prior therapy documented'])
        signals['missing_prior_therapy'] = no_prior
        if no_prior:
            score -= 0.25
            reasoning.append('Step therapy NOT met: no prior treatment failure documented')

        missing_docs = any(re.search(t, note) for t in [
            r'not available', r'not documented', r'not on file'
        ])
        signals['missing_documentation'] = missing_docs
        if missing_docs:
            score -= 0.20
            reasoning.append('Required documentation is missing')

        not_criteria = 'does not meet criteria' in ext.documentation_gaps
        signals['fails_criteria'] = not_criteria
        if not_criteria:
            score -= 0.30
            reasoning.append('Explicitly does not meet payer/guideline criteria')

        no_referral = 'no specialist referral on file' in ext.documentation_gaps
        signals['no_specialist'] = no_referral
        if no_referral:
            score -= 0.15
            reasoning.append('Specialist referral/consult not on file')

        # ── Safety escalation ─────────────────────────────────────────────────

        safety = any(kw in note for kw in self.SAFETY_KEYWORDS)
        signals['safety_escalation'] = safety
        if safety:
            reasoning.append('Safety/REMS flag — escalate to clinical pharmacist')

        # ── Clamp and decide ──────────────────────────────────────────────────

        score = max(0.0, min(1.0, score))

        if safety:
            decision_hint = 'PENDING_REVIEW'
        elif score >= self.APPROVE_THRESHOLD:
            decision_hint = 'APPROVE'
        elif score <= self.DENY_THRESHOLD:
            decision_hint = 'DENY'
        else:
            decision_hint = 'PENDING_REVIEW'

        return RuleEngineResult(
            case_id       = case['case_id'],
            score         = round(score, 3),
            rule_signals  = signals,
            decision_hint = decision_hint,
            reasoning     = reasoning,
        )

    def evaluate_batch(self, extractions: list, cases: list) -> list:
        """
        Evaluate a batch of cases.

        Args:
            extractions: list of PAExtraction instances
            cases:       list of case dicts
        Returns:
            List of RuleEngineResult instances
        """
        return [
            self.evaluate(ext, case)
            for ext, case in zip(extractions, cases)
        ]
