import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AdSpy — Ad Intelligence Platform",
  description:
    "Spy, swipe, and create winning ads. The ad library for MENA marketers.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en">
        {/* suppressHydrationWarning: browser extensions (e.g. Grammarly) inject
            attributes on <body> before hydration, causing a harmless mismatch. */}
        <body className={inter.className} suppressHydrationWarning>
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
