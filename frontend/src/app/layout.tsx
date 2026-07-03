import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "AdSpy — Ad Intelligence for MENA",
    template: "%s · AdSpy",
  },
  description:
    "Find the ads that print money. Spy winning Meta ads across Tunisia, Morocco, Algeria, Egypt, KSA and the UAE — then launch your own with an AI media buyer.",
  openGraph: {
    title: "AdSpy — Ad Intelligence for MENA",
    description:
      "Spy winning ads across 6 MENA markets, track any brand, and plan campaigns with an AI media buyer.",
    type: "website",
  },
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
