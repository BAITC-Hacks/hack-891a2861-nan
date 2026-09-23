import type { Metadata } from "next";
import { Header } from "@/components/header";
import { LocaleProvider } from "@/components/locale-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Career Quest | Halyk",
  description: "Explainable AI navigator for employee development",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body>
        <LocaleProvider>
          <Header />
          <main>{children}</main>
        </LocaleProvider>
      </body>
    </html>
  );
}
