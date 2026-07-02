"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useSignIn } from "@clerk/nextjs";
import { Loader2, ShieldAlert } from "lucide-react";

/**
 * Redeems a Clerk impersonation ticket minted by an admin (POST
 * /api/admin/users/{id}/impersonate). Public route (see middleware.ts) —
 * it must be reachable with NO existing Clerk session, which is exactly the
 * state a fresh private/incognito window is in.
 *
 * IMPORTANT: redeeming replaces whatever Clerk session is active in this
 * browser context. Always open this link in a private/incognito window,
 * never in the admin's own tab — otherwise it signs the admin out of their
 * own session and into the target user's.
 */
function Redeemer() {
  const params = useSearchParams();
  const router = useRouter();
  const { signIn, setActive, isLoaded } = useSignIn();
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isLoaded) return;
    const ticket = params.get("ticket");
    if (!ticket) {
      setError("No ticket in the URL.");
      return;
    }
    signIn
      .create({ strategy: "ticket", ticket })
      .then((res) => {
        if (res.status === "complete" && res.createdSessionId) {
          return setActive({ session: res.createdSessionId }).then(() => router.replace("/search"));
        }
        setError("Ticket could not be completed — it may have expired (5 min lifetime).");
      })
      .catch((e: unknown) => {
        const clerkMsg = (e as { errors?: { message?: string }[] })?.errors?.[0]?.message;
        const plainMsg = e instanceof Error ? e.message : "";
        setError(clerkMsg || plainMsg || "Redeem failed");
      });
  }, [isLoaded, params, signIn, setActive, router]);

  return (
    <div className="flex flex-col items-center justify-center h-screen text-center px-8">
      {error ? (
        <>
          <ShieldAlert className="w-10 h-10 text-red-400 mb-3" />
          <p className="text-sm text-red-600 max-w-sm">{error}</p>
        </>
      ) : (
        <>
          <Loader2 className="w-8 h-8 animate-spin text-gray-400 mb-3" />
          <p className="text-sm text-gray-500">Signing in as the user…</p>
        </>
      )}
    </div>
  );
}

export default function ImpersonateRedeemPage() {
  // useSearchParams() must sit under a Suspense boundary or `next build`
  // fails the static prerender of this page.
  return (
    <Suspense fallback={null}>
      <Redeemer />
    </Suspense>
  );
}
