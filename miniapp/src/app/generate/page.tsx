"use client";

import Link from "next/link";
import { startTransition, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence, type Variants } from "framer-motion";
import { Sparkles, Image as ImageIcon, Video, AlertCircle, ArrowRight, Loader2, Link as LinkIcon } from "lucide-react";
import { useMiniAppUser } from "@/lib/use-miniapp-user";
import { createJob, type GenerationProvider } from "@/lib/api";
import { getProviderLabel, t } from "@/lib/miniapp-i18n";

const PROVIDERS: { id: GenerationProvider; type: "image" | "video"; icon: React.ElementType; popular?: boolean }[] = [
  { id: "nano_banana", type: "image", icon: ImageIcon, popular: true },
  { id: "veo", type: "video", icon: Video },
  { id: "kling", type: "video", icon: Video, popular: true },
];

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.1 } },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } },
};

export default function GeneratePage() {
  const router = useRouter();
  const { backendUser, telegramUser, language, loading: userLoading, error: userError } =
    useMiniAppUser();
    
  const [provider, setProvider] = useState<GenerationProvider>("kling");
  const [prompt, setPrompt] = useState("");
  const [sourceImageUrl, setSourceImageUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const telegramUserId = backendUser?.telegram_user_id ?? null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!telegramUserId) {
      setError(t(language, "jobs.telegramUnavailable"));
      return;
    }
    if (prompt.trim().length < 3) {
      setError("Промпт должен быть не короче 3 символов");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      await createJob({
        telegram_user_id: telegramUserId,
        provider,
        prompt: prompt.trim(),
        source_image_url: sourceImageUrl.trim() || undefined,
      });
      
      setSuccess(true);
      setTimeout(() => {
        router.push("/jobs");
      }, 1500);

    } catch {
      setError(t(language, "jobs.failedCreate"));
      setSubmitting(false);
    }
  }

  if (userLoading) {
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
        <motion.div variants={itemVariants} className="flex items-center gap-3">
          <Link href="/" className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors">
            <ArrowRight className="text-white rotate-180" size={20} />
          </Link>
          <h1 className="text-2xl font-bold text-white tracking-tight">Создание нейроарта</h1>
        </motion.div>

        {error && (
          <motion.div variants={itemVariants} className="p-4 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-start gap-3 text-red-400">
            <AlertCircle className="shrink-0 mt-0.5" size={18} />
            <p className="text-sm font-medium">{error}</p>
          </motion.div>
        )}

        <AnimatePresence>
          {success && (
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }} 
              animate={{ opacity: 1, scale: 1 }} 
              className="p-6 glass-card bg-green-500/10 border-green-500/20 text-center space-y-3"
            >
              <div className="w-12 h-12 mx-auto rounded-full bg-green-500/20 flex items-center justify-center">
                <Sparkles className="text-green-400" size={24} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-green-400">Генерация запущена!</h3>
                <p className="text-green-400/70 text-sm mt-1">Ожидайте результат в очереди...</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <motion.form variants={itemVariants} className="space-y-6" onSubmit={handleSubmit}>
          
          {/* Models Selection */}
          <div className="space-y-3">
            <label className="text-xs font-bold uppercase tracking-wider text-white/50 px-1">Выберите нейросеть</label>
            <div className="grid grid-cols-2 gap-3">
              {PROVIDERS.map((p) => {
                const Icon = p.icon;
                const isSelected = provider === p.id;
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setProvider(p.id)}
                    className={`relative overflow-hidden text-left p-4 rounded-2xl border transition-all duration-300 ${isSelected ? 'bg-brand-primary/20 border-brand-primary shadow-[0_0_15px_rgba(124,58,237,0.2)]' : 'bg-white/5 border-white/10 hover:bg-white/10'}`}
                  >
                    <Icon className={`mb-3 ${isSelected ? 'text-brand-primary' : 'text-white/40'}`} size={24} />
                    <div className={`font-semibold text-sm ${isSelected ? 'text-white' : 'text-white/70'}`}>{getProviderLabel(language, p.id)}</div>
                    {p.popular && (
                      <div className="absolute top-3 right-3 w-2 h-2 rounded-full bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.8)]" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Prompt Input */}
          <div className="space-y-3">
            <label className="text-xs font-bold uppercase tracking-wider text-white/50 px-1">Что вы хотите создать?</label>
            <textarea
              className="input-premium resize-none min-h-[140px]"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Например: неоновый киберпанк город в стиле аниме 80х, вид снизу, кинематографичное освещение..."
              required
            />
          </div>

          {/* Source Image (Optional) */}
          <div className="space-y-3">
            <label className="text-xs font-bold uppercase tracking-wider text-white/50 px-1 flex justify-between">
              <span>Исходное изображение</span>
              <span className="text-white/30">Опционально</span>
            </label>
            <div className="relative">
              <LinkIcon className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" size={18} />
              <input
                type="url"
                className="input-premium pl-11 py-3"
                value={sourceImageUrl}
                onChange={(e) => setSourceImageUrl(e.target.value)}
                placeholder="https://example.com/image.jpg"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting || success || !telegramUserId}
            className="btn-primary w-full mt-2"
          >
            {submitting ? (
              <Loader2 className="animate-spin text-white/80" size={24} />
            ) : (
              <>
                <Sparkles className="mr-2" size={18} />
                Сгенерировать
              </>
            )}
          </button>
        </motion.form>

      </motion.div>
    </main>
  );
}
