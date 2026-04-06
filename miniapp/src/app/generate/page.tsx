"use client";

import Link from "next/link";
import { useState, useRef, type ChangeEvent, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence, type Variants } from "framer-motion";
import { Sparkles, Image as ImageIcon, Video, AlertCircle, ArrowRight, Loader2, Upload, X, ChevronRight } from "lucide-react";
import { useMiniAppUser } from "@/lib/use-miniapp-user";
import { createJob, type GenerationProvider } from "@/lib/api";

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
};
const itemVariants: Variants = {
  hidden: { opacity: 0, y: 14 },
  visible: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } },
};

type AIOption = {
  id: GenerationProvider;
  label: string;
  descriptionRu: string;
  descriptionUz: string;
  type: "image" | "video";
};

type ModeOption = {
  key: string;
  labelRu: string;
  labelUz: string;
  detailRu: string;
  detailUz: string;
  cost: number;
};

const AI_LIST: AIOption[] = [
  {
    id: "nano_banana",
    label: "🍌 Nano Banana",
    descriptionRu: "Генерация изображений высокого качества",
    descriptionUz: "Yuqori sifatli rasm generatsiyasi",
    type: "image",
  },
  {
    id: "veo",
    label: "🎬 Veo 3",
    descriptionRu: "Видео от Google — плавное и реалистичное",
    descriptionUz: "Google'dan silliq va real video",
    type: "video",
  },
  {
    id: "kling",
    label: "🎥 Kling 3.0",
    descriptionRu: "Профессиональное видео — кинематографичность",
    descriptionUz: "Professional kinematografik video",
    type: "video",
  },
];

const MODES: Record<GenerationProvider, ModeOption[]> = {
  nano_banana: [
    { key: "nano:std", labelRu: "Стандарт 1K",  labelUz: "Standart 1K",  detailRu: "1024×1024 · быстро",    detailUz: "1024×1024 · tez",       cost: 5  },
    { key: "nano:hd",  labelRu: "HD 2K",         labelUz: "HD 2K",        detailRu: "1536×1536 · высокое",   detailUz: "1536×1536 · yuqori",    cost: 10 },
    { key: "nano:4k",  labelRu: "4K Ultra",       labelUz: "4K Ultra",     detailRu: "2048×2048 · максимум",  detailUz: "2048×2048 · maksimal",  cost: 20 },
  ],
  veo: [
    { key: "veo:fast",    labelRu: "Fast 720p",    labelUz: "Fast 720p",    detailRu: "720p · 8 сек · быстро",     detailUz: "720p · 8 son · tez",       cost: 30 },
    { key: "veo:quality", labelRu: "Quality 1080p", labelUz: "Quality 1080p", detailRu: "1080p · 8 сек · качество", detailUz: "1080p · 8 son · sifatli",  cost: 80 },
  ],
  kling: [
    { key: "kling:std5",  labelRu: "Стандарт 5 сек", labelUz: "Standart 5 son", detailRu: "Стандарт · 5 секунд",  detailUz: "Standart · 5 soniya",  cost: 40  },
    { key: "kling:pro5",  labelRu: "Pro 5 сек",       labelUz: "Pro 5 son",      detailRu: "Pro · 5 секунд",       detailUz: "Pro · 5 soniya",       cost: 70  },
    { key: "kling:pro10", labelRu: "Pro 10 сек",      labelUz: "Pro 10 son",     detailRu: "Pro · 10 секунд",      detailUz: "Pro · 10 soniya",      cost: 120 },
  ],
};

type Step = "ai" | "mode" | "prompt";

export default function GeneratePage() {
  const router = useRouter();
  const { backendUser, language, loading: userLoading } = useMiniAppUser();
  const uz = language === "uz";

  const [step, setStep] = useState<Step>("ai");
  const [provider, setProvider] = useState<GenerationProvider>("nano_banana");
  const [modeKey, setModeKey] = useState<string>("");
  const [prompt, setPrompt] = useState("");
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [uploadedUrl, setUploadedUrl] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const telegramUserId = backendUser?.telegram_user_id ?? null;
  const credits = backendUser?.credits_balance ?? 0;

  const selectedAI = AI_LIST.find((a) => a.id === provider)!;
  const selectedMode = MODES[provider].find((m) => m.key === modeKey);

  const handleSelectAI = (ai: AIOption) => {
    setProvider(ai.id);
    setModeKey("");
    setStep("mode");
  };

  const handleSelectMode = (mode: ModeOption) => {
    setModeKey(mode.key);
    setStep("prompt");
  };

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
      setError(uz ? "Rasmni yuklashda xato yuz berdi." : "Не удалось загрузить изображение.");
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
      setError(uz ? "Telegram orqali oching" : "Откройте через Telegram");
      return;
    }
    if (prompt.trim().length < 3) {
      setError(uz ? "Prompt kamida 3 ta belgidan iborat bo'lishi kerak" : "Промпт должен быть не короче 3 символов");
      return;
    }
    if (!modeKey) {
      setError(uz ? "Rejimni tanlang" : "Выберите режим");
      return;
    }

    setSubmitting(true);
    setError("");
    (document.activeElement as HTMLElement)?.blur?.();

    try {
      await createJob({
        telegram_user_id: telegramUserId,
        provider,
        quality_key: modeKey,
        prompt: prompt.trim(),
        source_image_url: uploadedUrl ?? undefined,
      });
      setSuccess(true);
      window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred("success");
      setTimeout(() => router.push("/jobs"), 1500);
    } catch {
      setError(uz
        ? "Vazifani yaratib bo'lmadi. Balansni tekshiring."
        : "Не удалось создать задачу. Проверьте баланс.");
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
          {step === "ai" ? (
            <Link href="/" className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors">
              <ArrowRight className="text-white rotate-180" size={20} />
            </Link>
          ) : (
            <button
              type="button"
              onClick={() => setStep(step === "prompt" ? "mode" : "ai")}
              className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors"
            >
              <ArrowRight className="text-white rotate-180" size={20} />
            </button>
          )}
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              {uz ? "Yaratish" : "Создание"}
            </h1>
            <p className="text-xs text-white/40 mt-0.5">
              {step === "ai" && (uz ? "Neyrosetni tanlang" : "Выберите нейросеть")}
              {step === "mode" && `${selectedAI.label} — ${uz ? "rejimni tanlang" : "выберите режим"}`}
              {step === "prompt" && `${selectedAI.label} · ${uz ? selectedMode?.labelUz : selectedMode?.labelRu}`}
            </p>
          </div>
        </motion.div>

        {/* Step indicator */}
        <motion.div variants={itemVariants} className="flex gap-2">
          {(["ai", "mode", "prompt"] as Step[]).map((s, i) => (
            <div
              key={s}
              className={`h-1 flex-1 rounded-full transition-all duration-300 ${
                step === s ? "bg-brand-primary" : i < ["ai","mode","prompt"].indexOf(step) ? "bg-brand-primary/40" : "bg-white/10"
              }`}
            />
          ))}
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
                <h3 className="text-lg font-bold text-green-400">
                  {uz ? "Generatsiya boshlandi!" : "Генерация запущена!"}
                </h3>
                <p className="text-green-400/70 text-sm mt-1">
                  {uz ? "Ishlarga o'tmoqdamiz..." : "Переходим к работам..."}
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* STEP 1: Select AI */}
        <AnimatePresence mode="wait">
          {step === "ai" && (
            <motion.div
              key="step-ai"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-3"
            >
              {AI_LIST.map((ai) => (
                <button
                  key={ai.id}
                  type="button"
                  onClick={() => handleSelectAI(ai)}
                  className="w-full glass-card p-4 flex items-center justify-between hover:bg-white/8 active:scale-[0.98] transition-all duration-200"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-2xl bg-brand-primary/10 flex items-center justify-center text-2xl">
                      {ai.type === "image" ? <ImageIcon className="text-brand-cyan" size={22} /> : <Video className="text-brand-cyan" size={22} />}
                    </div>
                    <div className="text-left">
                      <div className="font-semibold text-white text-base">{ai.label}</div>
                      <div className="text-xs text-white/50 mt-0.5">
                        {uz ? ai.descriptionUz : ai.descriptionRu}
                      </div>
                    </div>
                  </div>
                  <ChevronRight className="text-white/30" size={18} />
                </button>
              ))}
            </motion.div>
          )}

          {/* STEP 2: Select Mode */}
          {step === "mode" && (
            <motion.div
              key="step-mode"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-3"
            >
              <p className="text-xs text-white/40 px-1">
                {uz ? "Balans:" : "Баланс:"}{" "}
                <span className="text-white/70 font-semibold">
                  {credits} {uz ? "kr." : "кр."}
                </span>
              </p>
              {MODES[provider].map((mode) => {
                const canAfford = credits >= mode.cost;
                return (
                  <button
                    key={mode.key}
                    type="button"
                    onClick={() => canAfford && handleSelectMode(mode)}
                    className={`w-full glass-card p-4 flex items-center justify-between transition-all duration-200 ${
                      canAfford ? "hover:bg-white/8 active:scale-[0.98]" : "opacity-40 cursor-not-allowed"
                    }`}
                  >
                    <div className="text-left">
                      <div className="font-semibold text-white text-sm">
                        {uz ? mode.labelUz : mode.labelRu}
                      </div>
                      <div className="text-xs text-white/40 mt-0.5">
                        {uz ? mode.detailUz : mode.detailRu}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-brand-cyan font-bold text-sm">
                        {mode.cost} {uz ? "kr." : "кр."}
                      </span>
                      <ChevronRight className="text-white/30" size={18} />
                    </div>
                  </button>
                );
              })}
            </motion.div>
          )}

          {/* STEP 3: Prompt */}
          {step === "prompt" && !success && (
            <motion.form
              key="step-prompt"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="space-y-4"
              onSubmit={handleSubmit}
            >
              {/* Selected summary */}
              <div className="glass-card p-3 flex items-center justify-between">
                <span className="text-xs text-white/50">
                  {uz ? "Rejim" : "Режим"}
                </span>
                <span className="text-xs font-semibold text-brand-cyan">
                  {uz ? selectedMode?.labelUz : selectedMode?.labelRu} · {selectedMode?.cost} {uz ? "kr." : "кр."}
                </span>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-white/50 px-1">
                  {uz ? "Prompt" : "Промпт"}
                </label>
                <div className="flex gap-3">
                  {/* Image Upload */}
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className={`relative rounded-2xl border transition-all cursor-pointer flex-shrink-0 ${
                      imagePreview ? "border-brand-primary/40" : "border-dashed border-white/20 hover:border-white/40"
                    } bg-white/5 flex flex-col items-center justify-center overflow-hidden`}
                    style={{ width: "80px", minHeight: "120px" }}
                  >
                    {uploading && (
                      <div className="absolute inset-0 flex items-center justify-center bg-black/40 z-10">
                        <Loader2 className="animate-spin text-brand-primary" size={18} />
                      </div>
                    )}
                    {imagePreview ? (
                      <>
                        <img src={imagePreview} alt={uz ? "Ko'rinish" : "Превью"} className="w-full h-full object-cover" />
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
                        <span className="text-[10px] text-center leading-tight">
                          {uz ? "Rasm" : "Фото"}
                        </span>
                      </div>
                    )}
                  </div>
                  <input ref={fileInputRef} type="file" accept="image/*" style={{ display: "none" }} onChange={handleImageSelect} />

                  <textarea
                    className="input-premium resize-none flex-1"
                    style={{ minHeight: "120px" }}
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder={
                      uz
                        ? "Masalan: neon shahar kechasi, sinematografik 4K..."
                        : "Например: неоновый город ночью, кинематографично 4K..."
                    }
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={submitting || !telegramUserId || uploading}
                className="btn-primary w-full"
              >
                {submitting ? (
                  <div className="flex items-center gap-2">
                    <Loader2 className="animate-spin" size={20} />
                    <span>{uz ? "Generatsiya..." : "Генерирую..."}</span>
                  </div>
                ) : (
                  <>
                    <Sparkles className="mr-2" size={18} />
                    {uz
                      ? `Yaratish · ${selectedMode?.cost} kr.`
                      : `Сгенерировать · ${selectedMode?.cost} кр.`}
                  </>
                )}
              </button>
            </motion.form>
          )}
        </AnimatePresence>

      </motion.div>
    </main>
  );
}
