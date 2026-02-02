import { User } from '@supabase/supabase-js'

export interface ProfileData {
  display_name?: string
  phone_number?: string
}

export function getProfileCompletionStatus(user: User | null): {
  isComplete: boolean
  completionPercentage: number
  missingFields: string[]
} {
  if (!user) {
    return {
      isComplete: false,
      completionPercentage: 0,
      missingFields: ['display_name', 'phone_number']
    }
  }

  const metadata = user.user_metadata || {}
  const fields = ['display_name', 'phone_number']
  const completedFields = fields.filter(field =>
    metadata[field] && metadata[field].toString().trim()
  )

  const missingFields = fields.filter(field =>
    !metadata[field] || !metadata[field].toString().trim()
  )

  return {
    isComplete: completedFields.length === fields.length,
    completionPercentage: (completedFields.length / fields.length) * 100,
    missingFields
  }
}

export function getDisplayName(user: User | null): string {
  if (!user) return ''

  const metadata = user.user_metadata || {}
  return metadata.display_name || user.email?.split('@')[0] || ''
}

export function getUserInitials(user: User | null): string {
  if (!user) return '?'

  const displayName = getDisplayName(user)
  if (displayName && displayName !== user.email?.split('@')[0]) {
    return displayName.charAt(0).toUpperCase()
  }

  return user.email?.charAt(0).toUpperCase() || '?'
}