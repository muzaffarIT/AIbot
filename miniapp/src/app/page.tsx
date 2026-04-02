"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion, type Variants } from "framer-motion";
import {
  Sparkles, Users, Coins, ChevronRight, Activity, Zap, AlertCircle,
} from "lucide-react";
import { useTelegramAuth } from "@/hooks/useTelegramAuth";
import { api, type GenerationJob } from "@/lib/api";

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.1, delayChildren: 0.1 } },
};
const itemVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } },
};

function isActiveJob(status: string) {
  return status === "pending" || status === "processing";
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

export default function HomePage() {
  const { tgUser, userData, loading, error } = useTelegramAuth();
  const [jobs, setJobs] = useState<GenerationJob[]>([]);
  const [jobsLoaded, setJobsLoaded] = useState(false);

  useEffect(() => {
    if (!userData?.telegram_user_id) return;
    api.getJobs(userData.telegram_user_id, 4)
      .then((res) => setJobs(res.jobs))
      .catch(() => {})
      .finally(() => setJobsLoaded(true));
  }, [userData?.telegram_user_id]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const displayName = tgUser?.first_name || userData?.username || "Creator";
  const credits = userData?.credits_balance ?? 0;
  const activeCount = jobs.filter((j) => isActiveJob(j.status)).length;

  return (
    <main className="min-h-screen px-5 pt-6 pb-24 overflow-x-hidden">
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="max-w-md mx-auto space-y-8"
      >
        {/* Hero */}
        <motion.section variants={itemVariants} className="relative">
          <div className="absolute inset-0 bg-gradient-to-br from-brand-primary/20 to-brand-cyan/20 blur-3xl -z-10 rounded-[3rem]" />
          <div className="glass-card p-6 border-white/20 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-50 text-white">
              <Sparkles size={48} strokeWidth={1} />
            </div>
            <div
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-primary/20 text-brand-accent text-xs font-bold uppercase tracking-wider mb-4 border border-brand-primary/30"
            >
              <Zap size={14} className="text-brand-accent fill-brand-accent/50" />
              AI Генератор
            </div>
            <div style={{
              background: "linear-gradient(135deg, #7C3AED, #3B82F6)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              fontSize: "2.5rem",
              fontWeight: 900,
              letterSpacing: "-0.02em",
            }}>
              HARF AI
            </div>
            <p style={{ color: "#888", marginTop: 8 }}>
              ✨ {displayName}, создавай контент за секунды
            </p>
            <p style={{ color: "#888", fontSize: 13, marginTop: 4 }}>
              Картинки • Видео • Анимация
            </p>
          </div>
        </motion.section>

        {/* Error banner */}
        {error && (
          <motion.div
            variants={itemVariants}
            className="p-4 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-start gap-3 text-red-400"
          >
            <AlertCircle className="shrink-0 mt-0.5" size={18} />
            <p className="text-sm font-medium">{error}</p>
          </motion.div>
        )}

        {/* Quick Actions */}
        <motion.section variants={itemVariants} className="grid grid-cols-2 gap-4">
          <Link
            href="/referral"
            className="glass-card p-5 group hover:bg-white/5 transition-colors relative overflow-hidden"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-cyan to-blue-500 flex items-center justify-center mb-4 shadow-lg shadow-brand-cyan/20">
              <Users className="text-white" size={20} />
            </div>
            <h3 className="font-semibold text-white mb-1">Рефералы</h3>
            <p className="text-xs text-white/50">Пригласить друзей</p>
            <ChevronRight
              className="absolute bottom-4 right-4 text-white/30 group-hover:text-white/70 transition-colors"
              size={18}
            />
          </Link>

          <Link
            href="/plans"
            className="glass-card p-5 group hover:bg-white/5 transition-colors relative overflow-hidden"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-primary to-purple-600 flex items-center justify-center mb-4 shadow-lg shadow-brand-primary/20">
              <Coins className="text-white" size={20} />
            </div>
            <h3 className="font-semibold text-white mb-1">Тарифы</h3>
            <p className="text-xs text-white/50">Пополнить баланс</p>
            <ChevronRight
              className="absolute bottom-4 right-4 text-white/30 group-hover:text-white/70 transition-colors"
              size={18}
            />
          </Link>
        </motion.section>

        {/* Stats */}
        <motion.section variants={itemVariants} className="flex gap-4">
          <div className="flex-1 glass-panel p-4 flex flex-col items-center justify-center text-center">
            <span className="text-white/50 text-[10px] font-bold uppercase tracking-wider mb-1">Кредиты</span>
            <span className="text-2xl font-bold text-white tracking-tight">{credits}</span>
          </div>
          <div className="flex-1 glass-panel p-4 flex flex-col items-center justify-center text-center">
            <span className="text-white/50 text-[10px] font-bold uppercase tracking-wider mb-1">Активные</span>
            <span className="text-2xl font-bold text-white tracking-tight">{activeCount}</span>
          </div>
        </motion.section>

        {/* Latest Activity */}
        <motion.section variants={itemVariants} className="space-y-4">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Activity size={18} className="text-brand-primary" /> Активность
            </h2>
            <Link
              href="/jobs"
              className="text-xs font-semibold text-brand-cyan hover:text-brand-cyan/80 transition-colors uppercase tracking-wider"
            >
              Все
            </Link>
          </div>

          <div className="glass-card p-1">
            {!jobsLoaded ? (
              <div className="p-8 text-center">
                <div className="w-6 h-6 border-2 border-brand-cyan/40 border-t-brand-cyan rounded-full animate-spin mx-auto" />
              </div>
            ) : jobs.length ? (
              <div className="divide-y divide-white/5">
                {jobs.map((job) => (
                  <Link
                    href="/jobs"
                    key={job.id}
                    className="flex items-center justify-between p-4 hover:bg-white/5 transition-colors first:rounded-t-2xl last:rounded-b-2xl"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          isActiveJob(job.status)
                            ? "bg-brand-cyan animate-pulse"
                            : job.status === "completed"
                            ? "bg-green-500"
                            : "bg-red-500"
                        }`}
                      />
                      <div>
                        <div className="text-sm font-semibold text-white">
                          {providerLabel(job.provider)}
                        </div>
                        <div className="text-xs text-white/40">{formatDate(job.created_at)}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs font-medium text-white/70">{statusLabel(job.status)}</div>
                      <div className="text-[10px] text-white/40 font-mono mt-0.5">#{job.id}</div>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-sm text-white/40 italic">
                Нет генераций. Создай первую через бота!
              </div>
            )}
          </div>
        </motion.section>
      </motion.div>
    </main>
  );
}
