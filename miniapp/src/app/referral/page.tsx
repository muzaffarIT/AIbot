"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import { motion, type Variants } from "framer-motion";
import { ArrowLeft, Users, Copy, Check, ChevronRight, Sparkles, Zap, Gift, Share2, CreditCard } from "lucide-react";
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

export default function PartnershipPage() {
  const { language, backendUser } = useMiniAppUser();
  const [copied, setCopied] = useState(false);

  const userId = backendUser?.telegram_user_id;
  const botUsername = "batirai_bot"; 

  const [refLink, setRefLink] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!userId) {
      if (!backendUser) return; // wait for backendUser to load
    }
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);

    // Fallback if the API fails, we use userId (which is the tg id)
    const defaultRef = `https://t.me/${botUsername}?start=ref_${userId || backendUser?.telegram_user_id}`;

    fetch(`/api/users/${userId}`, { signal: controller.signal })
      .then(r => r.json())
      .then(data => {
        if (data && data.referral_code) {
          setRefLink(`https://t.me/${botUsername}?start=ref_${data.referral_code}`);
        } else {
          setRefLink(defaultRef);
        }
      })
      .catch(err => {
        console.error('Referral load error:', err);
        setRefLink(defaultRef);
      })
      .finally(() => {
        setLoading(false);
        clearTimeout(timeout);
      });
  }, [userId, backendUser]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(refLink);
    } catch {
      const el = document.createElement('textarea');
      el.value = refLink;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    if ((window as any).Telegram?.WebApp?.HapticFeedback) {
      (window as any).Telegram.WebApp.HapticFeedback.impactOccurred('light');
    }
  };

  const handleShare = () => {
    const text = language === 'uz' 
      ? "AI botida rasm va video yarating! Ro'yxatdan o'tish uchun 10 kredit oling:"
      : "Создавай крутые AI фото и видео! Получи 10 кредитов при регистрации:";
    const url = `https://t.me/share/url?url=${encodeURIComponent(refLink)}&text=${encodeURIComponent(text)}`;
    (window as any).Telegram?.WebApp?.openTelegramLink(url);
  };

  return (
    <main className="min-h-screen px-5 pt-6 pb-24 overflow-x-hidden">
      <motion.div variants={containerVariants} initial="hidden" animate="visible" className="max-w-md mx-auto space-y-6">
        
        {/* Header */}
        <motion.div variants={itemVariants} className="flex items-center gap-3">
          <Link href="/" className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors">
            <ArrowLeft className="text-white" size={20} />
          </Link>
          <h1 className="text-2xl font-bold text-white tracking-tight">Рефералы</h1>
        </motion.div>

        {/* Hero Card */}
        <motion.div variants={itemVariants} className="glass-card p-6 relative overflow-hidden border-brand-primary/30">
          <div className="absolute -top-10 -right-10 w-32 h-32 bg-brand-primary/20 blur-3xl rounded-full" />
          <div className="relative z-10">
            <div className="w-12 h-12 rounded-2xl bg-brand-primary/20 flex items-center justify-center mb-4 border border-brand-primary/30">
              <Gift className="text-brand-accent" size={24} />
            </div>
            <h2 className="text-xl font-bold text-white mb-2">Приглашай друзей — получай кредиты</h2>
            <p className="text-white/60 text-sm leading-relaxed">
              За каждого друга, который зарегистрируется по твоей ссылке, ты получишь <b>20 кредитов</b>, а друг — <b>10 кредитов</b>.
            </p>
          </div>
        </motion.div>

        {/* Referral Link Box */}
        <motion.div variants={itemVariants} className="space-y-3">
          <label className="text-xs font-bold uppercase tracking-wider text-white/40 px-1">Твоя ссылка</label>
          <div className="flex gap-2">
            <div className="flex-1 glass-input py-3 px-4 text-sm text-white/80 truncate border-white/5 bg-white/5 rounded-2xl font-mono">
              {loading ? "Загрузка..." : refLink || "Ошибка загрузки"}
            </div>
            <button 
              onClick={handleCopy}
              className="w-12 h-12 rounded-2xl bg-brand-primary flex items-center justify-center text-white active:scale-90 transition-transform shadow-lg shadow-brand-primary/20"
            >
              {copied ? <Check size={20} /> : <Copy size={20} />}
            </button>
          </div>
          <button 
            onClick={handleShare}
            className="w-full btn-primary py-4 flex items-center justify-center gap-2"
          >
            <Share2 size={18} /> Отправить другу
          </button>
        </motion.div>

        {/* Stats Grid */}
        <motion.section variants={itemVariants} className="grid grid-cols-2 gap-4">
          <div className="glass-panel p-5 flex flex-col items-center justify-center text-center">
            <Users size={24} className="text-brand-cyan mb-2" />
            <span className="text-[10px] font-bold uppercase tracking-wider text-white/40 mb-1">Друзей</span>
            <span className="text-2xl font-bold text-white">{backendUser?.referral_count ?? 0}</span>
          </div>
          <div className="glass-panel p-5 flex flex-col items-center justify-center text-center">
            <Zap size={24} className="text-brand-accent mb-2" />
            <span className="text-[10px] font-bold uppercase tracking-wider text-white/40 mb-1">Заработано</span>
            <span className="text-2xl font-bold text-white">{(backendUser?.referral_count ?? 0) * 20}</span>
          </div>
        </motion.section>

        {/* How it works */}
        <motion.div variants={itemVariants} className="space-y-4">
          <h3 className="text-lg font-bold text-white">Как это работает?</h3>
          <div className="space-y-3">
             {[
               { icon: <Share2 size={18}/>, text: "Поделись ссылкой с друзьями" },
               { icon: <Users size={18}/>, text: "Друг заходит и получает +10 кредитов" },
               { icon: <Gift size={18}/>, text: "Ты получаешь +20 кредитов сразу" },
               { icon: <CreditCard size={18}/>, text: "10% от любой их покупки — твои" }
             ].map((item, i) => (
               <div key={i} className="flex items-center gap-4 p-4 glass-card border-white/5 bg-white/2 hover:bg-white/5 transition-colors">
                  <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center text-brand-primary">
                    {item.icon}
                  </div>
                  <span className="text-sm text-white/80">{item.text}</span>
               </div>
             ))}
          </div>
        </motion.div>

      </motion.div>
    </main>
  );
}
