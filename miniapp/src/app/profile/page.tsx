'use client'
import { useEffect, useState } from 'react'
import { useUser } from '@/hooks/useUser'

export default function ProfilePage() {
  const { user, tgUser, loading } = useUser()
  const [achievements, setAchievements] = useState<any[]>([])

  useEffect(() => {
    if (!tgUser?.id) return
    fetch(`/api/users/${tgUser.id}/achievements`)
      .then(r => r.json())
      .then(data => setAchievements(Array.isArray(data) ? data : []))
      .catch(() => setAchievements([]))
  }, [tgUser])

  const name = tgUser?.first_name || 'Пользователь'
  const username = tgUser?.username
    ? `@${tgUser.username}` : ''
  const balance = user?.credits_balance ?? 0
  const streak = user?.daily_streak ?? 0
  const friends = user?.referral_count ?? 0
  const earnedCount = achievements.filter(a => a.earned).length

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
      {/* Заголовок */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 20
      }}>
        <h2 style={{margin: 0, fontSize: 22, fontWeight: 700}}>
          Профиль
        </h2>
        <div style={{
          background: '#1a1a2e',
          borderRadius: 20,
          padding: '6px 14px',
          fontSize: 13,
          color: '#a78bfa',
          border: '1px solid #2d2d4e'
        }}>
          🌐 RU
        </div>
      </div>

      {/* Карточка пользователя */}
      <div style={{
        background: '#111120',
        borderRadius: 16,
        padding: 16,
        marginBottom: 16,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        border: '1px solid #1f1f35'
      }}>
        <div style={{
          width: 56, height: 56,
          background: 'linear-gradient(135deg, #7c3aed, #3b82f6)',
          borderRadius: 14,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 22,
          fontWeight: 700,
          flexShrink: 0
        }}>
          {name[0]?.toUpperCase()}
        </div>
        <div>
          <p style={{
            fontWeight: 700, fontSize: 18, margin: '0 0 2px'
          }}>{name}</p>
          {username && (
            <p style={{
              color: '#666', fontSize: 13, margin: 0
            }}>{username}</p>
          )}
        </div>
      </div>

      {/* Статистика */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr 1fr',
        gap: 10,
        marginBottom: 20
      }}>
        {[
          { label: 'STREAK', value: streak, icon: '🔥' },
          { label: 'КРЕДИТЫ', value: balance, icon: '⚡',
            color: '#a78bfa' },
          { label: 'ДРУЗЬЯ', value: friends, icon: '👥',
            color: '#a78bfa' },
        ].map(stat => (
          <div key={stat.label} style={{
            background: '#111120',
            borderRadius: 14,
            padding: '14px 10px',
            textAlign: 'center',
            border: '1px solid #1f1f35'
          }}>
            <p style={{
              color: '#555', fontSize: 10,
              textTransform: 'uppercase',
              letterSpacing: '0.05em', margin: '0 0 6px'
            }}>{stat.label}</p>
            <p style={{
              fontSize: 24, fontWeight: 700, margin: 0,
              color: stat.color || 'white'
            }}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Достижения */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12
      }}>
        <p style={{
          fontWeight: 600, fontSize: 16,
          margin: 0, display: 'flex',
          alignItems: 'center', gap: 8
        }}>
          🏆 Достижения
        </p>
        <span style={{color: '#666', fontSize: 13}}>
          {earnedCount}/8
        </span>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 10
      }}>
        {achievements.map(ach => (
          <div key={ach.code} style={{
            background: ach.earned ? '#111120' : '#0d0d18',
            borderRadius: 14,
            padding: 14,
            border: ach.earned
              ? '1px solid rgba(124,58,237,0.4)'
              : '1px solid #1a1a2e',
            opacity: ach.earned ? 1 : 0.6
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginBottom: 8
            }}>
              <span style={{fontSize: 22}}>{ach.emoji}</span>
              <span style={{fontSize: 16}}>
                {ach.earned ? '✅' : '🔒'}
              </span>
            </div>
            <p style={{
              fontWeight: 600, fontSize: 13,
              margin: '0 0 4px'
            }}>{ach.name}</p>
            <p style={{
              color: ach.earned ? '#a78bfa' : '#666',
              fontSize: 12, margin: 0
            }}>+{ach.bonus} кр.</p>
          </div>
        ))}
      </div>
    </div>
  )
}
