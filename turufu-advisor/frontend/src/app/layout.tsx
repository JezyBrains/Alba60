import type { Metadata, Viewport } from "next";
import { LanguageProvider } from "@/lib/LanguageContext";
import "./globals.css";

export const metadata: Metadata = {
  title: "Albastini",
  description: "Unbeatable IS-MCTS game advisor for the 36-card Tanzanian trick-taking card game.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-surface text-ink antialiased">
        <LanguageProvider>{children}</LanguageProvider>
      </body>
    </html>
  );
}
