/**
 * Authenticated backend calls.
 *
 * The backend now verifies Clerk session JWTs (Authorization: Bearer) instead
 * of trusting an X-User-Id header. Components grab `getToken` from Clerk's
 * useAuth() and pass it here.
 */

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type GetToken = () => Promise<string | null>;

export async function authFetch(
  getToken: GetToken,
  path: string,
  init: RequestInit = {}
): Promise<Response> {
  const headers = new Headers(init.headers);
  try {
    const token = await getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  } catch {
    /* signed out — request goes through unauthenticated and the API returns 401 */
  }
  return fetch(`${API_URL}${path}`, { ...init, headers });
}

/** Human-readable message for non-OK API responses (handles 401/402/429). */
export async function apiError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    const d = data?.detail;
    if (typeof d === "string") return d;
    if (d?.message) return d.message;
  } catch {}
  if (res.status === 401) return "Please sign in again.";
  if (res.status === 402) return "You're out of AI credits this month — upgrade to keep going.";
  if (res.status === 429) return "Too many requests — wait a minute and retry.";
  return `API error ${res.status}`;
}
