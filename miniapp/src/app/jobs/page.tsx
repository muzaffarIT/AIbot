"use client";

import Link from "next/link";
import {
  startTransition,
  useCallback,
  useEffect,
  useState,
  useTransition,
  type FormEvent,
} from "react";
import { formatDate } from "@/lib/format";
import {
  createJob,
  getJobs,
  type GenerationJob,
  type GenerationProvider,
} from "@/lib/api";
import {
  getJobStatusLabel,
  getProviderDescription,
  getProviderLabel,
  t,
} from "@/lib/miniapp-i18n";
import { useMiniAppUser } from "@/lib/use-miniapp-user";

const PROVIDERS: GenerationProvider[] = ["nano_banana", "kling", "veo"];

function isActiveStatus(status: string) {
  return status === "pending" || status === "processing";
}

function getStatusClassName(status: string) {
  if (status === "completed") return "badge success";
  if (status === "failed" || status === "cancelled") return "badge danger";
  if (status === "processing") return "badge warning";
  return "badge";
}

export default function JobsPage() {
  const { backendUser, telegramUser, language, loading: userLoading, error: userError } =
    useMiniAppUser();
  const [jobs, setJobs] = useState<GenerationJob[]>([]);
  const [provider, setProvider] = useState<GenerationProvider>("nano_banana");
  const [prompt, setPrompt] = useState("");
  const [sourceImageUrl, setSourceImageUrl] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [isRefreshing, startRefreshing] = useTransition();

  const telegramUserId = backendUser?.telegram_user_id ?? null;
  const runningJobs = jobs.filter((job) => isActiveStatus(job.status)).length;
  const completedJobs = jobs.filter((job) => job.status === "completed").length;

  const refreshJobs = useCallback(
    async (userId: number, silenceErrors = false) => {
      try {
        const data = await getJobs(userId, 12);
        startRefreshing(() => {
          setJobs(data.jobs);
          setError("");
        });
      } catch {
        if (!silenceErrors) {
          setError(t(language, "jobs.failedLoad"));
        }
      }
    },
    [language, startRefreshing]
  );

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

      if (!telegramUserId) {
        setError(userError ? t(language, "common.profileSyncFailed") : "");
        setLoading(false);
        return;
      }

      try {
        await refreshJobs(telegramUserId);
      } catch {
        setError(t(language, "jobs.failedPrepare"));
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [language, refreshJobs, telegramUser?.id, telegramUserId, userError, userLoading]);

  useEffect(() => {
    if (!telegramUserId || !jobs.some((job) => isActiveStatus(job.status))) {
      return;
    }

    const intervalId = window.setInterval(() => {
      void refreshJobs(telegramUserId, true);
    }, 5000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [jobs, refreshJobs, telegramUserId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!telegramUserId) {
      setError(t(language, "jobs.telegramUnavailable"));
      return;
    }

    setSubmitting(true);
    setError("");
    setNotice("");

    try {
      const job = await createJob({
        telegram_user_id: telegramUserId,
        provider,
        prompt: prompt.trim(),
        source_image_url: sourceImageUrl.trim() || undefined,
      });

      setNotice(
        t(language, "jobs.createdNotice", {
          id: job.id,
          status: getJobStatusLabel(language, job.status),
        })
      );
      setPrompt("");
      setSourceImageUrl("");

      startTransition(() => {
        setJobs((currentJobs) => {
          const nextJobs = [
            job,
            ...currentJobs.filter((currentJob) => currentJob.id !== job.id),
          ];
          return nextJobs.slice(0, 12);
        });
      });

      if (job.status !== "completed") {
        await refreshJobs(telegramUserId, true);
      }
    } catch {
      setError(t(language, "jobs.failedCreate"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page">
      <section className="hero">
        <div className="eyebrow">{t(language, "jobs.eyebrow")}</div>
        <h1 className="title">{t(language, "jobs.title")}</h1>
        <p className="lead">{t(language, "jobs.lead")}</p>
        <div className="hero-meta">
          <span>
            {t(language, "common.telegramId")}:{" "}
            {telegramUser?.id ?? t(language, "common.notConnected")}
          </span>
          <span>
            {isRefreshing
              ? t(language, "jobs.refreshing")
              : t(language, "jobs.autoRefresh")}
          </span>
        </div>
        <div className="cta-row">
          <Link className="button secondary" href="/">
            {t(language, "common.dashboard")}
          </Link>
          <Link className="button secondary" href="/wallet">
            {t(language, "common.wallet")}
          </Link>
          <button
            className="button ghost"
            type="button"
            onClick={() => {
              if (telegramUserId) {
                void refreshJobs(telegramUserId);
              }
            }}
            disabled={!telegramUserId || loading}
          >
            {t(language, "common.refreshNow")}
          </button>
        </div>
      </section>

      <section className="stats-grid">
        <div className="card">
          <div className="stat-label">{t(language, "jobs.recentJobs")}</div>
          <div className="stat-value">{jobs.length}</div>
        </div>
        <div className="card">
          <div className="stat-label">{t(language, "jobs.runningNow")}</div>
          <div className="stat-value">{runningJobs}</div>
        </div>
        <div className="card">
          <div className="stat-label">{t(language, "jobs.completed")}</div>
          <div className="stat-value">{completedJobs}</div>
        </div>
      </section>

      {error ? <div className="notice">{error}</div> : null}
      {notice ? <div className="notice success-notice">{notice}</div> : null}

      <section className="section-grid">
        <div className="card">
          <div className="section-header">
            <div>
              <p className="subtitle">{t(language, "jobs.createJob")}</p>
              <h2 className="section-title">{t(language, "jobs.startGeneration")}</h2>
            </div>
            <span className="pill">{getProviderLabel(language, provider)}</span>
          </div>
          <form className="form-grid" onSubmit={handleSubmit}>
            <label className="field">
              <span className="field-label">{t(language, "jobs.provider")}</span>
              <select
                className="input"
                value={provider}
                onChange={(event) => setProvider(event.target.value as GenerationProvider)}
              >
                {PROVIDERS.map((item) => (
                  <option key={item} value={item}>
                    {getProviderLabel(language, item)}
                  </option>
                ))}
              </select>
            </label>

            <label className="field">
              <span className="field-label">{t(language, "jobs.prompt")}</span>
              <textarea
                className="textarea"
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                placeholder={t(language, "jobs.promptPlaceholder")}
                required
              />
            </label>

            <label className="field">
              <span className="field-label">{t(language, "jobs.sourceImage")}</span>
              <input
                className="input"
                type="url"
                value={sourceImageUrl}
                onChange={(event) => setSourceImageUrl(event.target.value)}
                placeholder={t(language, "jobs.sourceImagePlaceholder")}
              />
            </label>

            <div className="helper-text">
              {t(language, "jobs.helper", {
                providerDescription: getProviderDescription(language, provider),
              })}
            </div>

            <button className="button full" type="submit" disabled={submitting || loading}>
              {submitting ? t(language, "jobs.creating") : t(language, "jobs.createButton")}
            </button>
          </form>
        </div>

        <div className="card">
          <div className="section-header">
            <div>
              <p className="subtitle">{t(language, "jobs.queue")}</p>
              <h2 className="section-title">{t(language, "jobs.latestQueue")}</h2>
            </div>
            <span className="pill">
              {runningJobs
                ? `${runningJobs} ${t(language, "jobs.runningNow").toLowerCase()}`
                : t(language, "jobs.idle")}
            </span>
          </div>

          {loading ? (
            <div className="empty-state">{t(language, "jobs.loadingQueue")}</div>
          ) : jobs.length ? (
            <div className="stack">
              {jobs.map((job) => (
                <article className="job-card" key={job.id}>
                  <div className="job-header">
                    <div>
                      <p className="subtitle">#{job.id}</p>
                      <h3 className="section-title">
                        {getProviderLabel(language, job.provider)}
                      </h3>
                    </div>
                    <span className={getStatusClassName(job.status)}>
                      {getJobStatusLabel(language, job.status)}
                    </span>
                  </div>

                  <p className="prompt-block">{job.prompt}</p>

                  <div className="inline-list">
                    <span className="meta-chip">
                      {job.credits_reserved} {t(language, "plans.credits").toLowerCase()}
                    </span>
                    <span className="meta-chip">
                      {formatDate(job.created_at, language)}
                    </span>
                    {job.external_job_id ? (
                      <span className="meta-chip">
                        {t(language, "jobs.external", { id: job.external_job_id })}
                      </span>
                    ) : null}
                  </div>

                  {job.source_image_url ? (
                    <div className="helper-text">
                      {t(language, "jobs.sourceImageLabel")}{" "}
                      <a href={job.source_image_url} target="_blank" rel="noreferrer">
                        {job.source_image_url}
                      </a>
                    </div>
                  ) : null}

                  {job.result_url ? (
                    <div className="cta-row">
                      <a
                        className="button secondary"
                        href={job.result_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {t(language, "common.openResult")}
                      </a>
                      <span className="helper-text">
                        {job.completed_at
                          ? t(language, "jobs.completedAt", {
                              date: formatDate(job.completed_at, language),
                            })
                          : t(language, "jobs.ready")}
                      </span>
                    </div>
                  ) : null}

                  {job.error_message ? (
                    <div className="notice error-notice">{job.error_message}</div>
                  ) : null}
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state">{t(language, "jobs.noJobs")}</div>
          )}
        </div>
      </section>
    </main>
  );
}
