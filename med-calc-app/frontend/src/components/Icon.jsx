const paths = {
  pulse: 'M2 12h5l3-7 4 14 3-7h5',
  droplet: 'M12 2.8c3.3 4.8 6.8 8 6.8 12.1a6.8 6.8 0 1 1-13.6 0c0-4.1 3.5-7.3 6.8-12.1Z M9 15a3 3 0 0 0 3 3',
  info: 'M12 11v5m0-8h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z',
  arrow: 'M4 12h15m-6-6 6 6-6 6',
  chevron: 'm6 9 6 6 6-6',
  book: 'M4 19V5a2 2 0 0 1 2-2h14v18H6a2 2 0 1 1 0-4h14M8 7h8m-8 4h5',
  external: 'M13 5h6v6m0-6-9 9m6-1v6H5V8h6',
  check: 'm5 12 4 4L19 6',
  flask: 'M9 3h6m-5 0v7l-5.5 8a1.5 1.5 0 0 0 1.3 2.3h12.4a1.5 1.5 0 0 0 1.3-2.3L14 10V3M8 15h8',
}

export default function Icon({ name, className = 'size-5' }) {
  return (
    <svg aria-hidden="true" className={className} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <path d={paths[name]} />
    </svg>
  )
}
