import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

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
        <body suppressHydrationWarning>
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
