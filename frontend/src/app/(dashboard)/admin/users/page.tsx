"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { Loader2, Search, ShieldAlert } from "lucide-react";
import { adminApi, AdminUser } from "@/lib/admin";
import { errMessage } from "@/lib/api";

const PLAN_COLOR: Record<string, string> = {
  free: "bg-gray-100 text-gray-600",
  pro: "bg-blue-100 text-blue-700",
  agency: "bg-purple-100 text-purple-700",
};

export default function AdminUsersPage() {
  const { getToken } = useAuth();
  const [q, setQ] = useState("");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(
    async (query: string) => {
      setLoading(true);
      setError("");
      try {
        const data = await adminApi.users(getToken, query);
        setUsers(data.results);
        setTotal(data.total);
      } catch (e) {
        setError(errMessage(e));
      } finally {
        setLoading(false);
      }
    },
    [getToken]
  );

  useEffect(() => {
    load("");
  }, [load]);

  return (
    <div className="p-4 md:p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Users {total > 0 && <span className="text-gray-400 font-normal">({total})</span>}</h2>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          load(q);
        }}
        className="relative mb-5 max-w-sm"
      >
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by email…"
          className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm"
        />
      </form>

      {error && (
        <p className="text-sm text-red-600 mb-4 flex items-center gap-1.5">
          <ShieldAlert className="w-4 h-4" /> {error}
        </p>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : (
        <div className="bg-white border border-[#e6e6e7] rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-gray-400 border-b border-gray-100 bg-gray-50">
                <th className="py-2.5 px-4">User</th>
                <th className="py-2.5 px-4">Plan</th>
                <th className="py-2.5 px-4">AI credits</th>
                <th className="py-2.5 px-4">Saved ads</th>
                <th className="py-2.5 px-4">Joined</th>
                <th className="py-2.5 px-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="py-2.5 px-4">
                    <Link href={`/admin/users/${u.id}`} className="font-medium text-gray-900 hover:underline">
                      {u.email || u.id}
                    </Link>
                    {u.role === "admin" && (
                      <span className="ml-2 text-[10px] font-semibold bg-gray-900 text-white px-1.5 py-0.5 rounded">
                        ADMIN
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 px-4">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded ${PLAN_COLOR[u.plan] || ""}`}>
                      {u.plan}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-gray-600">
                    {u.credits_used} / {u.credits_limit}
                  </td>
                  <td className="py-2.5 px-4 text-gray-600">{u.saved_ads}</td>
                  <td className="py-2.5 px-4 text-gray-500">
                    {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                  </td>
                  <td className="py-2.5 px-4">
                    {u.banned_in_app ? (
                      <span className="text-xs font-medium text-red-600">Suspended</span>
                    ) : (
                      <span className="text-xs text-emerald-600">Active</span>
                    )}
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-10 text-center text-gray-400">
                    No users found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
