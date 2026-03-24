'use client'

import type { TargetSuggestion } from '@/lib/types'

export default function TargetSuggestionCard({ suggestion }: { suggestion: TargetSuggestion }) {
  return <div>{suggestion.protein_name} — coming soon</div>
}
