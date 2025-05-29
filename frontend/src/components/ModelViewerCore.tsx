'use client'

import { Suspense, useRef, useEffect } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import { OrbitControls, Environment, Grid, Stats } from '@react-three/drei'
import * as THREE from 'three'
import { ModelInfo } from '@/types'
import ModelLoader from './ModelLoader'
import ModelInfo3D from './ModelInfo3D'

interface ModelViewerCoreProps {
  modelFile: { url: string; type: string; filename: string; size: number }
  onModelLoad: (info: ModelInfo) => void
  onError: (error: string) => void
  className?: string
  modelInfo?: ModelInfo | null
}

interface ModelSceneProps {
  modelFile: { url: string; type: string; filename: string }
  onModelLoad: (info: ModelInfo) => void
  onError: (error: string) => void
}

function ModelScene({ modelFile, onModelLoad, onError }: ModelSceneProps) {
  const { scene, camera } = useThree()
  const modelRef = useRef<THREE.Group>(null)
  
  useEffect(() => {
    // Clean up previous models
    return () => {
      scene.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.geometry?.dispose()
          if (Array.isArray(child.material)) {
            child.material.forEach((material) => material?.dispose())
          } else {
            child.material?.dispose()
          }
        }
      })
    }
  }, [scene, modelFile.url])

  const centerAndScaleModel = (group: THREE.Group) => {
    const box = new THREE.Box3().setFromObject(group)
    const center = box.getCenter(new THREE.Vector3())
    const size = box.getSize(new THREE.Vector3())
    
    // Center the model
    group.position.sub(center)
    
    // Scale to fit in viewport (max dimension = 4 units)
    const maxDimension = Math.max(size.x, size.y, size.z)
    const scale = maxDimension > 0 ? 4 / maxDimension : 1
    group.scale.setScalar(scale)
    
    // Position camera
    const distance = Math.max(5, maxDimension * 1.5)
    camera.position.set(distance, distance * 0.5, distance)
    camera.lookAt(0, 0, 0)
    
    return {
      center: center.toArray() as [number, number, number],
      scale,
      boundingBox: {
        min: box.min.toArray() as [number, number, number],
        max: box.max.toArray() as [number, number, number]
      }
    }
  }

  return (
    <>
      <ModelLoader
        ref={modelRef}
        url={modelFile.url}
        fileType={modelFile.type}
        onLoad={(group: THREE.Group) => {
          const { center, scale, boundingBox } = centerAndScaleModel(group)
          
          // Calculate model info
          let vertexCount = 0
          let faceCount = 0
          
          group.traverse((child) => {
            if (child instanceof THREE.Mesh && child.geometry) {
              const geometry = child.geometry
              if (geometry.attributes.position) {
                vertexCount += geometry.attributes.position.count
              }
              if (geometry.index) {
                faceCount += geometry.index.count / 3
              } else if (geometry.attributes.position) {
                faceCount += geometry.attributes.position.count / 3
              }
            }
          })
          
          onModelLoad({
            filename: modelFile.filename,
            fileSize: 0, // Will be set by parent component
            vertexCount,
            faceCount,
            center,
            scale,
            boundingBox
          })
        }}
        onError={onError}
      />
      
      {/* Lighting */}
      <ambientLight intensity={0.4} />
      <directionalLight
        position={[10, 10, 5]}
        intensity={1}
        castShadow
        shadow-mapSize-width={2048}
        shadow-mapSize-height={2048}
      />
      <directionalLight position={[-10, -10, -5]} intensity={0.5} />
      
      {/* Environment */}
      <Environment preset="studio" />
      
      {/* Grid */}
      <Grid
        args={[20, 20]}
        cellSize={0.5}
        cellThickness={0.5}
        cellColor="#6f6f6f"
        sectionSize={5}
        sectionThickness={1}
        sectionColor="#9d9d9d"
        fadeDistance={30}
        fadeStrength={1}
        followCamera={false}
        infiniteGrid={true}
      />
    </>
  )
}

export default function ModelViewerCore({ 
  modelFile, 
  onModelLoad, 
  onError, 
  className = '',
  modelInfo
}: ModelViewerCoreProps) {
  return (
    <div className={`relative w-full h-full ${className}`}>
      <Canvas
        camera={{ 
          position: [5, 5, 5], 
          fov: 50,
          near: 0.1,
          far: 1000
        }}
        shadows
        gl={{ 
          antialias: true, 
          alpha: true,
          preserveDrawingBuffer: true
        }}
        className="w-full h-full bg-gradient-to-b from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-900"
      >
        <Suspense fallback={null}>
          <ModelScene
            modelFile={modelFile}
            onModelLoad={onModelLoad}
            onError={onError}
          />
          
          <OrbitControls
            enablePan
            enableZoom
            enableRotate
            dampingFactor={0.05}
            screenSpacePanning={false}
            minDistance={1}
            maxDistance={100}
            maxPolarAngle={Math.PI}
          />
        </Suspense>
        
        {/* Performance monitoring in development */}
        {process.env.NODE_ENV === 'development' && <Stats />}
      </Canvas>
      
      {/* Model info display */}
      {modelInfo && (
        <div className="absolute top-4 left-4">
          <ModelInfo3D modelInfo={modelInfo} />
        </div>
      )}
    </div>
  )
}