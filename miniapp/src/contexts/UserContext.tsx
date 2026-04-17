"use client";

import { createContext, useContext, type ReactNode } from "react";
import { useTelegramAuth, type TgUser } from "@/hooks/useTelegramAuth";
import type { BackendUser } from "@/lib/api";

type UserContextType = {
  tgUser: TgUser | null;
  userData: BackendUser | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

const UserContext = createContext<UserContextType | null>(null);

export function UserProvider({ children }: { children: ReactNode }) {
  const auth = useTelegramAuth();
  return <UserContext.Provider value={auth}>{children}</UserContext.Provider>;
}

export function useUserContext(): UserContextType {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useUserContext must be inside UserProvider");
  return ctx;
}
