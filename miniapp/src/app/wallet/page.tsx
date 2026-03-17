"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getBalanceHistory, type BalanceHistoryResponse } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { t } from "@/lib/miniapp-i18n";
import { useMiniAppUser } from "@/lib/use-miniapp-user";

export default function WalletPage() {
  const { backendUser, telegramUser, language, loading: userLoading, error: userError } =
    useMiniAppUser();
  const [history, setHistory] = useState<BalanceHistoryResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      if (userLoading) {
        return;
      }

      if (!telegramUser?.id) {
        setError(t(language, "common.openFromTelegram"));
        return;
      }

      if (!backendUser?.telegram_user_id) {
        setError(userError ? t(language, "common.profileSyncFailed") : "");
        return;
      }

      try {
        setError("");
        const data = await getBalanceHistory(backendUser.telegram_user_id, 20);
        setHistory(data);
      } catch {
        setError(t(language, "common.failedLoadData"));
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
        <div className="eyebrow">{t(language, "wallet.eyebrow")}</div>
        <h1 className="title">{t(language, "wallet.title")}</h1>
        <p className="lead">{t(language, "wallet.lead")}</p>
        <div className="cta-row">
          <Link className="button" href="/plans">
            {t(language, "wallet.buyCredits")}
          </Link>
          <Link className="button secondary" href="/">
            {t(language, "wallet.back")}
          </Link>
        </div>
      </section>

      <section className="stats-grid">
        <div className="card">
          <div className="stat-label">{t(language, "wallet.availableCredits")}</div>
          <div className="stat-value">{history?.credits_balance ?? 0}</div>
        </div>
        <div className="card">
          <div className="stat-label">{t(language, "wallet.loggedOperations")}</div>
          <div className="stat-value">{history?.transactions.length ?? 0}</div>
        </div>
      </section>

      {error ? <div className="notice">{error}</div> : null}

      <section className="card">
        <div className="section-header">
          <div>
            <p className="subtitle">{t(language, "wallet.history")}</p>
            <h2 className="section-title">{t(language, "wallet.latestEvents")}</h2>
          </div>
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
                    {formatDate(transaction.created_at, language)} ·{" "}
                    {t(language, "wallet.afterOperation", {
                      balance: transaction.balance_after,
                    })}
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
          <div className="empty-state">{t(language, "wallet.noTransactions")}</div>
        )}
      </section>
    </main>
  );
}
