import "./globals.css";
import type { Metadata, Viewport } from "next";
import Script from "next/script";
import { Inter } from "next/font/google";
import { BottomNav } from "@/components/BottomNav";
import { ClientProviders } from "@/components/ClientProviders";

const inter = Inter({ subsets: ["latin", "cyrillic"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "HARF AI",
  description: "Создавай. Удивляй. Зарабатывай.",
};

// Lock the scale so focusing an input never zooms the mini app (iOS WebView
// auto-zooms on focus otherwise) and respect the device safe areas.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru" className={inter.variable} suppressHydrationWarning>
      <head>
        {/* КРИТИЧНО: загружаем до React, чтобы initData был доступен при монтировании */}
        <Script
          src="https://telegram.org/js/telegram-web-app.js"
          strategy="beforeInteractive"
        />
      </head>
      <body className="font-inter antialiased">
        <ClientProviders>
          {children}
          <BottomNav />
        </ClientProviders>
      </body>
    </html>
  );
}
