"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion, type Variants } from "framer-motion";
import { ArrowLeft, Star, Zap, CheckCircle2, ChevronRight, Crown, AlertCircle, Loader2 } from "lucide-react";
import { getPlans, type Plan } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { t } from "@/lib/miniapp-i18n";
import { useMiniAppUser } from "@/lib/use-miniapp-user";

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.1 } },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, scale: 0.95, y: 15 },
  visible: { opacity: 1, scale: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } },
};

export default function PlansPage() {
  const { telegramUser, language, loading: userLoading } = useMiniAppUser();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [error, setError] = useState("");
  const [loadingCode, setLoadingCode] = useState<string>("");

  useEffect(() => {
    async function load() {
      try {
        const data = await getPlans();
        setPlans(data);
      } catch {
        setError(t(language, "plans.failedLoad"));
      }
    }
    void load();
  }, [language]);

  const handleBuy = (plan: Plan) => {
    if (!telegramUser?.id) {
      setError(t(language, "plans.openFromTelegram"));
      return;
    }
    
    setLoadingCode(plan.code);
    
    try {
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.sendData?.(
          JSON.stringify({ action: "buy_plan", package_id: plan.code })
        );
        // Add a slight delay just to show button loading state briefly before the app closes
        setTimeout(() => setLoadingCode(""), 1000);
      } else {
        setError("Telegram WebApp API is not available.");
        setLoadingCode("");
      }
    } catch (e) {
      console.error(e);
      setError("Failed to trigger Telegram payment.");
      setLoadingCode("");
    }
  };

  if (userLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="animate-spin text-brand-primary" size={32} />
      </div>
    );
  }

  return (
    <main className="min-h-screen px-5 pt-6 pb-24 overflow-x-hidden relative">
      <div className="absolute top-0 right-0 w-64 h-64 bg-brand-primary/20 blur-[100px] -z-10 rounded-full" />
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-brand-cyan/20 blur-[100px] -z-10 rounded-full" />
      
      <motion.div variants={containerVariants} initial="hidden" animate="visible" className="max-w-md mx-auto space-y-6">
        
       {/* Header */}
       <motion.div variants={itemVariants} className="flex justify-between items-center">
          <Link href="/" className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors">
            <ArrowLeft className="text-white" size={20} />
          </Link>
          <Link href="/wallet" className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-brand-primary/20 text-brand-cyan text-sm font-semibold border border-brand-primary/30">
            <Star size={14} className="fill-brand-cyan" />
            Баланс
          </Link>
        </motion.div>

        <motion.div variants={itemVariants} className="text-center space-y-2 mb-8 mt-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-orange-500/20 text-orange-400 text-xs font-bold uppercase tracking-wider mx-auto border border-orange-500/30">
            <Crown size={14} /> Безлимит возможностей
          </div>
          <h1 className="text-4xl font-extrabold text-white tracking-tight leading-tight">
            Выберите <span className="text-gradient">Пакет</span>
          </h1>
          <p className="text-white/60 text-sm max-w-[280px] mx-auto">
            Пополните баланс кредитов для генерации нейроарта и видео.
          </p>
        </motion.div>

        {error && (
          <motion.div variants={itemVariants} className="p-4 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-start gap-3 text-red-400">
            <AlertCircle className="shrink-0 mt-0.5" size={18} />
            <p className="text-sm font-medium">{error}</p>
          </motion.div>
        )}

        {/* Pricing Grid */}
        <motion.div variants={itemVariants} className="space-y-4">
          {!plans.length && !error ? (
             <div className="flex justify-center p-8">
               <Loader2 className="animate-spin text-brand-primary" size={32} />
             </div>
          ) : (
            plans.map((plan) => {
              const isPro = plan.code === "pro" || plan.code === "standard"; // Define "featured" packs
              return (
                <div 
                  key={plan.code} 
                  className={`relative p-5 sm:p-6 rounded-3xl border overflow-hidden transition-all duration-300 ${isPro ? 'bg-brand-primary/10 border-brand-primary/50 shadow-[0_8px_32px_rgba(124,58,237,0.15)] shadow-brand-primary/20 scale-[1.02]' : 'bg-brand-800/60 border-white/10 hover:border-white/20'}`}
                >
                  {isPro && (
                    <div className="absolute top-0 right-0">
                      <div className="bg-gradient-to-r from-brand-primary to-brand-cyan text-white text-[10px] font-bold uppercase tracking-wider py-1 px-3 rounded-bl-2xl">
                        Популярный
                      </div>
                    </div>
                  )}
                  
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-xl font-bold text-white mb-1">{plan.name}</h3>
                      <div className="flex items-baseline gap-1">
                        <span className="text-3xl font-extrabold text-white">{formatCurrency(plan.price, plan.currency, language)}</span>
                      </div>
                    </div>
                    <div className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 ${isPro ? 'bg-brand-primary/20 text-brand-primary' : 'bg-white/5 text-white/50'}`}>
                      <Zap size={24} className={isPro ? "fill-brand-primary/50" : ""} />
                    </div>
                  </div>

                  <p className="text-sm text-white/60 mb-6 min-h-[40px]">
                    {plan.description || t(language, "plans.defaultDescription")}
                  </p>

                  <div className="space-y-3 mb-6">
                    <div className="flex items-center gap-3 text-sm text-white/80">
                      <CheckCircle2 size={16} className={isPro ? "text-brand-cyan" : "text-white/40"} />
                      <span><strong>{plan.credits_amount}</strong> {t(language, "plans.credits")}</span>
                    </div>
                    {plan.duration_days && (
                      <div className="flex items-center gap-3 text-sm text-white/80">
                        <CheckCircle2 size={16} className={isPro ? "text-brand-cyan" : "text-white/40"} />
                        <span>Доступ на {t(language, "plans.days", { days: plan.duration_days })}</span>
                      </div>
                    )}
                  </div>

                  <button
                    onClick={() => handleBuy(plan)}
                    disabled={loadingCode === plan.code}
                    className={`w-full relative overflow-hidden flex items-center justify-center min-h-[52px] font-semibold text-white rounded-xl transition-all duration-300 ${isPro ? 'bg-gradient-to-r from-brand-primary to-brand-cyan hover:scale-[1.02] active:scale-[0.98] shadow-lg shadow-brand-primary/30' : 'bg-white/10 hover:bg-white/15'}`}
                  >
                    {loadingCode === plan.code ? (
                      <Loader2 size={20} className="animate-spin text-white/80" />
                    ) : (
                      <>
                        <Star size={16} className="mr-2" />
                        Оплатить Telegram Stars
                      </>
                    )}
                  </button>
                </div>
              );
            })
          )}
        </motion.div>

      </motion.div>
    </main>
  );
}
