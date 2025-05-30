'use client'

import { Suspense, useRef, useEffect, useState } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { useLoader } from '@react-three/fiber'
import { PLYLoader } from 'three/addons/loaders/PLYLoader.js'
import * as THREE from 'three'
import LoadingSpinner from './LoadingSpinner'

interface PLYViewerCoreProps {
  modelFile: { url: string; filename: string; size: number }
  onModelLoad?: (info: any) => void
  onError?: (error: string) => void
  className?: string
}

interface PLYViewerToolsProps {
  onResetView: () => void
  onToggleFullscreen: () => void
  onPointSizeChange: (size: number) => void
  pointSize: number
  isFullscreen: boolean
}

interface PLYSceneProps {
  modelFile: { url: string; filename: string }
  onModelLoad?: (info: any) => void
  onError?: (error: string) => void
  pointSize: number
  controlsRef: React.MutableRefObject<any>
}

function PLYViewerTools({ 
  onResetView, 
  onToggleFullscreen, 
  onPointSizeChange, 
  pointSize, 
  isFullscreen 
}: PLYViewerToolsProps) {
  return (
    <div className="absolute top-4 right-4 z-10 bg-black/80 backdrop-blur-sm rounded-lg p-3 space-y-2">
      {/* Point Size Control */}
      <div className="flex items-center space-x-2">
        <label className="text-white text-xs font-medium">Point Size:</label>
        <input
          type="range"
          min="0.005"
          max="0.1"
          step="0.005"
          value={pointSize}
          onChange={(e) => onPointSizeChange(parseFloat(e.target.value))}
          className="w-16 h-1 bg-gray-600 rounded-lg appearance-none cursor-pointer"
        />
        <span className="text-white text-xs w-8">{pointSize.toFixed(3)}</span>
      </div>
      
      {/* Control Buttons */}
      <div className="flex flex-col space-y-1">
        <button
          onClick={onResetView}
          className="bg-white/20 hover:bg-white/30 text-white text-xs px-3 py-1 rounded transition-colors"
          title="Reset View"
        >
          <div className="flex items-center space-x-1">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Reset</span>
          </div>
        </button>
        
        <button
          onClick={onToggleFullscreen}
          className="bg-white/20 hover:bg-white/30 text-white text-xs px-3 py-1 rounded transition-colors"
          title="Toggle Fullscreen"
        >
          <div className="flex items-center space-x-1">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              {isFullscreen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 9V4.5M9 9H4.5M9 9L3.5 3.5M15 9h4.5M15 9V4.5M15 9l5.5-5.5M9 15v4.5M9 15H4.5M9 15l-5.5 5.5M15 15h4.5M15 15v4.5m0-4.5l5.5 5.5" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2 2z" />
              )}
            </svg>
            <span>{isFullscreen ? 'Exit' : 'Full'}</span>
          </div>
        </button>
      </div>
      
      {/* Info */}
      <div className="border-t border-white/20 pt-2">
        <div className="text-white/70 text-xs space-y-1">
          <div>• Drag to rotate</div>
          <div>• Scroll to zoom</div>
          <div>• Right-click drag to pan</div>
        </div>
      </div>
    </div>
  )
}

function PLYScene({ modelFile, onModelLoad, onError, pointSize, controlsRef }: PLYSceneProps) {
  const { scene, camera } = useThree()
  const pointsRef = useRef<THREE.Points>(null)
  const [modelData, setModelData] = useState<THREE.BufferGeometry | null>(null)
  
  // Load PLY file
  useEffect(() => {
    const loader = new PLYLoader()
    
    loader.load(
      modelFile.url,
      (geometry: THREE.BufferGeometry) => {
        setModelData(geometry)
      },
      undefined,
      (error: any) => {
        console.error('PLY loading error:', error)
        onError?.('Failed to load PLY file')
      }
    )
  }, [modelFile.url, onError])

  // Create point cloud when model data is loaded
  useEffect(() => {
    if (!modelData || !pointsRef.current) return

    // Clean up previous geometry
    if (pointsRef.current.geometry) {
      pointsRef.current.geometry.dispose()
    }

    // Set the new geometry
    pointsRef.current.geometry = modelData

    // Center and scale the model
    const box = new THREE.Box3().setFromObject(pointsRef.current)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    
    // Center the point cloud
    pointsRef.current.position.sub(center)
    
    // Scale to fit in viewport (max dimension = 4 units)
    const maxDimension = Math.max(size.x, size.y, size.z)
    const scale = maxDimension > 0 ? 4 / maxDimension : 1
    pointsRef.current.scale.setScalar(scale)
    
    // Position camera
    const distance = Math.max(6, maxDimension * 1.5)
    camera.position.set(distance, distance * 0.5, distance)
    camera.lookAt(0, 0, 0)
    
    // Calculate point count
    const pointCount = modelData.attributes.position ? modelData.attributes.position.count : 0
    
    onModelLoad?.({
      filename: modelFile.filename,
      pointCount,
      center: center.toArray(),
      scale,
      boundingBox: {
        min: box.min.toArray(),
        max: box.max.toArray()
      }
    })
  }, [modelData, camera, onModelLoad, modelFile.filename])

  // Update point size when it changes
  useEffect(() => {
    if (pointsRef.current?.material) {
      const material = pointsRef.current.material as THREE.PointsMaterial
      if (material && 'size' in material) {
        material.size = pointSize
        material.needsUpdate = true
      }
    }
  }, [pointSize])

  return (
    <>
      {/* Point Cloud */}
      <points ref={pointsRef}>
        <pointsMaterial
          color="white"
          size={pointSize}
          sizeAttenuation={true}
          transparent={true}
          opacity={0.9}
          vertexColors={false}
        />
      </points>
      
      {/* Lighting (minimal for point clouds) */}
      <ambientLight intensity={0.3} />
      
      {/* Controls */}
      <OrbitControls
        ref={controlsRef}
        enablePan={true}
        enableZoom={true}
        enableRotate={true}
        dampingFactor={0.05}
        screenSpacePanning={false}
        minDistance={0.5}
        maxDistance={50}
        maxPolarAngle={Math.PI}
      />
    </>
  )
}

export default function PLYViewerCore({ modelFile, onModelLoad, onError, className = '' }: PLYViewerCoreProps) {
  const [pointSize, setPointSize] = useState(0.02)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const controlsRef = useRef<any>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const handleModelLoad = (info: any) => {
    setIsLoading(false)
    onModelLoad?.(info)
  }

  const handleError = (error: string) => {
    setIsLoading(false)
    setLoadError(error)
    onError?.(error)
  }

  const handleResetView = () => {
    if (controlsRef.current) {
      controlsRef.current.reset()
    }
  }

  const handleToggleFullscreen = () => {
    if (!containerRef.current) return

    if (!isFullscreen) {
      if (containerRef.current.requestFullscreen) {
        containerRef.current.requestFullscreen()
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen()
      }
    }
  }

  // Listen for fullscreen changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }

    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  if (loadError) {
    return (
      <div className={`flex items-center justify-center h-full bg-black rounded-lg ${className}`}>
        <div className="text-center">
          <div className="text-red-400 text-4xl mb-4">⚠️</div>
          <h3 className="text-lg font-semibold text-white mb-2">
            Failed to Load PLY File
          </h3>
          <p className="text-sm text-gray-300 max-w-md">
            {loadError}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div 
      ref={containerRef}
      className={`relative w-full h-full bg-black rounded-lg overflow-hidden ${className} ${
        isFullscreen ? 'fixed inset-0 z-50 rounded-none' : ''
      }`}
    >
      <Canvas
        camera={{ 
          position: [5, 5, 5], 
          fov: 50,
          near: 0.1,
          far: 1000
        }}
        gl={{ 
          antialias: true,
          alpha: false,
          preserveDrawingBuffer: true
        }}
        className="w-full h-full"
        style={{ background: 'black' }}
      >
        <Suspense fallback={null}>
          <PLYScene
            modelFile={modelFile}
            onModelLoad={handleModelLoad}
            onError={handleError}
            pointSize={pointSize}
            controlsRef={controlsRef}
          />
        </Suspense>
      </Canvas>

      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-black/80 flex items-center justify-center backdrop-blur-sm z-10">
          <div className="text-center">
            <LoadingSpinner size="lg" />
            <p className="mt-4 text-sm text-white">
              Loading PLY point cloud...
            </p>
          </div>
        </div>
      )}

      {/* Tools */}
      {!isLoading && !loadError && (
        <PLYViewerTools
          onResetView={handleResetView}
          onToggleFullscreen={handleToggleFullscreen}
          onPointSizeChange={setPointSize}
          pointSize={pointSize}
          isFullscreen={isFullscreen}
        />
      )}

      {/* Point count info */}
      {!isLoading && !loadError && (
        <div className="absolute bottom-4 left-4 bg-black/80 backdrop-blur-sm rounded-lg p-2">
          <div className="text-white text-xs">
            PLY Point Cloud Viewer
          </div>
        </div>
      )}
    </div>
  )
}