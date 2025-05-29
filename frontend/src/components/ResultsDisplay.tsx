'use client'

import { useState, useEffect } from 'react'
import { ProcessingResults, ModelFile, ModelInfo } from '@/types'
import { apiClient, downloadFileFromBlob, formatFileSize } from '@/lib/api'
import ModelViewer from './ModelViewer'

interface ResultsDisplayProps {
  sessionId: string
  results: ProcessingResults
}

export default function ResultsDisplay({ sessionId, results }: ResultsDisplayProps) {
  const [downloading, setDownloading] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState<ModelFile | null>(null)
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null)
  const [viewerError, setViewerError] = useState<string | null>(null)

  const handleDownloadFile = async (filename: string) => {
    try {
      setDownloading(filename)
      const blob = await apiClient.downloadFile(sessionId, filename)
      downloadFileFromBlob(blob, filename)
    } catch (error) {
      console.error('Download failed:', error)
      // Could show error notification here
    } finally {
      setDownloading(null)
    }
  }

  const handleDownloadAll = async () => {
    try {
      setDownloading('all')
      // Download as zip or individual files
      const response = await fetch(results.download_url)
      const blob = await response.blob()
      downloadFileFromBlob(blob, `3d-model-${sessionId.slice(0, 8)}.zip`)
    } catch (error) {
      console.error('Download all failed:', error)
    } finally {
      setDownloading(null)
    }
  }

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase()
    
    switch (ext) {
      case 'ply':
      case 'obj':
      case 'fbx':
      case 'stl':
        return (
          <svg className="h-5 w-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
        )
      case 'txt':
      case 'log':
        return (
          <svg className="h-5 w-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        )
      case 'jpg':
      case 'jpeg':
      case 'png':
        return (
          <svg className="h-5 w-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        )
      default:
        return (
          <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        )
    }
  }

  const getFileType = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase()
    
    switch (ext) {
      case 'ply':
        return '3D Model (PLY)'
      case 'obj':
        return '3D Model (OBJ)'
      case 'fbx':
        return '3D Model (FBX)'
      case 'stl':
        return '3D Model (STL)'
      case 'txt':
        return 'Text File'
      case 'log':
        return 'Log File'
      case 'jpg':
      case 'jpeg':
        return 'JPEG Image'
      case 'png':
        return 'PNG Image'
      default:
        return 'File'
    }
  }

  // Extract available 3D model files from the output_files array
  const getAvailable3DFiles = (): Array<{type: string, path: string, size: number}> => {
    if (!results.output_files) return []
    
    return results.output_files.filter(file => {
      const ext = file.path.split('.').pop()?.toLowerCase()
      return ['obj', 'ply', 'gltf', 'glb', 'fbx'].includes(ext || '')
    })
  }

  // Check if a file is a 3D model that can be viewed
  const is3DModelFile = (filename: string): boolean => {
    const ext = filename.split('.').pop()?.toLowerCase()
    return ['obj', 'ply', 'gltf', 'glb', 'fbx'].includes(ext || '')
  }

  // Get the first viewable 3D model file
  const getFirst3DModel = (): ModelFile | null => {
    const availableFiles = getAvailable3DFiles()
    const modelFile = availableFiles[0]
    
    if (modelFile) {
      const ext = modelFile.path.split('.').pop()?.toLowerCase() as 'obj' | 'ply' | 'stl'
      const filename = modelFile.path.split('/').pop() || modelFile.path
      return {
        url: `/api/sessions/${sessionId}/files/${filename}`,
        filename,
        size: modelFile.size,
        type: ext
      }
    }
    return null
  }

  // Handle model selection for viewing
  const handleViewModel = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase() as 'obj' | 'ply' | 'stl'
    const model: ModelFile = {
      url: `/api/sessions/${sessionId}/files/${filename}`,
      filename,
      size: 0,
      type: ext
    }
    setSelectedModel(model)
    setViewerError(null)
    setModelInfo(null)
  }

  const handleModelLoad = (info: ModelInfo) => {
    setModelInfo(info)
  }

  const handleModelError = (error: string) => {
    setViewerError(error)
  }

  // Auto-select first 3D model if available and none selected
  useEffect(() => {
    const first3DModel = getFirst3DModel()
    if (first3DModel && !selectedModel && !viewerError) {
      setSelectedModel(first3DModel)
    }
  }, [results.output_files, selectedModel, viewerError])

  return (
    <div className="space-y-6">
      {/* Success Message */}
      <div className="bg-green-50 border border-green-200 rounded-md p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-green-800">
              3D Model Generated Successfully!
            </h3>
            <p className="mt-1 text-sm text-green-700">
              Your photogrammetry processing is complete. Download your 3D model files below.
            </p>
          </div>
        </div>
      </div>

      {/* Statistics */}
      {results.statistics && (
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="text-lg font-medium text-gray-900 mb-3">Processing Statistics</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {results.statistics.input_images}
              </div>
              <div className="text-sm text-gray-500">Input Images</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {results.statistics.reconstructed_points?.toLocaleString() || 'N/A'}
              </div>
              <div className="text-sm text-gray-500">3D Points</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {results.statistics.cameras}
              </div>
              <div className="text-sm text-gray-500">Camera Poses</div>
            </div>
          </div>
          {results.processing_time && (
            <div className="mt-3 text-center">
              <div className="text-sm text-gray-500">
                Processing Time: <span className="font-medium">{Math.round(results.processing_time / 60)} minutes</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 3D Model Viewer */}
      {getAvailable3DFiles().length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="border-b border-gray-200 px-4 py-3">
            <h3 className="text-lg font-medium text-gray-900">3D Model Preview</h3>
            {(() => {
              const availableFiles = getAvailable3DFiles()
              return availableFiles.length > 1 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {availableFiles.map((fileObj) => {
                    const filename = fileObj.path.split('/').pop() || fileObj.path
                    return (
                      <button
                        key={filename}
                        onClick={() => handleViewModel(filename)}
                        className={`px-3 py-1 text-xs rounded-full border transition-colors ${
                          selectedModel?.filename === filename
                            ? 'bg-blue-100 border-blue-500 text-blue-700'
                            : 'bg-gray-100 border-gray-300 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {filename}
                      </button>
                    )
                  })}
                </div>
              )
            })()}
          </div>
          
          <div className="h-96 md:h-[500px]">
            {selectedModel ? (
              <ModelViewer
                modelFile={selectedModel}
                onModelLoad={handleModelLoad}
                onError={handleModelError}
                className="w-full h-full"
              />
            ) : (
              <div className="flex items-center justify-center h-full bg-gray-50">
                <div className="text-center">
                  <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                  <h3 className="mt-2 text-sm font-medium text-gray-900">No 3D model selected</h3>
                  <p className="mt-1 text-sm text-gray-500">Select a model from the list above to preview</p>
                </div>
              </div>
            )}
          </div>
          
          {viewerError && (
            <div className="border-t border-gray-200 bg-red-50 px-4 py-3">
              <div className="flex">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">3D Viewer Error</h3>
                  <p className="mt-1 text-sm text-red-700">{viewerError}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Download All Button */}
      <div className="flex justify-center">
        <button
          onClick={handleDownloadAll}
          disabled={downloading === 'all'}
          className="btn-primary px-6 py-3 text-lg"
        >
          {downloading === 'all' ? (
            <div className="flex items-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Downloading...
            </div>
          ) : (
            <div className="flex items-center">
              <svg className="mr-2 h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              Download All Files
            </div>
          )}
        </button>
      </div>

      {/* Individual Files */}
      {(() => {
        const allFiles = getAvailable3DFiles()
        return allFiles.length > 0 && (
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">Available Files</h3>
            <div className="bg-white border border-gray-200 rounded-lg divide-y divide-gray-200">
              {allFiles.map((fileObj, index) => {
                const filename = fileObj.path.split('/').pop() || fileObj.path
                return (
                  <div key={index} className="p-4 flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      {getFileIcon(filename)}
                      <div>
                        <p className="text-sm font-medium text-gray-900">{filename}</p>
                        <p className="text-xs text-gray-500">{getFileType(filename)}</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      {is3DModelFile(filename) && (
                        <button
                          onClick={() => handleViewModel(filename)}
                          className="btn-secondary text-sm bg-blue-50 hover:bg-blue-100 text-blue-700 border-blue-200"
                        >
                          <div className="flex items-center">
                            <svg className="mr-1 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                            View 3D
                          </div>
                        </button>
                      )}
                      <button
                        onClick={() => handleDownloadFile(filename)}
                        disabled={downloading === filename}
                        className="btn-secondary text-sm"
                      >
                        {downloading === filename ? (
                          <div className="flex items-center">
                            <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Downloading...
                          </div>
                        ) : (
                          <div className="flex items-center">
                            <svg className="mr-1 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            Download
                          </div>
                        )}
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )
      })()}

      {/* Usage Instructions */}
      <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
        <h3 className="text-sm font-medium text-blue-800 mb-2">How to Use Your 3D Model</h3>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• <strong>PLY files:</strong> Open in MeshLab, CloudCompare, or Blender</li>
          <li>• <strong>OBJ files:</strong> Import into 3D software like Blender, Maya, or 3ds Max</li>
          <li>• <strong>Point clouds:</strong> View in specialized software like CloudCompare</li>
          <li>• <strong>Textures:</strong> Apply to your 3D model for realistic rendering</li>
        </ul>
      </div>
    </div>
  )
}