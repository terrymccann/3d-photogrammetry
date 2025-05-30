'use client'

import { useState } from 'react'
import FileUpload from '@/components/FileUpload'
import ProcessingStatus from '@/components/ProcessingStatus'
import ResultsDisplay from '@/components/ResultsDisplay'
import Notification from '@/components/Notification'
import { usePhotogrammetry } from '@/hooks/usePhotogrammetry'
import { useNotification } from '@/hooks/useNotification'

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const {
    uploadFiles,
    startProcessing,
    getStatus,
    status,
    isUploading,
    isProcessing,
    results,
    error
  } = usePhotogrammetry()
  
  const { 
    notification, 
    showNotification, 
    hideNotification 
  } = useNotification()

  const handleFilesSelected = async (files: File[]) => {
    try {
      const response = await uploadFiles(files)
      if (response.session_id) {
        setSessionId(response.session_id)
        
        // Fetch the status to show the "Start Processing" button
        try {
          await getStatus(response.session_id)
        } catch (statusErr) {
          console.warn('Failed to fetch status:', statusErr)
        }
        
        showNotification(
          'success',
          'Files uploaded successfully!',
          `${response.files_uploaded} files uploaded. Click "Start Processing" to begin.`
        )
      }
    } catch (err) {
      showNotification(
        'error',
        'Upload failed',
        error || 'An error occurred during upload.'
      )
    }
  }

  const handleStartProcessing = async () => {
    if (!sessionId) return
    
    try {
      await startProcessing(sessionId)
      showNotification(
        'info',
        'Processing started',
        'Your 3D model is being generated...'
      )
    } catch (err) {
      showNotification(
        'error',
        'Processing failed',
        error || 'An error occurred during processing.'
      )
    }
  }

  return (
    <div className="px-4 sm:px-0">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          3D Photogrammetry
        </h1>
        <p className="text-lg text-gray-600">
          Upload multiple images of an object to create a 3D model.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Upload Section */}
        <div className="lg:col-span-2">
          <div className="card">
            <h2 className="text-xl font-semibold mb-4">Upload Images</h2>
            <FileUpload
              onFilesSelected={handleFilesSelected}
              isUploading={isUploading}
              disabled={isProcessing}
            />
            
            {sessionId && status && (
              <div className="mt-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium">Session: {sessionId.slice(0, 8)}...</h3>
                  {status.status === 'uploaded' && (
                    <button
                      onClick={handleStartProcessing}
                      disabled={isProcessing}
                      className="btn-primary"
                    >
                      {isProcessing ? 'Starting...' : 'Start Processing'}
                    </button>
                  )}
                </div>
                <ProcessingStatus status={status} />
              </div>
            )}
          </div>
        </div>

        {/* Status and Results Section */}
        <div>
          <div className="card">
            <h2 className="text-xl font-semibold mb-4">Status</h2>
            
            {!sessionId ? (
              <div className="text-center py-8">
                <div className="text-gray-400 mb-2">
                  <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <p className="text-gray-500">Upload images to get started</p>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-500">Session ID</span>
                  <span className="text-sm font-mono text-gray-900">
                    {sessionId.slice(0, 8)}...
                  </span>
                </div>
                
                {status && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-500">Status</span>
                    <span className={`status-badge status-${status.status}`}>
                      {status.status}
                    </span>
                  </div>
                )}
                
                {status?.status === 'complete' && results && (
                  <ResultsDisplay 
                    sessionId={sessionId}
                    results={results}
                  />
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Notification */}
      {notification && (
        <Notification
          type={notification.type}
          title={notification.title}
          message={notification.message}
          onClose={hideNotification}
        />
      )}
    </div>
  )
}