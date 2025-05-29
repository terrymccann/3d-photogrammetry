'use client'

import { Suspense, useRef, useEffect, useState } from 'react'
import { ErrorBoundary } from 'react-error-boundary'
import dynamic from 'next/dynamic'
import { ModelViewerProps, ModelLoadingState, ModelInfo } from '@/types'
import LoadingSpinner from './LoadingSpinner'

// Dynamically import the entire viewer to avoid SSR issues
const DynamicModelViewerCore = dynamic(() => import('./ModelViewerCore'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-gray-50 dark:bg-gray-900 rounded-lg">
      <LoadingSpinner size="lg" />
      <p className="ml-4 text-sm text-gray-600 dark:text-gray-400">
        Loading 3D viewer...
      </p>
    </div>
  )
})

function ModelViewerFallback({ error }: { error: Error }) {
  return (
    <div className="flex flex-col items-center justify-center h-full bg-gray-100 dark:bg-gray-800 rounded-lg">
      <div className="text-red-500 text-xl mb-2">⚠️</div>
      <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-2">
        3D Viewer Error
      </h3>
      <p className="text-sm text-gray-600 dark:text-gray-400 text-center max-w-md">
        {error.message || 'Failed to load 3D model. Please check the file format and try again.'}
      </p>
    </div>
  )
}

function LoadingFallback() {
  return (
    <div className="flex flex-col items-center justify-center h-full bg-gray-50 dark:bg-gray-900 rounded-lg">
      <LoadingSpinner size="lg" />
      <p className="mt-4 text-sm text-gray-600 dark:text-gray-400">
        Loading 3D model...
      </p>
    </div>
  )
}

export default function ModelViewer({
  modelFile,
  onModelLoad,
  onError,
  className = ''
}: ModelViewerProps) {
  const [loadingState, setLoadingState] = useState<ModelLoadingState>({
    isLoading: true,
    progress: 0
  })

  const handleModelLoad = (info: ModelInfo) => {
    setLoadingState({
      isLoading: false,
      progress: 100,
      modelInfo: info
    })
    onModelLoad?.(info)
  }

  const handleError = (error: string) => {
    setLoadingState({
      isLoading: false,
      progress: 0,
      error
    })
    onError?.(error)
  }

  return (
    <div className={`relative w-full h-full min-h-96 ${className}`}>
      <ErrorBoundary
        FallbackComponent={ModelViewerFallback}
        onError={(error: any) => handleError(error.message)}
      >
        <DynamicModelViewerCore
          modelFile={modelFile}
          onModelLoad={handleModelLoad}
          onError={handleError}
          className="w-full h-full"
          modelInfo={loadingState.modelInfo}
        />
        
        {/* Loading overlay */}
        {loadingState.isLoading && (
          <div className="absolute inset-0 bg-white/80 dark:bg-gray-900/80 flex items-center justify-center backdrop-blur-sm z-10">
            <LoadingFallback />
          </div>
        )}
        
        {/* Error overlay */}
        {loadingState.error && (
          <div className="absolute inset-0 bg-white/90 dark:bg-gray-900/90 flex items-center justify-center backdrop-blur-sm z-10">
            <div className="text-center">
              <div className="text-red-500 text-4xl mb-4">⚠️</div>
              <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-2">
                Failed to Load Model
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 max-w-md">
                {loadingState.error}
              </p>
            </div>
          </div>
        )}
      </ErrorBoundary>
    </div>
  )
}