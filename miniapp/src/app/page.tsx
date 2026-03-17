"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useMiniAppUser } from "@/lib/use-miniapp-user";
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

export default function HomePage() {
  const { telegramUser, backendUser, language, loading: userLoading, error: userError } =
    useMiniAppUser();
  const [history, setHistory] = useState<BalanceHistoryResponse | null>(null);
  const [orders, setOrders] = useState<OrderSummary[]>([]);
  const [jobs, setJobs] = useState<GenerationJob[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

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
  }, [
    backendUser?.telegram_user_id,
    language,
    telegramUser?.id,
    userError,
    userLoading,
  ]);

  return (
    <main className="page">
      <section className="hero">
        <div className="eyebrow">{t(language, "home.eyebrow")}</div>
        <h1 className="title">{t(language, "home.title")}</h1>
        <p className="lead">
          {loading || userLoading
            ? t(language, "home.leadLoading")
            : t(language, "home.leadReady", {
                name: getDisplayName(
                  backendUser?.first_name,
                  backendUser?.username,
                  getDisplayName(
                    telegramUser?.first_name,
                    telegramUser?.username,
                    "Creator"
                  )
                ),
              })}
        </p>
        <div className="hero-meta">
          <span>
            {t(language, "common.telegramId")}:{" "}
            {telegramUser?.id ?? t(language, "common.notConnected")}
          </span>
          <span>
            {t(language, "common.language")}: {getLanguageLabel(language)}
          </span>
        </div>
        <div className="cta-row">
          <Link className="button" href="/plans">
            {t(language, "home.explorePlans")}
          </Link>
          <Link className="button secondary" href="/jobs">
            {t(language, "home.openJobs")}
          </Link>
          <Link className="button secondary" href="/wallet">
            {t(language, "home.openWallet")}
          </Link>
        </div>
      </section>

      <section className="stats-grid">
        <div className="card">
          <div className="stat-label">{t(language, "home.creditsBalance")}</div>
          <div className="stat-value">
            {history?.credits_balance ?? backendUser?.credits_balance ?? 0}
          </div>
        </div>
        <div className="card">
          <div className="stat-label">{t(language, "home.runningJobs")}</div>
          <div className="stat-value">
            {jobs.filter((job) => isRunningStatus(job.status)).length}
          </div>
        </div>
        <div className="card">
          <div className="stat-label">{t(language, "home.recentOrders")}</div>
          <div className="stat-value">{orders.length}</div>
        </div>
      </section>

      {error ? <div className="notice">{error}</div> : null}

      <section className="nav-grid">
        <Link className="card nav-card" href="/plans">
          <p className="subtitle">{t(language, "common.plans")}</p>
          <h2 className="section-title">{t(language, "home.pickPlanTitle")}</h2>
          <p className="muted">{t(language, "home.pickPlanText")}</p>
        </Link>
        <Link className="card nav-card" href="/wallet">
          <p className="subtitle">{t(language, "common.wallet")}</p>
          <h2 className="section-title">{t(language, "home.walletTitle")}</h2>
          <p className="muted">{t(language, "home.walletText")}</p>
        </Link>
        <Link className="card nav-card" href="/jobs">
          <p className="subtitle">{t(language, "common.jobs")}</p>
          <h2 className="section-title">{t(language, "home.jobsTitle")}</h2>
          <p className="muted">{t(language, "home.jobsText")}</p>
        </Link>
        <Link className="card nav-card" href="/partnership">
          <p className="subtitle">{t(language, "partnership.eyebrow")}</p>
          <h2 className="section-title">{t(language, "home.partnershipTitle")}</h2>
          <p className="muted">{t(language, "home.partnershipText")}</p>
        </Link>
      </section>

      <section className="section-grid">
        <div className="card">
          <div className="section-header">
            <div>
              <p className="subtitle">{t(language, "home.profileSnapshot")}</p>
              <h2 className="section-title">{t(language, "home.accountDetails")}</h2>
            </div>
            <span className="pill">{t(language, "home.syncedWithBackend")}</span>
          </div>
          <div className="stack">
            <div className="detail-row">
              <span className="muted">{t(language, "home.name")}</span>
              <strong>
                {backendUser?.first_name ??
                  telegramUser?.first_name ??
                  t(language, "common.unknown")}
              </strong>
            </div>
            <div className="detail-row">
              <span className="muted">{t(language, "home.username")}</span>
              <strong>
                {backendUser?.username ??
                  telegramUser?.username ??
                  t(language, "common.notSet")}
              </strong>
            </div>
            <div className="detail-row">
              <span className="muted">{t(language, "common.language")}</span>
              <strong>{getLanguageLabel(language)}</strong>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="section-header">
            <div>
              <p className="subtitle">{t(language, "home.recentActivity")}</p>
              <h2 className="section-title">{t(language, "home.latestTransactions")}</h2>
            </div>
            <Link className="button ghost" href="/wallet">
              {t(language, "home.fullWallet")}
            </Link>
          </div>
          {history?.transactions.length ? (
            <div className="list">
              {history.transactions.map((transaction) => (
                <div className="list-item" key={transaction.id}>
                  <div className="list-main">
                    <div className="list-title">
                      {transaction.comment || transaction.transaction_type}
                    </div>
                    <div className="list-meta">
                      {formatDate(transaction.created_at, language)}
                    </div>
                  </div>
                  <div
                    className={
                      transaction.amount >= 0 ? "amount-positive" : "amount-negative"
                    }
                  >
                    {transaction.amount > 0 ? "+" : ""}
                    {transaction.amount}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">{t(language, "home.noBalanceActivity")}</div>
          )}
        </div>

        <div className="card">
          <div className="section-header">
            <div>
              <p className="subtitle">{t(language, "home.generations")}</p>
              <h2 className="section-title">{t(language, "home.latestJobs")}</h2>
            </div>
            <Link className="button ghost" href="/jobs">
              {t(language, "home.fullQueue")}
            </Link>
          </div>
          {jobs.length ? (
            <div className="list">
              {jobs.map((job) => (
                <div className="list-item" key={job.id}>
                  <div className="list-main">
                    <div className="list-title">
                      {getProviderLabel(language, job.provider)} ·{" "}
                      {getJobStatusLabel(language, job.status)}
                    </div>
                    <div className="list-meta">
                      #{job.id} · {formatDate(job.created_at, language)} ·{" "}
                      {job.credits_reserved} {t(language, "plans.credits").toLowerCase()}
                    </div>
                  </div>
                  <div>
                    {job.result_url ? (
                      <a
                        className="button ghost"
                        href={job.result_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {t(language, "common.openResult")}
                      </a>
                    ) : (
                      <div className="list-meta">
                        {isRunningStatus(job.status)
                          ? t(language, "home.jobInProgress")
                          : t(language, "home.jobNotReady")}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">{t(language, "home.noJobs")}</div>
          )}
        </div>

        <div className="card">
          <div className="section-header">
            <div>
              <p className="subtitle">{t(language, "home.orders")}</p>
              <h2 className="section-title">{t(language, "home.latestOrders")}</h2>
            </div>
            <Link className="button ghost" href="/plans">
              {t(language, "home.buyCredits")}
            </Link>
          </div>
          {orders.length ? (
            <div className="list">
              {orders.map((order) => (
                <div className="list-item" key={order.id}>
                  <div className="list-main">
                    <div className="list-title">
                      {order.plan_name || order.plan_code || t(language, "checkout.selectedPlan")}
                    </div>
                    <div className="list-meta">
                      {order.order_number} · {formatDate(order.created_at, language)}
                    </div>
                  </div>
                  <div>
                    <div>{formatCurrency(order.amount, order.currency, language)}</div>
                    <div className="list-meta">
                      {getOrderStatusLabel(language, order.status)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">{t(language, "home.noOrders")}</div>
          )}
        </div>
      </section>
    </main>
  );
}
