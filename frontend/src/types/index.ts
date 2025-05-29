export interface UploadResponse {
  session_id: string
  upload_status: 'success' | 'partial' | 'failed'
  files_uploaded: number
  files_failed: number
  total_files: number
  total_size: number
  uploaded_files: UploadedFile[]
  failed_files?: FailedFile[]
}

export interface UploadedFile {
  original_filename: string
  saved_filename: string
  filepath: string
  size: number
}

export interface FailedFile {
  filename: string
  error: string
}

export interface ProcessingStatus {
  session_id: string
  status: 'uploaded' | 'processing' | 'complete' | 'error'
  message: string
  start_time: string
  end_time?: string
  error?: string
  output_files: Array<{
    type: string
    path: string
    size: number
    format?: string
    metadata?: any
  }>
  progress?: number
}

export interface ProcessingResults {
  session_id: string
  output_files: Array<{
    type: string
    path: string
    size: number
    format?: string
    metadata?: any
  }>
  download_url: string
  processing_time?: number
  statistics?: {
    input_images: number
    reconstructed_points: number
    cameras: number
  }
}

export interface NotificationState {
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  duration?: number
}

export interface ApiError {
  error: string
  details?: string
  session_id?: string
}

export interface HealthCheck {
  status: 'healthy' | 'degraded' | 'unhealthy'
  timestamp: string
  services: {
    upload_directory: boolean
    output_directory: boolean
    opencv: boolean
    numpy: boolean
    colmap: boolean
  }
  versions: {
    opencv: string
    numpy: string
    colmap: string
  }
}

export interface PreprocessingOptions {
  max_dimension?: number
}

export interface ProcessingOptions {
  enable_dense_reconstruction?: boolean
  enable_meshing?: boolean
  max_image_size?: number
  matcher_type?: 'exhaustive' | 'sequential' | 'spatial'
}

// 3D Model Types
export interface ModelFile {
  url: string
  filename: string
  size: number
  type: 'obj' | 'ply' | 'stl'
}

export interface ModelInfo {
  filename: string
  fileSize: number
  vertexCount?: number
  faceCount?: number
  boundingBox?: {
    min: [number, number, number]
    max: [number, number, number]
  }
  center?: [number, number, number]
  scale?: number
}

export interface ModelViewerProps {
  modelFile: ModelFile
  onModelLoad?: (info: ModelInfo) => void
  onError?: (error: string) => void
  className?: string
}

export interface ModelLoadingState {
  isLoading: boolean
  progress: number
  error?: string
  modelInfo?: ModelInfo
}