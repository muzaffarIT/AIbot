'use client'
import Link from 'next/link'
import { useEffect, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { useMiniAppUser } from '@/lib/use-miniapp-user'
import { fetchJson } from '@/lib/api'

export default function ReferralPage() {
  const { telegramUser, backendUser, loading: userLoading, language } = useMiniAppUser()
  const [refLink, setRefLink] = useState('')
  const [stats, setStats] = useState({ count: 0, earned: 0 })
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (userLoading) return
    if (!backendUser?.telegram_user_id) {
      setLoading(false)
      return
    }

    fetchJson<{ referral_code: string; referral_count: number; referral_earnings: number }>(
      `/api/users/${backendUser.telegram_user_id}/referral`
    )
      .then(data => {
        if (data.referral_code) {
          setRefLink(`https://t.me/harfai_bot?start=ref_${data.referral_code}`)
        }
        setStats({
          count: data.referral_count || 0,
          earned: data.referral_earnings || 0,
        })
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [backendUser?.telegram_user_id, userLoading])

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

  if (userLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <main className="min-h-screen px-5 pt-6 pb-24 overflow-x-hidden">
      <div className="max-w-md mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center gap-3">
          <Link href="/" className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors">
            <ArrowLeft className="text-white" size={20} />
          </Link>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            {language === 'uz' ? 'Hamkorlik dasturi' : 'Партнёрская программа'}
          </h1>
        </div>

        {/* Description */}
        <p className="text-white/60 text-sm">
          {language === 'uz'
            ? 'Do\'stlarni taklif qiling — har biri uchun 20 kredit oling!'
            : 'Приглашай друзей — получай 20 кредитов за каждого!'}
        </p>

        {/* Referral link */}
        <div className="glass-card p-5 space-y-4">
          <p className="text-white/50 text-xs uppercase tracking-wider font-bold">
            {language === 'uz' ? 'SIZNING HAVOLANGIZ' : 'ТВОЯ ССЫЛКА'}
          </p>
          <p className="text-brand-primary text-sm break-all font-mono">
            {refLink || (
              <span className="text-white/30 italic">
                {backendUser ? '—' : (language === 'uz' ? 'Yuklanmoqda...' : 'Загрузка...')}
              </span>
            )}
          </p>
          <div className="flex gap-3">
            <button
              onClick={copyLink}
              disabled={!refLink}
              className={`flex-1 py-3 rounded-xl text-sm font-bold transition-all active:scale-95 ${
                copied ? 'bg-green-500 text-white' : 'bg-brand-primary text-white hover:opacity-90'
              } disabled:opacity-40`}
            >
              {copied ? '✅ Скопировано!' : '📋 Скопировать'}
            </button>
            <button
              onClick={shareLink}
              disabled={!refLink}
              className="flex-1 py-3 rounded-xl text-sm font-bold bg-blue-600 text-white hover:opacity-90 transition-all active:scale-95 disabled:opacity-40"
            >
              📤 Поделиться
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4">
          <div className="glass-card p-5 text-center">
            <p className="text-white/50 text-xs uppercase tracking-wider font-bold mb-2">
              {language === 'uz' ? 'TAKLIF QILINGAN' : 'ПРИГЛАШЕНО'}
            </p>
            <p className="text-4xl font-extrabold text-white">{stats.count}</p>
            <p className="text-white/40 text-xs mt-1">
              {language === 'uz' ? 'kishi' : 'человек'}
            </p>
          </div>
          <div className="glass-card p-5 text-center">
            <p className="text-white/50 text-xs uppercase tracking-wider font-bold mb-2">
              {language === 'uz' ? 'ISHLAB OLINGAN' : 'ЗАРАБОТАНО'}
            </p>
            <p className="text-4xl font-extrabold text-brand-primary">{stats.earned}</p>
            <p className="text-white/40 text-xs mt-1">
              {language === 'uz' ? 'kredit' : 'кредитов'}
            </p>
          </div>
        </div>

      </div>
    </main>
  )
}
