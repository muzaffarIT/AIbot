'use client'
import { useEffect, useState } from 'react'
import { useTelegramUser } from './useTelegramUser'

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

    fetch('/api/users/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        telegram_id: tgUser.id,
        username: tgUser.username || '',
        first_name: tgUser.first_name || '',
        last_name: tgUser.last_name || '',
        language_code: tgUser.language_code || 'ru'
      })
    })
    .then(r => {
      if (!r.ok) throw new Error(`Sync failed: HTTP ${r.status}`)
      return r.json()
    })
    .then(data => {
      setUser(data)
      console.log('[USER] Synced:', data?.telegram_id,
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
