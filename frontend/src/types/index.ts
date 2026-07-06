export interface Ad {
  id: string;
  platform: "meta" | "tiktok" | "google";
  advertiser_name: string;
  advertiser_id: string;
  ad_id: string;
  country: string;
  countries?: string[];                       // every market sweeps have seen it in
  brand_live_ads?: number;                    // advertiser's TOTAL live ads (deep-dive)
  language: string;
  ad_format: "image" | "video" | "carousel";
  copy_text: string;
  cta_text: string;
  landing_page: string;
  media_urls: string[];
  thumbnail?: string;
  snapshot_url?: string;
  variant_count?: number;
  performance_score?: number;
  heat?: number;                              // "printing money NOW" composite 0-100
  velocity?: number;                          // creative variants per 30d of age
  momentum?: "hot" | "proven" | "steady";
  est_spend_min_usd?: number;                 // honest wide band, labeled estimate
  est_spend_max_usd?: number;
  spend_basis?: "heuristic" | "reach";        // reach = real DSA numbers (EU ads)
  eu_total_reach?: number;
  first_seen: string;
  last_seen: string;
  is_active: boolean;
  days_running?: number;                      // absent on TikTok top ads (unknowable)
  // TikTok engagement — the Creative Center publishes what Meta hides
  likes?: number;
  ctr?: number;                               // percentage figure, e.g. 0.45
  video_duration?: number;
}

export interface Brand {
  advertiser_id: string;
  advertiser_name: string;
  total_ads: number;
  active_ads: number;
  countries: string[];
  total_variants?: number;
  top_score?: number;
  max_days?: number;
  live_ads?: number;          // REAL total live-ad count from the brand deep-dive
}
