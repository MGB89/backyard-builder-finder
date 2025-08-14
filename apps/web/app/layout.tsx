import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { cn } from '@/lib/utils';
import { Providers } from './providers';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
});

export const metadata: Metadata = {
  title: {
    default: 'Property Assessment Platform',
    template: '%s | Property Assessment Platform',
  },
  description: 'Modern property assessment and evaluation platform',
  keywords: [
    'property assessment',
    'real estate',
    'property evaluation',
    'assessment platform',
  ],
  authors: [
    {
      name: 'Property Assessment Team',
    },
  ],
  creator: 'Property Assessment Platform',
  metadataBase: new URL('https://property-assessment.com'),
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: 'https://property-assessment.com',
    title: 'Property Assessment Platform',
    description: 'Modern property assessment and evaluation platform',
    siteName: 'Property Assessment Platform',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Property Assessment Platform',
    description: 'Modern property assessment and evaluation platform',
    creator: '@propertyassessment',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  verification: {
    google: 'google-site-verification-token',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={cn(
          'min-h-screen bg-background font-sans antialiased',
          inter.variable
        )}
      >
        <Providers>
          <div className="relative flex min-h-screen flex-col">
            <main className="flex-1">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}