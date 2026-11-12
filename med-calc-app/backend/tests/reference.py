"""Referencia decimal por tramos, independiente del código de producción.

Transcripción de NIDDK, tablas 1 y 2 y ecuación eGFRcys 2012.
Las publicaciones y el estado de revisión constan en sources.json.
"""

from decimal import Decimal, localcontext


def calculate(method, age, sex, creatinine=None, cystatin=None):
    with localcontext() as context:
        context.prec = 60
        years = Decimal(str(age))
        female = sex == 'F'
        if sex not in ('F', 'M') or years < 18:
            raise ValueError('La referencia requiere un adulto y sexo F o M.')

        if method in ('creatinine', 'combined'):
            cr = Decimal(str(creatinine))
            if cr <= 0 or not cr.is_finite():
                raise ValueError('Creatinina fuera del dominio matemático.')
            knot = Decimal('0.7') if female else Decimal('0.9')
            ratio_cr = cr / knot
        if method in ('cystatin', 'combined'):
            cy = Decimal(str(cystatin))
            if cy <= 0 or not cy.is_finite():
                raise ValueError('Cistatina fuera del dominio matemático.')
            ratio_cy = cy / Decimal('0.8')

        if method == 'creatinine':
            if cr <= knot:
                power = Decimal('-0.241' if female else '-0.302')
            else:
                power = Decimal('-1.200')
            return Decimal(142) * ratio_cr ** power * Decimal('0.9938') ** years * Decimal('1.012' if female else '1')
        if method == 'cystatin':
            power = Decimal('-0.499' if cy <= Decimal('0.8') else '-1.328')
            return Decimal(133) * ratio_cy ** power * Decimal('0.996') ** years * Decimal('0.932' if female else '1')
        if method == 'combined':
            if cr <= knot:
                power_cr = Decimal('-0.219' if female else '-0.144')
            else:
                power_cr = Decimal('-0.544')
            power_cy = Decimal('-0.323' if cy <= Decimal('0.8') else '-0.778')
            return Decimal(135) * ratio_cr ** power_cr * ratio_cy ** power_cy * Decimal('0.9961') ** years * Decimal('0.963' if female else '1')
        raise ValueError('Ecuación desconocida.')


def category(value):
    value = Decimal(str(value))
    if value >= 90:
        return 'G1'
    if value >= 60:
        return 'G2'
    if value >= 45:
        return 'G3a'
    if value >= 30:
        return 'G3b'
    if value >= 15:
        return 'G4'
    return 'G5'
