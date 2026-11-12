from bisect import bisect_right


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
