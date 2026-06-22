import type { ReactNode } from "react";

import "./styles.css";

export const metadata = {
  title: "AI Workflow Challenge",
  description: "Minimal frontend shell for the interview challenge"
};

export default function RootLayout({
  children
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
