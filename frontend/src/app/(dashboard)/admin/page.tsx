"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Loader2, DollarSign, Users, Sparkles, Database } from "lucide-react";
import { adminApi, Overview } from "@/lib/admin";

function Card({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5">
      <div className="flex items-center gap-2 text-xs font-medium text-gray-500 mb-2">
        <Icon className="w-4 h-4" /> {label}
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

export default function AdminOverviewPage() {
  const { getToken } = useAuth();
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    adminApi
      .overview(getToken)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [getToken]);

  if (error) return <p className="p-8 text-sm text-red-600">{error}</p>;
  if (!data) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  const { revenue, usage, catalog } = data;

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card
          icon={DollarSign}
          label="MRR"
          value={`${revenue.mrr_tnd} TND`}
          sub={`${revenue.paid_subscriptions} paid · ${revenue.comp_subscriptions} comp`}
        />
        <Card
          icon={Users}
          label="Plan mix"
          value={`${revenue.plan_breakdown.pro ?? 0} Pro / ${revenue.plan_breakdown.agency ?? 0} Agency`}
          sub={`${revenue.plan_breakdown.free ?? 0} on Free`}
        />
        <Card
          icon={Sparkles}
          label="AI credits used"
          value={usage.ai_credits_used_this_month}
          sub="this calendar month, all users"
        />
        <Card
          icon={Database}
          label="Catalog"
          value={catalog.total_ads}
          sub={`${catalog.active_ads} active · ${catalog.stale_ads} stale`}
        />
      </div>

      {revenue.pending_payments > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
          {revenue.pending_payments} payment{revenue.pending_payments === 1 ? "" : "s"} pending
          verification — check Billing.
        </div>
      )}

      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Catalog by country</h3>
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Object.entries(catalog.per_country)
              .sort((a, b) => b[1] - a[1])
              .map(([country, count]) => (
                <div key={country} className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2">
                  <span className="text-sm font-medium text-gray-700">{country}</span>
                  <span className="text-sm text-gray-500">{count}</span>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}
