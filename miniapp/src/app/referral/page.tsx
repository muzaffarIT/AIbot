'use client'
import { useEffect, useState } from 'react'
import { useTelegramUser } from '@/hooks/useTelegramUser'

export default function ReferralPage() {
  const { tgUser, ready } = useTelegramUser()
  const [refLink, setRefLink] = useState('')
  const [stats, setStats] = useState({ count: 0, earned: 0 })
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!ready) return
    if (!tgUser?.id) { setLoading(false); return }

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
      .catch(err => console.error('[REFERRAL]', err))
      .finally(() => setLoading(false))
  }, [ready, tgUser])

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
      `🤖 HARF AI — создавай картинки и видео за секунды!\n` +
      `Регистрируйся и получи 10 бесплатных кредитов:`
    )
    window.open(
      `https://t.me/share/url?url=${encodeURIComponent(refLink)}` +
      `&text=${text}`,
      '_blank'
    )
  }

  if (loading) return (
    <div style={{
      display:'flex', justifyContent:'center',
      alignItems:'center', height:'80vh', color:'white'
    }}>
      Загрузка...
    </div>
  )

  return (
    <div style={{
      background: '#0a0a0f', minHeight: '100vh',
      color: 'white', padding: '20px 16px 100px'
    }}>
      <h2 style={{margin: '0 0 8px', fontSize: 22, fontWeight: 700}}>
        👥 Партнёрская программа
      </h2>
      <p style={{color: '#666', fontSize: 14, margin: '0 0 24px'}}>
        Приглашай друзей — получай 20 кредитов за каждого!
      </p>

      {/* Карточка ссылки */}
      <div style={{
        background: '#111120',
        borderRadius: 16, padding: 16,
        marginBottom: 16,
        border: '1px solid #1f1f35'
      }}>
        <p style={{
          color: '#555', fontSize: 11,
          textTransform: 'uppercase',
          letterSpacing: '0.05em', margin: '0 0 8px'
        }}>ТВОЯ ССЫЛКА</p>
        <p style={{
          color: '#a78bfa', fontSize: 12,
          wordBreak: 'break-all',
          margin: '0 0 12px',
          fontFamily: 'monospace'
        }}>
          {refLink || 'Загрузка...'}
        </p>
        <div style={{display: 'flex', gap: 8}}>
          <button onClick={copyLink} style={{
            flex: 1,
            background: copied ? '#22c55e' : '#7c3aed',
            color: 'white', border: 'none',
            borderRadius: 10, padding: '10px',
            cursor: 'pointer', fontSize: 13, fontWeight: 600
          }}>
            {copied ? '✅ Скопировано!' : '📋 Скопировать'}
          </button>
          <button onClick={shareLink} style={{
            flex: 1,
            background: '#1d4ed8',
            color: 'white', border: 'none',
            borderRadius: 10, padding: '10px',
            cursor: 'pointer', fontSize: 13, fontWeight: 600
          }}>
            📤 Поделиться
          </button>
        </div>
      </div>

      {/* Статистика */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 12
      }}>
        <div style={{
          background: '#111120', borderRadius: 14,
          padding: 16, textAlign: 'center',
          border: '1px solid #1f1f35'
        }}>
          <p style={{
            color: '#555', fontSize: 11,
            textTransform: 'uppercase', margin: '0 0 8px'
          }}>ПРИГЛАШЕНО</p>
          <p style={{
            fontSize: 32, fontWeight: 700, margin: 0
          }}>{stats.count}</p>
          <p style={{color: '#666', fontSize: 12, margin: '4px 0 0'}}>
            человек
          </p>
        </div>
        <div style={{
          background: '#111120', borderRadius: 14,
          padding: 16, textAlign: 'center',
          border: '1px solid #1f1f35'
        }}>
          <p style={{
            color: '#555', fontSize: 11,
            textTransform: 'uppercase', margin: '0 0 8px'
          }}>ЗАРАБОТАНО</p>
          <p style={{
            fontSize: 32, fontWeight: 700,
            margin: 0, color: '#a78bfa'
          }}>{stats.earned}</p>
          <p style={{color: '#666', fontSize: 12, margin: '4px 0 0'}}>
            кредитов
          </p>
        </div>
      </div>

      {/* Условия */}
      <div style={{
        background: 'rgba(124,58,237,0.1)',
        border: '1px solid rgba(124,58,237,0.2)',
        borderRadius: 14, padding: 16, marginTop: 16
      }}>
        <p style={{
          fontWeight: 600, margin: '0 0 8px'
        }}>🎁 Условия программы</p>
        <p style={{
          color: '#888', fontSize: 13,
          margin: '0 0 4px', lineHeight: 1.6
        }}>
          ✓ Ты получаешь +20 кр. за первую покупку реферала
        </p>
        <p style={{
          color: '#888', fontSize: 13,
          margin: 0, lineHeight: 1.6
        }}>
          ✓ Твой друг получает +10 кр. при регистрации
        </p>
      </div>
    </div>
  )
}
