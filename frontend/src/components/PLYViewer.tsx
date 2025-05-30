'use client'

import dynamic from 'next/dynamic'
import LoadingSpinner from './LoadingSpinner'

interface PLYViewerProps {
  modelFile: { url: string; filename: string; size: number }
  onModelLoad?: (info: any) => void
  onError?: (error: string) => void
  className?: string
}

// Dynamically import the core PLY viewer to avoid SSR issues
const PLYViewerCore = dynamic(() => import('./PLYViewerCore'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-black rounded-lg">
      <div className="text-center">
        <LoadingSpinner size="lg" />
        <p className="mt-4 text-white text-sm">Loading PLY viewer...</p>
      </div>
    </div>
  )
})

export default function PLYViewer(props: PLYViewerProps) {
  return <PLYViewerCore {...props} />
}