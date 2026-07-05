/** @type {import('next').NextConfig} */
const nextConfig = {
  async redirects() {
    return [
      // The ad detail page lives at /creative/[id], NOT /ad/[id]: ad blockers
      // (uBlock/AdBlock/Edge tracking prevention) block any subresource whose
      // URL contains "/ad/" — which included the route's own JS chunk under
      // /_next/static/chunks/app/(dashboard)/ad/[id]/page.js, leaving the page
      // stuck on its loading spinner. Same reason the API mounts /api/creatives.
      { source: "/ad/:id", destination: "/creative/:id", permanent: true },
    ];
  },
};

export default nextConfig;
