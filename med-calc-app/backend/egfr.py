from bisect import bisect_right
from decimal import Decimal, localcontext
from math import isfinite


# KDIGO 2024, nomenclatura CGA (S126, PDF 11). Filas G, columnas A1–A3.
KDIGO_RISK_MATRIX = {
    'G1': ('low', 'moderate', 'high'),
    'G2': ('low', 'moderate', 'high'),
    'G3a': ('moderate', 'high', 'very_high'),
    'G3b': ('high', 'very_high', 'very_high'),
    'G4': ('very_high', 'very_high', 'very_high'),
    'G5': ('very_high', 'very_high', 'very_high'),
}


def albuminuria_category(acr_mg_g: float) -> str:
    # Tabla 3: 30 y 300 mg/g están incluidos en A2; cero no equivale a dato ausente.
    if not isfinite(acr_mg_g) or acr_mg_g < 0:
        raise ValueError('Introduce un CAC válido en mg/g, mayor o igual que cero y finito.')
    if acr_mg_g < 30:
        return 'A1'
    return 'A2' if acr_mg_g <= 300 else 'A3'


def kdigo_risk_level(gfr: str, albuminuria: str) -> str:
    return KDIGO_RISK_MATRIX[gfr][('A1', 'A2', 'A3').index(albuminuria)]


def creatinine_to_mg_dl(value: float) -> float:
    # NIDDK: µmol/L ÷ 88,4, sin redondear a un número fijo de decimales.
    # Decimal evita falsos avisos en límites exactos como 17,68 µmol/L = 0,2 mg/dL.
    with localcontext() as context:
        context.prec = 34
        return float(Decimal(str(value)) / Decimal('88.4'))


# CKD-EPI para adultos. Fuente: NIDDK, eGFR Equations for Adults.
# Creatinina sérica en mg/dL y cistatina C sérica en mg/L.
def creatinine_2021(age: int, female: bool, creatinine: float) -> float:
    ratio = creatinine / (0.7 if female else 0.9)
    exponent = -0.241 if female else -0.302
    return (
        142 * min(ratio, 1) ** exponent * max(ratio, 1) ** -1.200
        * 0.9938 ** age * (1.012 if female else 1)
    )


def cystatin_2012(age: int, female: bool, cystatin: float) -> float:
    ratio = cystatin / 0.8
    return (
        133 * min(ratio, 1) ** -0.499 * max(ratio, 1) ** -1.328
        * 0.996 ** age * (0.932 if female else 1)
    )


def combined_2021(age: int, female: bool, creatinine: float, cystatin: float) -> float:
    creatinine_ratio = creatinine / (0.7 if female else 0.9)
    cystatin_ratio = cystatin / 0.8
    exponent = -0.219 if female else -0.144
    return (
        135 * min(creatinine_ratio, 1) ** exponent * max(creatinine_ratio, 1) ** -0.544
        * min(cystatin_ratio, 1) ** -0.323 * max(cystatin_ratio, 1) ** -0.778
        * 0.9961 ** age * (0.963 if female else 1)
    )


def gfr_category(value: float) -> str:
    # Tabla 2 de KDIGO 2024. Aplicar al valor antes de redondearlo.
    limits = (15, 30, 45, 60, 90)
    categories = ('G5', 'G4', 'G3b', 'G3a', 'G2', 'G1')
    return categories[bisect_right(limits, value)]
