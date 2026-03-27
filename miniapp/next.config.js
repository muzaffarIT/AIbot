/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const backend =
      process.env.BACKEND_INTERNAL_URL ||
      'https://backendapp-production-c193.up.railway.app'
    return [{
      source: '/api/:path*',
      destination: `${backend}/api/:path*`,
    }]
  },
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: '**' },
    ],
  },
}

module.exports = nextConfig
