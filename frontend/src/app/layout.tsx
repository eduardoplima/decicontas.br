import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DeciContas",
  description: "Revisão de decisões extraídas por LLM.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
