import type { Metadata } from "next";
import { Providers } from "./providers";
import { NavTabs } from "@/components/ui/nav-tabs";
import "./globals.css";

export const metadata: Metadata = {
  title: "Bord",
  description: "Tableau de bord personnel",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen">
        <Providers>
          <div className="mx-auto max-w-7xl px-4 py-4">
            <header className="mb-6 flex items-center justify-between">
              <h1 className="text-xl font-bold tracking-tight text-text-primary">
                B<span className="text-accent-blue">ord</span>
              </h1>
              <NavTabs />
            </header>
            <main>{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
