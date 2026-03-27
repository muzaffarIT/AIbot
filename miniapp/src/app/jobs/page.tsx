"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, type Variants } from "framer-motion";
import { 
  Clock, 
  ExternalLink, 
  Image as ImageIcon, 
  Video, 
  AlertCircle, 
  CheckCircle2, 
  XCircle, 
  RefreshCcw,
  Calendar,
  ChevronRight
} from "lucide-react";
import { getJobs, type GenerationJob } from "@/lib/api";
import { useMiniAppUser } from "@/lib/use-miniapp-user";
import { t } from "@/lib/miniapp-i18n";
import { useTelegramUser } from "@/hooks/useTelegramUser";

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.1 } },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } },
};

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 size={14} className="text-green-500" />;
    case 'pending':
    case 'processing':
      return <RefreshCcw size={14} className="text-brand-cyan animate-spin" />;
    case 'failed':
      return <XCircle size={14} className="text-red-500" />;
    default:
      return <AlertCircle size={14} className="text-white/40" />;
  }
}

function getJobStatusLabel(lang: string, status: string) {
  switch (status) {
    case 'completed':
      return lang === 'uz' ? "Tayyor" : "Готово";
    case 'pending':
      return lang === 'uz' ? "Kutilmoqda" : "В очереди";
    case 'processing':
      return lang === 'uz' ? "Jarayonda" : "Обработка";
    case 'failed':
      return lang === 'uz' ? "Xatolik" : "Ошибка";
    default:
      return status;
  }
}

function getProviderLabel(lang: string, provider: string) {
  switch (provider) {
    case 'nano_banana':
      return "Nano Banana";
    case 'veo':
      return "Google Veo";
    case 'kling':
      return "Kling AI";
    default:
      return provider;
  }
}

function isActiveStatus(status: string) {
  return ['pending', 'processing'].includes(status);
}

function formatDate(dateStr?: string | null, lang?: string) {
  if (!dateStr) return "";
  const date = new Date(dateStr);
  return date.toLocaleDateString(lang === 'uz' ? 'uz-UZ' : 'ru-RU', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit'
  });
}

export default function JobsPage() {
  const { language, telegramUser } = useMiniAppUser();
  const { tgUser, ready } = useTelegramUser();
  const [jobs, setJobs] = useState<GenerationJob[]>([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    if (!ready || !tgUser?.id) {
      setLoading(false)
      return
    }
    fetch(`/api/jobs/telegram/${tgUser.id}`)
      .then(r => r.json())
      .then(data => {
        setJobs(Array.isArray(data) ? data : (data?.items || []))
      })
      .catch(() => setJobs([]))
      .finally(() => setLoading(false))
  }, [ready, tgUser])

  if (!ready) return <div style={{padding: 20, color: 'white'}}>Загрузка...</div>;

  return (
    <main className="min-h-screen px-5 pt-6 pb-24 overflow-x-hidden">
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="max-w-md mx-auto space-y-6"
      >
        <motion.div variants={itemVariants} className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white tracking-tight">Мои работы</h1>
          <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center">
            <Clock className="text-brand-cyan" size={20} />
          </div>
        </motion.div>

        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <div className="w-12 h-12 border-4 border-brand-cyan/20 border-t-brand-cyan rounded-full animate-spin" />
            <p className="text-white/40 font-medium">Загрузка истории...</p>
          </div>
        ) : (
          <motion.div variants={itemVariants} className="space-y-4">
            {jobs.length ? (
              jobs.map((job) => (
                <div key={job.id} style={{
                  background: '#1a1a2e',
                  borderRadius: 12,
                  padding: 16,
                  marginBottom: 8,
                  display: 'flex',
                  gap: 12
                }}>
                  {job.result_url && job.provider !== 'veo' && (
                    <img
                      src={job.result_url as string}
                      style={{width: 60, height: 60,
                              borderRadius: 8, objectFit: 'cover'}}
                      alt="Job Result"
                    />
                  )}
                  <div style={{flex: 1}}>
                    <p style={{fontWeight: 600, margin: 0, color: 'white'}}>
                      {job.provider === 'nano_banana' ? '🍌 Nano Banana' :
                       job.provider === 'veo' ? '🎬 Veo 3' :
                       job.provider === 'kling' ? '🎥 Kling' : job.provider}
                    </p>
                    <p style={{color: '#888', fontSize: 12, margin: '4px 0'}}>
                      {((job as any).original_prompt || job.prompt || '').slice(0, 60)}
                    </p>
                    <p style={{color: '#666', fontSize: 11, margin: 0}}>
                      {job.created_at ? new Date(job.created_at).toLocaleDateString('ru') : ""}
                    </p>
                  </div>
                  <span style={{
                    color: job.status === 'completed' ? '#22c55e' :
                           job.status === 'failed' ? '#ef4444' : '#f59e0b',
                    fontSize: 12,
                    alignSelf: 'center'
                  }}>
                    {job.status === 'completed' ? '✅' :
                     job.status === 'failed' ? '❌' : '⏳'}
                  </span>
                </div>
              ))
            ) : (
              <div className="text-center p-8 bg-white/5 border border-white/5 rounded-3xl font-medium">
                <ImageIcon className="mx-auto text-white/20 mb-3" size={48} />
                <h3 className="text-white mb-1">Ничего нет</h3>
                <p className="text-white/50 text-sm mb-4">Вы еще не запускали нейросети</p>
                <Link href="/" className="btn-primary py-3 px-6 h-auto min-h-0 text-sm inline-flex">
                  На главную
                </Link>
              </div>
            )}
            {jobs.length === 0 && !loading && (
              <p style={{textAlign:'center', color:'#666', marginTop:40}}>
                У тебя пока нет генераций.<br/>Создай первую через бота!
              </p>
            )}
          </motion.div>
        )}
      </motion.div>
    </main>
  );
}
