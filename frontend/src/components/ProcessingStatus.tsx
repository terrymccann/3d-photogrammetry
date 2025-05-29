'use client'

import { ProcessingStatus as ProcessingStatusType } from '@/types'

interface ProcessingStatusProps {
  status: ProcessingStatusType
}

export default function ProcessingStatus({ status }: ProcessingStatusProps) {
  const getStatusColor = (statusType: string) => {
    switch (statusType) {
      case 'uploaded':
        return 'text-blue-600 bg-blue-100'
      case 'processing':
        return 'text-yellow-600 bg-yellow-100'
      case 'complete':
        return 'text-green-600 bg-green-100'
      case 'error':
        return 'text-red-600 bg-red-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  const getStatusIcon = (statusType: string) => {
    switch (statusType) {
      case 'uploaded':
        return (
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
        )
      case 'processing':
        return (
          <svg className="h-5 w-5 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        )
      case 'complete':
        return (
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        )
      case 'error':
        return (
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )
      default:
        return null
    }
  }

  const formatTime = (isoString: string) => {
    try {
      return new Date(isoString).toLocaleString()
    } catch {
      return isoString
    }
  }

  const getProcessingDuration = () => {
    if (!status.start_time) return null
    
    const start = new Date(status.start_time)
    const end = status.end_time ? new Date(status.end_time) : new Date()
    
    const diffMs = end.getTime() - start.getTime()
    const diffMins = Math.floor(diffMs / (1000 * 60))
    const diffSecs = Math.floor((diffMs % (1000 * 60)) / 1000)
    
    if (diffMins > 0) {
      return `${diffMins}m ${diffSecs}s`
    }
    return `${diffSecs}s`
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-start space-x-3">
        <div className={`flex-shrink-0 p-2 rounded-full ${getStatusColor(status.status)}`}>
          {getStatusIcon(status.status)}
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-gray-900 capitalize">
              {status.status}
            </h3>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(status.status)}`}>
              {status.status}
            </span>
          </div>
          
          <p className="mt-1 text-sm text-gray-600">
            {status.message}
          </p>
          
          {/* Progress bar for processing */}
          {status.status === 'processing' && status.progress !== undefined && (
            <div className="mt-3">
              <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
                <span>Progress</span>
                <span>{Math.round(status.progress)}%</span>
              </div>
              <div className="progress-bar">
                <div 
                  className="progress-fill" 
                  style={{ width: `${status.progress}%` }}
                />
              </div>
            </div>
          )}
          
          {/* Timing information */}
          <div className="mt-3 grid grid-cols-1 gap-2 text-xs text-gray-500">
            {status.start_time && (
              <div className="flex justify-between">
                <span>Started:</span>
                <span>{formatTime(status.start_time)}</span>
              </div>
            )}
            
            {status.end_time && (
              <div className="flex justify-between">
                <span>Completed:</span>
                <span>{formatTime(status.end_time)}</span>
              </div>
            )}
            
            {status.start_time && (
              <div className="flex justify-between">
                <span>Duration:</span>
                <span>{getProcessingDuration()}</span>
              </div>
            )}
          </div>
          
          {/* Error details */}
          {status.status === 'error' && status.error && (
            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md">
              <h4 className="text-sm font-medium text-red-800">Error Details</h4>
              <p className="mt-1 text-sm text-red-700">{status.error}</p>
            </div>
          )}
          
          {/* Output files */}
          {status.output_files && status.output_files.length > 0 && (
            <div className="mt-3">
              <h4 className="text-sm font-medium text-gray-700 mb-2">
                Output Files ({status.output_files.length})
              </h4>
              <div className="space-y-1">
                {status.output_files.slice(0, 5).map((file, index) => (
                  <div key={index} className="text-xs text-gray-600 font-mono bg-gray-50 px-2 py-1 rounded">
                    <div className="flex justify-between items-center">
                      <span className="font-medium">{file.type}</span>
                      <span className="text-gray-400">{(file.size / 1024).toFixed(1)} KB</span>
                    </div>
                    <div className="text-gray-500 truncate">{file.path.split('/').pop()}</div>
                  </div>
                ))}
                {status.output_files.length > 5 && (
                  <div className="text-xs text-gray-500">
                    ... and {status.output_files.length - 5} more files
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}