import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { PostHogProvider } from "./providers";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "LinkRight — AI-Powered Career Tools",
  description:
    "Pixel-perfect resumes tailored to every job description. Built by a PM, for PMs.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.className} antialiased`}>
      <body className="min-h-screen flex flex-col">
        <PostHogProvider>{children}</PostHogProvider>
      </body>
    </html>
  );
}
