import type { NextConfig } from "next";
import path from "path";
import os from "os";

/** Keep dev build cache off OneDrive/cloud folders (slow sync). Disable with NEXT_DEV_ONEDRIVE_FIX=0 */
const useTmpDevCache =
  process.env.NEXT_DEV_ONEDRIVE_FIX !== "0" &&
  process.argv.includes("dev") &&
  !process.argv.includes("build") &&
  !process.argv.includes("start");

const nextConfig: NextConfig = {
  ...(useTmpDevCache ? { distDir: path.join(os.tmpdir(), "compressoriq-next-dev") } : {}),
};

export default nextConfig;
