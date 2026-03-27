'use client'
import { useEffect, useState } from 'react'

export function useTelegramUser() {
  const [tgUser, setTgUser] = useState<any>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const init = () => {
      const tg = (window as any).Telegram?.WebApp
      if (!tg) { setReady(true); return }
      tg.ready()
      tg.expand()
      const user = tg.initDataUnsafe?.user
      if (user) setTgUser(user)
      setReady(true)
    }
    if ((window as any).Telegram?.WebApp) {
      init()
    } else {
      const t = setTimeout(init, 300)
      return () => clearTimeout(t)
    }
  }, [])

  return { tgUser, ready }
}
