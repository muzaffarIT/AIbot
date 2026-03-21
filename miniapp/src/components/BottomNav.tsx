"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Clock, CreditCard, Users, UserCircle } from "lucide-react";

export function BottomNav() {
  const pathname = usePathname();

  const items = [
    { href: "/jobs",        icon: Clock,        label: "Работы"   },
    { href: "/wallet",      icon: CreditCard,   label: "Баланс",  extraPaths: ["/plans"] },
    { href: "/partnership", icon: Users,         label: "Партнёры" },
    { href: "/profile",     icon: UserCircle,    label: "Профиль"  },
  ] as const;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-brand-900/80 backdrop-blur-xl border-t border-white/10 pb-[env(safe-area-inset-bottom,0px)]">
      <nav className="flex items-center justify-around h-16 max-w-md mx-auto px-2">
        {items.map(({ href, icon: Icon, label, ...rest }) => {
          const extraPaths = (rest as any).extraPaths as string[] | undefined;
          const active = pathname === href || extraPaths?.includes(pathname);
          return (
            <Link
              key={href}
              href={href}
              className={`flex flex-col items-center justify-center w-16 h-full transition-colors ${
                active ? "text-brand-cyan" : "text-white/40 hover:text-white/70"
              }`}
            >
              <Icon size={22} className="mb-1" />
              <span className="text-[10px] font-medium tracking-wide">{label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
