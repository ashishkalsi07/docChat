'use client'
import React, { useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

const LandingPage = () => {
  const { user, loading } = useAuth()
  const router = useRouter()

  // Redirect authenticated users to home page
  useEffect(() => {
    if (!loading && user) {
      router.push('/home')
    }
  }, [user, loading, router])

  // Show loading spinner while auth is loading
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-linear-to-br from-blue-50 to-blue-100">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  // If user is authenticated, show loading while redirecting
  if (user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-linear-to-br from-blue-50 to-blue-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Redirecting to your dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-linear-to-br from-blue-50 to-blue-100">
      {/* Header */}
      <header className="w-full px-4 sm:px-6 lg:px-8 py-4 sm:py-6">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="text-xl sm:text-2xl lg:text-3xl font-bold text-gray-800 truncate">
            <span className="hidden sm:inline">AI Knowledge Assistant</span>
            <span className="sm:hidden">AI Assistant</span>
          </div>
          <nav className="flex items-center space-x-2 sm:space-x-4">
            <Link
              href="/login"
              className="px-3 py-2 sm:px-4 sm:py-2 text-sm sm:text-base text-gray-600 hover:text-gray-800 transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/signup"
              className="px-4 py-2 sm:px-6 sm:py-2 bg-blue-600 text-white text-sm sm:text-base rounded-lg hover:bg-blue-700 transition-colors shadow-md"
            >
              <span className="hidden sm:inline">Get Started</span>
              <span className="sm:hidden">Join</span>
            </Link>
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8 pb-16 sm:pb-24 lg:pb-32 pt-8 sm:pt-12">
        <div className="max-w-7xl w-full">
          {/* Hero Section */}
          <div className="text-center space-y-6 sm:space-y-8 lg:space-y-12 animate-fade-in">
            <div className="space-y-4 sm:space-y-6 lg:space-y-8">
              <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl xl:text-7xl font-bold text-gray-800 leading-tight px-4">
                <span className="block sm:inline">Chat with your</span>
                <span className="bg-linear-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent"> Documents</span>
              </h1>
              <p className="text-base sm:text-lg md:text-xl lg:text-2xl text-gray-600 max-w-xs sm:max-w-2xl md:max-w-3xl lg:max-w-4xl mx-auto leading-relaxed px-4">
                Upload your documents and start having intelligent conversations with your data. Get instant answers, summaries, and insights powered by advanced AI technology.
              </p>
            </div>

            {/* Call to Action */}
            <div className="mt-8 sm:mt-12 lg:mt-16 space-y-4 sm:space-y-6">
              <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center items-center px-4">
                <Link
                  href="/signup"
                  className="w-full sm:w-auto px-6 sm:px-8 lg:px-10 py-3 sm:py-4 bg-blue-600 text-white text-base sm:text-lg lg:text-xl font-medium rounded-xl hover:bg-blue-700 transition-all duration-200 shadow-lg hover:shadow-xl text-center min-w-50"
                >
                  Start Chatting Now
                </Link>
                <Link
                  href="/login"
                  className="w-full sm:w-auto px-6 sm:px-8 lg:px-10 py-3 sm:py-4 bg-white text-gray-800 text-base sm:text-lg lg:text-xl font-medium rounded-xl hover:bg-gray-50 transition-all duration-200 shadow-md hover:shadow-lg border border-gray-200 text-center min-w-50"
                >
                  Sign In
                </Link>
              </div>

              <p className="text-xs sm:text-sm text-gray-500 px-4">
                The application is completely free
              </p>
            </div>

            {/* Features Preview */}
            <div className="mt-12 sm:mt-16 lg:mt-20 xl:mt-24">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 lg:gap-8 px-4">
                <div className="bg-white/50 backdrop-blur-sm rounded-xl p-4 sm:p-6 lg:p-8 border border-white/20 hover:bg-white/60 transition-colors">
                  <div className="w-10 h-10 sm:w-12 sm:h-12 lg:w-14 lg:h-14 bg-blue-100 rounded-lg flex items-center justify-center mb-3 sm:mb-4 lg:mb-6 mx-auto">
                    <svg className="w-5 h-5 sm:w-6 sm:h-6 lg:w-7 lg:h-7 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                    </svg>
                  </div>
                  <h3 className="text-base sm:text-lg lg:text-xl font-semibold text-gray-800 mb-2 sm:mb-3">Intelligent Chat</h3>
                  <p className="text-gray-600 text-sm sm:text-base leading-relaxed">
                    Ask questions in natural language and get accurate answers from your documents.
                  </p>
                </div>

                <div className="bg-white/50 backdrop-blur-sm rounded-xl p-4 sm:p-6 lg:p-8 border border-white/20 hover:bg-white/60 transition-colors">
                  <div className="w-10 h-10 sm:w-12 sm:h-12 lg:w-14 lg:h-14 bg-purple-100 rounded-lg flex items-center justify-center mb-3 sm:mb-4 lg:mb-6 mx-auto">
                    <svg className="w-5 h-5 sm:w-6 sm:h-6 lg:w-7 lg:h-7 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <h3 className="text-base sm:text-lg lg:text-xl font-semibold text-gray-800 mb-2 sm:mb-3">Multiple Formats</h3>
                  <p className="text-gray-600 text-sm sm:text-base leading-relaxed">
                    Support for PDF, Word, text files and more. Upload and start chatting instantly.
                  </p>
                </div>

                <div className="bg-white/50 backdrop-blur-sm rounded-xl p-4 sm:p-6 lg:p-8 border border-white/20 hover:bg-white/60 transition-colors sm:col-span-2 lg:col-span-1">
                  <div className="w-10 h-10 sm:w-12 sm:h-12 lg:w-14 lg:h-14 bg-green-100 rounded-lg flex items-center justify-center mb-3 sm:mb-4 lg:mb-6 mx-auto">
                    <svg className="w-5 h-5 sm:w-6 sm:h-6 lg:w-7 lg:h-7 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                  <h3 className="text-base sm:text-lg lg:text-xl font-semibold text-gray-800 mb-2 sm:mb-3">Instant Results</h3>
                  <p className="text-gray-600 text-sm sm:text-base leading-relaxed">
                    Get fast, accurate responses powered by cutting-edge AI technology.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default LandingPage
