import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach Clerk token to requests
api.interceptors.request.use(async (config) => {
  if (typeof window !== "undefined") {
    const { Clerk } = await import("@clerk/nextjs");
    // Token will be attached via Clerk's session
  }
  return config;
});

// API functions
export const searchAds = (params: {
  q?: string;
  platform?: string;
  format?: string;
  country?: string;
  page?: number;
  limit?: number;
}) => api.get("/api/ads/search", { params });

export const getAd = (id: string) => api.get(`/api/ads/${id}`);

export const searchBrands = (q: string) => api.get("/api/brands/search", { params: { q } });

export const getBrandAds = (id: string) => api.get(`/api/brands/${id}/ads`);

export const generateScript = (adId: string) =>
  api.post("/api/ai/generate-script", { ad_id: adId });

export const generateCopy = (data: { product: string; audience: string; platform: string }) =>
  api.post("/api/ai/generate-copy", data);

export const saveAd = (adId: string, board: string) =>
  api.post("/api/user/save", { ad_id: adId, board });

export const getSavedAds = () => api.get("/api/user/saved");
