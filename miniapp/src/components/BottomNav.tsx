"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Copy, PlusCircle, CreditCard } from "lucide-react";

export function BottomNav() {
  const pathname = usePathname();

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-brand-900/80 backdrop-blur-xl border-t border-white/10 pb-[env(safe-area-inset-bottom,0px)]">
      <nav className="flex items-center justify-around h-16 max-w-md mx-auto px-4">
        
        <Link 
          href="/jobs" 
          className={`flex flex-col items-center justify-center w-16 h-full transition-colors ${pathname === '/jobs' ? 'text-brand-cyan' : 'text-white/40 hover:text-white/70'}`}
        >
          <Copy size={22} className="mb-1" />
          <span className="text-[10px] font-medium tracking-wide">Работы</span>
        </Link>

        {/* Floating Action Button for Create */}
        <Link 
          href="/generate" 
          className="relative -top-5 flex items-center justify-center w-14 h-14 bg-gradient-to-tr from-brand-primary to-brand-cyan rounded-full text-white shadow-[0_8px_24px_rgba(124,58,237,0.4)] hover:scale-105 active:scale-95 transition-all"
        >
          <PlusCircle size={28} />
        </Link>

        <Link 
          href="/wallet" 
          className={`flex flex-col items-center justify-center w-16 h-full transition-colors ${pathname === '/wallet' || pathname === '/plans' ? 'text-brand-cyan' : 'text-white/40 hover:text-white/70'}`}
        >
          <CreditCard size={22} className="mb-1" />
          <span className="text-[10px] font-medium tracking-wide">Баланс</span>
        </Link>
        
      </nav>
    </div>
  );
}
