'use client'

import { useState, useCallback } from 'react'
import { NotificationState } from '@/types'

export const useNotification = () => {
  const [notification, setNotification] = useState<NotificationState | null>(null)

  const showNotification = useCallback((
    type: NotificationState['type'],
    title: string,
    message: string,
    duration: number = 5000
  ) => {
    setNotification({ type, title, message, duration })
    
    if (duration > 0) {
      setTimeout(() => {
        setNotification(null)
      }, duration)
    }
  }, [])

  const hideNotification = useCallback(() => {
    setNotification(null)
  }, [])

  return {
    notification,
    showNotification,
    hideNotification,
  }
}