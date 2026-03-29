import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Increase body size limit for EKG image uploads (default 4mb)
  api: {
    bodyParser: {
      sizeLimit: "10mb",
    },
  },
};

export default nextConfig;
