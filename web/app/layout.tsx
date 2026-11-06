import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Footer, Nav, SosFab } from "@/components/Nav";
import { ServiceWorker } from "@/components/Pwa";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "KinCare: know the batch, not just the brand",
  description:
    "Scan a medicine strip. Live agents check every regulator alert list, then keep watching that batch for you.",
  icons: { apple: "/icons/apple-touch-icon.png" },
  appleWebApp: { capable: true, title: "KinCare", statusBarStyle: "default" },
};

export const viewport: Viewport = { themeColor: "#f7f1ec" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}>
        <a href="#content" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-full focus:bg-espresso focus:px-4 focus:py-2 focus:text-sm focus:text-paper">
          Skip to content
        </a>
        <Nav />
        <div id="content" tabIndex={-1} className="outline-none">{children}</div>
        <Footer />
        <SosFab />
        <ServiceWorker />
      </body>
    </html>
  );
}
