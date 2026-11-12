import { useEffect, useRef, useState } from 'react'
import Icon from '../components/Icon.jsx'

const methods = [
  { id: 'creatinine', label: 'Creatinina', equation: 'CKD-EPI 2021', markers: ['creatinine'] },
  { id: 'cystatin', label: 'Cistatina C', equation: 'CKD-EPI 2012', markers: ['cystatin'] },
  { id: 'combined', label: 'Combinada', equation: 'CKD-EPI 2021', markers: ['creatinine', 'cystatin'] },
]

const markers = {
  creatinine: { label: 'Creatinina sérica', unit: 'mg/dL', placeholder: 'Ej. 1,2' },
  cystatin: { label: 'Cistatina C sérica', unit: 'mg/L', placeholder: 'Ej. 0,9' },
}

// Tramos de filtrado de la tabla 2 de KDIGO 2024.
const categories = [
  { code: 'G1', range: '≥90', label: 'Filtrado normal o elevado' },
  { code: 'G2', range: '60–<90', label: 'Filtrado levemente disminuido' },
  { code: 'G3a', range: '45–<60', label: 'Filtrado de leve a moderadamente disminuido' },
  { code: 'G3b', range: '30–<45', label: 'Filtrado de moderada a gravemente disminuido' },
  { code: 'G4', range: '15–<30', label: 'Filtrado gravemente disminuido' },
  { code: 'G5', range: '<15', label: 'Filtrado en rango de fallo renal' },
]

const egfrFormat = new Intl.NumberFormat('es-ES', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const initialValues = { age: '', sex: '', creatinine: '', cystatin: '' }
const inputClasses = 'min-h-12 w-full rounded-xl border border-line bg-white px-3.5 text-base text-ink placeholder:text-slate-500 focus:border-teal focus:outline-offset-2 aria-invalid:border-red-600'

function validate(values, method) {
  const errors = {}
  const age = values.age.trim()

  if (!/^\d+$/.test(age) || !Number.isSafeInteger(Number(age))) {
    errors.age = 'Introduce la edad en años cumplidos.'
  } else if (Number(age) < 18) {
    errors.age = 'Esta calculadora es para personas de 18 años o más.'
  }

  if (!['F', 'M'].includes(values.sex)) {
    errors.sex = 'Selecciona el sexo utilizado por la ecuación.'
  }

  for (const marker of method.markers) {
    const value = values[marker].trim()
    const number = Number(value.replace(',', '.'))
    if (!/^(?:\d+(?:[.,]\d+)?|[.,]\d+)$/.test(value) || !Number.isFinite(number) || number <= 0) {
      errors[marker] = `Introduce un valor mayor que cero en ${markers[marker].unit}.`
    }
  }

  return errors
}

function Field({ name, label, unit, error, children }) {
  return (
    <div className="min-w-0">
      <label htmlFor={name} className="mb-2 block text-sm font-bold text-navy">{label}</label>
      <div className="relative">
        {children}
        {unit && (
          <span id={`${name}-unit`} className="pointer-events-none absolute inset-y-0 right-3.5 flex items-center text-sm font-medium text-slate-600">
            {unit}
          </span>
        )}
      </div>
      {error && <p id={`${name}-error`} className="mt-1.5 text-sm text-red-700">{error}</p>}
    </div>
  )
}

function CalculatorForm({ method, pending, onMethodChange, onClear, onCalculate }) {
  const [values, setValues] = useState(initialValues)
  const [errors, setErrors] = useState({})

  function changeValue(event) {
    const { name, value } = event.target
    setValues((previous) => ({ ...previous, [name]: value }))
    setErrors((previous) => ({ ...previous, [name]: undefined }))
    onClear()
  }

  function changeMethod(option) {
    setErrors(({ age, sex }) => ({ age, sex }))
    onMethodChange(option)
  }

  function submit(event) {
    event.preventDefault()
    const form = event.currentTarget
    const nextErrors = validate(values, method)
    setErrors(nextErrors)

    const [firstInvalid] = Object.keys(nextErrors)
    if (firstInvalid) {
      onClear()
      requestAnimationFrame(() => form.elements.namedItem(firstInvalid)?.focus())
      return
    }

    onCalculate(values)
  }

  function reset(event) {
    event.preventDefault()
    setValues(initialValues)
    setErrors({})
    onClear()
    event.currentTarget.elements.namedItem('age')?.focus()
  }

  function fieldProps(name, unit) {
    const descriptions = [unit && `${name}-unit`, errors[name] && `${name}-error`].filter(Boolean)
    return {
      id: name,
      name,
      value: values[name],
      onChange: changeValue,
      required: true,
      'aria-invalid': Boolean(errors[name]),
      'aria-describedby': descriptions.join(' ') || undefined,
    }
  }

  return (
    <form noValidate onSubmit={submit} onReset={reset} aria-labelledby="form-title"
      className="rounded-2xl border border-line bg-white p-5 shadow-card sm:p-7">
      <h2 id="form-title" className="text-xl font-bold tracking-tight text-navy">Datos para el cálculo</h2>
      <p className="mt-1 text-sm text-slate-600">Selecciona los marcadores disponibles e introduce sus valores.</p>

      <fieldset className="mt-6">
        <legend className="mb-2.5 text-sm font-bold text-navy">Método de estimación</legend>
        <div className="grid gap-2 sm:grid-cols-3">
          {methods.map((option) => (
            <label key={option.id} className="relative cursor-pointer">
              <input type="radio" name="method" value={option.id} checked={option.id === method.id}
                onChange={() => changeMethod(option)} className="peer sr-only" />
              <span className="flex min-h-13 items-center gap-2.5 rounded-xl border border-line px-3 py-2.5 transition hover:border-teal peer-checked:border-teal peer-checked:bg-aqua peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-teal sm:flex-col sm:items-start sm:gap-1">
                <span className="text-sm font-bold text-navy">{option.label}</span>
                <span className="text-xs text-slate-600">{option.equation}</span>
              </span>
              {option.id === method.id && <Icon name="check" className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-teal sm:top-3 sm:translate-y-0" />}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="mt-6 grid gap-x-4 gap-y-4 sm:grid-cols-2">
        <Field name="age" label="Edad" unit="años" error={errors.age}>
          <input {...fieldProps('age', 'años')} inputMode="numeric" placeholder="Ej. 62" className={`${inputClasses} pr-17`} />
        </Field>
        <Field name="sex" label="Sexo según la ecuación" error={errors.sex}>
          <select {...fieldProps('sex')} className={`${inputClasses} appearance-none pr-10`}>
            <option value="" disabled>Selecciona una opción</option>
            <option value="F">Mujer</option>
            <option value="M">Hombre</option>
          </select>
          <Icon name="chevron" className="pointer-events-none absolute top-1/2 right-3.5 size-4 -translate-y-1/2 text-slate-600" />
        </Field>
        {method.markers.map((name) => {
          const { label, unit, placeholder } = markers[name]
          return (
            <Field key={name} name={name} label={label} unit={unit} error={errors[name]}>
              <input {...fieldProps(name, unit)} inputMode="decimal" placeholder={placeholder} className={`${inputClasses} pr-20`} />
            </Field>
          )
        })}
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-line pt-5">
        <button type="submit" disabled={pending} className="inline-flex min-h-12 items-center justify-center gap-3 rounded-xl bg-navy px-5 text-sm font-bold text-white transition hover:bg-[#0c293e] disabled:opacity-60">
          {pending ? 'Calculando…' : 'Calcular eGFR'} <Icon name="arrow" className="size-4" />
        </button>
        <button type="reset" className="min-h-12 rounded-xl px-4 text-sm font-bold text-navy transition hover:bg-mist">Limpiar</button>
      </div>
    </form>
  )
}

function CategoryScale({ category, hasResult }) {
  const guideRef = useRef(null)

  return (
    <div className="mt-5">
      <div className="flex flex-wrap items-center justify-between gap-x-3">
        <h3 id="egfr-scale-title" className="text-sm font-semibold text-slate-200">Categoría de filtrado KDIGO</h3>
        <button type="button" aria-haspopup="dialog" aria-controls="egfr-kdigo-guide"
          onClick={() => guideRef.current.showModal()}
          className="inline-flex min-h-11 items-center gap-1.5 rounded-lg text-sm font-semibold text-[#aeeae3] underline underline-offset-4 hover:text-white focus-visible:outline-[#9ee6de]">
          <Icon name="info" className="size-4" /> Sobre KDIGO
        </button>
      </div>
      <dialog id="egfr-kdigo-guide" ref={guideRef} aria-labelledby="egfr-kdigo-title"
        className="fixed inset-0 m-auto max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-sm overflow-y-auto rounded-2xl border border-line bg-white p-5 text-ink shadow-xl backdrop:bg-navy/50 sm:p-6">
        <h3 id="egfr-kdigo-title" className="text-lg font-bold text-navy">¿Qué significa la categoría KDIGO?</h3>
        <div className="mt-3 space-y-2 text-sm leading-relaxed text-slate-700">
          <p>La escala agrupa el filtrado glomerular estimado en tramos de <strong>G1 a G5</strong>. Por ejemplo, <strong>G3a</strong> corresponde a un filtrado de 45 a menos de 60 mL/min/1,73 m².</p>
          <p>Para clasificar la enfermedad renal crónica, KDIGO combina la <strong>causa</strong>, la <strong>categoría de filtrado</strong> y la <strong>categoría de albuminuria</strong>. Para establecer que una alteración es crónica se requiere evidencia de al menos 3 meses de duración.</p>
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <a href="https://kdigo.org/wp-content/uploads/2024/03/KDIGO-2024-CKD-Guideline.pdf#page=22"
            className="text-sm font-semibold text-teal underline underline-offset-4">Guía KDIGO 2024</a>
          <form method="dialog">
            <button className="min-h-11 rounded-xl bg-navy px-4 text-sm font-bold text-white hover:bg-[#0c293e]">Cerrar</button>
          </form>
        </div>
      </dialog>
      <ul role="list" aria-labelledby="egfr-scale-title" className="mt-2 grid grid-cols-6 gap-1 text-center">
        {categories.map(({ code, range }) => (
          <li key={code} aria-current={category?.code === code ? 'true' : undefined}
            className="group">
            <span className="block rounded-md bg-[#365872] py-1.5 text-xs font-semibold text-white group-aria-[current=true]:bg-[#aeeae3] group-aria-[current=true]:font-bold group-aria-[current=true]:text-navy">
              {code}
            </span>
            <span className="mt-1 block text-[11px] text-slate-200">{range}</span>
          </li>
        ))}
      </ul>
      <div aria-live="polite" className="mt-3 text-sm">
        {category && (
          <>
            <p className="font-semibold text-[#aeeae3]">{category.code} · {category.label}</p>
            <p className="mt-1 text-xs text-slate-200">Categoría asignada con el valor sin redondear.</p>
          </>
        )}
        {hasResult && !category && <p className="text-slate-200">Categoría de filtrado no disponible.</p>}
      </div>
    </div>
  )
}

export function ResultPanel({ method, pending, error, panelRef, result }) {
  const combined = method.id === 'combined'
  const hasResult = Number.isFinite(result?.value) && result.value >= 0
  const category = hasResult ? categories.find(({ code }) => code === result.category) : undefined
  const value = hasResult ? egfrFormat.format(result.value) : '—'
  const status = pending ? 'Calculando…' : 'Pendiente de cálculo'

  return (
    <section aria-labelledby="result-title" className="self-start overflow-hidden rounded-2xl border border-navy bg-navy text-white shadow-card">
      <div className="relative isolate p-5 sm:p-6">
        <div aria-hidden="true" className="pointer-events-none absolute -top-21 -right-13 -z-10 size-60 rounded-full border border-white/10 shadow-[0_0_0_28px_rgba(255,255,255,.035),0_0_0_56px_rgba(255,255,255,.025)]" />
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="result-title" className="flex items-center gap-2.5 text-lg font-bold">
            <Icon name="pulse" className="size-5 text-[#9ee6de]" /> Resultado estimado
          </h2>
          <span className="rounded-full border border-white/20 bg-white/10 px-2.5 py-1 text-xs text-slate-100">
            {hasResult ? 'Cálculo completado' : status}
          </span>
        </div>
        <div className="mt-6 rounded-xl border border-white/15 bg-white/8 px-4 py-4">
          <p className="text-xs font-semibold tracking-wide text-[#b4e7e3]">{method.equation} · {method.label}</p>
          <p className="mt-1 text-sm text-slate-200">Tasa de filtrado glomerular estimada (eGFR)</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-4xl leading-none font-semibold tabular-nums" aria-label={hasResult ? undefined : 'Sin valor'}>{value}</span>
            <span className="text-sm text-slate-200">mL/min/1,73 m²</span>
          </div>
          {combined && <p className="mt-3 text-xs font-medium text-[#b4e7e3]">Estimación preferente cuando se dispone de ambos marcadores.</p>}
        </div>
        {combined && (
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {methods.slice(0, 2).map((option) => {
              const comparison = result?.comparisons?.[option.id]
              return (
                <div key={option.id} className="rounded-lg border border-white/15 px-3 py-2.5">
                  <p className="text-xs font-medium text-slate-200">{option.label} · {option.equation}</p>
                  <p className="mt-1 text-sm font-semibold">
                    {comparison ? egfrFormat.format(comparison.value) : '—'}{' '}
                    <span className="text-xs font-normal text-slate-200">mL/min/1,73 m²</span>
                  </p>
                </div>
              )
            })}
          </div>
        )}
        <CategoryScale category={category} hasResult={hasResult} />
      </div>
      <div ref={panelRef} tabIndex={-1} className="flex scroll-mt-4 items-start gap-2.5 border-t border-white/15 bg-[#0d2a40] px-5 py-4 text-sm text-slate-200 outline-offset-[-4px] focus-visible:outline-[#9ee6de] sm:px-6">
        <Icon name="info" className="mt-0.5 size-4 shrink-0 text-[#9ee6de]" />
        {hasResult ? (
          <p>Para valorar enfermedad renal crónica se necesita evidencia de alteraciones durante al menos 3 meses. También se tienen en cuenta hallazgos como la albuminuria.{' '}
            <a href="https://kdigo.org/wp-content/uploads/2024/03/KDIGO-2024-CKD-Guideline.pdf#page=22"
              className="font-semibold text-[#aeeae3] underline underline-offset-2">Guía KDIGO 2024</a>
          </p>
        ) : <p role={error ? 'alert' : 'status'}>{error || (pending ? 'Calculando el filtrado estimado…' : 'Introduce los datos y pulsa Calcular eGFR.')}</p>}
      </div>
    </section>
  )
}

function AboutCalculator() {
  return (
    <section id="ficha" aria-labelledby="about-title" className="mt-8 scroll-mt-4 rounded-2xl border border-line bg-white p-5 shadow-card sm:p-7">
      <h2 id="about-title" className="flex items-center gap-2.5 text-xl font-bold tracking-tight text-navy">
        <Icon name="book" className="size-5 text-teal" /> Ficha de la calculadora
      </h2>
      <div className="mt-3 divide-y divide-line">
        <details className="group">
          <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-2 py-3 text-sm font-bold text-navy">
            Población y alcance <Icon name="chevron" className="size-4 shrink-0 text-teal group-open:rotate-180" />
          </summary>
          <p className="pb-4 text-sm leading-relaxed text-slate-700">La ficha recoge tres ecuaciones CKD-EPI para personas adultas. Cada ecuación utiliza la edad, el sexo y el marcador o los marcadores correspondientes.</p>
        </details>
        <details className="group">
          <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-2 py-3 text-sm font-bold text-navy">
            Unidades y limitaciones <Icon name="chevron" className="size-4 shrink-0 text-teal group-open:rotate-180" />
          </summary>
          <p className="pb-4 text-sm leading-relaxed text-slate-700">Introduce creatinina sérica estandarizada en mg/dL y cistatina C estandarizada en mg/L. La eGFR se expresa en mL/min/1,73 m². Un valor aislado es insuficiente para diagnosticar enfermedad renal crónica.</p>
        </details>
        <details className="group">
          <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-2 py-3 text-sm font-bold text-navy">
            ¿Qué es la albuminuria? <Icon name="chevron" className="size-4 shrink-0 text-teal group-open:rotate-180" />
          </summary>
          <div className="space-y-2 pb-4 text-sm leading-relaxed text-slate-700">
            <p>La <strong>albúmina</strong> es una proteína de la sangre. Cuando aparece en exceso en la orina se habla de <strong>albuminuria</strong>. Se suele evaluar con el <strong>cociente albúmina/creatinina en orina (CAC o ACR)</strong>.</p>
            <p>La eGFR estima cuánto filtran los riñones. El CAC aporta información sobre posibles signos de daño renal, incluso si el filtrado está conservado. Según KDIGO, un CAC de <strong>30 mg/g o más</strong> que persiste durante al menos 3 meses es un criterio de enfermedad renal crónica.</p>
            <p><a href="https://kdigo.org/wp-content/uploads/2024/03/KDIGO-2024-CKD-Guideline.pdf#page=22" className="font-semibold text-teal underline underline-offset-4">Criterios de la guía KDIGO 2024</a></p>
          </div>
        </details>
        <details className="group">
          <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-2 py-3 text-sm font-bold text-navy">
            Publicaciones originales <Icon name="chevron" className="size-4 shrink-0 text-teal group-open:rotate-180" />
          </summary>
          <ul className="space-y-2 pb-4 text-sm">
            <li><a href="https://pubmed.ncbi.nlm.nih.gov/34554658/" className="inline-flex items-center gap-1.5 font-semibold text-teal underline underline-offset-4">Inker et al. (2021) · Creatinina y ecuación combinada <Icon name="external" className="size-4 shrink-0" /></a></li>
            <li><a href="https://pubmed.ncbi.nlm.nih.gov/22762315/" className="inline-flex items-center gap-1.5 font-semibold text-teal underline underline-offset-4">Inker et al. (2012) · Cistatina C <Icon name="external" className="size-4 shrink-0" /></a></li>
          </ul>
        </details>
      </div>
    </section>
  )
}

export default function EgfrPage() {
  const [method, setMethod] = useState(methods[0])
  const [calculation, setCalculation] = useState({})
  const requestRef = useRef(null)
  const panelRef = useRef(null)

  useEffect(() => () => requestRef.current?.abort(), [])

  function clearResult() {
    requestRef.current?.abort()
    setCalculation({})
  }

  function changeMethod(option) {
    setMethod(option)
    clearResult()
  }

  async function calculate(values) {
    requestRef.current?.abort()
    const request = new AbortController()
    requestRef.current = request
    setCalculation({ pending: true })

    const body = { age: Number(values.age), sex: values.sex, method: method.id }
    if (method.markers.includes('creatinine')) body.creatinine_mg_dl = Number(values.creatinine.replace(',', '.'))
    if (method.markers.includes('cystatin')) body.cystatin_mg_l = Number(values.cystatin.replace(',', '.'))

    try {
      const response = await fetch('/api/egfr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: request.signal,
      })
      if (response.status === 422) {
        if (!request.signal.aborted) setCalculation({ error: 'El servidor no pudo calcular el filtrado. Revisa los datos y sus unidades.' })
      } else {
        if (!response.ok) throw new Error('Servicio no disponible')
        const result = await response.json()
        if (!request.signal.aborted) setCalculation({ result })
      }
    } catch {
      if (!request.signal.aborted) setCalculation({ error: 'El servicio de cálculo no está disponible. Inténtalo de nuevo.' })
    }

    requestAnimationFrame(() => {
      if (!request.signal.aborted) panelRef.current?.focus()
    })
  }

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#contenido" className="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-10 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2">Saltar al contenido</a>
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3.5 sm:px-7">
          <a href="#contenido" className="inline-flex items-center gap-2.5 rounded-lg">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-navy text-white"><Icon name="pulse" /></span>
            <span className="leading-tight">
              <span className="block font-bold tracking-tight text-navy">MED-CALC</span>
              <span className="block text-xs text-slate-600">Calculadoras clínicas</span>
            </span>
          </a>
          <a href="#ficha" className="inline-flex min-h-10 items-center gap-1.5 rounded-lg px-2 text-sm font-semibold text-navy hover:bg-mist">
            <Icon name="book" className="size-4 text-teal" /> Ficha técnica
          </a>
        </div>
      </header>

      <main id="contenido" className="mx-auto w-full max-w-6xl flex-1 px-4 pt-8 pb-10 sm:px-7 sm:pt-10">
        <div className="mb-7 sm:mb-8">
          <div className="mb-3 flex flex-wrap items-center gap-2.5">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-aqua px-3 py-1 text-xs font-bold text-teal">
              <Icon name="droplet" className="size-3.5" /> Nefrología
            </span>
            <span className="text-xs font-semibold text-slate-600">CKD-EPI · Adultos</span>
          </div>
          <h1 className="font-serif text-[clamp(2rem,5.2vw,3.25rem)] leading-[1.12] font-bold tracking-tight text-navy">Filtrado glomerular estimado</h1>
          <p className="mt-3 max-w-2xl text-base leading-relaxed text-slate-600">Calculadora de eGFR a partir de creatinina, cistatina C o ambos marcadores.</p>
        </div>

        <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]">
          <CalculatorForm method={method} pending={calculation.pending} onMethodChange={changeMethod}
            onClear={clearResult} onCalculate={calculate} />
          <ResultPanel method={method} panelRef={panelRef} {...calculation} />
        </div>

        <AboutCalculator />
      </main>

      <footer className="border-t border-line bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-x-5 gap-y-2 px-4 py-4 text-xs text-slate-600 sm:px-7">
          <span className="inline-flex items-center gap-1.5 font-bold text-navy"><Icon name="flask" className="size-4 text-teal" /> MED-CALC · Prototipo académico</span>
          <span>Uso académico. Evita introducir datos identificativos.</span>
        </div>
      </footer>
    </div>
  )
}
