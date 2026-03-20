"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion, type Variants } from "framer-motion";
import { ArrowLeft, Wallet, History, ArrowUpRight, ArrowDownRight, CreditCard, ChevronRight, Loader2, AlertCircle } from "lucide-react";
import { getBalanceHistory, type BalanceHistoryResponse } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { t } from "@/lib/miniapp-i18n";
import { useMiniAppUser } from "@/lib/use-miniapp-user";

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.1 } },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } },
};

export default function WalletPage() {
  const { backendUser, telegramUser, language, loading: userLoading, error: userError } =
    useMiniAppUser();
  const [history, setHistory] = useState<BalanceHistoryResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      if (userLoading) return;
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
        const data = await getBalanceHistory(backendUser.telegram_user_id, 20);
        setHistory(data);
      } catch {
        setError(t(language, "common.failedLoadData"));
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [backendUser?.telegram_user_id, language, telegramUser?.id, userError, userLoading]);

  if (userLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="animate-spin text-brand-primary" size={32} />
      </div>
    );
  }

  return (
    <main className="min-h-screen px-5 pt-6 pb-24 overflow-x-hidden relative">
      <div className="absolute top-0 right-0 w-64 h-64 bg-brand-cyan/20 blur-[100px] -z-10 rounded-full" />
      
      <motion.div variants={containerVariants} initial="hidden" animate="visible" className="max-w-md mx-auto space-y-6">
        
       {/* Header */}
       <motion.div variants={itemVariants} className="flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Link href="/" className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors">
              <ArrowLeft className="text-white" size={20} />
            </Link>
            <h1 className="text-2xl font-bold text-white tracking-tight">Кошелёк</h1>
          </div>
        </motion.div>

        {error && (
          <motion.div variants={itemVariants} className="p-4 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-start gap-3 text-red-400">
            <AlertCircle className="shrink-0 mt-0.5" size={18} />
            <p className="text-sm font-medium">{error}</p>
          </motion.div>
        )}

        {/* Balance Card */}
        <motion.div variants={itemVariants} className="relative overflow-hidden rounded-[2rem] p-6 text-white border border-white/10 glass-card bg-gradient-to-br from-brand-800 to-brand-900 shadow-2xl">
          <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-b from-white/5 to-transparent pointer-events-none" />
          <div className="absolute -top-24 -right-12 text-brand-cyan/10 pointer-events-none">
            <Wallet size={164} />
          </div>
          
          <div className="relative z-10 flex flex-col gap-6">
            <div>
               <div className="text-white/60 text-sm font-medium uppercase tracking-widest mb-1">{t(language, "wallet.availableCredits")}</div>
               <div className="text-6xl font-extrabold tracking-tighter">
                 {history?.credits_balance ?? backendUser?.credits_balance ?? 0}
               </div>
            </div>
            
            <Link 
              href="/plans" 
              className="flex items-center justify-between w-full p-4 rounded-2xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors group"
            >
              <div className="flex items-center gap-3">
                 <div className="w-10 h-10 rounded-full bg-brand-cyan/20 flex items-center justify-center text-brand-cyan">
                   <CreditCard size={20} />
                 </div>
                 <div className="text-left">
                   <div className="font-semibold">{t(language, "wallet.buyCredits")}</div>
                   <div className="text-xs text-white/50">Пополнить через Telegram Stars</div>
                 </div>
              </div>
              <ChevronRight size={20} className="text-white/30 group-hover:text-white/70 transition-colors" />
            </Link>
          </div>
        </motion.div>

        {/* Transaction History */}
        <motion.div variants={itemVariants} className="space-y-4">
          <div className="flex items-center gap-2 px-1">
            <History size={18} className="text-brand-primary" />
            <h2 className="text-lg font-bold text-white">История транзакций</h2>
          </div>

          <div className="glass-card mb-8">
            {history?.transactions.length ? (
              <div className="divide-y divide-white/5">
                {history.transactions.map((transaction) => {
                  const isPositive = transaction.amount >= 0;
                  return (
                    <div key={transaction.id} className="flex items-center justify-between p-4 hover:bg-white/5 transition-colors first:rounded-t-3xl last:rounded-b-3xl">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${isPositive ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                          {isPositive ? <ArrowUpRight size={20} /> : <ArrowDownRight size={20} />}
                        </div>
                        <div>
                          <div className="text-sm font-semibold text-white/90 truncate max-w-[180px]">
                             {transaction.comment || transaction.transaction_type}
                          </div>
                          <div className="text-xs text-white/40 mt-0.5">{formatDate(transaction.created_at, language)}</div>
                        </div>
                      </div>
                      
                      <div className="text-right shrink-0">
                         <div className={`font-bold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
                            {isPositive ? '+' : ''}{transaction.amount}
                         </div>
                         <div className="text-[10px] text-white/40 font-mono mt-0.5">
                            Остаток: {transaction.balance_after}
                         </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-8 text-center text-sm text-white/40 italic flex flex-col items-center">
                 <Wallet size={32} className="text-white/20 mb-2" />
                 {t(language, "wallet.noTransactions")}
              </div>
            )}
          </div>
        </motion.div>

      </motion.div>
    </main>
  );
}
