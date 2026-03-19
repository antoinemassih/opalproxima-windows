/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.DAEMON_URL || 'http://localhost:7477'}/:path*`,
      },
    ]
  },
}
module.exports = nextConfig
