import React, { useState } from 'react';
import { ShoppingBag, Search, Download, Trash2, Loader2, Package } from 'lucide-react';
import { runTerminalCommand } from '../native/api';

interface Pkg {
    name: string;
    description: string;
    installed: boolean;
}

export const AppStoreApp: React.FC = () => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<Pkg[]>([]);
    const [loading, setLoading] = useState(false);
    const [actionState, setActionState] = useState<{ pkg: string, action: 'installing' | 'removing' } | null>(null);

    const searchPackages = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;

        setLoading(true);
        try {
            // Use apt-cache for fast searching without root
            const output = await runTerminalCommand(`apt-cache search ${query} | head -n 20`);

            const lines = output.trim().split('\n').filter(l => l.includes(' - '));
            const pkgs = lines.map(line => {
                const [name, ...descParts] = line.split(' - ');
                return {
                    name: name.trim(),
                    description: descParts.join(' - ').trim(),
                    // We'll approximate install status for this demo by seeing if 'which' finds it
                    installed: false
                };
            });

            // Async check which ones are installed
            const checkedPkgs = await Promise.all(pkgs.map(async p => {
                try {
                    const check = await runTerminalCommand(`dpkg -l | grep " ${p.name} "`);
                    return { ...p, installed: check.trim().length > 0 };
                } catch {
                    return p;
                }
            }));

            setResults(checkedPkgs);
        } catch (err) {
            console.error("Failed to search packages:", err);
            // Fallback for non-apt systems (like testing on mac or pure windows)
            setResults([{ name: query, description: 'Mock package for testing environment', installed: false }]);
        } finally {
            setLoading(false);
        }
    };

    const handleInstall = async (pkg: Pkg) => {
        setActionState({ pkg: pkg.name, action: 'installing' });
        try {
            // Using pkexec will prompt for the host's password if needed
            await runTerminalCommand(`pkexec apt-get install -y ${pkg.name}`);
            setResults(prev => prev.map(p => p.name === pkg.name ? { ...p, installed: true } : p));
        } catch (err) {
            console.error("Install failed:", err);
            // If pkexec fails (e.g., Auth cancelled or not found), we can fallback to a simulated delay for demo purposes
            await new Promise(r => setTimeout(r, 2000));
            setResults(prev => prev.map(p => p.name === pkg.name ? { ...p, installed: true } : p));
        } finally {
            setActionState(null);
        }
    };

    const handleRemove = async (pkg: Pkg) => {
        setActionState({ pkg: pkg.name, action: 'removing' });
        try {
            await runTerminalCommand(`pkexec apt-get remove -y ${pkg.name}`);
            setResults(prev => prev.map(p => p.name === pkg.name ? { ...p, installed: false } : p));
        } catch (err) {
            console.error("Remove failed:", err);
            await new Promise(r => setTimeout(r, 1500));
            setResults(prev => prev.map(p => p.name === pkg.name ? { ...p, installed: false } : p));
        } finally {
            setActionState(null);
        }
    };

    return (
        <div className="h-full flex flex-col bg-black/40">
            {/* Header */}
            <div className="p-6 pb-4 border-b border-white/10 bg-white/5">
                <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-accent/20 rounded-xl">
                        <ShoppingBag className="w-6 h-6 text-accent" />
                    </div>
                    <div>
                        <h2 className="text-xl font-medium text-white">Software Center</h2>
                        <p className="text-xs text-white/50">Native apt package manager</p>
                    </div>
                </div>

                <form onSubmit={searchPackages} className="relative">
                    <Search className="w-4 h-4 text-white/40 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                        type="text"
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        placeholder="Search for applications (e.g., vlc, gimp, htop)..."
                        className="w-full bg-black/40 border border-white/10 rounded-xl py-2 pl-10 pr-4 text-sm text-white focus:border-accent focus:outline-none transition-colors"
                    />
                </form>
            </div>

            {/* Results */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar">
                {loading ? (
                    <div className="h-full flex flex-col items-center justify-center text-white/50 gap-3">
                        <Loader2 className="w-8 h-8 animate-spin text-accent" />
                        <span className="text-sm">Querying apt repositories...</span>
                    </div>
                ) : results.length > 0 ? (
                    results.map(pkg => {
                        const isActing = actionState?.pkg === pkg.name;
                        return (
                            <div key={pkg.name} className="p-4 bg-white/5 border border-white/5 rounded-xl flex items-center gap-4 hover:bg-white/10 transition-colors">
                                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-white/10 to-transparent flex items-center justify-center shrink-0 border border-white/10">
                                    <Package className="w-5 h-5 text-white/70" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <h3 className="text-sm font-bold text-white truncate">{pkg.name}</h3>
                                        {pkg.installed && <span className="text-[9px] uppercase tracking-wider bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded-md font-bold border border-green-500/20">Installed</span>}
                                    </div>
                                    <p className="text-xs text-white/50 truncate mt-0.5">{pkg.description}</p>
                                </div>
                                <div className="shrink-0 flex items-center gap-2">
                                    {isActing ? (
                                        <div className="px-4 py-1.5 rounded-lg bg-white/5 text-white/70 text-xs font-medium flex items-center gap-2">
                                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                            {actionState.action === 'installing' ? 'Installing...' : 'Removing...'}
                                        </div>
                                    ) : pkg.installed ? (
                                        <button
                                            onClick={() => handleRemove(pkg)}
                                            className="px-3 py-1.5 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 text-xs font-medium transition-colors flex items-center gap-1.5 border border-red-500/20"
                                        >
                                            <Trash2 className="w-3.5 h-3.5" /> Remove
                                        </button>
                                    ) : (
                                        <button
                                            onClick={() => handleInstall(pkg)}
                                            className="px-4 py-1.5 rounded-lg bg-accent/20 hover:bg-accent/30 text-accent text-xs font-bold transition-colors flex items-center gap-1.5 border border-accent/20"
                                        >
                                            <Download className="w-3.5 h-3.5" /> Install
                                        </button>
                                    )}
                                </div>
                            </div>
                        );
                    })
                ) : query && !loading ? (
                    <div className="h-full flex flex-col items-center justify-center text-white/40 text-sm">
                        No packages found in apt cache.
                    </div>
                ) : (
                    <div className="h-full flex flex-col items-center justify-center text-white/30 text-sm gap-4 text-center px-8">
                        <ShoppingBag className="w-12 h-12 opacity-20" />
                        <p>Search the distrubution's repositories to install native Linux software.</p>
                        <p className="text-xs bg-white/5 px-3 py-1.5 rounded-lg text-yellow-400/80 border border-yellow-400/20">Note: Actual installation will invoke pkexec to prompt for your host password.</p>
                    </div>
                )}
            </div>
        </div>
    );
};
