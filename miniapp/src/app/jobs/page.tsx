"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { motion, type Variants } from "framer-motion";
import { Clock, CheckCircle2, XCircle, RefreshCcw, AlertCircle, Image as ImageIcon, ExternalLink } from "lucide-react";
import { useTelegramAuth } from "@/hooks/useTelegramAuth";
import { api, type GenerationJob } from "@/lib/api";

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
    case "completed": return <CheckCircle2 size={14} className="text-green-500" />;
    case "pending":
    case "processing": return <RefreshCcw size={14} className="text-brand-cyan animate-spin" />;
    case "failed": return <XCircle size={14} className="text-red-500" />;
    default: return <AlertCircle size={14} className="text-white/40" />;
  }
}

function providerLabel(provider: string) {
  if (provider === "nano_banana") return "🍌 Nano Banana";
  if (provider === "veo") return "🎬 Veo 3";
  if (provider === "kling") return "🎥 Kling";
  return provider;
}

function statusLabel(status: string) {
  if (status === "completed") return "Готово";
  if (status === "pending") return "В очереди";
  if (status === "processing") return "Обработка";
  if (status === "failed") return "Ошибка";
  return status;
}

function formatDate(d?: string | null) {
  if (!d) return "";
  return new Date(d).toLocaleDateString("ru-RU", {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

/** Open URL in Telegram's internal browser (keeps user inside TG) */
function openResult(url: string) {
  const tg = (window as any).Telegram?.WebApp;
  if (tg?.openLink) {
    tg.openLink(url);
  } else {
    window.open(url, "_blank");
  }
}

export default function JobsPage() {
  const { tgUser, userData, loading } = useTelegramAuth();
  const [jobs, setJobs] = useState<GenerationJob[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);

  useEffect(() => {
    const id = userData?.telegram_user_id ?? tgUser?.id;
    if (!id) {
      setJobsLoading(false);
      return;
    }
    api.getJobs(id, 20)
      .then((res) => setJobs(res.jobs))
      .catch(() => setJobs([]))
      .finally(() => setJobsLoading(false));
  }, [userData?.telegram_user_id, tgUser?.id]);

  if (loading || jobsLoading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <div className="w-12 h-12 border-4 border-brand-cyan/20 border-t-brand-cyan rounded-full animate-spin" />
        <p className="text-white/40 font-medium">Загрузка истории...</p>
      </div>
    );
  }

  return (
    <main className="min-h-screen px-5 pt-6 pb-24 overflow-x-hidden">
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="max-w-md mx-auto space-y-6"
      >
        {/* Header */}
        <motion.div variants={itemVariants} className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white tracking-tight">Мои работы</h1>
          <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center">
            <Clock className="text-brand-cyan" size={20} />
          </div>
        </motion.div>

        {jobs.length ? (
          <motion.div variants={itemVariants} className="space-y-3">
            {jobs.map((job) => (
              <div key={job.id} className="glass-card p-4 flex flex-col gap-3">
                <div className="flex gap-3">
                  {/* Preview thumbnail (only for image providers) */}
                  {job.result_url && job.provider === "nano_banana" && (
                    <button
                      onClick={() => openResult(job.result_url!)}
                      className="relative w-16 h-16 rounded-xl overflow-hidden shrink-0 bg-white/5 block"
                    >
                      <Image
                        src={job.result_url}
                        alt="Результат"
                        fill
                        className="object-cover"
                        unoptimized
                      />
                    </button>
                  )}

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <StatusIcon status={job.status} />
                      <span className="text-sm font-semibold text-white">
                        {providerLabel(job.provider)}
                      </span>
                    </div>
                    {(job as any).original_prompt || job.prompt ? (
                      <p className="text-xs text-white/50 truncate">
                        {((job as any).original_prompt || job.prompt || "").slice(0, 60)}
                      </p>
                    ) : null}
                    <p className="text-[11px] text-white/30 mt-1">{formatDate(job.created_at)}</p>
                  </div>

                  <div className="shrink-0 flex flex-col items-end justify-between">
                    <span
                      className={`text-xs font-bold ${
                        job.status === "completed"
                          ? "text-green-400"
                          : job.status === "failed"
                          ? "text-red-400"
                          : "text-amber-400"
                      }`}
                    >
                      {statusLabel(job.status)}
                    </span>
                    <span className="text-[10px] text-white/20 font-mono">#{job.id}</span>
                  </div>
                </div>

                {/* Open result button */}
                {job.status === "completed" && job.result_url && (
                  <button
                    onClick={() => openResult(job.result_url!)}
                    className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-brand-primary/20 border border-brand-primary/30 text-brand-cyan text-sm font-semibold hover:bg-brand-primary/30 transition-colors"
                  >
                    <ExternalLink size={14} />
                    {job.provider === "nano_banana" ? "Открыть картинку" : "Открыть видео"}
                  </button>
                )}
              </div>
            ))}
          </motion.div>
        ) : (
          <motion.div
            variants={itemVariants}
            className="text-center p-12 glass-card flex flex-col items-center gap-4"
          >
            <ImageIcon className="text-white/20" size={48} />
            <div>
              <h3 className="text-white font-semibold mb-1">Нет генераций</h3>
              <p className="text-white/50 text-sm">
                🎨 У тебя пока нет генераций.
                <br />Создай первую через бота!
              </p>
            </div>
          </motion.div>
        )}
      </motion.div>
    </main>
  );
}
