import { Linkedin, Github, Twitter } from 'lucide-react';

export function Footer() {
    return (
        <footer className="border-t border-border/40 mt-12 py-8 glass">
            <div className="max-w-7xl mx-auto px-4 flex flex-col md:flex-row items-center justify-between gap-4">

                {/* Brand & Powered By */}
                <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                        <span className="font-bold tracking-tight text-foreground">AlphaStream</span>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
                            v1.0.0
                        </span>
                    </div>
                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                        Powered by
                        <a href="https://pathway.com" target="_blank" rel="noopener noreferrer" className="font-medium text-blue-400 hover:underline">
                            Pathway
                        </a>
                        Streaming Engine
                    </div>
                </div>

                {/* Status Indicator */}
                <div className="flex items-center gap-2 text-xs text-muted-foreground bg-secondary/30 px-3 py-1.5 rounded-md border border-border/50">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    System Operational
                </div>

                {/* Socials / Links */}
                <div className="flex items-center gap-4">
                    <a href="#" className="text-muted-foreground hover:text-primary transition-colors">
                        <Github className="h-4 w-4" />
                    </a>
                    <a href="#" className="text-muted-foreground hover:text-primary transition-colors">
                        <Twitter className="h-4 w-4" />
                    </a>
                    <a href="#" className="text-muted-foreground hover:text-primary transition-colors">
                        <Linkedin className="h-4 w-4" />
                    </a>
                    <span className="text-xs text-muted-foreground">© 2026 CrowdWisdomTrading</span>
                </div>
            </div>
        </footer>
    );
}
