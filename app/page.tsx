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
      <header className="w-full px-4 py-6">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <div className="text-2xl font-bold text-gray-800">
            AI Knowledge Assistant
          </div>
          <nav className="flex items-center space-x-4">
            <Link
              href="/login"
              className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/signup"
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-md"
            >
              Get Started
            </Link>
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex items-center justify-center px-4 pb-32">
        <div className="max-w-4xl w-full">
          {/* Hero Section */}
          <div className="text-center space-y-8 animate-fade-in">
            <div className="space-y-6">
              <h1 className="text-5xl md:text-6xl font-bold text-gray-800 leading-tight">
                Chat with your
                <span className="bg-linear-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent"> Documents</span>
              </h1>
              <p className="text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed">
                Upload your documents and start having intelligent conversations with your data. Get instant answers, summaries, and insights powered by advanced AI technology.
              </p>
            </div>

            {/* Call to Action */}
            <div className="mt-12 space-y-6">
              <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
                <Link
                  href="/signup"
                  className="px-8 py-4 bg-blue-600 text-white text-lg font-medium rounded-xl hover:bg-blue-700 transition-all duration-200 shadow-lg hover:shadow-xl"
                >
                  Start Chatting Now
                </Link>
                <Link
                  href="/login"
                  className="px-8 py-4 bg-white text-gray-800 text-lg font-medium rounded-xl hover:bg-gray-50 transition-all duration-200 shadow-md hover:shadow-lg border border-gray-200"
                >
                  Sign In
                </Link>
              </div>

              <p className="text-sm text-gray-500">
                Free to get started • No credit card required
              </p>
            </div>

            {/* Features Preview */}
            <div className="mt-20 grid md:grid-cols-3 gap-8">
              <div className="bg-white/50 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4 mx-auto">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">Intelligent Chat</h3>
                <p className="text-gray-600 text-sm">
                  Ask questions in natural language and get accurate answers from your documents.
                </p>
              </div>

              <div className="bg-white/50 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4 mx-auto">
                  <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">Multiple Formats</h3>
                <p className="text-gray-600 text-sm">
                  Support for PDF, Word, text files and more. Upload and start chatting instantly.
                </p>
              </div>

              <div className="bg-white/50 backdrop-blur-sm rounded-xl p-6 border border-white/20">
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4 mx-auto">
                  <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">Instant Results</h3>
                <p className="text-gray-600 text-sm">
                  Get fast, accurate responses powered by cutting-edge AI technology.
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default LandingPage
