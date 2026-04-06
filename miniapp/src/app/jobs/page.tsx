"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence, type Variants } from "framer-motion";
import { Clock, CheckCircle2, XCircle, RefreshCcw, AlertCircle, Image as ImageIcon,
  Download, X, Play } from "lucide-react";
import { useMiniAppUser } from "@/lib/use-miniapp-user";
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

function statusLabel(status: string, lang: string) {
  const uz = lang === "uz";
  if (status === "completed")  return uz ? "Tayyor"        : "Готово";
  if (status === "pending")    return uz ? "Navbatda"      : "В очереди";
  if (status === "processing") return uz ? "Ishlanmoqda"   : "Обработка";
  if (status === "failed")     return uz ? "Xato"          : "Ошибка";
  return status;
}

function formatDate(d?: string | null) {
  if (!d) return "";
  return new Date(d).toLocaleDateString("ru-RU", {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

function isImageProvider(provider: string) {
  return provider === "nano_banana";
}

/** Download a file using Telegram WebApp API (v8+) or fallback to <a> */
function downloadFile(url: string, filename: string) {
  const tg = (window as any).Telegram?.WebApp;
  if (tg?.downloadFile) {
    tg.downloadFile({ url, file_name: filename });
  } else {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.click();
  }
}

interface MediaViewerProps {
  job: GenerationJob;
  lang: string;
  onClose: () => void;
}

function MediaViewer({ job, lang, onClose }: MediaViewerProps) {
  const uz = lang === "uz";
  const isImage = isImageProvider(job.provider);
  const ext = isImage ? "jpg" : "mp4";
  const filename = `harf_${job.provider}_${job.id}.${ext}`;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 bg-black/90 flex flex-col"
        onClick={onClose}
      >
        {/* Top bar */}
        <div
          className="flex items-center justify-between px-4 py-3 shrink-0"
          onClick={(e) => e.stopPropagation()}
        >
          <span className="text-sm font-semibold text-white/70">
            {providerLabel(job.provider)} #{job.id}
          </span>
          <button
            onClick={onClose}
            className="w-9 h-9 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20 transition-colors"
          >
            <X size={18} className="text-white" />
          </button>
        </div>

        {/* Media */}
        <div
          className="flex-1 flex items-center justify-center px-4 overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {isImage ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={job.result_url!}
              alt={job.prompt}
              className="max-w-full max-h-full object-contain rounded-2xl shadow-2xl"
              style={{ maxHeight: "calc(100vh - 180px)" }}
            />
          ) : (
            <video
              src={job.result_url!}
              controls
              autoPlay
              playsInline
              className="max-w-full max-h-full rounded-2xl shadow-2xl"
              style={{ maxHeight: "calc(100vh - 180px)" }}
            />
          )}
        </div>

        {/* Bottom bar — download */}
        <div
          className="px-4 pb-8 pt-3 shrink-0"
          onClick={(e) => e.stopPropagation()}
        >
          <button
            onClick={() => downloadFile(job.result_url!, filename)}
            className="w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl font-bold text-sm transition-all active:scale-95"
            style={{
              background: "linear-gradient(135deg, #7C3AED, #3B82F6)",
              boxShadow: "0 4px 20px rgba(124,58,237,0.4)",
            }}
          >
            <Download size={18} />
            {uz
              ? (isImage ? "Rasmni yuklash" : "Videoni yuklash")
              : (isImage ? "Скачать изображение" : "Скачать видео")}
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

export default function JobsPage() {
  const { backendUser: userData, telegramUser: tgUser, loading, language } = useMiniAppUser();
  const [jobs, setJobs] = useState<GenerationJob[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [viewingJob, setViewingJob] = useState<GenerationJob | null>(null);
  const uz = language === "uz";

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
        <p className="text-white/40 font-medium">
          {uz ? "Tarix yuklanmoqda..." : "Загрузка истории..."}
        </p>
      </div>
    );
  }

  return (
    <>
      {/* Inline media viewer */}
      {viewingJob && viewingJob.result_url && (
        <MediaViewer
          job={viewingJob}
          lang={language}
          onClose={() => setViewingJob(null)}
        />
      )}

      <main className="min-h-screen px-5 pt-6 pb-24 overflow-x-hidden">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="max-w-md mx-auto space-y-6"
        >
          {/* Header */}
          <motion.div variants={itemVariants} className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-white tracking-tight">
              {uz ? "Mening ishlarim" : "Мои работы"}
            </h1>
            <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center">
              <Clock className="text-brand-cyan" size={20} />
            </div>
          </motion.div>

          {jobs.length ? (
            <motion.div variants={itemVariants} className="space-y-3">
              {jobs.map((job) => (
                <div key={job.id} className="glass-card p-4 flex flex-col gap-3">
                  <div className="flex gap-3">
                    {/* Thumbnail for image jobs */}
                    {job.result_url && isImageProvider(job.provider) && (
                      <button
                        onClick={() => setViewingJob(job)}
                        className="relative w-16 h-16 rounded-xl overflow-hidden shrink-0 bg-white/5"
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={job.result_url}
                          alt={uz ? "Natija" : "Результат"}
                          className="w-full h-full object-cover"
                        />
                      </button>
                    )}

                    {/* Thumbnail for video jobs */}
                    {job.result_url && !isImageProvider(job.provider) && (
                      <button
                        onClick={() => setViewingJob(job)}
                        className="relative w-16 h-16 rounded-xl overflow-hidden shrink-0 bg-white/5 flex items-center justify-center"
                      >
                        <Play size={24} className="text-brand-cyan" />
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
                        {statusLabel(job.status, language)}
                      </span>
                      <span className="text-[10px] text-white/20 font-mono">#{job.id}</span>
                    </div>
                  </div>

                  {/* Open result button — opens inline viewer */}
                  {job.status === "completed" && job.result_url && (
                    <button
                      onClick={() => setViewingJob(job)}
                      className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-brand-primary/20 border border-brand-primary/30 text-brand-cyan text-sm font-semibold hover:bg-brand-primary/30 transition-colors"
                    >
                      {isImageProvider(job.provider) ? (
                        <ImageIcon size={14} />
                      ) : (
                        <Play size={14} />
                      )}
                      {isImageProvider(job.provider)
                        ? (uz ? "Rasmni ko'rish" : "Просмотреть изображение")
                        : (uz ? "Videoni ko'rish" : "Просмотреть видео")}
                      <Download size={12} className="ml-auto text-white/40" />
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
                <h3 className="text-white font-semibold mb-1">
                  {uz ? "Generatsiyalar yo'q" : "Нет генераций"}
                </h3>
                <p className="text-white/50 text-sm">
                  {uz
                    ? "🎨 Hali hech narsa yaratmadingiz.\nBotda birinchi generatsiyangizni boshlang!"
                    : "🎨 У вас пока нет генераций.\nСоздайте первую через бота!"}
                </p>
              </div>
            </motion.div>
          )}
        </motion.div>
      </main>
    </>
  );
}
