import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "맛집 리스트",
  description: "가게명, 메뉴, 별점을 기록하는 맛집 리스트 앱",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-gray-50">{children}</body>
    </html>
  );
}
