'use client'
import { useEffect, useState } from 'react'

export function useTelegramUser() {
  const [tgUser, setTgUser] = useState<any>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let attempts = 0
    const check = () => {
      const tg = (window as any).Telegram?.WebApp
      if (tg && tg.initDataUnsafe?.user) {
        tg.ready()
        tg.expand()
        setTgUser(tg.initDataUnsafe.user)
        setReady(true)
        console.log('[TG] WebApp ready, user found:', tg.initDataUnsafe.user.id)
        return true
      }
      return false
    }

    if (check()) return

    console.log('[TG] WebApp not ready, starting polling...')
    const interval = setInterval(() => {
      attempts++
      if (check()) {
        clearInterval(interval)
      } else if (attempts >= 20) {
        console.warn('[TG] WebApp polling timeout (2s), user not found')
        clearInterval(interval)
        setReady(true)
      }
    }, 100)

    return () => clearInterval(interval)
  }, [])

  return { tgUser, ready }
}
