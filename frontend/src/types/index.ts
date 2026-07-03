export interface Ad {
  id: string;
  platform: "meta" | "tiktok" | "google";
  advertiser_name: string;
  advertiser_id: string;
  ad_id: string;
  country: string;
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
  first_seen: string;
  last_seen: string;
  is_active: boolean;
  days_running: number;
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
}
