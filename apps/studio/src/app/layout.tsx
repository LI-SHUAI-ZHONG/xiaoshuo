import type { Metadata } from "next";
import type { ReactNode } from "react";

import { StudioProviders } from "../providers/studio-providers";
import "./globals.css";

export const metadata: Metadata = {
  description: "ACCOS 创作者工作台",
  title: {
    default: "ACCOS Studio",
    template: "%s · ACCOS Studio",
  },
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>
        <a className="studio-skip-link" href="#main-content">
          跳到主要内容
        </a>
        <StudioProviders>{children}</StudioProviders>
      </body>
    </html>
  );
}
