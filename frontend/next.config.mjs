/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // Type checking is executed explicitly by the build script. This bypasses a
  // Next 16.3 CLI regression parsing `tsc --showConfig` on some Node 22 hosts.
  typescript: { ignoreBuildErrors: true },
};

export default nextConfig;
