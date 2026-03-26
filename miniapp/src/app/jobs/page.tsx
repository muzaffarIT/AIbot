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
  const [jobs, setJobs] = useState<GenerationJob[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    if (!telegramUser?.id) { setLoading(false); return }
    const ctrl = new AbortController()
    setTimeout(() => ctrl.abort(), 8000)
    fetch(`/api/jobs/telegram/${telegramUser.id}`,
          { signal: ctrl.signal })
      .then(r => r.json())
      .then(j => setJobs(Array.isArray(j) ? j : []))
      .catch(() => setJobs([]))
      .finally(() => setLoading(false))
  }, [telegramUser?.id])

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
              jobs.map((job) => {
                const jobDate = new Date(job.created_at || "");
                const isStuck = isActiveStatus(job.status) && (new Date().getTime() - jobDate.getTime()) > 30 * 60 * 1000;
                const displayStatus = isStuck ? "failed" : job.status;
                const statusLabel = isStuck ? (language === 'uz' ? "Xatolik" : "Ошибка") : getJobStatusLabel(language, job.status);

                return (
                  <div key={job.id} className="glass-card p-5 overflow-hidden relative group hover:border-white/20 transition-colors">
                    <div className={`absolute left-0 top-0 bottom-0 w-1 ${displayStatus === 'completed' ? 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]' : isActiveStatus(displayStatus) ? 'bg-brand-cyan animate-pulse shadow-[0_0_10px_rgba(6,182,212,0.5)]' : 'bg-red-500'}`} />
                    
                    <div className="flex justify-between items-start mb-3">
                      <div className="flex items-center gap-2">
                        {job.provider === "nano_banana" ? <ImageIcon size={20} className="text-white/60" /> : <Video size={20} className="text-white/60" />}
                        <h3 className="font-semibold text-white/90">{getProviderLabel(language, job.provider)}</h3>
                      </div>
                      <div className="flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-md bg-white/5 border border-white/5">
                        <StatusIcon status={displayStatus} />
                        <span className={isStuck ? "text-red-400" : "text-white/80"}>{statusLabel}</span>
                      </div>
                    </div>

                    <p className="text-sm text-white/70 leading-relaxed mb-4 line-clamp-3">
                      &quot;{job.prompt}&quot;
                    </p>

                    <div className="flex items-center justify-between mt-auto">
                      <div className="flex items-center gap-3 text-xs text-white/40 font-medium">
                        <span className="flex items-center gap-1"><Calendar size={12} /> {formatDate(job.created_at, language)}</span>
                      </div>
                      
                      {job.result_url ? (
                        <a href={job.result_url} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 text-xs font-bold text-brand-primary bg-brand-primary/10 px-3 py-1.5 rounded-lg hover:bg-brand-primary/20 transition-colors">
                          Открыть <ExternalLink size={12} />
                        </a>
                      ) : job.error_message ? (
                        <span className="text-xs text-red-400 font-medium truncate max-w-[120px]" title={job.error_message}>
                          {job.error_message}
                        </span>
                      ) : null}
                    </div>
                  </div>
                );
              })
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
