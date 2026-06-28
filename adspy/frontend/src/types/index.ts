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
  first_seen: string;
  last_seen: string;
  is_active: boolean;
  days_running: number;
}

export interface Brand {
  advertiser_id: string;
  advertiser_name: string;
  platform: string;
  total_ads: number;
  active_ads: number;
  countries: string[];
}

export interface AIGeneration {
  id: string;
  type: "script" | "copy" | "analysis";
  output: {
    hooks: string[];
    script?: string;
    copy?: string;
    score?: number;
    suggestions?: string[];
  };
  created_at: string;
}

export interface UserUsage {
  plan: "free" | "pro" | "agency";
  searches_today: number;
  searches_limit: number;
  credits_remaining: number;
  credits_limit: number;
}
