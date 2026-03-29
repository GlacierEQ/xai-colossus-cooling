import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Colossus — APEX Thermal Dashboard',
  description: 'Real-time thermal telemetry, MORPHEUS RL decisions, piston control | GlacierEQ',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-apex-dark text-white font-mono min-h-screen">{children}</body>
    </html>
  )
}
