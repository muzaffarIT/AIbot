'use client'
import { useEffect, useState } from 'react'
import { useTelegramUser } from './useTelegramUser'
import { syncUser } from '@/lib/api'

export function useUser() {
  const { tgUser, ready: tgReady } = useTelegramUser()
  const [user, setUser] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!tgReady) return
    if (!tgUser) {
      setLoading(false)
      return
    }

    syncUser({
      telegram_id: tgUser.id,
      username: tgUser.username || '',
      first_name: tgUser.first_name || '',
      last_name: tgUser.last_name || '',
      language_code: tgUser.language_code || 'ru',
    })
    .then(data => {
      setUser(data)
      console.log('[USER] Synced:', data?.telegram_user_id,
                  'balance:', data?.credits_balance)
    })
    .catch(err => {
      console.error('[USER] Sync error:', err)
      setError(err.message)
    })
    .finally(() => setLoading(false))
  }, [tgReady, tgUser])

  return { user, tgUser, loading, error }
}
