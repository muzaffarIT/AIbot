"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useMiniAppUser } from "@/lib/use-miniapp-user";
import { motion, type Variants } from "framer-motion";
import { Sparkles, Users, Image as ImageIcon, Video, Coins, AlertCircle, ChevronRight, Activity, Zap } from "lucide-react";
import {
  getBalanceHistory,
  getJobs,
  getOrders,
  type BalanceHistoryResponse,
  type GenerationJob,
  type OrderSummary,
} from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/format";
import {
  getJobStatusLabel,
  getLanguageLabel,
  getOrderStatusLabel,
  getProviderLabel,
  t,
} from "@/lib/miniapp-i18n";

function getDisplayName(
  firstName?: string | null,
  username?: string | null,
  fallback = "Creator"
) {
  return firstName || username || fallback;
}

function isRunningStatus(status: string) {
  return status === "pending" || status === "processing";
}

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.1 },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } },
};

export default function HomePage() {
  const { telegramUser, backendUser, language, loading: userLoading, error: userError } =
    useMiniAppUser();
  const [history, setHistory] = useState<BalanceHistoryResponse | null>(null);
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [jobs, setJobs] = useState<GenerationJob[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [isTelegram, setIsTelegram] = useState(true);

  useEffect(() => {
    // Check if opened from Telegram
    setIsTelegram(Boolean(window.Telegram?.WebApp?.initData));
  }, []);

  useEffect(() => {
    async function load() {
      if (userLoading) {
        return;
      }

      if (!telegramUser?.id) {
        setError(t(language, "common.openFromTelegram"));
        setLoading(false);
        return;
      }

      if (!backendUser?.telegram_user_id) {
        setError(userError ? t(language, "common.profileSyncFailed") : "");
        setLoading(false);
        return;
      }

      try {
        setError("");
        const [historyData, ordersData, jobsData] = await Promise.all([
          getBalanceHistory(backendUser.telegram_user_id, 5),
          getOrders(backendUser.telegram_user_id, 3),
          getJobs(backendUser.telegram_user_id, 4),
        ]);

        setHistory(historyData);
        setOrders(ordersData.orders);
        setJobs(jobsData.jobs);
      } catch {
        setError(t(language, "common.failedLoadData"));
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [backendUser?.telegram_user_id, language, telegramUser?.id, userError, userLoading]);

  return (
    <main className="min-h-screen px-5 pt-6 pb-24 overflow-x-hidden">
      <motion.div variants={containerVariants} initial="hidden" animate="visible" className="max-w-md mx-auto space-y-8">
        
        {/* Hero Section */}
        <motion.section variants={itemVariants} className="relative">
          <div className="absolute inset-0 bg-gradient-to-br from-brand-primary/20 to-brand-cyan/20 blur-3xl -z-10 rounded-[3rem]" />
          <div className="glass-card p-6 border-white/20 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-50 text-white"><Sparkles size={48} strokeWidth={1} /></div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-primary/20 text-brand-accent text-xs font-bold uppercase tracking-wider mb-4 border border-brand-primary/30">
              <Zap size={14} className="text-brand-accent fill-brand-accent/50" />
              {t(language, "home.eyebrow")}
            </div>
            <h1 className="text-4xl font-extrabold text-white mb-3">
              BATIR <span className="text-gradient">AI</span>
            </h1>
            <p className="text-white/60 text-sm leading-relaxed max-w-[280px]">
              {loading || userLoading
                ? t(language, "home.leadLoading")
                : t(language, "home.leadReady", {
                    name: getDisplayName(
                      backendUser?.first_name,
                      backendUser?.username,
                      getDisplayName(telegramUser?.first_name, telegramUser?.username, "Creator")
                    ),
                  })}
            </p>
          </div>
        </motion.section>

        {error && !isTelegram && (
          <motion.div variants={itemVariants} className="p-4 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-start gap-3 text-red-400">
            <AlertCircle className="shrink-0 mt-0.5" size={18} />
            <p className="text-sm font-medium">{error}</p>
          </motion.div>
        )}
        {error && isTelegram && (
          <motion.div variants={itemVariants} className="p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-2xl flex items-start gap-3 text-yellow-400">
            <AlertCircle className="shrink-0 mt-0.5" size={18} />
            <p className="text-sm font-medium">{error}</p>
          </motion.div>
        )}

        {/* Quick Actions Grid */}
        <motion.section variants={itemVariants} className="grid grid-cols-2 gap-4">
          <Link href="/partnership" className="glass-card p-5 group hover:bg-white/5 transition-colors relative overflow-hidden">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-cyan to-blue-500 flex items-center justify-center mb-4 shadow-lg shadow-brand-cyan/20">
              <Users className="text-white" size={20} />
            </div>
            <h3 className="font-semibold text-white mb-1">Рефералы</h3>
            <p className="text-xs text-white/50">Пригласить друзей</p>
            <ChevronRight className="absolute bottom-4 right-4 text-white/30 group-hover:text-white/70 transition-colors" size={18} />
          </Link>

          <Link href="/plans" className="glass-card p-5 group hover:bg-white/5 transition-colors relative overflow-hidden">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-primary to-purple-600 flex items-center justify-center mb-4 shadow-lg shadow-brand-primary/20">
              <Coins className="text-white" size={20} />
            </div>
            <h3 className="font-semibold text-white mb-1">{t(language, "common.plans")}</h3>
            <p className="text-xs text-white/50">Пополнить баланс</p>
            <ChevronRight className="absolute bottom-4 right-4 text-white/30 group-hover:text-white/70 transition-colors" size={18} />
          </Link>
        </motion.section>

        {/* Stats Row */}
        <motion.section variants={itemVariants} className="flex gap-4">
          <div className="flex-1 glass-panel p-4 flex flex-col items-center justify-center text-center">
            <span className="text-white/50 text-[10px] font-bold uppercase tracking-wider mb-1">{t(language, "home.creditsBalance")}</span>
            <span className="text-2xl font-bold text-white tracking-tight">{history?.credits_balance ?? backendUser?.credits_balance ?? 0}</span>
          </div>
          <div className="flex-1 glass-panel p-4 flex flex-col items-center justify-center text-center">
            <span className="text-white/50 text-[10px] font-bold uppercase tracking-wider mb-1">Активные</span>
            <span className="text-2xl font-bold text-white tracking-tight">{jobs.filter((job) => isRunningStatus(job.status)).length}</span>
          </div>
        </motion.section>

        {/* Latest Activity */}
        <motion.section variants={itemVariants} className="space-y-4">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-lg font-bold text-white flex items-center gap-2"><Activity size={18} className="text-brand-primary"/> Активность</h2>
            <Link href="/jobs" className="text-xs font-semibold text-brand-cyan hover:text-brand-cyan/80 transition-colors uppercase tracking-wider">Все</Link>
          </div>
          
          <div className="glass-card p-1">
            {jobs.length ? (
              <div className="divide-y divide-white/5">
                {jobs.map((job) => (
                  <Link href="/jobs" key={job.id} className="flex items-center justify-between p-4 hover:bg-white/5 transition-colors first:rounded-t-2xl last:rounded-b-2xl">
                    <div className="flex items-center gap-3">
                      <div className={`w-2 h-2 rounded-full ${isRunningStatus(job.status) ? "bg-brand-cyan animate-pulse shadow-[0_0_10px_rgba(6,182,212,0.8)]" : job.status === "completed" ? "bg-green-500" : "bg-red-500"}`} />
                      <div>
                        <div className="text-sm font-semibold text-white">{getProviderLabel(language, job.provider)}</div>
                        <div className="text-xs text-white/40">{formatDate(job.created_at, language)}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs font-medium text-white/70">{getJobStatusLabel(language, job.status)}</div>
                      <div className="text-[10px] text-white/40 font-mono mt-0.5">#{job.id}</div>
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-sm text-white/40 italic">{t(language, "home.noJobs")}</div>
            )}
          </div>
        </motion.section>

      </motion.div>
    </main>
  );
}
