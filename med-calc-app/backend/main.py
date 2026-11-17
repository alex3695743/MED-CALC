from math import isfinite
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from egfr import (KDIGO_RISK_MATRIX, albuminuria_category, combined_2021, creatinine_2021,
                  creatinine_to_mg_dl, cystatin_2012, gfr_category, kdigo_risk_level)

app = FastAPI(title='MED-CALC', version='0.1.0')

Biomarker = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class EgfrInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    age: Annotated[int, Field(ge=18, le=120)]
    sex: Literal['F', 'M']
    method: Literal['creatinine', 'cystatin', 'combined']
    # SI precede a mg/dL para comprobar exclusión y ausencia en el validador de mg/dL.
    creatinine_umol_l: Biomarker | None = Field(default=None, validate_default=True)
    creatinine_mg_dl: Biomarker | None = Field(default=None, validate_default=True)
    cystatin_mg_l: Biomarker | None = Field(default=None, validate_default=True)
    acr_mg_g: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None = None

    @field_validator('creatinine_umol_l', 'creatinine_mg_dl', 'cystatin_mg_l')
    @classmethod
    def check_biomarker(cls, value: float | None, info: ValidationInfo) -> float | None:
        method = info.data.get('method')
        if method is None:
            return value
        creatinine = info.field_name != 'cystatin_mg_l'
        required = method in ('creatinine' if creatinine else 'cystatin', 'combined')
        label, unit = ('creatinina', 'µmol/L' if info.field_name == 'creatinine_umol_l' else 'mg/dL') if creatinine else ('cistatina C', 'mg/L')
        if info.field_name == 'creatinine_mg_dl' and info.data.get('creatinine_umol_l') is not None:
            if value is not None:
                raise ValueError('Introduce la creatinina en una sola unidad: mg/dL o µmol/L.')
            return value
        if info.field_name == 'creatinine_umol_l' and value is None:
            return value
        if required and value is None:
            units = 'mg/dL o µmol/L' if creatinine else unit
            raise ValueError(f'Introduce una {label} válida en {units}, mayor que cero.')
        if not required and value is not None:
            raise ValueError(f'La {label} en {unit} no corresponde al método seleccionado.')
        return value


class Estimate(BaseModel):
    value: float
    category: str
    equation: str


class InputWarning(BaseModel):
    field: Literal['creatinine_mg_dl', 'creatinine_umol_l', 'cystatin_mg_l']
    message: str


class Discrepancy(BaseModel):
    detected: bool
    absolute_difference: float
    threshold: float = 25
    different_categories: bool
    message: str | None = None


RiskLevel = Literal['low', 'moderate', 'high', 'very_high']


class KdigoAssessment(BaseModel):
    acr_mg_g: float
    gfr_category: str
    albuminuria_category: Literal['A1', 'A2', 'A3']
    risk_level: RiskLevel
    risk_label: str
    risk_matrix: dict[str, tuple[RiskLevel, RiskLevel, RiskLevel]]


class EgfrResult(Estimate):
    unit: Literal['mL/min/1.73 m²'] = 'mL/min/1.73 m²'
    comparisons: dict[Literal['creatinine', 'cystatin'], Estimate] = Field(default_factory=dict)
    warnings: list[InputWarning] = Field(default_factory=list)
    discrepancy: Discrepancy | None = None
    kdigo: KdigoAssessment | None = None


def assess_kdigo(gfr: str, acr_mg_g: float) -> KdigoAssessment:
    albuminuria = albuminuria_category(acr_mg_g)
    risk = kdigo_risk_level(gfr, albuminuria)
    labels = {'low': 'Riesgo bajo', 'moderate': 'Riesgo moderado',
              'high': 'Riesgo alto', 'very_high': 'Riesgo muy alto'}
    return KdigoAssessment(acr_mg_g=acr_mg_g, gfr_category=gfr, albuminuria_category=albuminuria,
                           risk_level=risk, risk_label=labels[risk], risk_matrix=KDIGO_RISK_MATRIX)


def compare_estimates(creatinine: Estimate, cystatin: Estimate) -> Discrepancy:
    # Regla operativa de Tomeu: comparar valores y categorías sin redondear.
    difference = abs(creatinine.value - cystatin.value)
    different_categories = creatinine.category != cystatin.category
    detected = difference >= 25 or different_categories
    return Discrepancy(
        detected=detected,
        absolute_difference=difference,
        different_categories=different_categories,
        message=('Existen diferencias relevantes entre las estimaciones; revise calidad analítica, '
                 'contexto clínico y factores no relacionados con la TFG.') if detected else None,
    )


def input_warnings(data: EgfrInput, creatinine: float | None) -> list[InputWarning]:
    # Límites operativos propuestos por Tomeu y adoptados para revisar entradas.
    si = data.creatinine_umol_l is not None
    limits = [
        ('creatinine_umol_l' if si else 'creatinine_mg_dl', creatinine, 0.2, 15, 'Creatinina',
         '17,68–1326 µmol/L' if si else '0,2–15 mg/dL'),
        ('cystatin_mg_l', data.cystatin_mg_l, 0.3, 8, 'Cistatina C', '0,3–8 mg/L'),
    ]
    warnings = []
    for field, value, lower, upper, label, interval in limits:
        if value is not None and (value < lower or value > upper):
            warnings.append(InputWarning(
                field=field,
                message=f'{label} fuera del intervalo de revisión de {interval}. Comprueba el dato y la unidad.',
            ))
    return warnings


def estimate(value: float, equation: str) -> Estimate:
    if not isfinite(value) or value <= 0:
        raise HTTPException(status_code=422, detail='Revisa la magnitud y las unidades de los datos.')
    return Estimate(value=value, category=gfr_category(value), equation=equation)


@app.exception_handler(RequestValidationError)
async def invalid_input(_request: Request, error: RequestValidationError) -> JSONResponse:
    messages = {
        'age': 'Introduce una edad entera de 18 a 120 años.',
        'sex': 'Selecciona el sexo utilizado por la ecuación: F o M.',
        'method': 'Selecciona un método válido: creatinina, cistatina C o combinada.',
        'creatinine_mg_dl': 'Introduce una creatinina válida en mg/dL, mayor que cero y finita.',
        'creatinine_umol_l': 'Introduce una creatinina válida en µmol/L, mayor que cero y finita.',
        'cystatin_mg_l': 'Introduce una cistatina C válida en mg/L, mayor que cero y finita.',
        'acr_mg_g': 'Introduce un CAC válido en mg/g, mayor o igual que cero y finito.',
    }
    errors = {}
    for issue in error.errors():
        field = issue['loc'][1] if len(issue['loc']) > 1 else 'request'
        if field in messages:
            # Estos ValueError proceden de la comprobación del método, sin datos del usuario.
            message = (str(issue['ctx']['error']) if issue['type'] == 'value_error'
                       else messages[field])
            errors[field] = message
        else:
            errors['request'] = ('La solicitud contiene campos no admitidos.' if issue['type'] == 'extra_forbidden'
                                 else 'Envía un objeto JSON válido con los datos para el cálculo.')
    return JSONResponse(status_code=422, content={
        'detail': ' '.join(errors.values()), 'errors': errors,
    })


@app.post('/api/egfr', response_model=EgfrResult)
def calculate_egfr(data: EgfrInput) -> EgfrResult:
    age, female = data.age, data.sex == 'F'
    creatinine = (creatinine_to_mg_dl(data.creatinine_umol_l)
                  if data.creatinine_umol_l is not None else data.creatinine_mg_dl)
    cystatin = data.cystatin_mg_l
    comparisons = {}
    try:
        if creatinine is not None and cystatin is not None:
            primary = estimate(combined_2021(age, female, creatinine, cystatin), 'CKD-EPI 2021 eGFRcr-cys')
            comparisons = {
                'creatinine': estimate(creatinine_2021(age, female, creatinine), 'CKD-EPI 2021 eGFRcr'),
                'cystatin': estimate(cystatin_2012(age, female, cystatin), 'CKD-EPI 2012 eGFRcys'),
            }
        elif creatinine is not None:
            primary = estimate(creatinine_2021(age, female, creatinine), 'CKD-EPI 2021 eGFRcr')
        else:
            primary = estimate(cystatin_2012(age, female, cystatin), 'CKD-EPI 2012 eGFRcys')
    except (OverflowError, ZeroDivisionError) as error:
        raise HTTPException(status_code=422, detail='Revisa la magnitud y las unidades de los datos.') from error

    discrepancy = compare_estimates(comparisons['creatinine'], comparisons['cystatin']) if comparisons else None
    return EgfrResult(**primary.model_dump(), comparisons=comparisons,
                      warnings=input_warnings(data, creatinine), discrepancy=discrepancy,
                      kdigo=assess_kdigo(primary.category, data.acr_mg_g) if data.acr_mg_g is not None else None)
