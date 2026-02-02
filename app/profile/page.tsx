'use client'
import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { createClient } from '@/utils/supabase-client'

const ProfilePage = () => {
  const [displayName, setDisplayName] = useState('')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  const { user, loading: authLoading } = useAuth()
  const router = useRouter()
  const supabase = createClient()

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
    }
  }, [user, authLoading, router])

  // Load existing profile data
  useEffect(() => {
    const loadProfile = async () => {
      if (!user) return

      setInitialLoading(true)
      try {
        // Get user metadata from Supabase auth
        const { data: { user: authUser }, error } = await supabase.auth.getUser()

        if (error) {
          console.error('Error loading profile:', error)
        } else if (authUser) {
          // Load from user_metadata
          const metadata = authUser.user_metadata || {}
          setDisplayName(metadata.display_name || '')
          setPhoneNumber(metadata.phone_number || '')
        }
      } catch (err) {
        console.error('Error loading profile:', err)
      } finally {
        setInitialLoading(false)
      }
    }

    if (user) {
      loadProfile()
    }
  }, [user, supabase.auth])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!user) return

    setLoading(true)
    setError('')
    setMessage('')

    try {
      // Update user metadata
      const { error } = await supabase.auth.updateUser({
        data: {
          display_name: displayName.trim(),
          phone_number: phoneNumber.trim(),
        }
      })

      if (error) {
        setError(error.message)
      } else {
        setMessage('Profile updated successfully! 🎉')
        // Clear message after 3 seconds
        setTimeout(() => setMessage(''), 3000)
      }
    } catch (err) {
      setError('An unexpected error occurred')
      console.error('Profile update error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    const { signOut } = useAuth()
    await signOut()
    router.push('/')
  }

  // Show loading while auth is loading or profile is loading
  if (authLoading || initialLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  // This shouldn't happen due to middleware, but just in case
  if (!user) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-3">
              <button
                onClick={() => router.push('/home')}
                className="text-gray-600 hover:text-gray-800 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <h1 className="text-xl font-semibold text-gray-800">Profile Settings</h1>
            </div>
            <button
              onClick={handleLogout}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-2xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          {/* Profile Header */}
          <div className="flex items-center space-x-4 mb-6 pb-6 border-b border-gray-100">
            <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center">
              <span className="text-white text-xl font-medium">
                {displayName ? displayName.charAt(0).toUpperCase() : user.email?.charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-800">
                {displayName || 'Complete Your Profile'}
              </h2>
              <p className="text-sm text-gray-600">{user.email}</p>
            </div>
          </div>

          {/* Profile Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="displayName" className="block text-sm font-medium text-gray-700 mb-2">
                Display Name
              </label>
              <input
                id="displayName"
                name="displayName"
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="Enter your display name"
              />
              <p className="mt-1 text-xs text-gray-500">
                This is how your name will appear to others in the app
              </p>
            </div>

            <div>
              <label htmlFor="phoneNumber" className="block text-sm font-medium text-gray-700 mb-2">
                Phone Number
              </label>
              <input
                id="phoneNumber"
                name="phoneNumber"
                type="tel"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="Enter your phone number"
              />
              <p className="mt-1 text-xs text-gray-500">
                Optional - used for account recovery and notifications
              </p>
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            {message && (
              <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg text-sm">
                {message}
              </div>
            )}

            <div className="flex gap-3">
              <button
                type="submit"
                disabled={loading}
                className="flex-1 py-2 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Saving...
                  </div>
                ) : (
                  'Save Profile'
                )}
              </button>

              <button
                type="button"
                onClick={() => router.push('/home')}
                className="px-6 py-2 border border-gray-300 text-sm font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Skip for now
              </button>
            </div>
          </form>

          {/* Profile Completion Status */}
          <div className="mt-8 pt-6 border-t border-gray-100">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium text-gray-800">Profile Completion</h3>
                <p className="text-xs text-gray-500">Complete your profile for the best experience</p>
              </div>
              <div className="flex items-center">
                <div className="w-16 h-2 bg-gray-200 rounded-full mr-2">
                  <div
                    className="h-2 bg-blue-600 rounded-full transition-all duration-300"
                    style={{ width: `${(displayName ? 50 : 0) + (phoneNumber ? 50 : 0)}%` }}
                  ></div>
                </div>
                <span className="text-xs text-gray-600">
                  {(displayName ? 1 : 0) + (phoneNumber ? 1 : 0)}/2
                </span>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default ProfilePage