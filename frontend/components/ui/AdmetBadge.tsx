'use client'

interface AdmetBadgeProps {
  label: string
  pass: boolean | null
}

export default function AdmetBadge({ label, pass }: AdmetBadgeProps) {
  const color =
    pass === null ? 'bg-gray-200 text-gray-700' :
    pass ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${color}`}>
      {label}
    </span>
  )
}
