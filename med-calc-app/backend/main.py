from math import isfinite
from typing import Annotated, Literal, Self

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator

from egfr import combined_2021, creatinine_2021, cystatin_2012, gfr_category

app = FastAPI(title='MED-CALC', version='0.1.0')

Biomarker = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class EgfrInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    age: Annotated[int, Field(ge=18)]
    sex: Literal['F', 'M']
    method: Literal['creatinine', 'cystatin', 'combined']
    creatinine_mg_dl: Biomarker | None = None
    cystatin_mg_l: Biomarker | None = None

    @model_validator(mode='after')
    def check_biomarkers(self) -> Self:
        needs_creatinine = self.method in ('creatinine', 'combined')
        needs_cystatin = self.method in ('cystatin', 'combined')
        if needs_creatinine != (self.creatinine_mg_dl is not None):
            raise ValueError('La creatinina debe corresponder al método seleccionado.')
        if needs_cystatin != (self.cystatin_mg_l is not None):
            raise ValueError('La cistatina C debe corresponder al método seleccionado.')
        return self


class Estimate(BaseModel):
    value: float
    category: str
    equation: str


class EgfrResult(Estimate):
    unit: Literal['mL/min/1.73 m²'] = 'mL/min/1.73 m²'
    comparisons: dict[Literal['creatinine', 'cystatin'], Estimate] = Field(default_factory=dict)


def estimate(value: float, equation: str) -> Estimate:
    if not isfinite(value) or value <= 0:
        raise HTTPException(status_code=422, detail='Revisa la magnitud y las unidades de los datos.')
    return Estimate(value=value, category=gfr_category(value), equation=equation)


@app.exception_handler(RequestValidationError)
async def invalid_input(_request: Request, _error: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={'detail': 'Revisa los datos y el método de cálculo.'})


@app.post('/api/egfr', response_model=EgfrResult)
def calculate_egfr(data: EgfrInput) -> EgfrResult:
    age, female = data.age, data.sex == 'F'
    creatinine, cystatin = data.creatinine_mg_dl, data.cystatin_mg_l
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

    return EgfrResult(**primary.model_dump(), comparisons=comparisons)
