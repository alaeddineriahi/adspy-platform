"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Check, Loader2, CreditCard, Sparkles } from "lucide-react";
import { authFetch, apiError, errMessage, API_URL } from "@/lib/api";
import { useUsage } from "@/components/UsageProvider";

interface Plan {
  id: string;
  name: string;
  price_tnd: number;
  searches_per_day: number;
  ai_credits_per_month: number;
  saved_ads: number;
  brand_spy: boolean;
  brand_spy_limit?: number;
}

const TAGLINE: Record<string, string> = {
  free: "Kick the tires",
  pro: "For solo media buyers & store owners",
  agency: "For agencies running many clients",
};

function features(p: Plan): string[] {
  return [
    p.searches_per_day === -1 ? "Unlimited ad searches" : `${p.searches_per_day} searches / day`,
    `${p.ai_credits_per_month} AI credits / month`,
    "AI media-buyer co-pilot",
    p.saved_ads === -1 ? "Unlimited saved ads" : `${p.saved_ads} saved ads`,
    p.brand_spy
      ? `Brand Spy — track ${p.brand_spy_limit ?? "∞"} brands`
      : "Brand Spy locked",
  ];
}

export default function PricingPage() {
  const { getToken } = useAuth();
  const { usage, refresh } = useUsage();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [paying, setPaying] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API_URL}/api/payments/plans`)
      .then((r) => r.json())
      .then((d) => setPlans(d.plans || []))
      .catch(() => setError("Couldn't load plans — is the backend running?"))
      .finally(() => setLoading(false));
    refresh();
  }, [refresh]);

  const subscribe = async (planId: string) => {
    setPaying(planId);
    setError("");
    try {
      const res = await authFetch(getToken, "/api/payments/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan: planId, payment_method: "konnect" }),
      });
      if (!res.ok) throw new Error(await apiError(res));
      const data = await res.json();
      window.location.href = data.pay_url; // off to Konnect checkout
    } catch (err) {
      setError(errMessage(err, "Couldn't start checkout"));
      setPaying(null);
    }
  };

  const currentPlan = usage?.plan ?? "free";

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="text-center mb-10">
        <h2 className="text-3xl font-bold text-gray-900 flex items-center justify-center gap-2">
          <CreditCard className="w-7 h-7" /> Plans & pricing
        </h2>
        <p className="text-sm text-gray-500 mt-2">
          Search and Brand Spy stay unlimited on paid plans — AI credits are the only meter.
          Pay in TND with your local card or e-DINAR.
        </p>
        {usage && (
          <p className="text-xs text-gray-400 mt-2">
            You&apos;re on <span className="font-semibold text-gray-600 capitalize">{currentPlan}</span>{" "}
            · {usage.credits_remaining} of {usage.credits_limit} AI credits left this month
          </p>
        )}
      </div>

      {error && (
        <div className="mb-6 max-w-xl mx-auto text-center text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {plans.map((p) => {
            const highlight = p.id === "pro";
            const isCurrent = p.id === currentPlan;
            return (
              <div
                key={p.id}
                className={`relative bg-white rounded-2xl p-6 flex flex-col border ${
                  highlight ? "border-blue-600 shadow-lg shadow-blue-100" : "border-gray-200"
                }`}
              >
                {highlight && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 text-[11px] font-semibold bg-blue-600 text-white px-3 py-1 rounded-full flex items-center gap-1">
                    <Sparkles className="w-3 h-3" /> Most popular
                  </span>
                )}
                <h3 className="text-lg font-bold text-gray-900">{p.name}</h3>
                <p className="text-xs text-gray-500 mb-4">{TAGLINE[p.id]}</p>
                <div className="mb-5">
                  <span className="text-4xl font-extrabold text-gray-900">{p.price_tnd}</span>
                  <span className="text-sm text-gray-500 ml-1">TND / month</span>
                </div>
                <ul className="space-y-2.5 flex-1 mb-6">
                  {features(p).map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-gray-700">
                      <Check
                        className={`w-4 h-4 mt-0.5 shrink-0 ${
                          f.endsWith("locked") ? "text-gray-300" : "text-emerald-600"
                        }`}
                      />
                      <span className={f.endsWith("locked") ? "text-gray-400" : ""}>{f}</span>
                    </li>
                  ))}
                </ul>
                {p.id === "free" ? (
                  <button
                    disabled
                    className="w-full py-2.5 rounded-xl text-sm font-medium border border-gray-200 text-gray-400"
                  >
                    {isCurrent ? "Your current plan" : "Included"}
                  </button>
                ) : isCurrent ? (
                  <button
                    disabled
                    className="w-full py-2.5 rounded-xl text-sm font-medium bg-emerald-50 text-emerald-700 border border-emerald-200"
                  >
                    ✓ Your current plan
                  </button>
                ) : (
                  <button
                    onClick={() => subscribe(p.id)}
                    disabled={paying !== null}
                    className={`w-full py-2.5 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 disabled:opacity-60 ${
                      highlight
                        ? "bg-blue-600 text-white hover:bg-blue-500"
                        : "bg-gray-900 text-white hover:bg-gray-800"
                    }`}
                  >
                    {paying === p.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      `Upgrade to ${p.name}`
                    )}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      <p className="text-center text-xs text-gray-400 mt-8">
        Payments processed by Konnect (bank card, e-DINAR, wallet). Subscriptions renew manually —
        no surprise charges.
      </p>
    </div>
  );
}
