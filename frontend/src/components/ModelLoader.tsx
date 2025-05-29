'use client'

import { forwardRef, useImperativeHandle, useRef, useEffect, useState } from 'react'
import { useLoader } from '@react-three/fiber'
import { useGLTF, useFBX } from '@react-three/drei'
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js'
import { PLYLoader } from 'three/addons/loaders/PLYLoader.js'
import * as THREE from 'three'

interface ModelLoaderProps {
  url: string
  fileType: string
  onLoad?: (group: THREE.Group) => void
  onError?: (error: string) => void
  onProgress?: (progress: ProgressEvent) => void
}

const ModelLoader = forwardRef<THREE.Group, ModelLoaderProps>(
  ({ url, fileType, onLoad, onError, onProgress }, ref) => {
    const groupRef = useRef<THREE.Group>(null!)
    const [isLoading, setIsLoading] = useState(true)
    
    useImperativeHandle(ref, () => groupRef.current)

    // Create the model group based on file type
    const createModelFromData = (data: any) => {
      const group = new THREE.Group()
      
      if (data.scene) {
        // GLTF/GLB format
        group.add(data.scene.clone())
      } else if (data instanceof THREE.Group) {
        // OBJ format
        const children = [...data.children]
        children.forEach(child => {
          group.add(child.clone())
        })
      } else if (data instanceof THREE.BufferGeometry) {
        // PLY format (geometry only)
        const material = new THREE.MeshStandardMaterial({
          color: 0x888888,
          metalness: 0.2,
          roughness: 0.7,
          flatShading: true
        })
        
        // Check if it's a point cloud or mesh
        if (data.index || data.attributes.normal) {
          // It's a mesh
          const mesh = new THREE.Mesh(data, material)
          group.add(mesh)
        } else {
          // It's a point cloud
          const pointsMaterial = new THREE.PointsMaterial({
            color: 0x888888,
            size: 0.02,
            sizeAttenuation: true
          })
          const points = new THREE.Points(data, pointsMaterial)
          group.add(points)
        }
      }
      
      return group
    }

    // Load model based on file type
    let modelData: any = null
    let loadError: string | null = null

    try {
      const fileExt = fileType.toLowerCase()
      
      if (fileExt === 'obj') {
        modelData = useLoader(OBJLoader, url)
      } else if (fileExt === 'gltf' || fileExt === 'glb') {
        modelData = useGLTF(url)
      } else if (fileExt === 'fbx') {
        modelData = useFBX(url)
      } else if (fileExt === 'ply') {
        modelData = useLoader(PLYLoader, url)
      } else {
        loadError = `Unsupported file format: ${fileExt}. Supported formats: OBJ, GLTF, GLB, FBX, PLY`
      }
    } catch (error) {
      console.error('Model loading error:', error)
      loadError = `Failed to load model: ${error instanceof Error ? error.message : 'Unknown error'}`
    }

    useEffect(() => {
      if (loadError) {
        onError?.(loadError)
        setIsLoading(false)
        return
      }

      if (modelData && groupRef.current) {
        try {
          // Clear previous content
          while (groupRef.current.children.length > 0) {
            const child = groupRef.current.children[0]
            groupRef.current.remove(child)
            
            // Dispose of geometries and materials
            if (child instanceof THREE.Mesh) {
              child.geometry?.dispose()
              if (Array.isArray(child.material)) {
                child.material.forEach(material => material?.dispose())
              } else {
                child.material?.dispose()
              }
            }
          }

          // Create and add the new model
          const newModel = createModelFromData(modelData)
          
          // Apply default materials to any mesh without materials
          newModel.traverse((child) => {
            if (child instanceof THREE.Mesh) {
              if (!child.material || (Array.isArray(child.material) && child.material.length === 0)) {
                child.material = new THREE.MeshStandardMaterial({
                  color: 0x888888,
                  metalness: 0.2,
                  roughness: 0.7
                })
              }
              
              // Enable shadows
              child.castShadow = true
              child.receiveShadow = true
            }
          })
          
          // Add to our group
          const children = [...newModel.children]
          children.forEach(child => {
            groupRef.current.add(child)
          })

          setIsLoading(false)
          onLoad?.(groupRef.current)
        } catch (error) {
          console.error('Error processing model:', error)
          onError?.(error instanceof Error ? error.message : 'Unknown processing error')
          setIsLoading(false)
        }
      }
    }, [modelData, loadError, onLoad, onError])

    if (loadError) {
      return null
    }

    return <group ref={groupRef} />
  }
)

ModelLoader.displayName = 'ModelLoader'

export default ModelLoader