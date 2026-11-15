// Redondear solo al presentar. El valor original se conserva para la clasificación.
export const egfrFormat = new Intl.NumberFormat('es-ES', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
  roundingMode: 'halfExpand',
  useGrouping: false,
})
