import React, { useState, useEffect, useRef } from 'react';
import { useKernelStore, type AppType } from '../kernel/store';
import {
    Search, BrainCircuit, Image, Settings, Shield, Terminal,
    CalendarDays, CloudSun, Mail, FolderOpen, Sparkles, Globe,
    Clock, ArrowRight, X
} from 'lucide-react';

// ─── App Registry ────────────────────────────────────────
// All available apps, grouped by category

interface AppEntry {
    id: AppType;
    name: string;
    description: string;
    icon: React.ReactNode;
    color: string;
    category: 'core' | 'productivity' | 'system';
}

const APP_REGISTRY: AppEntry[] = [
    { id: 'canvas', name: 'Universal Canvas', description: 'Create documents, draw, and design', icon: <BrainCircuit className="w-5 h-5" />, color: '#8b5cf6', category: 'core' },
    { id: 'media', name: 'Media Viewer', description: 'View photos and videos', icon: <Image className="w-5 h-5" />, color: '#10b981', category: 'core' },
    { id: 'files', name: 'Files', description: 'Browse and manage your files', icon: <FolderOpen className="w-5 h-5" />, color: '#22d3ee', category: 'core' },
    { id: 'calendar', name: 'Calendar', description: 'View your schedule and events', icon: <CalendarDays className="w-5 h-5" />, color: '#6366f1', category: 'productivity' },
    { id: 'weather', name: 'Weather', description: 'Current conditions and forecast', icon: <CloudSun className="w-5 h-5" />, color: '#f59e0b', category: 'productivity' },
    { id: 'email', name: 'Email', description: 'Read and send messages', icon: <Mail className="w-5 h-5" />, color: '#ef4444', category: 'productivity' },
    { id: 'settings', name: 'Settings', description: 'Configure your system', icon: <Settings className="w-5 h-5" />, color: '#64748b', category: 'system' },
    { id: 'privacy-moat', name: 'Privacy Moat', description: 'Security and privacy tools', icon: <Shield className="w-5 h-5" />, color: '#22c55e', category: 'system' },
    { id: 'terminal', name: 'Terminal', description: 'Command line interface', icon: <Terminal className="w-5 h-5" />, color: '#ef4444', category: 'system' },
];

// ─── Web Quick-Launch ────────────────────────────────────
// Common websites users might ask to "open"

const WEB_SHORTCUTS: { query: string[]; label: string; url: string; icon: string }[] = [
    { query: ['amazon', 'shop', 'shopping'], label: 'Amazon', url: 'https://amazon.com', icon: '🛒' },
    { query: ['youtube', 'video', 'videos'], label: 'YouTube', url: 'https://youtube.com', icon: '▶️' },
    { query: ['google', 'search'], label: 'Google', url: 'https://google.com', icon: '🔍' },
    { query: ['facebook', 'fb'], label: 'Facebook', url: 'https://facebook.com', icon: '👥' },
    { query: ['twitter', 'x.com'], label: 'X / Twitter', url: 'https://x.com', icon: '🐦' },
    { query: ['netflix', 'watch'], label: 'Netflix', url: 'https://netflix.com', icon: '🎬' },
    { query: ['gmail'], label: 'Gmail', url: 'https://gmail.com', icon: '📧' },
    { query: ['reddit'], label: 'Reddit', url: 'https://reddit.com', icon: '🤖' },
    { query: ['instagram', 'ig'], label: 'Instagram', url: 'https://instagram.com', icon: '📸' },
    { query: ['spotify', 'music'], label: 'Spotify', url: 'https://spotify.com', icon: '🎵' },
    { query: ['news', 'cnn'], label: 'CNN News', url: 'https://cnn.com', icon: '📰' },
    { query: ['bank', 'banking'], label: 'Your Bank', url: 'https://chase.com', icon: '🏦' },
];

export const AppLauncher: React.FC = () => {
    const { spawnApp } = useKernelStore();
    const [isOpen, setIsOpen] = useState(false);
    const [query, setQuery] = useState('');
    const inputRef = useRef<HTMLInputElement>(null);

    // Focus input when opened
    useEffect(() => {
        if (isOpen && inputRef.current) {
            inputRef.current.focus();
        }
    }, [isOpen]);

    // Close on Escape
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isOpen) setIsOpen(false);
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [isOpen]);

    const q = query.toLowerCase().trim();

    // Filter apps
    const filteredApps = q
        ? APP_REGISTRY.filter(a => a.name.toLowerCase().includes(q) || a.description.toLowerCase().includes(q))
        : APP_REGISTRY;

    // Match websites (for "open amazon" type queries)
    const matchedWebsite = WEB_SHORTCUTS.find(w => w.query.some(wq => q.includes(wq)));

    // Is it a natural language "open" command?
    const isOpenCommand = q.startsWith('open ') || q.startsWith('go to ') || q.startsWith('launch ');
    const cleanQuery = q.replace(/^(open |go to |launch )/, '');

    // Smart suggestions when typing
    const smartMatchedApp = isOpenCommand
        ? APP_REGISTRY.find(a => a.name.toLowerCase().includes(cleanQuery))
        : null;
    const smartMatchedWeb = isOpenCommand
        ? WEB_SHORTCUTS.find(w => w.query.some(wq => cleanQuery.includes(wq)))
        : null;

    const handleLaunchApp = (appType: AppType) => {
        spawnApp(appType);
        setIsOpen(false);
        setQuery('');
    };

    const handleOpenWebsite = (url: string) => {
        window.open(url, '_blank');
        setIsOpen(false);
        setQuery('');
    };

    const handleSubmit = () => {
        // If "open xxx" matches an app, launch it
        if (smartMatchedApp) {
            handleLaunchApp(smartMatchedApp.id);
            return;
        }
        // If it matches a website, open it
        if (smartMatchedWeb) {
            handleOpenWebsite(smartMatchedWeb.url);
            return;
        }
        // If just a website name/URL, open it
        if (matchedWebsite) {
            handleOpenWebsite(matchedWebsite.url);
            return;
        }
        // If filtered to one app, launch it
        if (filteredApps.length === 1) {
            handleLaunchApp(filteredApps[0].id);
            return;
        }
        // If looks like a URL, open it
        if (q.includes('.com') || q.includes('.org') || q.includes('.net') || q.includes('http')) {
            const url = q.startsWith('http') ? q : `https://${q}`;
            handleOpenWebsite(url);
            return;
        }
    };

    if (!isOpen) return null;

    const groupedApps = {
        core: filteredApps.filter(a => a.category === 'core'),
        productivity: filteredApps.filter(a => a.category === 'productivity'),
        system: filteredApps.filter(a => a.category === 'system'),
    };

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 z-[150] bg-black/40 backdrop-blur-md"
                onClick={() => { setIsOpen(false); setQuery(''); }}
            />

            {/* Launcher Panel */}
            <div className="fixed inset-0 z-[155] flex items-start justify-center pt-[12vh] pointer-events-none">
                <div className="pointer-events-auto w-[520px] bg-black/90 backdrop-blur-2xl border border-white/15 rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.7)] overflow-hidden animate-in fade-in slide-in-from-bottom-3 duration-200">

                    {/* Search Bar */}
                    <div className="flex items-center gap-3 px-5 py-4 border-b border-white/8">
                        <Search className="w-5 h-5 text-white/30" />
                        <input
                            ref={inputRef}
                            value={query}
                            onChange={e => setQuery(e.target.value)}
                            onKeyDown={e => { if (e.key === 'Enter') handleSubmit(); }}
                            placeholder='Search apps or say "open amazon"...'
                            className="flex-1 bg-transparent outline-none text-base text-white placeholder-white/30"
                        />
                        {query && (
                            <button onClick={() => setQuery('')} className="text-white/20 hover:text-white/50">
                                <X className="w-4 h-4" />
                            </button>
                        )}
                    </div>

                    {/* Smart Command Match */}
                    {(smartMatchedApp || smartMatchedWeb || (matchedWebsite && q)) && (
                        <div className="px-5 py-3 border-b border-white/8">
                            {smartMatchedApp && (
                                <button
                                    onClick={() => handleLaunchApp(smartMatchedApp.id)}
                                    className="w-full flex items-center gap-3 p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20 hover:bg-cyan-500/20 transition-colors"
                                >
                                    <Sparkles className="w-4 h-4 text-cyan-400" />
                                    <span className="text-sm text-white">Open <strong>{smartMatchedApp.name}</strong></span>
                                    <ArrowRight className="w-3.5 h-3.5 text-cyan-400 ml-auto" />
                                </button>
                            )}
                            {(smartMatchedWeb || matchedWebsite) && (
                                <button
                                    onClick={() => handleOpenWebsite((smartMatchedWeb || matchedWebsite)!.url)}
                                    className="w-full flex items-center gap-3 p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20 hover:bg-cyan-500/20 transition-colors mt-1.5"
                                >
                                    <Globe className="w-4 h-4 text-cyan-400" />
                                    <span className="text-sm text-white">
                                        Open <strong>{(smartMatchedWeb || matchedWebsite)!.label}</strong>
                                    </span>
                                    <span className="text-xs text-white/30 ml-auto">{(smartMatchedWeb || matchedWebsite)!.url}</span>
                                </button>
                            )}
                        </div>
                    )}

                    {/* App Grid */}
                    <div className="px-5 py-4 max-h-[50vh] overflow-y-auto">
                        {/* Recents row */}
                        {!q && (
                            <div className="mb-4">
                                <div className="text-[10px] text-white/25 uppercase tracking-wider font-semibold mb-2 flex items-center gap-1.5">
                                    <Clock className="w-3 h-3" /> Recent
                                </div>
                                <div className="flex gap-3">
                                    {APP_REGISTRY.slice(0, 4).map(app => (
                                        <button
                                            key={app.id}
                                            onClick={() => handleLaunchApp(app.id)}
                                            className="flex flex-col items-center gap-1.5 p-3 rounded-xl hover:bg-white/[0.06] transition-colors w-20"
                                        >
                                            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: `${app.color}20`, color: app.color }}>
                                                {app.icon}
                                            </div>
                                            <span className="text-[10px] text-white/50 text-center leading-tight">{app.name}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Grouped apps */}
                        {Object.entries(groupedApps).map(([category, apps]) => {
                            if (apps.length === 0) return null;
                            return (
                                <div key={category} className="mb-3">
                                    <div className="text-[10px] text-white/25 uppercase tracking-wider font-semibold mb-2">
                                        {category}
                                    </div>
                                    <div className="space-y-0.5">
                                        {apps.map(app => (
                                            <button
                                                key={app.id}
                                                onClick={() => handleLaunchApp(app.id)}
                                                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/[0.06] transition-colors text-left"
                                            >
                                                <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ backgroundColor: `${app.color}15`, color: app.color }}>
                                                    {app.icon}
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="text-sm text-white/70 font-medium">{app.name}</div>
                                                    <div className="text-[10px] text-white/25">{app.description}</div>
                                                </div>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            );
                        })}

                        {filteredApps.length === 0 && !matchedWebsite && (
                            <div className="text-center py-8">
                                <Globe className="w-8 h-8 text-white/10 mx-auto mb-2" />
                                <p className="text-xs text-white/30">No apps found. Press Enter to search the web.</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </>
    );
};

// ─── Launcher Trigger ────────────────────────────────────
// Hook + context for opening the launcher from anywhere

let openLauncherFn: (() => void) | null = null;

export function useAppLauncher() {
    return {
        openLauncher: () => openLauncherFn?.(),
    };
}

export const AppLauncherProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [isOpen, setIsOpen] = useState(false);

    useEffect(() => {
        openLauncherFn = () => setIsOpen(true);
        return () => { openLauncherFn = null; };
    }, []);

    return (
        <>
            {children}
            {isOpen && <AppLauncherInner onClose={() => setIsOpen(false)} />}
        </>
    );
};

// Inner component that uses the real isOpen state from provider
const AppLauncherInner: React.FC<{ onClose: () => void }> = ({ onClose }) => {
    const { spawnApp } = useKernelStore();
    const [query, setQuery] = useState('');
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        inputRef.current?.focus();
    }, []);

    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [onClose]);

    const q = query.toLowerCase().trim();
    const filteredApps = q
        ? APP_REGISTRY.filter(a => a.name.toLowerCase().includes(q) || a.description.toLowerCase().includes(q))
        : APP_REGISTRY;

    const matchedWebsite = WEB_SHORTCUTS.find(w => w.query.some(wq => q.includes(wq)));
    const isOpenCommand = q.startsWith('open ') || q.startsWith('go to ') || q.startsWith('launch ');
    const cleanQuery = q.replace(/^(open |go to |launch )/, '');
    const smartMatchedApp = isOpenCommand ? APP_REGISTRY.find(a => a.name.toLowerCase().includes(cleanQuery)) : null;
    const smartMatchedWeb = isOpenCommand ? WEB_SHORTCUTS.find(w => w.query.some(wq => cleanQuery.includes(wq))) : null;

    const handleLaunchApp = (appType: AppType) => { spawnApp(appType); onClose(); };
    const handleOpenWebsite = (url: string) => { window.open(url, '_blank'); onClose(); };

    const handleSubmit = () => {
        if (smartMatchedApp) { handleLaunchApp(smartMatchedApp.id); return; }
        if (smartMatchedWeb) { handleOpenWebsite(smartMatchedWeb.url); return; }
        if (matchedWebsite) { handleOpenWebsite(matchedWebsite.url); return; }
        if (filteredApps.length === 1) { handleLaunchApp(filteredApps[0].id); return; }
        if (q.includes('.com') || q.includes('.org') || q.includes('.net') || q.includes('http')) {
            handleOpenWebsite(q.startsWith('http') ? q : `https://${q}`);
        }
    };

    const groupedApps = {
        core: filteredApps.filter(a => a.category === 'core'),
        productivity: filteredApps.filter(a => a.category === 'productivity'),
        system: filteredApps.filter(a => a.category === 'system'),
    };

    return (
        <>
            <div className="fixed inset-0 z-[150] bg-black/40 backdrop-blur-md" onClick={onClose} />
            <div className="fixed inset-0 z-[155] flex items-start justify-center pt-[12vh] pointer-events-none">
                <div className="pointer-events-auto w-[520px] bg-black/90 backdrop-blur-2xl border border-white/15 rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.7)] overflow-hidden animate-in fade-in slide-in-from-bottom-3 duration-200">
                    {/* Search Bar */}
                    <div className="flex items-center gap-3 px-5 py-4 border-b border-white/8">
                        <Search className="w-5 h-5 text-white/30" />
                        <input
                            ref={inputRef}
                            value={query}
                            onChange={e => setQuery(e.target.value)}
                            onKeyDown={e => { if (e.key === 'Enter') handleSubmit(); }}
                            placeholder='Search apps or say "open amazon"...'
                            className="flex-1 bg-transparent outline-none text-base text-white placeholder-white/30"
                        />
                        {query && (
                            <button onClick={() => setQuery('')} className="text-white/20 hover:text-white/50">
                                <X className="w-4 h-4" />
                            </button>
                        )}
                    </div>

                    {/* Smart Match */}
                    {(smartMatchedApp || smartMatchedWeb || (matchedWebsite && q)) && (
                        <div className="px-5 py-3 border-b border-white/8">
                            {smartMatchedApp && (
                                <button onClick={() => handleLaunchApp(smartMatchedApp.id)} className="w-full flex items-center gap-3 p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20 hover:bg-cyan-500/20 transition-colors">
                                    <Sparkles className="w-4 h-4 text-cyan-400" />
                                    <span className="text-sm text-white">Open <strong>{smartMatchedApp.name}</strong></span>
                                    <ArrowRight className="w-3.5 h-3.5 text-cyan-400 ml-auto" />
                                </button>
                            )}
                            {(smartMatchedWeb || matchedWebsite) && !smartMatchedApp && (
                                <button onClick={() => handleOpenWebsite((smartMatchedWeb || matchedWebsite)!.url)} className="w-full flex items-center gap-3 p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20 hover:bg-cyan-500/20 transition-colors">
                                    <Globe className="w-4 h-4 text-cyan-400" />
                                    <span className="text-sm text-white">Open <strong>{(smartMatchedWeb || matchedWebsite)!.label}</strong></span>
                                    <span className="text-xs text-white/30 ml-auto">{(smartMatchedWeb || matchedWebsite)!.url}</span>
                                </button>
                            )}
                        </div>
                    )}

                    {/* App Grid */}
                    <div className="px-5 py-4 max-h-[50vh] overflow-y-auto">
                        {!q && (
                            <div className="mb-4">
                                <div className="text-[10px] text-white/25 uppercase tracking-wider font-semibold mb-2 flex items-center gap-1.5">
                                    <Clock className="w-3 h-3" /> Recent
                                </div>
                                <div className="flex gap-3">
                                    {APP_REGISTRY.slice(0, 4).map(app => (
                                        <button key={app.id} onClick={() => handleLaunchApp(app.id)} className="flex flex-col items-center gap-1.5 p-3 rounded-xl hover:bg-white/[0.06] transition-colors w-20">
                                            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: `${app.color}20`, color: app.color }}>{app.icon}</div>
                                            <span className="text-[10px] text-white/50 text-center leading-tight">{app.name}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {Object.entries(groupedApps).map(([category, apps]) => {
                            if (apps.length === 0) return null;
                            return (
                                <div key={category} className="mb-3">
                                    <div className="text-[10px] text-white/25 uppercase tracking-wider font-semibold mb-2">{category}</div>
                                    <div className="space-y-0.5">
                                        {apps.map(app => (
                                            <button key={app.id} onClick={() => handleLaunchApp(app.id)} className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/[0.06] transition-colors text-left">
                                                <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ backgroundColor: `${app.color}15`, color: app.color }}>{app.icon}</div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="text-sm text-white/70 font-medium">{app.name}</div>
                                                    <div className="text-[10px] text-white/25">{app.description}</div>
                                                </div>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            );
                        })}

                        {filteredApps.length === 0 && !matchedWebsite && (
                            <div className="text-center py-8">
                                <Globe className="w-8 h-8 text-white/10 mx-auto mb-2" />
                                <p className="text-xs text-white/30">No apps found. Press Enter to search the web.</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </>
    );
};
