"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { UserCircle, Package, Users, ClipboardList } from "lucide-react";

export function BottomNav() {
  const pathname = usePathname();

  const items = [
    { href: "/profile",     icon: UserCircle,    labelRu: "Профиль",   labelUz: "Profil"    },
    { href: "/plans",       icon: Package,       labelRu: "Услуги",    labelUz: "Xizmatlar" },
    { href: "/partnership", icon: Users,         labelRu: "Партнёры",  labelUz: "Hamkorlar" },
    { href: "/jobs",        icon: ClipboardList, labelRu: "Работы",    labelUz: "Ishlar"    },
  ] as const;

  // Read language from localStorage (set by profile page switcher)
  const lang = typeof window !== "undefined"
    ? (localStorage.getItem("miniapp_language") ?? "ru")
    : "ru";

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-brand-900/80 backdrop-blur-xl border-t border-white/10 pb-[env(safe-area-inset-bottom,0px)]">
      <nav className="flex items-center justify-around h-16 max-w-md mx-auto px-2">
        {items.map(({ href, icon: Icon, labelRu, labelUz }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex flex-col items-center justify-center w-16 h-full transition-colors ${
                active ? "text-brand-cyan" : "text-white/40 hover:text-white/70"
              }`}
            >
              <Icon size={22} className="mb-1" />
              <span className="text-[10px] font-medium tracking-wide">
                {lang === "uz" ? labelUz : labelRu}
              </span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
