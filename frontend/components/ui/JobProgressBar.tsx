'use client'

export default function JobProgressBar({ progress }: { progress: number }) {
  return (
    <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-gray-700">
      <div
        className="h-2 rounded-full bg-blue-600 transition-all"
        style={{ width: `${Math.min(progress, 100)}%` }}
      />
    </div>
  )
}
