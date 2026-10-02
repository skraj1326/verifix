import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "react-hot-toast";

// `next/font/google` downloads the font at build time and its ESM font loader
// crashes on Windows with Node 24 (ERR_UNSUPPORTED_ESM_URL_SCHEME: protocol
// 'c:'). Using a local system font stack keeps the build hermetic and avoids
// the incompatible loader.
const fontClassName = "font-sans";

export const metadata: Metadata = {
  title: "VerifiX AI - Verification Platform",
  description: "AI-assisted verification from RTL to coverage closure",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${fontClassName} bg-gray-950 text-white antialiased`}>
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: "#1e293b",
              color: "#f8fafc",
              border: "1px solid #334155",
            },
            success: {
              iconTheme: {
                primary: "#22c55e",
                secondary: "#f8fafc",
              },
            },
            error: {
              iconTheme: {
                primary: "#ef4444",
                secondary: "#f8fafc",
              },
            },
          }}
        />
      </body>
    </html>
  );
}