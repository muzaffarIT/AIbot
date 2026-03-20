"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, useTransition } from "react";
import { motion, type Variants } from "framer-motion";
import { ArrowLeft, RefreshCw, Loader2, AlertCircle, ImageIcon, Video, ExternalLink, Calendar, CheckCircle2, Clock, XCircle } from "lucide-react";
import { formatDate } from "@/lib/format";
import { getJobs, type GenerationJob } from "@/lib/api";
import { getJobStatusLabel, getProviderLabel, t } from "@/lib/miniapp-i18n";
import { useMiniAppUser } from "@/lib/use-miniapp-user";

function isActiveStatus(status: string) {
  return status === "pending" || status === "processing";
}

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.1 } },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } },
};

function StatusIcon({ status }: { status: string }) {
  if (status === "completed") return <CheckCircle2 size={16} className="text-green-400" />;
  if (status === "failed" || status === "cancelled") return <XCircle size={16} className="text-red-400" />;
  if (isActiveStatus(status)) return <Clock size={16} className="text-brand-cyan animate-pulse" />;
  return <Clock size={16} className="text-white/40" />;
}

export default function JobsPage() {
  const { backendUser, telegramUser, language, loading: userLoading, error: userError } = useMiniAppUser();
  const [jobs, setJobs] = useState<GenerationJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isRefreshing, startRefreshing] = useTransition();

  const telegramUserId = backendUser?.telegram_user_id ?? null;

  const refreshJobs = useCallback(
    async (userId: number, silenceErrors = false) => {
      try {
        const data = await getJobs(userId, 15);
        startRefreshing(() => {
          setJobs(data.jobs);
          setError("");
        });
      } catch {
        if (!silenceErrors) {
          setError(t(language, "jobs.failedLoad"));
        }
      }
    },
    [language]
  );

  useEffect(() => {
    async function load() {
      if (userLoading) return;
      if (!telegramUser?.id) {
        setError(t(language, "common.openFromTelegram"));
        setLoading(false);
        return;
      }
      if (!telegramUserId) {
        setError(userError ? t(language, "common.profileSyncFailed") : "");
        setLoading(false);
        return;
      }

      try {
        await refreshJobs(telegramUserId);
      } catch {
        setError(t(language, "jobs.failedPrepare"));
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [language, refreshJobs, telegramUser?.id, telegramUserId, userError, userLoading]);

  // Polling
  useEffect(() => {
    if (!telegramUserId || !jobs.some((job) => isActiveStatus(job.status))) return;
    const intervalId = window.setInterval(() => {
      void refreshJobs(telegramUserId, true);
    }, 5000);
    return () => window.clearInterval(intervalId);
  }, [jobs, refreshJobs, telegramUserId]);

  if (userLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="animate-spin text-brand-primary" size={32} />
      </div>
    );
  }

  return (
    <main className="min-h-screen px-5 pt-6 pb-24 overflow-x-hidden">
      <motion.div variants={containerVariants} initial="hidden" animate="visible" className="max-w-md mx-auto space-y-6">
        
        {/* Header */}
        <motion.div variants={itemVariants} className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors">
              <ArrowLeft className="text-white" size={20} />
            </Link>
            <h1 className="text-2xl font-bold text-white tracking-tight">Работы</h1>
          </div>
          <button 
            onClick={() => telegramUserId && refreshJobs(telegramUserId)}
            disabled={isRefreshing}
            className="w-10 h-10 rounded-full bg-brand-primary/20 text-brand-cyan flex items-center justify-center hover:bg-brand-primary/30 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={18} className={isRefreshing ? "animate-spin" : ""} />
          </button>
        </motion.div>

        {error && (
          <motion.div variants={itemVariants} className="p-4 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-start gap-3 text-red-400">
            <AlertCircle className="shrink-0 mt-0.5" size={18} />
            <p className="text-sm font-medium">{error}</p>
          </motion.div>
        )}

        <motion.div variants={itemVariants} className="space-y-4">
          {jobs.length ? (
            jobs.map((job) => (
              <div key={job.id} className="glass-card p-5 overflow-hidden relative group hover:border-white/20 transition-colors">
                {/* Status Indicator Bar */}
                <div className={`absolute left-0 top-0 bottom-0 w-1 ${job.status === 'completed' ? 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]' : isActiveStatus(job.status) ? 'bg-brand-cyan animate-pulse shadow-[0_0_10px_rgba(6,182,212,0.5)]' : 'bg-red-500'}`} />
                
                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-center gap-2">
                    {job.provider === "nano_banana" ? <ImageIcon size={20} className="text-white/60" /> : <Video size={20} className="text-white/60" />}
                    <h3 className="font-semibold text-white/90">{getProviderLabel(language, job.provider)}</h3>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-md bg-white/5 border border-white/5">
                    <StatusIcon status={job.status} />
                    <span className="text-white/80">{getJobStatusLabel(language, job.status)}</span>
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
            ))
          ) : (
            <div className="text-center p-8 bg-white/5 border border-white/5 rounded-3xl">
              <ImageIcon className="mx-auto text-white/20 mb-3" size={48} />
              <h3 className="text-white font-semibold mb-1">Ничего нет</h3>
              <p className="text-white/50 text-sm mb-4">Вы еще не запускали нейросети</p>
              <Link href="/generate" className="btn-primary py-3 px-6 h-auto min-h-0 text-sm inline-flex">
                Создать первый арт
              </Link>
            </div>
          )}
        </motion.div>

      </motion.div>
    </main>
  );
}
