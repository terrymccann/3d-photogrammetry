'use client'

import { useState, useCallback } from 'react'
import { apiClient } from '@/lib/api'
import { 
  UploadResponse, 
  ProcessingStatus, 
  ProcessingResults,
  ProcessingOptions,
  PreprocessingOptions 
} from '@/types'

export const usePhotogrammetry = () => {
  const [isUploading, setIsUploading] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [status, setStatus] = useState<ProcessingStatus | null>(null)
  const [results, setResults] = useState<ProcessingResults | null>(null)
  const [error, setError] = useState<string | null>(null)

  const uploadFiles = useCallback(async (files: File[]): Promise<UploadResponse> => {
    setIsUploading(true)
    setError(null)
    
    try {
      const response = await apiClient.uploadFiles(files)
      return response
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Upload failed'
      setError(errorMessage)
      throw err
    } finally {
      setIsUploading(false)
    }
  }, [])

  const preprocessImages = useCallback(async (
    sessionId: string, 
    options: PreprocessingOptions = {}
  ) => {
    try {
      const response = await apiClient.preprocessImages(sessionId, options)
      return response
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Preprocessing failed'
      setError(errorMessage)
      throw err
    }
  }, [])

  const startProcessing = useCallback(async (
    sessionId: string, 
    options: ProcessingOptions = {}
  ) => {
    setIsProcessing(true)
    setError(null)
    
    try {
      const response = await apiClient.startProcessing(sessionId, options)
      
      // Start polling for status updates
      const pollStatus = async () => {
        try {
          const statusResponse = await apiClient.getProcessingStatus(sessionId)
          setStatus(statusResponse)
          
          if (statusResponse.status === 'complete') {
            setIsProcessing(false)
            try {
              const resultsResponse = await apiClient.getProcessingResults(sessionId)
              setResults(resultsResponse)
            } catch (resultsErr) {
              console.warn('Failed to fetch results:', resultsErr)
            }
          } else if (statusResponse.status === 'error') {
            setIsProcessing(false)
            setError(statusResponse.error || 'Processing failed')
          } else if (statusResponse.status === 'processing') {
            // Continue polling
            setTimeout(pollStatus, 2000)
          }
        } catch (pollErr) {
          console.error('Status polling error:', pollErr)
          setTimeout(pollStatus, 5000) // Retry with longer delay
        }
      }
      
      // Start polling after a short delay
      setTimeout(pollStatus, 1000)
      
      return response
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Processing failed'
      setError(errorMessage)
      setIsProcessing(false)
      throw err
    }
  }, [])

  const getStatus = useCallback(async (sessionId: string) => {
    try {
      const response = await apiClient.getProcessingStatus(sessionId)
      setStatus(response)
      return response
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get status'
      setError(errorMessage)
      throw err
    }
  }, [])

  const getResults = useCallback(async (sessionId: string) => {
    try {
      const response = await apiClient.getProcessingResults(sessionId)
      setResults(response)
      return response
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get results'
      setError(errorMessage)
      throw err
    }
  }, [])

  const downloadFile = useCallback(async (sessionId: string, filename: string) => {
    try {
      const blob = await apiClient.downloadFile(sessionId, filename)
      
      // Create download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
      return blob
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Download failed'
      setError(errorMessage)
      throw err
    }
  }, [])

  const reset = useCallback(() => {
    setIsUploading(false)
    setIsProcessing(false)
    setStatus(null)
    setResults(null)
    setError(null)
  }, [])

  return {
    // State
    isUploading,
    isProcessing,
    status,
    results,
    error,
    
    // Actions
    uploadFiles,
    preprocessImages,
    startProcessing,
    getStatus,
    getResults,
    downloadFile,
    reset,
  }
}