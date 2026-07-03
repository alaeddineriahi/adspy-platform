"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import {
  ArrowLeft, Loader2, ShieldAlert, RotateCcw, Ban, ShieldCheck,
  Copy, CheckCheck,
} from "lucide-react";
import { adminApi } from "@/lib/admin";
import { errMessage } from "@/lib/api";

interface Detail {
  user: { id: string; email: string; name: string | null; role: string; created_at: number };
  subscription: { plan: string; status: string; current_period_end: string | null; credit_bonus: number; is_comp: boolean };
  usage: { credits_used: number; credits_limit: number };
  saved_ads: number;
  banned: boolean;
  ban_reason: string | null;
  payments: { payment_ref: string; plan: string; provider: string; status: string; created_at: string }[];
  audit_log: { action: string; detail: string | null; admin_user_id: string; created_at: string }[];
}

export default function AdminUserDetailPage() {
  const { id } = useParams();
  const { getToken, userId: myId } = useAuth();
  const [data, setData] = useState<Detail | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [plan, setPlan] = useState("pro");
  const [days, setDays] = useState(31);
  const [bonus, setBonus] = useState(0);
  const [banReason, setBanReason] = useState("");
  const [ticket, setTicket] = useState("");
  const [copied, setCopied] = useState(false);

  const load = useCallback(async () => {
    try {
      const d = await adminApi.userDetail(getToken, id as string);
      setData(d);
      setPlan(d.subscription.plan === "free" ? "pro" : d.subscription.plan);
    } catch (e) {
      setError(errMessage(e));
    }
  }, [getToken, id]);

  useEffect(() => {
    load();
  }, [load]);

  const run = async (label: string, fn: () => Promise<unknown>) => {
    setBusy(label);
    setError("");
    try {
      await fn();
      await load();
    } catch (e) {
      setError(errMessage(e));
    } finally {
      setBusy("");
    }
  };

  if (error && !data) return <p className="p-8 text-sm text-red-600">{error}</p>;
  if (!data) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  const isSelf = id === myId;

  return (
    <div className="p-4 md:p-8 max-w-4xl mx-auto">
      <Link href="/admin/users" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-900 mb-4">
        <ArrowLeft className="w-4 h-4" /> Users
      </Link>

      <div className="flex items-center justify-between mb-1">
        <h2 className="text-xl font-black tracking-tight text-[#1d1d1f]">{data.user.email || data.user.id}</h2>
        {data.user.role === "admin" && (
          <span className="text-xs font-semibold bg-gray-900 text-white px-2 py-1 rounded">ADMIN</span>
        )}
      </div>
      <p className="text-xs text-gray-400 mb-6 font-mono">{data.user.id}</p>

      {error && (
        <p className="text-sm text-red-600 mb-4 flex items-center gap-1.5">
          <ShieldAlert className="w-4 h-4" /> {error}
        </p>
      )}

      {data.banned && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-sm text-red-800">
          Suspended{data.ban_reason ? ` — ${data.ban_reason}` : ""}.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Plan & credits */}
        <div className="bg-white border border-[#e6e6e7] rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Plan & credits</h3>
          <p className="text-sm text-gray-600 mb-1">
            Current: <span className="font-medium text-gray-900">{data.subscription.plan}</span>
            {data.subscription.is_comp && <span className="text-xs text-amber-600 ml-1">(comp)</span>}
          </p>
          <p className="text-sm text-gray-600 mb-4">
            Credits: {data.usage.credits_used} / {data.usage.credits_limit}
            {data.subscription.credit_bonus > 0 && (
              <span className="text-xs text-gray-400"> (+{data.subscription.credit_bonus} bonus)</span>
            )}
          </p>

          <div className="grid grid-cols-3 gap-2 mb-3">
            <select value={plan} onChange={(e) => setPlan(e.target.value)} className="col-span-1 border border-gray-300 rounded-lg text-xs px-2 py-2">
              <option value="free">free</option>
              <option value="pro">pro</option>
              <option value="agency">agency</option>
            </select>
            <input
              type="number"
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              placeholder="days"
              className="col-span-1 border border-gray-300 rounded-lg text-xs px-2 py-2"
            />
            <input
              type="number"
              value={bonus}
              onChange={(e) => setBonus(Number(e.target.value))}
              placeholder="bonus credits"
              className="col-span-1 border border-gray-300 rounded-lg text-xs px-2 py-2"
            />
          </div>
          <button
            disabled={busy !== ""}
            onClick={() => run("plan", () => adminApi.setPlan(getToken, id as string, plan, days, bonus))}
            className="w-full text-sm font-medium bg-gray-900 text-white rounded-lg py-2 hover:bg-gray-800 disabled:opacity-50"
          >
            {busy === "plan" ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : "Apply override"}
          </button>
          <button
            disabled={busy !== ""}
            onClick={() => run("reset", () => adminApi.resetCredits(getToken, id as string))}
            className="w-full mt-2 flex items-center justify-center gap-1.5 text-sm text-gray-600 border border-gray-200 rounded-lg py-2 hover:bg-gray-50 disabled:opacity-50"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Reset this month&apos;s usage
          </button>
        </div>

        {/* Account controls */}
        <div className="bg-white border border-[#e6e6e7] rounded-2xl p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Account</h3>

          <div className="mb-4">
            <p className="text-xs text-gray-500 mb-1.5">Role</p>
            <button
              disabled={busy !== "" || isSelf}
              onClick={() =>
                run("role", () => adminApi.setRole(getToken, id as string, data.user.role === "admin" ? "member" : "admin"))
              }
              className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 hover:bg-gray-50 disabled:opacity-50"
              title={isSelf ? "You can't change your own role" : undefined}
            >
              {data.user.role === "admin" ? "Demote to member" : "Promote to admin"}
            </button>
          </div>

          <div className="mb-4">
            <p className="text-xs text-gray-500 mb-1.5">Suspend</p>
            {!data.banned ? (
              <div className="flex gap-2">
                <input
                  value={banReason}
                  onChange={(e) => setBanReason(e.target.value)}
                  placeholder="reason (optional)"
                  className="flex-1 border border-gray-300 rounded-lg text-xs px-2 py-2"
                />
                <button
                  disabled={busy !== "" || isSelf}
                  onClick={() => run("ban", () => adminApi.setBan(getToken, id as string, true, banReason))}
                  className="flex items-center gap-1.5 text-sm text-red-600 border border-red-200 rounded-lg px-3 py-1.5 hover:bg-red-50 disabled:opacity-50"
                >
                  <Ban className="w-3.5 h-3.5" /> Suspend
                </button>
              </div>
            ) : (
              <button
                disabled={busy !== ""}
                onClick={() => run("unban", () => adminApi.setBan(getToken, id as string, false))}
                className="flex items-center gap-1.5 text-sm text-emerald-700 border border-emerald-200 rounded-lg px-3 py-1.5 hover:bg-emerald-50 disabled:opacity-50"
              >
                <ShieldCheck className="w-3.5 h-3.5" /> Unsuspend
              </button>
            )}
          </div>

          <div>
            <p className="text-xs text-gray-500 mb-1.5">Support — view as this user</p>
            <button
              disabled={busy !== "" || isSelf}
              onClick={() =>
                run("imp", async () => {
                  const { ticket: t } = await adminApi.impersonate(getToken, id as string);
                  setTicket(t);
                })
              }
              className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 hover:bg-gray-50 disabled:opacity-50"
            >
              Generate impersonation link
            </button>
            {ticket && (
              <div className="mt-2 bg-amber-50 border border-amber-200 rounded-lg p-3">
                <p className="text-xs text-amber-800 mb-2">
                  Open this in a <strong>private/incognito window</strong> — not this tab, or you&apos;ll
                  sign yourself out. Expires in 5 minutes.
                </p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-[10px] bg-white border border-amber-200 rounded px-2 py-1.5 truncate">
                    {`${window.location.origin}/impersonate?ticket=${ticket}`}
                  </code>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(`${window.location.origin}/impersonate?ticket=${ticket}`);
                      setCopied(true);
                      setTimeout(() => setCopied(false), 1500);
                    }}
                    className="shrink-0 p-1.5 border border-amber-300 rounded hover:bg-amber-100"
                  >
                    {copied ? <CheckCheck className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-amber-700" />}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Payments */}
      <div className="mt-6 bg-white border border-[#e6e6e7] rounded-2xl p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Payment history</h3>
        {data.payments.length === 0 ? (
          <p className="text-sm text-gray-400">No payments yet.</p>
        ) : (
          <table className="w-full text-sm">
            <tbody>
              {data.payments.map((p) => (
                <tr key={p.payment_ref} className="border-b border-gray-50 last:border-0">
                  <td className="py-1.5 text-gray-600">{new Date(p.created_at).toLocaleString()}</td>
                  <td className="py-1.5 text-gray-900 font-medium">{p.plan}</td>
                  <td className="py-1.5 text-gray-500">{p.provider}</td>
                  <td className="py-1.5">
                    <span className={p.status === "completed" ? "text-emerald-600" : "text-amber-600"}>{p.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Audit trail for this user */}
      <div className="mt-6 bg-white border border-[#e6e6e7] rounded-2xl p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Admin actions on this account</h3>
        {data.audit_log.length === 0 ? (
          <p className="text-sm text-gray-400">No admin actions yet.</p>
        ) : (
          <ul className="space-y-1.5">
            {data.audit_log.map((a, i) => (
              <li key={i} className="text-sm text-gray-600 flex items-center gap-2">
                <span className="text-xs text-gray-400 shrink-0">{new Date(a.created_at).toLocaleString()}</span>
                <span className="font-medium text-gray-800">{a.action}</span>
                {a.detail && <span className="text-gray-500">— {a.detail}</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
