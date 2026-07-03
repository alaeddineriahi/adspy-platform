"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { adminApi } from "@/lib/admin";

interface Sub {
  user_id: string; plan: string; status: string; current_period_end: string | null;
  credit_bonus: number; is_comp: boolean; payment_ref: string | null;
}
interface Payment {
  payment_ref: string; user_id: string; plan: string; provider: string; status: string; created_at: string;
}

export default function AdminBillingPage() {
  const { getToken } = useAuth();
  const [subs, setSubs] = useState<Sub[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    adminApi
      .billing(getToken)
      .then((d) => {
        setSubs(d.subscriptions);
        setPayments(d.payments);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [getToken]);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }
  if (error) return <p className="p-8 text-sm text-red-600">{error}</p>;

  return (
    <div className="p-4 md:p-8 max-w-5xl mx-auto space-y-8">
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Active & recent subscriptions</h3>
        <div className="bg-white border border-[#e6e6e7] rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-400 border-b border-gray-100 bg-gray-50">
                <th className="py-2.5 px-4">User</th>
                <th className="py-2.5 px-4">Plan</th>
                <th className="py-2.5 px-4">Status</th>
                <th className="py-2.5 px-4">Renews / expires</th>
                <th className="py-2.5 px-4">Bonus</th>
                <th className="py-2.5 px-4">Source</th>
              </tr>
            </thead>
            <tbody>
              {subs.map((s) => (
                <tr key={s.user_id} className="border-b border-gray-50">
                  <td className="py-2 px-4">
                    <Link href={`/admin/users/${s.user_id}`} className="text-blue-600 hover:underline font-mono text-xs">
                      {s.user_id}
                    </Link>
                  </td>
                  <td className="py-2 px-4 font-medium text-gray-800">{s.plan}</td>
                  <td className="py-2 px-4">
                    <span className={s.status === "active" ? "text-emerald-600" : "text-gray-400"}>{s.status}</span>
                  </td>
                  <td className="py-2 px-4 text-gray-500">
                    {s.current_period_end ? new Date(s.current_period_end).toLocaleDateString() : "—"}
                  </td>
                  <td className="py-2 px-4 text-gray-500">{s.credit_bonus > 0 ? `+${s.credit_bonus}` : "—"}</td>
                  <td className="py-2 px-4 text-gray-500">{s.is_comp ? "comp" : "payment"}</td>
                </tr>
              ))}
              {subs.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-gray-400">No subscriptions yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Payment intents</h3>
        <div className="bg-white border border-[#e6e6e7] rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-400 border-b border-gray-100 bg-gray-50">
                <th className="py-2.5 px-4">Date</th>
                <th className="py-2.5 px-4">User</th>
                <th className="py-2.5 px-4">Plan</th>
                <th className="py-2.5 px-4">Provider</th>
                <th className="py-2.5 px-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {payments.map((p) => (
                <tr key={p.payment_ref} className="border-b border-gray-50">
                  <td className="py-2 px-4 text-gray-500">{new Date(p.created_at).toLocaleString()}</td>
                  <td className="py-2 px-4">
                    <Link href={`/admin/users/${p.user_id}`} className="text-blue-600 hover:underline font-mono text-xs">
                      {p.user_id}
                    </Link>
                  </td>
                  <td className="py-2 px-4 text-gray-800">{p.plan}</td>
                  <td className="py-2 px-4 text-gray-500">{p.provider}</td>
                  <td className="py-2 px-4">
                    <span className={p.status === "completed" ? "text-emerald-600" : "text-amber-600"}>{p.status}</span>
                  </td>
                </tr>
              ))}
              {payments.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-gray-400">No payments yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
