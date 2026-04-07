"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion, type Variants } from "framer-motion";
import { ArrowLeft, Plus, ArrowUpRight, ArrowDownRight, RefreshCw, Coins, Banknote, PlusCircle } from "lucide-react";
import { useMiniAppUser } from "@/lib/use-miniapp-user";
import { api, type BalanceHistoryResponse } from "@/lib/api";
import { formatDate } from "@/lib/format";

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
};
const itemVariants: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } },
};

function humanizeComment(comment: string | null | undefined, lang: "ru" | "uz"): string {
  if (!comment) return lang === "uz" ? "Operatsiya" : "Операция";
  const c = comment.toLowerCase();
  if (c === "welcome_bonus") return lang === "uz" ? "Xush kelibsiz bonusi 🎁" : "Приветственный бонус 🎁";
  if (c === "referral_welcome") return lang === "uz" ? "Referal bonusi 🎁" : "Реферальный бонус 🎁";
  if (c === "referral_registration_bonus") return lang === "uz" ? "Yangi referal 👥" : "Новый реферал 👥";
  if (c === "referral_commission") return lang === "uz" ? "Referal komissiyasi 👥" : "Комиссия с реферала 👥";
  if (c.startsWith("achievement_")) return lang === "uz" ? "Yutuq mukofoti 🏆" : "Достижение 🏆";
  if (c === "daily_bonus") return lang === "uz" ? "Kunlik bonus ☀️" : "Ежедневный бонус ☀️";
  if (c.includes("refund") || c.includes("qaytarildi")) return lang === "uz" ? "Qaytarildi ↩️" : "Возврат ↩️";
  if (c.includes("credits reserved") || c.includes("reserve")) return lang === "uz" ? "Generatsiya 🎨" : "Генерация 🎨";
  if (c.includes("payment") || c === "topup") return lang === "uz" ? "Balans to'ldirildi 💳" : "Пополнение 💳";
  return comment;
}

function txIcon(amount: number) {
  if (amount > 0) return <ArrowUpRight size={18} />;
  return <ArrowDownRight size={18} />;
}

function fmtUzs(n: number) {
  if (n === 0) return "0 so'm";
  return n.toLocaleString("uz-UZ") + " so'm";
}

export default function WalletPage() {
  const { backendUser: userData, telegramUser: tgUser, loading, language } = useMiniAppUser();
  const [history, setHistory] = useState<BalanceHistoryResponse | null>(null);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const uz = language === "uz";

  const loadHistory = async (id: number) => {
    setHistoryLoading(true);
    try {
      const data = await api.getBalanceHistory(id, 30);
      setHistory(data);
    } catch {}
    finally { setHistoryLoading(false); }
  };

  useEffect(() => {
    const id = userData?.telegram_user_id ?? tgUser?.id;
    if (id) loadHistory(id);
    else setHistoryLoading(false);
  }, [userData?.telegram_user_id, tgUser?.id]);

  const handleRefresh = async () => {
    const id = userData?.telegram_user_id ?? tgUser?.id;
    if (!id || refreshing) return;
    setRefreshing(true);
    await loadHistory(id);
    setRefreshing(false);
  };

  const credits = history?.credits_balance ?? userData?.credits_balance ?? 0;
  const uzsBalance = userData?.referral_earnings ?? 0;

  if (loading && historyLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <main className="min-h-screen px-5 pt-6 pb-28 overflow-x-hidden">
      {/* Ambient glows */}
      <div className="fixed top-0 left-0 w-72 h-72 bg-brand-primary/15 blur-[120px] -z-10 rounded-full pointer-events-none" />
      <div className="fixed bottom-20 right-0 w-56 h-56 bg-brand-cyan/10 blur-[100px] -z-10 rounded-full pointer-events-none" />

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="max-w-md mx-auto space-y-6"
      >
        {/* Header */}
        <motion.div variants={itemVariants} className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors"
            >
              <ArrowLeft className="text-white" size={20} />
            </Link>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              {uz ? "Balans" : "Баланс"}
            </h1>
          </div>
          <button
            onClick={handleRefresh}
            className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors"
          >
            <RefreshCw className={`text-white/60 ${refreshing ? "animate-spin" : ""}`} size={18} />
          </button>
        </motion.div>

        {/* Credits balance card */}
        <motion.div variants={itemVariants}>
          <div className="relative rounded-3xl overflow-hidden p-6 border border-white/10"
            style={{
              background: "linear-gradient(135deg, rgba(124,58,237,0.35) 0%, rgba(16,16,32,0.95) 60%, rgba(6,182,212,0.15) 100%)",
              boxShadow: "0 0 60px rgba(124,58,237,0.2), inset 0 0 0 1px rgba(255,255,255,0.06)",
            }}
          >
            <div className="absolute -top-12 -right-12 w-40 h-40 rounded-full border border-brand-primary/20 pointer-events-none" />
            <div className="absolute -top-6 -right-6 w-24 h-24 rounded-full border border-brand-cyan/15 pointer-events-none" />

            <div className="flex items-center gap-2 mb-2">
              <Coins size={16} className="text-brand-cyan" />
              <p className="text-xs font-bold uppercase tracking-[0.15em] text-white/40">
                {uz ? "Kredit balansi" : "Баланс кредитов"}
              </p>
            </div>
            <div className="flex items-end gap-3 mb-6">
              <span className="text-6xl font-black tracking-tighter text-white leading-none">{credits}</span>
              <span className="text-lg text-white/40 font-medium pb-1">
                {uz ? "kr." : "кр."}
              </span>
            </div>

            <Link
              href="/plans"
              className="flex items-center gap-2 w-full py-3.5 px-5 rounded-2xl font-bold text-sm transition-all active:scale-95"
              style={{
                background: "linear-gradient(135deg, #7C3AED, #3B82F6)",
                boxShadow: "0 4px 20px rgba(124,58,237,0.4)",
              }}
            >
              <Plus size={18} />
              {uz ? "Kredit sotib olish" : "Купить кредиты"}
            </Link>
          </div>
        </motion.div>

        {/* UZS balance card */}
        <motion.div variants={itemVariants}>
          <div className="relative rounded-3xl overflow-hidden p-5 border border-white/10"
            style={{
              background: "linear-gradient(135deg, rgba(16,185,129,0.20) 0%, rgba(16,16,32,0.95) 70%, rgba(16,185,129,0.08) 100%)",
              boxShadow: "0 0 40px rgba(16,185,129,0.12), inset 0 0 0 1px rgba(255,255,255,0.05)",
            }}
          >
            <div className="flex items-center gap-2 mb-2">
              <Banknote size={16} className="text-green-400" />
              <p className="text-xs font-bold uppercase tracking-[0.15em] text-white/40">
                {uz ? "So'm balansi" : "Баланс в сумах"}
              </p>
            </div>
            <div className="flex items-end gap-3 mb-4">
              <span className="text-3xl font-black tracking-tighter text-green-400 leading-none">
                {fmtUzs(uzsBalance)}
              </span>
            </div>
            <button
              onClick={() => {
                const tg = (window as any).Telegram?.WebApp;
                const url = "https://t.me/harfai_bot?start=uzs_topup";
                if (tg?.openTelegramLink) {
                  tg.openTelegramLink(url);
                } else {
                  window.open(url, "_blank");
                }
              }}
              className="flex items-center justify-center gap-2 w-full py-3 px-4 rounded-2xl font-bold text-sm transition-all active:scale-95"
              style={{
                background: "linear-gradient(135deg, #10b981, #059669)",
                boxShadow: "0 4px 16px rgba(16,185,129,0.35)",
              }}
            >
              <PlusCircle size={16} />
              {uz ? "So'm balansini to'ldirish" : "Пополнить баланс в сумах"}
            </button>
            <p className="text-xs text-white/35 mt-3">
              {uz
                ? "Referal komissiyalari va to'ldirishlar shu yerga tushadi"
                : "Комиссии с рефералов и пополнения накапливаются здесь"}
            </p>
          </div>
        </motion.div>

        {/* Quick stats row */}
        <motion.div variants={itemVariants} className="grid grid-cols-2 gap-3">
          <div className="glass-card p-4 text-center">
            <p className="text-[10px] font-bold uppercase tracking-wider text-white/30 mb-1">
              {uz ? "Jami to'ldirilgan" : "Всего пополнено"}
            </p>
            <p className="text-2xl font-extrabold text-green-400">
              +{(history?.transactions ?? [])
                .filter(t => t.amount > 0 && (t.reference_type === "payment" || (t.comment ?? "").includes("payment") || (t.comment ?? "").includes("topup")))
                .reduce((s, t) => s + t.amount, 0)}
            </p>
          </div>
          <div className="glass-card p-4 text-center">
            <p className="text-[10px] font-bold uppercase tracking-wider text-white/30 mb-1">
              {uz ? "Generatsiyalarga sarflangan" : "Потрачено на генерации"}
            </p>
            <p className="text-2xl font-extrabold text-red-400">
              {(history?.transactions ?? [])
                .filter(t => t.amount < 0)
                .reduce((s, t) => s + t.amount, 0)}
            </p>
          </div>
        </motion.div>

        {/* Transaction history */}
        <motion.div variants={itemVariants} className="space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-wider text-white/40 px-1">
            {uz ? "Operatsiyalar tarixi" : "История операций"}
          </h2>

          <div className="glass-card overflow-hidden">
            {historyLoading ? (
              <div className="p-10 flex justify-center">
                <div className="w-6 h-6 border-2 border-brand-primary/40 border-t-brand-primary rounded-full animate-spin" />
              </div>
            ) : (history?.transactions ?? []).length === 0 ? (
              <div className="p-10 text-center">
                <p className="text-white/30 text-sm italic">
                  {uz ? "Hali operatsiyalar yo'q" : "Операций пока нет"}
                </p>
              </div>
            ) : (
              <div className="divide-y divide-white/5">
                {(history?.transactions ?? []).map((tx) => {
                  const isPositive = tx.amount >= 0;
                  return (
                    <div
                      key={tx.id}
                      className="flex items-center justify-between px-4 py-3.5 hover:bg-white/3 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-9 h-9 rounded-2xl flex items-center justify-center shrink-0 ${
                          isPositive
                            ? "bg-green-500/15 text-green-400"
                            : "bg-red-500/15 text-red-400"
                        }`}>
                          {txIcon(tx.amount)}
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-white/90 leading-tight">
                            {humanizeComment(tx.comment ?? tx.transaction_type, language)}
                          </p>
                          <p className="text-xs text-white/35 mt-0.5">
                            {formatDate(tx.created_at, language)}
                          </p>
                        </div>
                      </div>
                      <div className="text-right shrink-0 ml-3">
                        <p className={`font-extrabold text-base ${isPositive ? "text-green-400" : "text-red-400"}`}>
                          {isPositive ? "+" : ""}{tx.amount}
                        </p>
                        <p className="text-[10px] text-white/30 mt-0.5">
                          {uz ? "qoldiq:" : "остаток:"} {tx.balance_after}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </motion.div>
      </motion.div>
    </main>
  );
}
