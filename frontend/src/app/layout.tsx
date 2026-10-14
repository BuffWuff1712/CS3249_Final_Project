import type {Metadata} from 'next';
import './globals.css';
export const metadata: Metadata = {title: 'Beany · Shopping copilot', description: 'A safety-focused conversational shopping prototype'};
export default function RootLayout({children}: {children: React.ReactNode}) {return <html lang="en"><body>{children}</body></html>;}
