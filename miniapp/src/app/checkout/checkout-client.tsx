"use client";

import Link from "next/link";
import { useState } from "react";
import { confirmPayment, type PaymentResponse } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { getPaymentStatusLabel, t } from "@/lib/miniapp-i18n";
import { useMiniAppUser } from "@/lib/use-miniapp-user";

type CheckoutClientProps = {
  planName?: string;
  amount?: string;
  currency?: string;
  credits?: string;
  orderId?: string;
  orderNumber?: string;
  paymentId?: string;
};

export default function CheckoutClient({
  planName,
  amount,
  currency,
  credits,
  orderId,
  orderNumber,
  paymentId,
}: CheckoutClientProps) {
  const { language } = useMiniAppUser();
  const [confirmation, setConfirmation] = useState<PaymentResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const parsedAmount = Number(amount || "0");
  const parsedPaymentId = Number(paymentId || "0");

  async function handleConfirm() {
    if (!parsedPaymentId) {
      setError(t(language, "checkout.paymentIdMissing"));
      return;
    }

    try {
      setLoading(true);
      setError("");
      const result = await confirmPayment(parsedPaymentId);
      setConfirmation(result);
    } catch {
      setError(t(language, "checkout.failedConfirm"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <section className="hero">
        <div className="eyebrow">{t(language, "checkout.eyebrow")}</div>
        <h1 className="title">{t(language, "checkout.title")}</h1>
        <p className="lead">{t(language, "checkout.lead")}</p>
        <div className="badge-row">
          <span className="badge hot">{t(language, "checkout.testFlow")}</span>
          {confirmation?.status === "paid" ? (
            <span className="badge success">{t(language, "checkout.paymentConfirmed")}</span>
          ) : null}
        </div>
      </section>

      {error ? <div className="notice">{error}</div> : null}

      <section className="section-grid">
        <div className="card">
          <p className="subtitle">{t(language, "checkout.orderSummary")}</p>
          <h2 className="section-title">
            {planName || t(language, "checkout.selectedPlan")}
          </h2>
          <div className="stack">
            <div className="detail-row">
              <span className="muted">{t(language, "checkout.amount")}</span>
              <strong>{formatCurrency(parsedAmount, currency || "USD", language)}</strong>
            </div>
            <div className="detail-row">
              <span className="muted">{t(language, "checkout.credits")}</span>
              <strong>{credits || "0"}</strong>
            </div>
            <div className="detail-row">
              <span className="muted">{t(language, "checkout.order")}</span>
              <strong>{orderNumber || orderId || t(language, "common.missing")}</strong>
            </div>
            <div className="detail-row">
              <span className="muted">{t(language, "checkout.payment")}</span>
              <strong>{parsedPaymentId || t(language, "common.missing")}</strong>
            </div>
          </div>
        </div>

        <div className="card">
          <p className="subtitle">{t(language, "checkout.providers")}</p>
          <h2 className="section-title">{t(language, "checkout.providersReady")}</h2>
          <div className="timeline">
            <div className="timeline-card">{t(language, "checkout.cardsFlow")}</div>
            <div className="timeline-card">{t(language, "checkout.paymeFlow")}</div>
            <div className="timeline-card">{t(language, "checkout.clickFlow")}</div>
          </div>
        </div>
      </section>

      <section className="card">
        <div className="section-header">
          <div>
            <p className="subtitle">{t(language, "checkout.action")}</p>
            <h2 className="section-title">{t(language, "checkout.confirmPayment")}</h2>
          </div>
        </div>
        <div className="stack">
          <div className="notice">{t(language, "checkout.manualNotice")}</div>
          <button
            className="button full"
            onClick={handleConfirm}
            disabled={loading || !parsedPaymentId || confirmation?.status === "paid"}
          >
            {confirmation?.status === "paid"
              ? t(language, "checkout.alreadyConfirmed")
              : loading
                ? t(language, "checkout.confirming")
                : t(language, "checkout.confirmAndCredit")}
          </button>
          <div className="cta-row">
            <Link className="button secondary" href="/wallet">
              {t(language, "common.wallet")}
            </Link>
            <Link className="button ghost" href="/plans">
              {t(language, "common.plans")}
            </Link>
          </div>
        </div>
      </section>

      {confirmation ? (
        <section className="card">
          <div className="section-header">
            <div>
              <p className="subtitle">{t(language, "checkout.confirmationResult")}</p>
              <h2 className="section-title">{t(language, "checkout.creditsAdded")}</h2>
            </div>
            <span className="badge success">
              {getPaymentStatusLabel(language, confirmation.status)}
            </span>
          </div>
          <div className="stack">
            <div className="detail-row">
              <span className="muted">{t(language, "checkout.selectedPlan")}</span>
              <strong>
                {confirmation.plan_name ||
                  confirmation.plan_code ||
                  planName ||
                  t(language, "checkout.selectedPlan")}
              </strong>
            </div>
            <div className="detail-row">
              <span className="muted">{t(language, "checkout.addedCredits")}</span>
              <strong>{confirmation.credited_amount ?? credits ?? 0}</strong>
            </div>
            <div className="detail-row">
              <span className="muted">{t(language, "checkout.currentBalance")}</span>
              <strong>{confirmation.current_balance ?? 0}</strong>
            </div>
          </div>
        </section>
      ) : null}
    </main>
  );
}
