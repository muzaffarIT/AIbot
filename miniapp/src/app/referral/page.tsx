'use client'
import { useEffect, useState } from 'react'

export default function ReferralPage() {
  const [refLink, setRefLink] = useState('')
  const [stats, setStats] = useState({ count: 0, earned: 0 })
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const tgUser = (window as any).Telegram?.WebApp?.initDataUnsafe?.user
    if (!tgUser) { setLoading(false); return }

    fetch(`/api/users/${tgUser.id}/referral`)
      .then(r => r.json())
      .then(data => {
        if (data.referral_code) {
          setRefLink(
            `https://t.me/harfai_bot?start=ref_${data.referral_code}`
          )
        }
        setStats({
          count: data.referral_count || 0,
          earned: data.referral_earnings || 0
        })
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(refLink)
    } catch {
      const el = document.createElement('textarea')
      el.value = refLink
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const shareLink = () => {
    const text = encodeURIComponent(
      `🤖 HARF AI — нейросети в твоём телефоне!\n` +
      `Создавай картинки и видео за секунды.\n` +
      `Регистрируйся и получи 10 бесплатных кредитов:`
    )
    window.open(
      `https://t.me/share/url?url=${encodeURIComponent(refLink)}&text=${text}`,
      '_blank'
    )
  }

  if (loading) return <div style={{padding:20}}>Загрузка...</div>

  return (
    <div style={{padding: '20px', color: 'white', paddingBottom: '100px'}}>
      <h2>👥 Партнёрская программа</h2>
      <p style={{color: '#888'}}>
        Приглашай друзей — получай 20 кредитов за каждого!
      </p>

      <div style={{
        background: '#1a1a2e',
        borderRadius: 12,
        padding: 16,
        marginTop: 20
      }}>
        <p style={{color: '#888', fontSize: 12, textTransform: 'uppercase'}}>
          ТВОЯ ССЫЛКА
        </p>
        <p style={{
          wordBreak: 'break-all',
          fontSize: 13,
          color: '#a78bfa'
        }}>
          {refLink || 'Загрузка...'}
        </p>

        <div style={{display: 'flex', gap: 8, marginTop: 12}}>
          <button onClick={copyLink} style={{
            flex: 1,
            background: copied ? '#22c55e' : '#7c3aed',
            color: 'white',
            border: 'none',
            borderRadius: 8,
            padding: '10px',
            cursor: 'pointer'
          }}>
            {copied ? '✅ Скопировано!' : '📋 Скопировать'}
          </button>
          <button onClick={shareLink} style={{
            flex: 1,
            background: '#1d4ed8',
            color: 'white',
            border: 'none',
            borderRadius: 8,
            padding: '10px',
            cursor: 'pointer'
          }}>
            📤 Поделиться
          </button>
        </div>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 12,
        marginTop: 20
      }}>
        <div style={{
          background: '#1a1a2e',
          borderRadius: 12,
          padding: 16,
          textAlign: 'center'
        }}>
          <p style={{color: '#888', fontSize: 12}}>ПРИГЛАШЕНО</p>
          <p style={{fontSize: 32, fontWeight: 700}}>
            {stats.count}
          </p>
          <p style={{color: '#888', fontSize: 12}}>человек</p>
        </div>
        <div style={{
          background: '#1a1a2e',
          borderRadius: 12,
          padding: 16,
          textAlign: 'center'
        }}>
          <p style={{color: '#888', fontSize: 12}}>ЗАРАБОТАНО</p>
          <p style={{fontSize: 32, fontWeight: 700, color: '#a78bfa'}}>
            {stats.earned}
          </p>
          <p style={{color: '#888', fontSize: 12}}>кредитов</p>
        </div>
      </div>
    </div>
  )
}
