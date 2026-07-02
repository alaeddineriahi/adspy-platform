import { authFetch, apiError } from "@/lib/api";

type GetToken = () => Promise<string | null>;

async function get(getToken: GetToken, path: string) {
  const res = await authFetch(getToken, path);
  if (!res.ok) throw new Error(await apiError(res));
  return res.json();
}

async function send(getToken: GetToken, path: string, method: string, body?: unknown) {
  const res = await authFetch(getToken, path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(await apiError(res));
  return res.json();
}

export interface Overview {
  revenue: {
    mrr_tnd: number;
    paid_subscriptions: number;
    comp_subscriptions: number;
    plan_breakdown: Record<string, number>;
    pending_payments: number;
  };
  usage: { ai_credits_used_this_month: number };
  catalog: {
    total_ads: number;
    active_ads: number;
    stale_ads: number;
    per_country: Record<string, number>;
  };
}

export interface AdminUser {
  id: string;
  email: string;
  name: string | null;
  image_url?: string;
  role: string;
  created_at: number;
  last_sign_in_at: number | null;
  plan: string;
  credits_used: number;
  credits_limit: number;
  saved_ads: number;
  banned_in_app: boolean;
}

export const adminApi = {
  overview: (getToken: GetToken) => get(getToken, "/api/admin/overview") as Promise<Overview>,

  users: (getToken: GetToken, q: string, limit = 50, offset = 0) =>
    get(getToken, `/api/admin/users?limit=${limit}&offset=${offset}${q ? `&q=${encodeURIComponent(q)}` : ""}`) as Promise<{
      results: AdminUser[];
      total: number;
    }>,

  userDetail: (getToken: GetToken, id: string) => get(getToken, `/api/admin/users/${id}`),

  setPlan: (getToken: GetToken, id: string, plan: string, days: number, creditBonus: number) =>
    send(getToken, `/api/admin/users/${id}/plan`, "POST", { plan, days, credit_bonus: creditBonus }),

  resetCredits: (getToken: GetToken, id: string) =>
    send(getToken, `/api/admin/users/${id}/credits/reset`, "POST"),

  setBan: (getToken: GetToken, id: string, banned: boolean, reason?: string) =>
    send(getToken, `/api/admin/users/${id}/ban`, "POST", { banned, reason }),

  setRole: (getToken: GetToken, id: string, role: "admin" | "member") =>
    send(getToken, `/api/admin/users/${id}/role`, "POST", { role }),

  impersonate: (getToken: GetToken, id: string) =>
    send(getToken, `/api/admin/users/${id}/impersonate`, "POST") as Promise<{ ticket: string }>,

  billing: (getToken: GetToken) => get(getToken, "/api/admin/billing"),

  catalogOverview: (getToken: GetToken) => get(getToken, "/api/admin/catalog/overview"),

  browseAds: (getToken: GetToken, q: string, country: string, offset = 0) =>
    get(
      getToken,
      `/api/admin/catalog/ads?limit=30&offset=${offset}${q ? `&q=${encodeURIComponent(q)}` : ""}${country ? `&country=${country}` : ""}`
    ),

  deleteAd: (getToken: GetToken, id: string) =>
    send(getToken, `/api/admin/catalog/ads/${id}`, "DELETE"),

  audit: (getToken: GetToken, userId?: string) =>
    get(getToken, `/api/admin/audit${userId ? `?user_id=${userId}` : ""}`),

  health: (getToken: GetToken) => get(getToken, "/api/admin/health"),
};
