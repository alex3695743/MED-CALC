import Icon from './Icon.jsx'

const riskStyles = {
  low: { label: 'Bajo', className: 'bg-emerald-100 text-emerald-950' },
  moderate: { label: 'Moderado', className: 'bg-yellow-100 text-yellow-950' },
  high: { label: 'Alto', className: 'bg-orange-100 text-orange-950' },
  very_high: { label: 'Muy alto', className: 'bg-red-100 text-red-950' },
}
const albuminuriaColumns = [
  { code: 'A1', range: '<30' },
  { code: 'A2', range: '30–300' },
  { code: 'A3', range: '>300' },
]
const acrFormat = new Intl.NumberFormat('es-ES', { maximumSignificantDigits: 15 })

export default function KdigoAssessment({ assessment }) {
  const selectedRisk = riskStyles[assessment.risk_level]

  return (
    <section aria-labelledby="kdigo-assessment-title" className="mt-5 rounded-xl bg-white p-3.5 text-navy sm:p-4">
      <h3 id="kdigo-assessment-title" className="text-sm font-bold">Valoración conjunta de filtrado y albuminuria</h3>
      <div role="status" className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <p className="text-xl font-bold">{assessment.gfr_category} {assessment.albuminuria_category}</p>
        <p className={`rounded-lg px-2.5 py-1.5 text-sm font-bold ${selectedRisk.className}`}>{assessment.risk_label}</p>
      </div>
      <p className="mt-2 text-xs text-slate-600">CAC introducido: {acrFormat.format(assessment.acr_mg_g)} mg/g. Categorías asignadas sin redondear.</p>
      <table className="mt-3 w-full table-fixed border-separate border-spacing-1 text-center text-xs">
        <caption className="mb-2 text-left text-xs font-semibold text-slate-700">Matriz KDIGO G×A · CAC en mg/g</caption>
        <thead>
          <tr>
            <th scope="col" className="w-12 pb-1 text-left">Filtrado</th>
            {albuminuriaColumns.map(({ code, range }) => (
              <th key={code} scope="col" className="pb-1">{code}<span className="block font-normal text-slate-600">{range}</span></th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Object.entries(assessment.risk_matrix).map(([gfr, risks]) => (
            <tr key={gfr}>
              <th scope="row" className="py-2 text-left">{gfr}</th>
              {risks.map((risk, index) => {
                const albuminuria = albuminuriaColumns[index].code
                const selected = assessment.gfr_category === gfr && assessment.albuminuria_category === albuminuria
                return (
                  <td key={albuminuria} aria-label={`${gfr} ${albuminuria}: riesgo ${riskStyles[risk].label.toLowerCase()}${selected ? '. Resultado seleccionado' : ''}`}
                    className={`rounded-md px-1 py-2 ${riskStyles[risk].className} ${selected ? 'font-bold ring-2 ring-navy ring-inset' : ''}`}>
                    {selected && <Icon name="check" className="mr-0.5 inline-block size-3" />}{riskStyles[risk].label}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-xs leading-relaxed text-slate-600">Riesgo orientativo según el cruce G×A; no es una probabilidad individual ni un diagnóstico. La clasificación completa de ERC también considera la causa y la cronicidad de al menos 3 meses.</p>
      {assessment.risk_level === 'low' && (
        <p className="mt-2 text-xs leading-relaxed text-slate-600">G1 o G2 con A1 solo queda fuera de los criterios de ERC si no hay otros marcadores de daño renal.</p>
      )}
      <a href="https://kdigo.org/wp-content/uploads/2024/03/KDIGO-2024-CKD-Guideline.pdf#page=11" className="mt-3 inline-block text-xs font-semibold text-teal underline underline-offset-4">KDIGO 2024 · Matriz de filtrado y albuminuria</a>
    </section>
  )
}
