"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { adminApi } from "@/lib/admin";

interface Entry {
  admin_user_id: string; action: string; target_user_id: string | null; detail: string | null; created_at: string;
}

const ACTION_COLOR: Record<string, string> = {
  ban: "bg-red-100 text-red-700",
  unban: "bg-emerald-100 text-emerald-700",
  plan_override: "bg-blue-100 text-blue-700",
  credits_reset: "bg-amber-100 text-amber-700",
  role_change: "bg-purple-100 text-purple-700",
  impersonate: "bg-gray-200 text-gray-700",
  ad_delete: "bg-red-100 text-red-700",
};

export default function AdminAuditPage() {
  const { getToken } = useAuth();
  const [entries, setEntries] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    adminApi
      .audit(getToken)
      .then((d) => setEntries(d.results))
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
    <div className="p-8 max-w-4xl">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        Admin action log ({entries.length})
      </h3>
      <div className="bg-white border border-gray-200 rounded-xl divide-y divide-gray-50">
        {entries.map((e, i) => (
          <div key={i} className="flex items-start gap-3 px-4 py-3">
            <span className={`text-[10px] font-semibold px-2 py-1 rounded shrink-0 ${ACTION_COLOR[e.action] || "bg-gray-100 text-gray-600"}`}>
              {e.action}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-700">
                <span className="font-mono text-xs text-gray-500">{e.admin_user_id}</span>
                {e.target_user_id && (
                  <>
                    {" → "}
                    <Link href={`/admin/users/${e.target_user_id}`} className="font-mono text-xs text-blue-600 hover:underline">
                      {e.target_user_id}
                    </Link>
                  </>
                )}
              </p>
              {e.detail && <p className="text-xs text-gray-500 mt-0.5">{e.detail}</p>}
            </div>
            <span className="text-xs text-gray-400 shrink-0">{new Date(e.created_at).toLocaleString()}</span>
          </div>
        ))}
        {entries.length === 0 && (
          <p className="text-sm text-gray-400 text-center py-10">No admin actions logged yet.</p>
        )}
      </div>
    </div>
  );
}
