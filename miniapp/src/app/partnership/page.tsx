"use client";

import Link from "next/link";
import { t } from "@/lib/miniapp-i18n";
import { useMiniAppUser } from "@/lib/use-miniapp-user";

export default function PartnershipPage() {
  const { language } = useMiniAppUser();

  return (
    <main className="page">
      <section className="hero">
        <div className="eyebrow">{t(language, "partnership.eyebrow")}</div>
        <h1 className="title">{t(language, "partnership.title")}</h1>
        <p className="lead">{t(language, "partnership.lead")}</p>
        <div className="cta-row">
          <Link className="button" href="/plans">
            {t(language, "partnership.viewPlans")}
          </Link>
          <Link className="button secondary" href="/">
            {t(language, "partnership.dashboard")}
          </Link>
        </div>
      </section>

      <section className="section-grid">
        <div className="card">
          <p className="subtitle">{t(language, "partnership.referralLink")}</p>
          <h2 className="section-title">{t(language, "partnership.reserved")}</h2>
          <div className="empty-state">{t(language, "partnership.empty")}</div>
        </div>
        <div className="card">
          <p className="subtitle">{t(language, "partnership.partnerModel")}</p>
          <h2 className="section-title">{t(language, "partnership.rollout")}</h2>
          <div className="timeline">
            <div className="timeline-card">{t(language, "partnership.stepOne")}</div>
            <div className="timeline-card">{t(language, "partnership.stepTwo")}</div>
            <div className="timeline-card">{t(language, "partnership.stepThree")}</div>
          </div>
        </div>
      </section>
    </main>
  );
}
