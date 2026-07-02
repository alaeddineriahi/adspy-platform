"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useAuth } from "@clerk/nextjs";
import { authFetch } from "@/lib/api";

interface AdminCtx {
  isAdmin: boolean;
  checked: boolean;
}

const Ctx = createContext<AdminCtx>({ isAdmin: false, checked: false });

export function useIsAdmin(): AdminCtx {
  return useContext(Ctx);
}

/** Checks /api/admin/me once per session; cheap 403 for non-admins, no UI flash for admins. */
export function AdminProvider({ children }: { children: ReactNode }) {
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const [isAdmin, setIsAdmin] = useState(false);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      setIsAdmin(false);
      setChecked(true);
      return;
    }
    authFetch(getToken, "/api/admin/me")
      .then((res) => setIsAdmin(res.ok))
      .catch(() => setIsAdmin(false))
      .finally(() => setChecked(true));
  }, [isLoaded, isSignedIn, getToken]);

  return <Ctx.Provider value={{ isAdmin, checked }}>{children}</Ctx.Provider>;
}
