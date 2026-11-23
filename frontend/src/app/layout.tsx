import type {Metadata} from 'next';
import {Instrument_Serif, Inter, JetBrains_Mono} from 'next/font/google';
import './globals.css';

const inter = Inter({subsets: ['latin'], variable: '--font-sans', display: 'swap'});
const serif = Instrument_Serif({subsets: ['latin'], weight: '400', variable: '--font-serif', display: 'swap'});
const mono = JetBrains_Mono({subsets: ['latin'], variable: '--font-mono', display: 'swap'});

export const metadata: Metadata = {title: 'Beany · Shopping copilot', description: 'A safety-focused conversational shopping prototype'};
export default function RootLayout({children}: {children: React.ReactNode}) {
  return <html lang="en" className={`${inter.variable} ${serif.variable} ${mono.variable}`}><body>{children}</body></html>;
}
