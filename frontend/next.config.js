/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // API_URL = server-side (inside container, e.g. http://backend:8000)
    // NEXT_PUBLIC_API_URL = browser-side (e.g. http://localhost:8000)
    const api =
      process.env.API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${api}/:path*` }];
  },
};
module.exports = nextConfig;
