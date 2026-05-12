import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Civil Monitoring Platform",
  description: "Geotechnical & civil engineering instrumentation monitoring",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
