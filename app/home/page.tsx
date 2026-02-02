'use client'
import React, { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useRouter } from 'next/navigation'
import { createClient } from '@/utils/supabase-client'

interface Message {
  id: string
  role: 'USER' | 'ASSISTANT'
  content: string
  created_at: string
  citations?: any[]
}

interface ChatSession {
  id: string
  title: string
  document_name?: string
  last_message?: string
  created_at: string
  updated_at: string
}

interface Document {
  id: string
  name: string
  status: 'PROCESSING' | 'COMPLETED' | 'FAILED'
}

const HomePage = () => {
  const [message, setMessage] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const [showProfilePrompt, setShowProfilePrompt] = useState(false)
  const [profileComplete, setProfileComplete] = useState(false)

  // Document state
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [isUploading, setIsUploading] = useState(false)
  const [currentDocument, setCurrentDocument] = useState<Document | null>(null)
  const [documentStatus, setDocumentStatus] = useState<string>('')
  const [error, setError] = useState<string>('')

  // Chat state
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([])
  const [currentChatId, setCurrentChatId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [isMobile, setIsMobile] = useState(false)
  const messagesEndRef = React.useRef<HTMLDivElement>(null)

  // Delete confirmation state - no modal needed
  const [chatToDelete, setChatToDelete] = useState<string | null>(null)
  const [documentToDelete, setDocumentToDelete] = useState<boolean>(false)

  const { user, signOut, loading } = useAuth()
  const router = useRouter()
  const supabase = createClient()

  // Check profile completion status
  useEffect(() => {
    const checkProfileCompletion = async () => {
      if (!user) return

      try {
        const { data: { user: authUser }, error } = await supabase.auth.getUser()

        if (error) {
          console.error('Error loading profile:', error)
          return
        }

        if (authUser) {
          const metadata = authUser.user_metadata || {}
          const hasDisplayName = metadata.display_name && metadata.display_name.trim()
          const hasPhoneNumber = metadata.phone_number && metadata.phone_number.trim()

          const isComplete = hasDisplayName || hasPhoneNumber
          setProfileComplete(isComplete)
          setShowProfilePrompt(!isComplete)
        }
      } catch (err) {
        console.error('Error checking profile:', err)
      }
    }

    if (user) {
      checkProfileCompletion()
    }
  }, [user, supabase.auth])

  // Check for existing document when page loads
  useEffect(() => {
    const checkExistingDocument = async () => {
      if (!user) return

      try {
        const { data: { session } } = await supabase.auth.getSession()
        if (!session?.access_token) return

        const apiUrl = process.env.NEXT_PUBLIC_BACKEND_URL
        const response = await fetch(`${apiUrl}/api/documents/current`, {
          headers: {
            'Authorization': `Bearer ${session.access_token}`
          }
        })

        if (response.ok) {
          const document = await response.json()
          setCurrentDocument({
            id: document.id,
            name: document.original_name,
            status: document.status
          })

          if (document.status === 'COMPLETED') {
            setDocumentStatus('Document ready for chat')
            // Load chat sessions when document is ready
            loadChatSessions()
          } else if (document.status === 'PROCESSING') {
            setDocumentStatus('Processing document...')
          }
        } else if (response.status === 404) {
          // No existing document - this is fine
          setCurrentDocument(null)
        } else {
          console.error('Error checking existing document:', response.statusText)
        }
      } catch (err) {
        console.error('Error checking existing document:', err)
      }
    }

    if (user) {
      checkExistingDocument()
    }
  }, [user, supabase.auth])

  // Auto scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Handle responsive behavior
  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 768
      setIsMobile(mobile)

      // Auto-close sidebar on mobile
      if (mobile) {
        setSidebarOpen(false)
      }
    }

    // Initial check
    handleResize()

    // Add event listener
    window.addEventListener('resize', handleResize)

    // Cleanup
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // Load chat sessions
  const loadChatSessions = async () => {
    if (!user) return

    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) return

      const apiUrl = process.env.NEXT_PUBLIC_BACKEND_URL
      const response = await fetch(`${apiUrl}/api/chat/sessions`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      })

      if (response.ok) {
        const sessions = await response.json()
        setChatSessions(sessions)
      }
    } catch (err) {
      console.error('Error loading chat sessions:', err)
    }
  }

  // Load messages for a specific chat session
  const loadChatMessages = async (chatId: string) => {
    try {
      console.log('Loading messages for chat:', chatId)
      setIsLoading(true)
      setError('')

      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) {
        setError('Authentication required')
        setIsLoading(false)
        return
      }

      const apiUrl = process.env.NEXT_PUBLIC_BACKEND_URL
      console.log('Making request to:', `${apiUrl}/api/chat/sessions/${chatId}/messages`)

      const response = await fetch(`${apiUrl}/api/chat/sessions/${chatId}/messages`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      })

      console.log('Response status:', response.status)

      if (response.ok) {
        const data = await response.json()
        console.log('Raw response data:', data)
        console.log('Messages array:', data.messages)
        console.log('Loaded messages:', data.messages?.length || 0, 'messages')

        setMessages(data.messages || [])
        setCurrentChatId(chatId)

        // Log each message for debugging
        if (data.messages && data.messages.length > 0) {
          data.messages.forEach((msg: Message, idx: number) => {
            console.log(`Message ${idx + 1}:`, {
              id: msg.id,
              role: msg.role,
              content: msg.content?.substring(0, 50) + '...',
              created_at: msg.created_at
            })
          })
        } else {
          console.log('No messages found in response')
        }
      } else {
        console.error('Failed to load messages:', response.status, response.statusText)
        const errorText = await response.text()
        console.error('Error response body:', errorText)
        try {
          const errorData = JSON.parse(errorText)
          setError(`Failed to load chat history: ${errorData?.detail || 'Unknown error'}`)
        } catch {
          setError(`Failed to load chat history: ${response.statusText}`)
        }
      }
    } catch (err) {
      console.error('Error loading messages:', err)
      setError('Failed to load chat history. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  // Create new chat session
  const createNewChat = async () => {
    if (!currentDocument || currentDocument.status !== 'COMPLETED') {
      setError('Please upload and process a document first')
      return
    }

    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) return

      const apiUrl = process.env.NEXT_PUBLIC_BACKEND_URL
      const response = await fetch(`${apiUrl}/api/chat/sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          document_id: currentDocument.id,
          title: `New Chat with ${currentDocument.name}`
        })
      })

      if (response.ok) {
        const data = await response.json()
        const newChatId = data.chat_id

        // Reload sessions and switch to new chat
        await loadChatSessions()
        setCurrentChatId(newChatId)
        setMessages([])
      }
    } catch (err) {
      console.error('Error creating chat session:', err)
    }
  }

  // Show delete confirmation
  const showDeleteConfirmation = (chatId: string) => {
    setChatToDelete(chatId)
  }

  // Cancel delete confirmation
  const cancelDelete = () => {
    setChatToDelete(null)
  }

  // Delete chat session
  const deleteChatSession = async (chatId: string) => {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) return

      const apiUrl = process.env.NEXT_PUBLIC_BACKEND_URL
      const response = await fetch(`${apiUrl}/api/chat/sessions/${chatId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      })

      if (response.ok) {
        // Remove from local state
        setChatSessions(prev => prev.filter(chat => chat.id !== chatId))

        // If this was the current chat, clear it
        if (currentChatId === chatId) {
          setCurrentChatId(null)
          setMessages([])
        }

        console.log('Chat session deleted successfully')
      } else {
        console.error('Failed to delete chat session')
        setError('Failed to delete chat session')
      }
    } catch (err) {
      console.error('Error deleting chat session:', err)
      setError('Failed to delete chat session')
    } finally {
      setChatToDelete(null)
    }
  }

  // Show document delete confirmation
  const showDeleteDocumentConfirmation = () => {
    setDocumentToDelete(true)
  }

  // Cancel document delete confirmation
  const cancelDocumentDelete = () => {
    setDocumentToDelete(false)
  }

  // Delete document
  const deleteDocument = async () => {
    if (!currentDocument) return

    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) return

      const apiUrl = process.env.NEXT_PUBLIC_BACKEND_URL
      const response = await fetch(`${apiUrl}/api/documents/${currentDocument.id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      })

      if (response.ok) {
        // Clear document state
        setCurrentDocument(null)
        setDocumentStatus('')
        setError('')

        // Clear all chat sessions since they're tied to the document
        setChatSessions([])
        setCurrentChatId(null)
        setMessages([])

        console.log('Document deleted successfully')
      } else {
        const errorData = await response.json()
        console.error('Failed to delete document')
        setError(errorData?.detail || 'Failed to delete document')
      }
    } catch (err) {
      console.error('Error deleting document:', err)
      setError('Failed to delete document')
    } finally {
      setDocumentToDelete(false)
    }
  }

  // Show loading spinner while auth is loading
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  // This shouldn't happen due to middleware, but just in case
  if (!user) {
    router.push('/login')
    return null
  }

  const handleLogout = async () => {
    await signOut()
    router.push('/')
  }

  // File upload handler
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate file
    if (!file.type.includes('pdf')) {
      setError('Please select a PDF file')
      return
    }

    if (file.size > 10 * 1024 * 1024) { // 10MB limit
      setError('File size must be less than 10MB')
      return
    }

    setSelectedFile(file)
    setError('')

    // Upload immediately
    await uploadDocument(file)
  }

  // Upload document to backend
  const uploadDocument = async (file: File) => {
    setIsUploading(true)
    setUploadProgress(0)
    setError('')

    try {
      const formData = new FormData()
      formData.append('file', file)

      // Get auth token from Supabase
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) {
        throw new Error('Authentication required')
      }

      const apiUrl = process.env.NEXT_PUBLIC_BACKEND_URL
      const response = await fetch(`${apiUrl}/api/documents/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        },
        body: formData
      })

      if (!response.ok) {
        const errorData = await response.json()
        if (response.status === 409) {
          // User already has a document
          throw new Error('You already have a document. Please delete it first to upload a new one.')
        }
        throw new Error(errorData.detail || 'Upload failed')
      }

      const result = await response.json()

      setCurrentDocument({
        id: result.document_id,
        name: file.name,
        status: result.processing_status
      })

      setUploadProgress(100)
      setDocumentStatus('Processing document...')

      // Start polling for status updates
      pollDocumentStatus(result.document_id)

    } catch (error: any) {
      console.error('Upload error:', error)
      setError(error.message || 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  // Poll document processing status
  const pollDocumentStatus = async (documentId: string) => {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) return

      const apiUrl = process.env.NEXT_PUBLIC_BACKEND_URL
      const response = await fetch(`${apiUrl}/api/documents/${documentId}/status`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      })

      if (response.ok) {
        const statusData = await response.json()
        setDocumentStatus(statusData.progress || statusData.status)

        if (statusData.status === 'COMPLETED') {
          setCurrentDocument((prev: Document | null) => prev ? { ...prev, status: 'COMPLETED' } : null)
          setDocumentStatus('Document ready for chat!')
        } else if (statusData.status === 'FAILED') {
          setError(statusData.error_message || 'Document processing failed')
        } else {
          // Continue polling
          setTimeout(() => pollDocumentStatus(documentId), 2000)
        }
      }
    } catch (error) {
      console.error('Status polling error:', error)
    }
  }

  const handleSubmit = async (e: any) => {
    e.preventDefault()

    if (!currentDocument || currentDocument.status !== 'COMPLETED') {
      setError('Please upload and process a document first')
      return
    }

    if (!message.trim()) {
      return
    }

    const userMessage = message.trim()
    setMessage('')
    setIsLoading(true)
    setError('')

    // Add user message immediately
    const tempUserMessage: Message = {
      id: Date.now().toString(),
      role: 'USER',
      content: userMessage,
      created_at: new Date().toISOString()
    }
    setMessages(prev => [...prev, tempUserMessage])

    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) {
        setError('Please log in to continue')
        return
      }

      const apiUrl = process.env.NEXT_PUBLIC_BACKEND_URL
      let chatId = currentChatId

      // Create new chat session if none exists
      if (!chatId) {
        const chatResponse = await fetch(`${apiUrl}/api/chat/sessions`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${session.access_token}`
          },
          body: JSON.stringify({
            document_id: currentDocument.id,
            title: `Chat with ${currentDocument.name}`
          })
        })

        if (!chatResponse.ok) {
          throw new Error('Failed to create chat session')
        }

        const chatData = await chatResponse.json()
        chatId = chatData.chat_id
        setCurrentChatId(chatId)
        await loadChatSessions()
      }

      // Send message
      const messageResponse = await fetch(`${apiUrl}/api/chat/sessions/${chatId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          message: userMessage
        })
      })

      if (!messageResponse.ok) {
        throw new Error('Failed to send message')
      }

      const responseData = await messageResponse.json()

      // Add assistant response
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ASSISTANT',
        content: responseData.message,
        created_at: new Date().toISOString(),
        citations: responseData.citations || []
      }
      setMessages(prev => [...prev, assistantMessage])

      // Update chat sessions to refresh last message
      await loadChatSessions()

    } catch (error) {
      console.error('Chat error:', error)
      setError('Failed to send message. Please try again.')

      // Remove the temporary user message on error
      setMessages(prev => prev.filter(msg => msg.id !== tempUserMessage.id))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="h-screen bg-gray-50 flex overflow-hidden relative">
      {/* Mobile backdrop */}
      {isMobile && sidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`bg-gray-900 text-white transition-all duration-300 z-50 ${
        isMobile
          ? `fixed left-0 top-0 h-full ${sidebarOpen ? 'w-80' : 'w-0 overflow-hidden'}`
          : `${sidebarOpen ? 'w-80' : 'w-0 overflow-hidden'} shrink-0`
      }`}>
        <div className="h-full flex flex-col">
          {/* Header */}
          <div className="p-4 border-b border-gray-700">
            {/* Mobile close button */}
            {isMobile && (
              <div className="flex justify-end mb-3 md:hidden">
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="p-1 text-gray-400 hover:text-white transition-colors"
                  aria-label="Close sidebar"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => router.push('/profile')}
                  className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center hover:bg-blue-700 transition-colors"
                >
                  <span className="text-white text-sm font-medium">
                    {user.email?.charAt(0).toUpperCase()}
                  </span>
                </button>
                <div className="text-sm">
                  <p className="text-gray-300">Welcome back,</p>
                  <p className="font-medium">{user.email}</p>
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="p-1 text-gray-400 hover:text-white transition-colors"
                title="Sign out"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
              </button>
            </div>

            {/* New Chat Button */}
            <button
              onClick={createNewChat}
              disabled={!currentDocument || currentDocument.status !== 'COMPLETED'}
              className="w-full mt-4 p-2.5 md:p-3 bg-gray-800 hover:bg-gray-700 rounded-lg text-xs md:text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span>New Chat</span>
            </button>
          </div>

          {/* Document Status */}
          {(currentDocument || isUploading || error) && (
            <div className="p-4 border-b border-gray-700">
              {/* Error Message */}
              {error && (
                <div className="bg-red-900/50 border border-red-700 text-red-200 px-3 py-2 rounded text-sm mb-3">
                  {error}
                </div>
              )}

              {/* Upload Progress */}
              {isUploading && (
                <div className="bg-blue-900/50 border border-blue-700 rounded p-3 mb-3">
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full"></div>
                    <div className="flex-1">
                      <p className="text-sm text-blue-200">Uploading {selectedFile?.name}...</p>
                      <div className="mt-2 bg-blue-800 rounded-full h-1">
                        <div
                          className="bg-blue-400 h-1 rounded-full transition-all"
                          style={{ width: `${uploadProgress}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Document Status */}
              {currentDocument && !isUploading && (
                <div className="relative group">
                  {documentToDelete ? (
                    // Delete confirmation state
                    <div className="bg-red-900/50 border border-red-600 rounded p-3">
                      <p className="text-sm text-red-200 mb-3">Delete this document and all chats?</p>
                      <div className="flex space-x-2">
                        <button
                          onClick={deleteDocument}
                          className="flex-1 px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition-colors"
                        >
                          Yes
                        </button>
                        <button
                          onClick={cancelDocumentDelete}
                          className="flex-1 px-3 py-1 bg-gray-600 text-white text-sm rounded hover:bg-gray-700 transition-colors"
                        >
                          No
                        </button>
                      </div>
                    </div>
                  ) : (
                    // Normal document state
                    <div className={`border rounded p-3 ${
                      currentDocument.status === 'COMPLETED'
                        ? 'bg-green-900/50 border-green-700'
                        : 'bg-yellow-900/50 border-yellow-700'
                    }`}>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <div className={`w-2 h-2 rounded-full ${
                            currentDocument.status === 'COMPLETED' ? 'bg-green-400' : 'bg-yellow-400'
                          }`}></div>
                          <div>
                            <p className="text-sm font-medium">{currentDocument.name}</p>
                            <p className="text-xs text-gray-400">{documentStatus}</p>
                          </div>
                        </div>
                        <button
                          onClick={showDeleteDocumentConfirmation}
                          className="p-1 text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                          title="Delete document"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* File Upload */}
              {!currentDocument && (
                <div>
                  <input
                    type="file"
                    className="hidden"
                    id="sidebar-file-input"
                    accept=".pdf"
                    onChange={handleFileUpload}
                    disabled={isUploading}
                  />
                  <label
                    htmlFor="sidebar-file-input"
                    className="w-full p-3 border-2 border-dashed border-gray-600 rounded-lg text-center cursor-pointer hover:border-gray-500 transition-colors block"
                  >
                    <svg className="w-6 h-6 mx-auto mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    <p className="text-sm text-gray-300">Upload PDF Document</p>
                  </label>
                </div>
              )}
            </div>
          )}

          {/* Chat Sessions */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-4">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
                Chat History
              </h3>
              <div className="space-y-2">
                {chatSessions.map((session) => (
                  <div
                    key={session.id}
                    className={`relative group rounded-lg transition-colors ${
                      currentChatId === session.id ? 'bg-gray-800 border border-gray-600' : 'bg-gray-900'
                    }`}
                  >
                    {chatToDelete === session.id ? (
                      // Delete confirmation state
                      <div className="p-3 bg-red-900/50 border border-red-600 rounded-lg">
                        <p className="text-sm text-red-200 mb-3">Delete this chat?</p>
                        <div className="flex space-x-2">
                          <button
                            onClick={() => deleteChatSession(session.id)}
                            className="flex-1 px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition-colors"
                          >
                            Yes
                          </button>
                          <button
                            onClick={cancelDelete}
                            className="flex-1 px-3 py-1 bg-gray-600 text-white text-sm rounded hover:bg-gray-700 transition-colors"
                          >
                            No
                          </button>
                        </div>
                      </div>
                    ) : (
                      // Normal chat state
                      <>
                        <button
                          onClick={() => {
                            console.log('Clicking on chat session:', session.id)
                            loadChatMessages(session.id)
                          }}
                          className={`w-full p-3 text-left transition-colors rounded-lg ${
                            currentChatId === session.id
                              ? 'bg-blue-600 text-white'
                              : 'hover:bg-gray-800'
                          }`}
                        >
                          <p className={`text-sm font-medium truncate pr-8 ${
                            currentChatId === session.id ? 'text-white' : ''
                          }`}>
                            {session.title}
                          </p>
                          <p className={`text-xs mt-1 truncate ${
                            currentChatId === session.id ? 'text-blue-100' : 'text-gray-400'
                          }`}>
                            {session.last_message || 'No messages yet'}
                          </p>
                          <p className={`text-xs mt-1 ${
                            currentChatId === session.id ? 'text-blue-200' : 'text-gray-500'
                          }`}>
                            {new Date(session.created_at).toLocaleDateString()}
                          </p>
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            showDeleteConfirmation(session.id)
                          }}
                          className="absolute top-2 right-2 p-1 text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                          title="Delete chat"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </>
                    )}
                  </div>
                ))}
                {chatSessions.length === 0 && currentDocument?.status === 'COMPLETED' && (
                  <p className="text-sm text-gray-500 text-center py-4">
                    No chat sessions yet.<br/>Click "New Chat" to start.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 p-3 md:p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 md:space-x-3">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-1.5 md:p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              <h1 className="text-base md:text-lg font-semibold text-gray-800 truncate">
                {currentChatId ? 'Chat Session' : 'AI Knowledge Assistant'}
              </h1>
            </div>
            <div className="flex items-center space-x-2 md:space-x-4">
              {currentDocument && (
                <div className="text-xs md:text-sm text-gray-500 truncate max-w-32 md:max-w-none">
                  <span className="hidden md:inline">{currentDocument.name} • </span>
                  {currentDocument.status}
                </div>
              )}
              {currentChatId && messages.length > 0 && (
                <div className="text-xs md:text-sm text-gray-400">
                  {messages.length} <span className="hidden sm:inline">messages</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
          {!currentChatId && currentDocument?.status === 'COMPLETED' ? (
            // Welcome Screen
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center max-w-sm md:max-w-md px-4">
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-800 mb-2">Ready to Chat!</h3>
                <p className="text-gray-600 mb-4">
                  Your document "{currentDocument.name}" is processed and ready. Start a new chat or select an existing conversation.
                </p>
                <button
                  onClick={createNewChat}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Start New Chat
                </button>
              </div>
            </div>
          ) : currentChatId ? (
            // Messages Display
            <div className="flex-1 overflow-y-auto p-3 md:p-4">
              <div className="space-y-3 md:space-y-4">
                {/* Error Message */}
                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                    {error}
                    <button
                      onClick={() => setError('')}
                      className="ml-2 text-red-500 hover:text-red-700"
                    >
                      ×
                    </button>
                  </div>
                )}

                {/* Loading State */}
                {isLoading && messages.length === 0 ? (
                  <div className="text-center text-gray-500 py-8">
                    <div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-2"></div>
                    <p>Loading chat history...</p>
                  </div>
                ) : messages.length === 0 && !isLoading ? (
                  <div className="text-center text-gray-500 py-8">
                    <p>No messages in this chat yet.</p>
                    <p className="text-sm mt-2">Start the conversation below!</p>
                    {currentChatId && (
                      <button
                        onClick={() => loadChatMessages(currentChatId)}
                        className="mt-3 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
                      >
                        Try Loading Again
                      </button>
                    )}
                  </div>
                ) : (
                  messages.map((msg) => (
                    <div key={msg.id} className={`flex ${msg.role === 'USER' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-xs sm:max-w-md md:max-w-2xl lg:max-w-3xl ${
                        msg.role === 'USER'
                          ? 'bg-blue-600 text-white'
                          : 'bg-white border border-gray-200'
                      } rounded-lg p-3 md:p-4 shadow-sm`}>
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                        {msg.citations && msg.citations.length > 0 && (
                          <div className="mt-3 pt-3 border-t border-gray-200">
                            <p className="text-xs text-gray-500 mb-2">Sources:</p>
                            <div className="space-y-1">
                              {msg.citations.map((citation, idx) => (
                                <div key={idx} className="text-xs text-gray-600 bg-gray-50 p-2 rounded">
                                  Page {citation.page_number}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        <p className="text-xs text-gray-400 mt-2">
                          {new Date(msg.created_at).toLocaleString(undefined, {
                            hour: '2-digit',
                            minute: '2-digit',
                            day: '2-digit',
                            month: 'short',
                            timeZoneName: 'short'
                          })}
                        </p>
                      </div>
                    </div>
                  ))
                )}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
                      <div className="flex items-center space-x-2">
                        <div className="animate-spin w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full"></div>
                        <span className="text-sm text-gray-600">AI is thinking...</span>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </div>
          ) : (
            // No Document State
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center max-w-sm md:max-w-md px-4">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-800 mb-2">Upload a Document</h3>
                <p className="text-gray-600 mb-4">
                  Upload a PDF document to start having intelligent conversations with your content. Only one document is allowed per user.
                </p>
                <div className="">
                  <input
                    type="file"
                    className="hidden"
                    id="main-file-input"
                    accept=".pdf"
                    onChange={handleFileUpload}
                    disabled={isUploading}
                  />
                  <label
                    htmlFor="main-file-input"
                    className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors cursor-pointer"
                  >
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    Choose PDF File
                  </label>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        {currentChatId && (
          <div className="bg-white border-t border-gray-200 p-3 md:p-4">
            <form onSubmit={handleSubmit} className="flex items-end space-x-2 md:space-x-3">
              <div className="flex-1">
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Type your message..."
                  className="w-full px-3 py-2 text-sm md:text-base border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent max-h-32"
                  rows={1}
                  disabled={isLoading}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleSubmit(e)
                    }
                  }}
                />
              </div>
              <button
                type="submit"
                disabled={!message.trim() || isLoading}
                className="px-3 py-2 md:px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg className="w-4 h-4 md:w-5 md:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </form>
          </div>
        )}
      </div>

      {/* Profile Completion Modal */}
      {showProfilePrompt && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <div className="flex items-center space-x-3 mb-4">
              <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Complete your profile</h3>
                <p className="text-sm text-gray-600">Add your display name and phone number for a better experience</p>
              </div>
            </div>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowProfilePrompt(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
              >
                Skip for now
              </button>
              <button
                onClick={() => router.push('/profile')}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                Complete Profile
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}

export default HomePage