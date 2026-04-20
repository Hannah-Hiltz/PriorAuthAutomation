"""
extractor.py
Clinical NLP entity extraction pipeline.
Extracts ICD-10 codes, CPT codes, lab values, medications,
and clinical signals from unstructured physician notes.

Usage:
    from src.extractor import ClinicalNLPExtractor, PAExtraction
    import spacy
    nlp = spacy.load('en_core_web_sm')
    extractor = ClinicalNLPExtractor(nlp)
    result = extractor.extract(case_dict)
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class PAExtraction:
    """Structured output of the NLP pipeline for one PA case."""
    case_id:                   str
    diagnoses:                 List[str]      = field(default_factory=list)
    procedures:                List[str]      = field(default_factory=list)
    drugs_failed:              List[str]      = field(default_factory=list)
    lab_values:                Dict[str, str] = field(default_factory=dict)
    clinical_entities:         List[str]      = field(default_factory=list)
    has_prior_therapy_failure: bool           = False
    has_specialist_support:    bool           = False
    documentation_gaps:        List[str]      = field(default_factory=list)


class ClinicalNLPExtractor:
    """
    Multi-strategy clinical entity extractor.

    Strategy 1 — scispaCy NER:   biomedical named entities
    Strategy 2 — Regex:          ICD-10, CPT, lab values, drugs failed
    Strategy 3 — Rule-based:     prior therapy failure, specialist support, doc gaps
    """

    ICD_RE = re.compile(r'\b([A-TV-Z][0-9]{2}\.?[0-9A-Z]{0,4})\b')
    CPT_RE = re.compile(r'\bCPT[:\s]*([0-9]{5})\b', re.IGNORECASE)

    LAB_RES = {
        'HbA1c':  re.compile(r'HbA1c[\s:]*([0-9.]+%?)',          re.IGNORECASE),
        'BMI':    re.compile(r'BMI[\s:]*([0-9.]+)',               re.IGNORECASE),
        'PHQ-9':  re.compile(r'PHQ-9[\s\w]*?([0-9]+)',            re.IGNORECASE),
        'DAS28':  re.compile(r'DAS28[\s\w]*?([0-9.]+)',           re.IGNORECASE),
        'PASI':   re.compile(r'PASI[\s:]*([0-9.]+)',              re.IGNORECASE),
        'EASI':   re.compile(r'EASI[\s:]*([0-9.]+)',              re.IGNORECASE),
        'DLQI':   re.compile(r'DLQI[\s:]*([0-9]+)',               re.IGNORECASE),
        'ECOG':   re.compile(r'ECOG[\s\w]*?([0-9])',              re.IGNORECASE),
        'PD-L1':  re.compile(r'PD-L1[\s\w]*?([0-9]+%)',          re.IGNORECASE),
        'eGFR':   re.compile(r'eGFR[\s:]*([0-9]+)',               re.IGNORECASE),
        'AHI':    re.compile(r'AHI[\s:]*([0-9.]+)',               re.IGNORECASE),
        'LDH':    re.compile(r'LDH[\s:]*([0-9.]+x?\s*ULN)',      re.IGNORECASE),
        'PANSS':  re.compile(r'PANSS[\s\w]*?([0-9]+)',            re.IGNORECASE),
        'C-SSRS': re.compile(r'C-SSRS[:\s]*([\w\s]+ideation)',   re.IGNORECASE),
    }

    FAILURE_RES = [
        r'failed\s+[\w\s]+',
        r'inadequate response',
        r'discontinued(?:\s+due to)?',
        r'no response',
        r'partial response',
        r'loss of response',
        r'intolerance',
        r'primary non.?response',
        r'secondary loss',
        r'hypoglycemic episodes',
    ]

    SPECIALIST_RES = [
        r'(endocrinolog|rheumatolog|oncolog|psychiatr|pulmonolog|dermatolog|neurolog|hematolog|gastroenterolog)[iy]\w*\s+(consult|recommend|support|approv|note)',
        r'tumor board',
        r'academic (medical center|center)',
        r'tertiary',
    ]

    GAP_PATTERNS = [
        ('no prior therapy documented',    r'no\s+(prior|documented|previous)\s+(treatment|therapy|trial)'),
        ('no specialist referral on file', r'no\s+(specialist|referral|pulmonolog|oncolog)\s+on file'),
        ('missing lab values',             r'not\s+(available|documented|on file)'),
        ('does not meet criteria',         r"does not meet\s+[\w\s]+criteria"),
        ('no ICS trial documented',        r'no\s+(?:prior\s+)?(?:ICS|inhaled corticosteroid)'),
        ('no genetic counseling',          r'no\s+genetic counseling'),
        ('FEV1 not documented',            r'FEV1 not documented'),
        ('eosinophil count absent',        r'eosinophil count not'),
    ]

    def __init__(self, nlp_model):
        self.nlp = nlp_model

    def extract(self, case: dict) -> PAExtraction:
        """Run full extraction pipeline on a single PA case dict."""
        note   = case['note']
        note_l = note.lower()
        result = PAExtraction(case_id=case['case_id'])

        # Strategy 1: NER
        doc = self.nlp(note)
        result.clinical_entities = list(set(
            ent.text.strip() for ent in doc.ents if len(ent.text.strip()) > 2
        ))

        # Strategy 2: Regex codes
        result.diagnoses  = list(set(self.ICD_RE.findall(note)))
        result.procedures = list(set(self.CPT_RE.findall(note)))

        # Strategy 2: Lab values
        for lab, pattern in self.LAB_RES.items():
            m = pattern.search(note)
            if m:
                result.lab_values[lab] = m.group(1).strip()

        # Strategy 2: Drugs failed
        failed_re = re.compile(
            r'(?:failed|discontinued|trial of|no response to)\s+'
            r'([a-z]+(?:[\s-][a-z]+)?(?:\s+[0-9]+\s*mg)?)',
            re.IGNORECASE
        )
        result.drugs_failed = list(set(
            m.group(1).strip() for m in failed_re.finditer(note)
        ))[:8]

        # Strategy 3: Boolean signals
        result.has_prior_therapy_failure = any(
            re.search(p, note_l) for p in self.FAILURE_RES
        )
        result.has_specialist_support = any(
            re.search(p, note_l) for p in self.SPECIALIST_RES
        )

        # Strategy 3: Documentation gaps
        for gap_label, pattern in self.GAP_PATTERNS:
            if re.search(pattern, note_l):
                result.documentation_gaps.append(gap_label)

        return result

    def extract_batch(self, cases: list) -> list:
        """Run extraction on a list of case dicts."""
        return [self.extract(c) for c in cases]

    def to_dict(self, ext: PAExtraction) -> dict:
        """Convert a PAExtraction to a JSON-serializable dict."""
        return {
            'diagnoses':               ext.diagnoses,
            'procedures':              ext.procedures,
            'drugs_failed':            ext.drugs_failed,
            'lab_values':              ext.lab_values,
            'clinical_entities':       ext.clinical_entities[:10],
            'has_prior_therapy_failure': ext.has_prior_therapy_failure,
            'has_specialist_support':    ext.has_specialist_support,
            'documentation_gaps':      ext.documentation_gaps,
        }
