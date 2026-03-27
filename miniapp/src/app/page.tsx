'use client'
import { useUser } from '@/hooks/useUser'
import { useRouter } from 'next/navigation'

export default function HomePage() {
  const { user, tgUser, loading } = useUser()
  const router = useRouter()

  const name = tgUser?.first_name || user?.username || 'Creator'
  const balance = user?.credits_balance ?? 0
  const activeJobs = user?.active_jobs_count ?? 0

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        background: '#0a0a0f',
        color: 'white',
        flexDirection: 'column',
        gap: 16
      }}>
        <div style={{
          width: 48, height: 48,
          border: '3px solid #7c3aed',
          borderTop: '3px solid transparent',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }} />
        <p style={{color: '#888'}}>Загрузка...</p>
        <style>{`
          @keyframes spin {
            to { transform: rotate(360deg) }
          }
        `}</style>
      </div>
    )
  }

  return (
    <div style={{
      background: '#0a0a0f',
      minHeight: '100vh',
      color: 'white',
      paddingBottom: 80
    }}>
      {/* Шапка */}
      <div style={{
        padding: '24px 20px 20px',
        background: 'linear-gradient(180deg, #0f0f1a 0%, #0a0a0f 100%)'
      }}>
        {/* Логотип */}
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          background: 'rgba(124,58,237,0.15)',
          border: '1px solid rgba(124,58,237,0.3)',
          borderRadius: 20,
          padding: '6px 14px',
          marginBottom: 16
        }}>
          <span style={{fontSize: 14}}>⚡</span>
          <span style={{
            fontSize: 13,
            fontWeight: 600,
            color: '#a78bfa'
          }}>HARF AI</span>
        </div>

        {/* Заголовок */}
        <h1 style={{
          fontSize: '2rem',
          fontWeight: 900,
          margin: '0 0 8px',
          background: 'linear-gradient(135deg, #fff 0%, #a78bfa 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          lineHeight: 1.2
        }}>
          Создавай.<br/>Удивляй.
        </h1>
        <p style={{
          color: '#666',
          fontSize: 14,
          margin: '0 0 4px'
        }}>
          Картинки • Видео • Анимация
        </p>
        <p style={{color: '#555', fontSize: 12}}>
          С возвращением, {name}
        </p>
      </div>

      <div style={{padding: '0 16px'}}>
        {/* Быстрые карточки */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 12,
          marginBottom: 16
        }}>
          <div
            onClick={() => router.push('/referral')}
            style={{
              background: 'linear-gradient(135deg, #1e1040, #2d1b69)',
              borderRadius: 16,
              padding: 16,
              cursor: 'pointer',
              border: '1px solid rgba(124,58,237,0.2)'
            }}>
            <div style={{
              width: 40, height: 40,
              background: 'rgba(96,165,250,0.2)',
              borderRadius: 12,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 12,
              fontSize: 20
            }}>👥</div>
            <p style={{
              fontWeight: 600, margin: '0 0 4px', fontSize: 15
            }}>Рефералы</p>
            <p style={{
              color: '#888', fontSize: 12, margin: 0
            }}>Пригласить друзей →</p>
          </div>

          <div
            onClick={() => router.push('/plans')}
            style={{
              background: 'linear-gradient(135deg, #1a0a2e, #2d1050)',
              borderRadius: 16,
              padding: 16,
              cursor: 'pointer',
              border: '1px solid rgba(167,139,250,0.2)'
            }}>
            <div style={{
              width: 40, height: 40,
              background: 'rgba(167,139,250,0.2)',
              borderRadius: 12,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 12,
              fontSize: 20
            }}>💎</div>
            <p style={{
              fontWeight: 600, margin: '0 0 4px', fontSize: 15
            }}>Тарифы</p>
            <p style={{
              color: '#888', fontSize: 12, margin: 0
            }}>Пополнить баланс →</p>
          </div>
        </div>

        {/* Баланс */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 12,
          marginBottom: 16
        }}>
          <div style={{
            background: '#111120',
            borderRadius: 16,
            padding: 16,
            border: '1px solid #1f1f35'
          }}>
            <p style={{
              color: '#666', fontSize: 11,
              textTransform: 'uppercase',
              letterSpacing: '0.05em', margin: '0 0 8px'
            }}>БАЛАНС КРЕДИТОВ</p>
            <p style={{
              fontSize: 28, fontWeight: 700,
              margin: 0, color: '#a78bfa'
            }}>{balance}</p>
          </div>
          <div style={{
            background: '#111120',
            borderRadius: 16,
            padding: 16,
            border: '1px solid #1f1f35'
          }}>
            <p style={{
              color: '#666', fontSize: 11,
              textTransform: 'uppercase',
              letterSpacing: '0.05em', margin: '0 0 8px'
            }}>АКТИВНЫЕ</p>
            <p style={{
              fontSize: 28, fontWeight: 700, margin: 0
            }}>{activeJobs}</p>
          </div>
        </div>

        {/* Последние работы */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 12
        }}>
          <p style={{
            fontWeight: 600, fontSize: 16, margin: 0
          }}>⚡ Активность</p>
          <span
            onClick={() => router.push('/jobs')}
            style={{color: '#7c3aed', fontSize: 13, cursor: 'pointer'}}>
            ВСЕ →
          </span>
        </div>
      </div>
    </div>
  )
}
