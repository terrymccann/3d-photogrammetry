'use client'

import { useState, useCallback, useRef } from 'react'
import { validateImageFiles, formatFileSize } from '@/lib/api'

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void
  isUploading: boolean
  disabled?: boolean
  maxFiles?: number
  maxFileSize?: number // in bytes
}

export default function FileUpload({
  onFilesSelected,
  isUploading,
  disabled = false,
  maxFiles = 50,
  maxFileSize = 16 * 1024 * 1024, // 16MB
}: FileUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [errors, setErrors] = useState<string[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)

  const validateFiles = useCallback((files: File[]) => {
    const newErrors: string[] = []
    
    // Check file count
    if (files.length > maxFiles) {
      newErrors.push(`Maximum ${maxFiles} files allowed`)
      files = files.slice(0, maxFiles)
    }
    
    // Validate each file
    const { valid, invalid } = validateImageFiles(files)
    
    if (invalid.length > 0) {
      newErrors.push(`${invalid.length} files are not valid images (only JPG, PNG allowed)`)
    }
    
    // Check file sizes
    const oversizedFiles = valid.filter(file => file.size > maxFileSize)
    if (oversizedFiles.length > 0) {
      newErrors.push(`${oversizedFiles.length} files exceed size limit (${formatFileSize(maxFileSize)})`)
    }
    
    const validFiles = valid.filter(file => file.size <= maxFileSize)
    
    setErrors(newErrors)
    return validFiles
  }, [maxFiles, maxFileSize])

  const handleFileSelection = useCallback((files: File[]) => {
    const validFiles = validateFiles(files)
    setSelectedFiles(validFiles)
  }, [validateFiles])

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (!disabled) {
      setIsDragOver(true)
    }
  }, [disabled])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragOver(false)
    
    if (disabled) return
    
    const files = Array.from(e.dataTransfer.files)
    handleFileSelection(files)
  }, [disabled, handleFileSelection])

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    handleFileSelection(files)
  }, [handleFileSelection])

  const handleUpload = useCallback(() => {
    if (selectedFiles.length > 0) {
      onFilesSelected(selectedFiles)
    }
  }, [selectedFiles, onFilesSelected])

  const handleClearFiles = useCallback(() => {
    setSelectedFiles([])
    setErrors([])
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }, [])

  const handleSelectFiles = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const totalSize = selectedFiles.reduce((sum, file) => sum + file.size, 0)

  return (
    <div className="space-y-4">
      {/* Upload Area */}
      <div
        className={`upload-area ${isDragOver ? 'drag-over' : ''} ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        onClick={!disabled ? handleSelectFiles : undefined}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/jpeg,image/jpg,image/png"
          onChange={handleFileInputChange}
          className="hidden"
          disabled={disabled}
        />
        
        <div className="flex flex-col items-center">
          <div className="text-gray-400 mb-4">
            <svg className="mx-auto h-12 w-12" stroke="currentColor" fill="none" viewBox="0 0 48 48">
              <path
                d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div className="text-center">
            <p className="text-lg font-medium text-gray-900">
              {isDragOver ? 'Drop images here' : 'Upload your images'}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              Drag and drop images or click to browse
            </p>
            <p className="text-xs text-gray-400 mt-2">
              JPG, PNG up to {formatFileSize(maxFileSize)} • Max {maxFiles} files
            </p>
          </div>
        </div>
      </div>

      {/* Errors */}
      {errors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-md p-3">
          <div className="flex">
            <div className="text-red-400">
              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">File Upload Issues</h3>
              <ul className="mt-1 text-sm text-red-700 list-disc list-inside">
                {errors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Selected Files */}
      {selectedFiles.length > 0 && (
        <div className="bg-gray-50 rounded-md p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-900">
              Selected Files ({selectedFiles.length})
            </h3>
            <button
              onClick={handleClearFiles}
              disabled={isUploading}
              className="text-sm text-gray-500 hover:text-gray-700 disabled:opacity-50"
            >
              Clear all
            </button>
          </div>
          
          <div className="space-y-2 max-h-32 overflow-y-auto">
            {selectedFiles.map((file, index) => (
              <div key={index} className="flex items-center justify-between py-1">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900 truncate">{file.name}</p>
                </div>
                <p className="text-xs text-gray-500 ml-2">{formatFileSize(file.size)}</p>
              </div>
            ))}
          </div>
          
          <div className="mt-3 pt-3 border-t border-gray-200">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500">Total size:</span>
              <span className="font-medium text-gray-900">{formatFileSize(totalSize)}</span>
            </div>
          </div>
        </div>
      )}

      {/* Upload Button */}
      {selectedFiles.length > 0 && (
        <div className="flex justify-end">
          <button
            onClick={handleUpload}
            disabled={isUploading || selectedFiles.length === 0}
            className="btn-primary"
          >
            {isUploading ? (
              <div className="flex items-center">
                <svg className="animate-spin -ml-1 mr-3 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Uploading...
              </div>
            ) : (
              `Upload ${selectedFiles.length} file${selectedFiles.length !== 1 ? 's' : ''}`
            )}
          </button>
        </div>
      )}
    </div>
  )
}