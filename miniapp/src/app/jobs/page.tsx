'use client'
import { useEffect, useState } from 'react'
import { useTelegramUser } from '@/hooks/useTelegramUser'

const PROVIDER_NAMES: Record<string, string> = {
  nano_banana: '🍌 Nano Banana',
  veo: '🎬 Veo 3',
  veo3: '🎬 Veo 3',
  kling: '🎥 Kling',
}

export default function JobsPage() {
  const { tgUser, ready } = useTelegramUser()
  const [jobs, setJobs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!ready) return
    if (!tgUser?.id) { setLoading(false); return }

    const ctrl = new AbortController()
    setTimeout(() => ctrl.abort(), 10000)

    fetch(`/api/jobs/telegram/${tgUser.id}`,
          { signal: ctrl.signal })
      .then(r => r.json())
      .then(data => {
        const list = Array.isArray(data)
          ? data
          : (data?.items || [])
        setJobs(list)
        console.log('[JOBS] Loaded:', list.length)
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('[JOBS] Error:', err)
        }
        setJobs([])
      })
      .finally(() => setLoading(false))
  }, [ready, tgUser])

  if (loading) return (
    <div style={{
      display:'flex', justifyContent:'center',
      alignItems:'center', height:'80vh', color:'white'
    }}>
      Загрузка работ...
    </div>
  )

  return (
    <div style={{
      background: '#0a0a0f', minHeight: '100vh',
      color: 'white', padding: '20px 16px 100px'
    }}>
      <h2 style={{margin: '0 0 20px', fontSize: 22, fontWeight: 700}}>
        Мои работы
      </h2>

      {jobs.length === 0 ? (
        <div style={{
          textAlign: 'center', padding: '60px 20px',
          color: '#666'
        }}>
          <p style={{fontSize: 48}}>🎨</p>
          <p style={{fontSize: 16, fontWeight: 600,
                     color: '#888'}}>Ничего нет</p>
          <p style={{fontSize: 13}}>
            Создай первую генерацию через бота!
          </p>
        </div>
      ) : (
        jobs.map(job => (
          <div key={job.id} style={{
            background: '#111120',
            borderRadius: 14,
            padding: 14,
            marginBottom: 10,
            border: '1px solid #1f1f35',
            display: 'flex',
            gap: 12,
            alignItems: 'flex-start'
          }}>
            {/* Превью */}
            {job.result_url &&
             !['veo','veo3','kling'].includes(job.provider) ? (
              <img
                src={job.result_url}
                alt="result"
                style={{
                  width: 56, height: 56,
                  borderRadius: 10,
                  objectFit: 'cover',
                  flexShrink: 0
                }}
              />
            ) : (
              <div style={{
                width: 56, height: 56,
                background: '#1a1a2e',
                borderRadius: 10,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 24,
                flexShrink: 0
              }}>
                {['veo','veo3'].includes(job.provider)
                  ? '🎬' : '🎥'}
              </div>
            )}

            <div style={{flex: 1, minWidth: 0}}>
              <p style={{
                fontWeight: 600, margin: '0 0 4px', fontSize: 14
              }}>
                {PROVIDER_NAMES[job.provider] || job.provider}
              </p>
              <p style={{
                color: '#888', fontSize: 12,
                margin: '0 0 6px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap'
              }}>
                {job.original_prompt || job.prompt || '—'}
              </p>
              <p style={{color: '#555', fontSize: 11, margin: 0}}>
                {new Date(job.created_at)
                  .toLocaleDateString('ru', {
                    day: 'numeric', month: 'short',
                    hour: '2-digit', minute: '2-digit'
                  })}
              </p>
            </div>

            <div style={{
              flexShrink: 0,
              textAlign: 'right'
            }}>
              <span style={{
                fontSize: 11,
                padding: '3px 8px',
                borderRadius: 20,
                background:
                  job.status === 'completed'
                    ? 'rgba(34,197,94,0.15)'
                    : job.status === 'failed'
                      ? 'rgba(239,68,68,0.15)'
                      : 'rgba(245,158,11,0.15)',
                color:
                  job.status === 'completed' ? '#22c55e' :
                  job.status === 'failed' ? '#ef4444' : '#f59e0b'
              }}>
                {job.status === 'completed' ? 'Готово' :
                 job.status === 'failed' ? 'Ошибка' : 'В процессе'}
              </span>
              <p style={{
                color: '#555', fontSize: 11,
                margin: '4px 0 0', textAlign: 'right'
              }}>
                #{job.id}
              </p>
            </div>
          </div>
        ))
      )}
    </div>
  )
}
