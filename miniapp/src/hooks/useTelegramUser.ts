'use client'
import { useEffect, useState } from 'react'

export interface TelegramUser {
  id: number
  first_name: string
  last_name?: string
  username?: string
  language_code?: string
}

export function useTelegramUser() {
  const [tgUser, setTgUser] = useState<TelegramUser | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const init = () => {
      const tg = (window as any).Telegram?.WebApp
      if (!tg) {
        console.error('[TG] Telegram WebApp not found!')
        setReady(true)
        return
      }
      tg.ready()
      tg.expand()
      const user = tg.initDataUnsafe?.user
      if (user) {
        console.log('[TG] User loaded:', user.id, user.first_name)
        setTgUser(user)
      } else {
        console.warn('[TG] No user. initData:', tg.initData)
      }
      setReady(true)
    }

    if ((window as any).Telegram?.WebApp) {
      init()
    } else {
      const timer = setTimeout(init, 500)
      return () => clearTimeout(timer)
    }
  }, [])

  return { tgUser, ready }
}
