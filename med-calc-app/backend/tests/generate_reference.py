"""Generación explícita de referencias. Las pruebas habituales solo las leen."""

import json
from decimal import Decimal
from pathlib import Path

from tests.reference import calculate, category

DIRECTORY = Path(__file__).resolve().parent


def build_cases():
    cases = []
    for sex, knot in [('F', Decimal('0.7')), ('M', Decimal('0.9'))]:
        creatinines = [str(knot - Decimal('0.001')), str(knot), str(knot + Decimal('0.001'))]
        cystatins = ['0.799', '0.8', '0.801']
        for age in [18, 62, 100]:
            for cr in creatinines:
                cases.append(make_case('creatinine', age, sex, cr, None, 'punto de cambio de creatinina'))
            for cy in cystatins:
                cases.append(make_case('cystatin', age, sex, None, cy, 'punto de cambio de cistatina'))
            for cr in creatinines:
                for cy in cystatins:
                    cases.append(make_case('combined', age, sex, cr, cy, 'combinación de ramas'))
        for method in ['creatinine', 'cystatin', 'combined']:
            for cr, cy in [('0.1', '0.1'), ('16', '9')]:
                cases.append(make_case(method, 62, sex, cr if method != 'cystatin' else None,
                                       cy if method != 'creatinine' else None, 'extremo matemático'))

    observed = json.loads((DIRECTORY / 'evidence/nkf-observed.json').read_text(encoding='utf-8'))
    for anchor in observed['cases']:
        for method in ['creatinine', 'cystatin', 'combined']:
            case = make_case(method, anchor['age'], anchor['sex'][0],
                             anchor['cr'] if method != 'cystatin' else None,
                             anchor['cy'] if method != 'creatinine' else None,
                             'contraste externo NKF')
            case['external_evidence'] = anchor['id']
            cases.append(case)

    for index, case in enumerate(cases, start=1):
        case['id'] = f'N1-REF-{index:03d}'
    return cases


def make_case(method, age, sex, cr, cy, purpose):
    value = calculate(method, age, sex, cr, cy)
    return {
        'method': method, 'age': age, 'sex': sex,
        'creatinine_mg_dl': cr, 'cystatin_mg_l': cy,
        'expected_value': str(value), 'expected_category': category(value),
        'purpose': purpose, 'source_ids': ['NIDDK-ADULTS', 'INKER-2012' if method == 'cystatin' else 'INKER-2021', 'KDIGO-2024'],
    }


if __name__ == '__main__':
    path = DIRECTORY / 'data/reference-cases.json'
    if path.exists():
        raise SystemExit('Ya existe la referencia. Revisar y versionar explícitamente cualquier sustitución.')
    path.write_text(json.dumps(build_cases(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
