import type { Metadata } from 'next'
import Script from 'next/script'
import './globals.css'
import { BottomNav } from "@/components/BottomNav";

export const metadata: Metadata = {
  title: 'HARF AI',
  description: 'Создавай. Удивляй. Зарабатывай.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ru">
      <head>
        <Script
          src="https://telegram.org/js/telegram-web-app.js"
          strategy="beforeInteractive"
        />
      </head>
      <body>
        {children}
        <BottomNav />
      </body>
    </html>
  )
}
