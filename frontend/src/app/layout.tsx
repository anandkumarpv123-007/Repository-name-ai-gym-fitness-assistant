import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import FloatingGymBuddy from "@/components/FloatingGymBuddy";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Gym & Fitness Assistant",
  description: "Personalized Computer Vision Workout Tracking, Nutrition & Biomechanics Analytics",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col relative">
        {children}
        <FloatingGymBuddy />
      </body>
    </html>
  );
}
