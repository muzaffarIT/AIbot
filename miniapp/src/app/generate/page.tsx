"use client";

import Link from "next/link";
import { useState, useRef, type ChangeEvent, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence, type Variants } from "framer-motion";
import { Sparkles, Image as ImageIcon, Video, AlertCircle, ArrowRight, Loader2, Upload, X } from "lucide-react";
import { useMiniAppUser } from "@/lib/use-miniapp-user";
import { createJob, type GenerationProvider } from "@/lib/api";
import { t } from "@/lib/miniapp-i18n";

const PROVIDERS: { id: GenerationProvider; type: "image" | "video"; icon: React.ElementType; popular?: boolean; label: string }[] = [
  { id: "nano_banana", type: "image", icon: ImageIcon, popular: true, label: "🍌 Nano Banana" },
  { id: "veo", type: "video", icon: Video, label: "🎬 Veo 3" },
  { id: "kling", type: "video", icon: Video, popular: true, label: "🎥 Kling" },
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
  const { backendUser, language, loading: userLoading } = useMiniAppUser();

  const [provider, setProvider] = useState<GenerationProvider>("nano_banana");
  const [prompt, setPrompt] = useState("");
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [uploadedUrl, setUploadedUrl] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const telegramUserId = backendUser?.telegram_user_id ?? null;

  const handleImageSelect = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImagePreview(URL.createObjectURL(file));
    setUploadedUrl(null);
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("/api/upload", { method: "POST", body: form });
      const json = await res.json() as { url?: string };
      if (json.url) setUploadedUrl(json.url);
    } catch {
      setError("Не удалось загрузить изображение.");
      setImagePreview(null);
    } finally {
      setUploading(false);
    }
  };

  const clearImage = () => {
    setImagePreview(null);
    setUploadedUrl(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred("medium");

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
    (document.activeElement as HTMLElement)?.blur?.();

    try {
      await createJob({
        telegram_user_id: telegramUserId,
        provider,
        prompt: prompt.trim(),
        source_image_url: uploadedUrl ?? undefined,
      });
      setSuccess(true);
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred("success");
      setTimeout(() => router.push("/jobs"), 1500);
    } catch {
      setError(t(language, "jobs.failedCreate"));
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred("error");
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
                <p className="text-green-400/70 text-sm mt-1">Ожидайте результат (~2 мин)...</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <motion.form variants={itemVariants} className="space-y-6" onSubmit={handleSubmit}>

          {/* Model Selection */}
          <div className="space-y-3">
            <label className="text-xs font-bold uppercase tracking-wider text-white/50 px-1">Выберите нейросеть</label>
            <div className="grid grid-cols-3 gap-2">
              {PROVIDERS.map((p) => {
                const Icon = p.icon;
                const isSelected = provider === p.id;
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => setProvider(p.id)}
                    className={`relative overflow-hidden text-center p-3 rounded-2xl border transition-all duration-300 ${isSelected ? 'bg-brand-primary/20 border-brand-primary shadow-[0_0_15px_rgba(124,58,237,0.2)]' : 'bg-white/5 border-white/10 hover:bg-white/10'}`}
                  >
                    <Icon className={`mx-auto mb-1 ${isSelected ? 'text-brand-primary' : 'text-white/40'}`} size={20} />
                    <div className={`font-semibold text-xs ${isSelected ? 'text-white' : 'text-white/60'}`}>{p.label}</div>
                    {p.popular && (
                      <div className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-orange-500 shadow-[0_0_6px_rgba(249,115,22,0.8)]" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Prompt + Image Upload row */}
          <div className="space-y-3">
            <label className="text-xs font-bold uppercase tracking-wider text-white/50 px-1">Промпт</label>
            <div className="flex gap-3">
              {/* Image Upload */}
              <div
                onClick={() => fileInputRef.current?.click()}
                className={`relative rounded-2xl border transition-all cursor-pointer flex-shrink-0 ${imagePreview ? 'border-brand-primary/40' : 'border-dashed border-white/20 hover:border-white/40'} bg-white/5 flex flex-col items-center justify-center overflow-hidden`}
                style={{ width: "80px", minHeight: "120px" }}
              >
                {uploading && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/40 z-10">
                    <Loader2 className="animate-spin text-brand-primary" size={18} />
                  </div>
                )}
                {imagePreview ? (
                  <>
                    <img src={imagePreview} alt="preview" className="w-full h-full object-cover" />
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); clearImage(); }}
                      className="absolute top-1 right-1 w-5 h-5 rounded-full bg-black/70 flex items-center justify-center"
                    >
                      <X size={10} className="text-white" />
                    </button>
                  </>
                ) : (
                  <div className="flex flex-col items-center gap-1 text-white/40">
                    <Upload size={18} />
                    <span className="text-[10px] text-center leading-tight">Фото</span>
                  </div>
                )}
              </div>
              <input ref={fileInputRef} type="file" accept="image/*" style={{ display: "none" }} onChange={handleImageSelect} />

              {/* Prompt textarea */}
              <textarea
                className="input-premium resize-none flex-1"
                style={{ minHeight: "120px" }}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Например: a futuristic cat in neon city, 4k, cinematic..."
                required
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting || success || !telegramUserId || uploading}
            className="btn-primary w-full mt-2"
          >
            {submitting ? (
              <div className="flex items-center gap-2">
                <Loader2 className="animate-spin" size={20} />
                <span>Генерирую... (~2 мин)</span>
              </div>
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
