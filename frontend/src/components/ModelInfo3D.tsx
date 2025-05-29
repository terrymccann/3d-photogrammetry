'use client'

import { useState } from 'react'
import { ModelInfo } from '@/types'

interface ModelInfo3DProps {
  modelInfo: ModelInfo
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatNumber = (num: number): string => {
  return num.toLocaleString()
}

export default function ModelInfo3D({ modelInfo }: ModelInfo3DProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center justify-between"
      >
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          <span className="font-medium text-gray-900 dark:text-gray-100">
            Model Info
          </span>
        </div>
        <svg
          className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      
      {isExpanded && (
        <div className="px-4 pb-4 space-y-3 text-sm">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <span className="text-gray-500 dark:text-gray-400">Filename:</span>
              <p className="font-mono text-gray-900 dark:text-gray-100 truncate" title={modelInfo.filename}>
                {modelInfo.filename}
              </p>
            </div>
            
            {modelInfo.fileSize > 0 && (
              <div>
                <span className="text-gray-500 dark:text-gray-400">File Size:</span>
                <p className="font-mono text-gray-900 dark:text-gray-100">
                  {formatFileSize(modelInfo.fileSize)}
                </p>
              </div>
            )}
            
            {modelInfo.vertexCount && (
              <div>
                <span className="text-gray-500 dark:text-gray-400">Vertices:</span>
                <p className="font-mono text-gray-900 dark:text-gray-100">
                  {formatNumber(modelInfo.vertexCount)}
                </p>
              </div>
            )}
            
            {modelInfo.faceCount && (
              <div>
                <span className="text-gray-500 dark:text-gray-400">Faces:</span>
                <p className="font-mono text-gray-900 dark:text-gray-100">
                  {formatNumber(modelInfo.faceCount)}
                </p>
              </div>
            )}
          </div>
          
          {modelInfo.boundingBox && (
            <div>
              <span className="text-gray-500 dark:text-gray-400">Bounding Box:</span>
              <div className="mt-1 space-y-1 font-mono text-xs">
                <div className="text-gray-900 dark:text-gray-100">
                  Min: ({modelInfo.boundingBox.min.map(v => v.toFixed(2)).join(', ')})
                </div>
                <div className="text-gray-900 dark:text-gray-100">
                  Max: ({modelInfo.boundingBox.max.map(v => v.toFixed(2)).join(', ')})
                </div>
              </div>
            </div>
          )}
          
          {modelInfo.center && (
            <div>
              <span className="text-gray-500 dark:text-gray-400">Center:</span>
              <p className="font-mono text-xs text-gray-900 dark:text-gray-100">
                ({modelInfo.center.map(v => v.toFixed(2)).join(', ')})
              </p>
            </div>
          )}
          
          {modelInfo.scale && (
            <div>
              <span className="text-gray-500 dark:text-gray-400">Scale Factor:</span>
              <p className="font-mono text-gray-900 dark:text-gray-100">
                {modelInfo.scale.toFixed(3)}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}