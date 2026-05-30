import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'APEX Colossus Cooling — xAI Thermal Intelligence',
  description: 'Real-time thermal monitoring dashboard for xAI Colossus-class GPU clusters | GlacierEQ APEX Architecture',
  authors: [{ name: 'Casey Barton', url: 'https://github.com/GlacierEQ' }],
  keywords: ['xAI', 'Colossus', 'thermal management', 'APEX', 'GlacierEQ', 'GPU cooling'],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-apex-black text-white font-mono antialiased">
        {children}
      </body>
    </html>
  );
}
