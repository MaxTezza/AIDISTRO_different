import React, { useEffect, useMemo, useState } from 'react';
import {
    Folder, Search, Grid, List, Home, Monitor, FileText, Download, Camera, Music
} from 'lucide-react';
import { listFiles, type HostFileEntry } from '../native/api';

interface Category {
    id: string;
    label: string;
    icon: React.ReactNode;
    color: string;
    path: string;
}

const CATEGORIES: Category[] = [
    { id: 'home', label: 'Home', icon: <Home className="w-4 h-4" />, color: '#22d3ee', path: '~' },
    { id: 'desktop', label: 'Desktop', icon: <Monitor className="w-4 h-4" />, color: '#8b5cf6', path: '~/Desktop' },
    { id: 'documents', label: 'Documents', icon: <FileText className="w-4 h-4" />, color: '#6366f1', path: '~/Documents' },
    { id: 'downloads', label: 'Downloads', icon: <Download className="w-4 h-4" />, color: '#10b981', path: '~/Downloads' },
    { id: 'pictures', label: 'Pictures', icon: <Camera className="w-4 h-4" />, color: '#f59e0b', path: '~/Pictures' },
    { id: 'music', label: 'Music', icon: <Music className="w-4 h-4" />, color: '#ec4899', path: '~/Music' },
];

export const FileManagerApp: React.FC = () => {
    const [activeCategory, setActiveCategory] = useState(CATEGORIES[0].id);
    const [searchQuery, setSearchQuery] = useState('');
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
    const [entries, setEntries] = useState<HostFileEntry[]>([]);
    const [loading, setLoading] = useState(false);

    const activeCat = CATEGORIES.find((c) => c.id === activeCategory) ?? CATEGORIES[0];

    useEffect(() => {
        let mounted = true;
        setLoading(true);
        listFiles(activeCat.path, 500)
            .then((items) => {
                if (!mounted) return;
                setEntries(items);
            })
            .catch(() => {
                if (!mounted) return;
                setEntries([]);
            })
            .finally(() => {
                if (mounted) setLoading(false);
            });

        return () => {
            mounted = false;
        };
    }, [activeCat.path]);

    const filtered = useMemo(() => {
        const q = searchQuery.trim().toLowerCase();
        if (!q) return entries;
        return entries.filter((f) => f.name.toLowerCase().includes(q) || f.path.toLowerCase().includes(q));
    }, [entries, searchQuery]);

    return (
        <div className="h-full flex overflow-hidden">
            <div className="w-52 border-r border-white/8 flex flex-col py-3">
                <div className="px-3 mb-4">
                    <h3 className="text-[11px] font-semibold text-white/30 uppercase tracking-wider px-2 mb-2">Locations</h3>
                    {CATEGORIES.map((cat) => (
                        <button
                            key={cat.id}
                            onClick={() => {
                                setActiveCategory(cat.id);
                                setSearchQuery('');
                            }}
                            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-all mb-0.5 ${activeCategory === cat.id
                                ? 'bg-white/[0.08] text-white'
                                : 'text-white/40 hover:text-white/60 hover:bg-white/[0.04]'
                                }`}
                        >
                            <span style={activeCategory === cat.id ? { color: cat.color } : {}}>{cat.icon}</span>
                            {cat.label}
                        </button>
                    ))}
                </div>
            </div>

            <div className="flex-1 flex flex-col overflow-hidden">
                <div className="px-5 py-3 border-b border-white/8 flex items-center gap-3">
                    <div className="flex-1 flex items-center gap-2">
                        <span style={{ color: activeCat.color }}>{activeCat.icon}</span>
                        <h2 className="text-sm font-medium text-white">{activeCat.label}</h2>
                        <span className="text-xs text-white/30">{filtered.length} items</span>
                    </div>

                    <div className="flex items-center gap-2 bg-white/[0.04] border border-white/8 rounded-lg px-2.5 py-1.5 w-56 focus-within:border-white/20 transition-colors">
                        <Search className="w-3 h-3 text-white/30" />
                        <input
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            placeholder="Search files..."
                            className="flex-1 bg-transparent outline-none text-xs text-white placeholder-white/30"
                        />
                    </div>

                    <div className="flex bg-white/[0.04] rounded-lg overflow-hidden border border-white/8">
                        <button
                            onClick={() => setViewMode('grid')}
                            className={`p-1.5 ${viewMode === 'grid' ? 'bg-white/10 text-white' : 'text-white/30'}`}
                        >
                            <Grid className="w-3.5 h-3.5" />
                        </button>
                        <button
                            onClick={() => setViewMode('list')}
                            className={`p-1.5 ${viewMode === 'list' ? 'bg-white/10 text-white' : 'text-white/30'}`}
                        >
                            <List className="w-3.5 h-3.5" />
                        </button>
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-4">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center h-full text-white/35 text-sm">
                            Scanning {activeCat.path}...
                        </div>
                    ) : filtered.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full text-white/20">
                            <Folder className="w-10 h-10 mb-3" />
                            <p className="text-sm">No files found</p>
                        </div>
                    ) : viewMode === 'grid' ? (
                        <div className="grid grid-cols-4 gap-3">
                            {filtered.map((file) => (
                                <FileGridItem key={file.path} file={file} />
                            ))}
                        </div>
                    ) : (
                        <div className="space-y-1">
                            {filtered.map((file) => (
                                <FileListItem key={file.path} file={file} />
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

const FileGridItem: React.FC<{ file: HostFileEntry }> = ({ file }) => (
    <div className="group bg-white/[0.02] border border-white/6 rounded-xl p-3 hover:bg-white/[0.05] hover:border-white/12 transition-all cursor-pointer">
        <div className="w-full aspect-square rounded-lg bg-white/[0.03] flex items-center justify-center mb-2.5 text-3xl relative">
            {file.is_dir ? '📁' : iconForName(file.name)}
        </div>
        <div className="text-xs text-white/70 font-medium truncate" title={file.name}>{file.name}</div>
        <div className="flex items-center justify-between mt-1">
            <span className="text-[10px] text-white/25">{file.is_dir ? 'Folder' : formatBytes(file.size_bytes)}</span>
            <span className="text-[10px] text-white/25">{formatModified(file.modified_unix)}</span>
        </div>
    </div>
);

const FileListItem: React.FC<{ file: HostFileEntry }> = ({ file }) => (
    <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/[0.04] transition-colors cursor-pointer group">
        <span className="text-lg">{file.is_dir ? '📁' : iconForName(file.name)}</span>
        <div className="flex-1 min-w-0">
            <div className="text-xs text-white/70 font-medium truncate">{file.name}</div>
            <div className="text-[10px] text-white/25 truncate">{file.path}</div>
        </div>
        <span className="text-[10px] text-white/20 w-20 text-right">{file.is_dir ? 'Folder' : formatBytes(file.size_bytes)}</span>
        <span className="text-[10px] text-white/20 w-24 text-right">{formatModified(file.modified_unix)}</span>
    </div>
);

function iconForName(name: string): string {
    const lower = name.toLowerCase();
    if (lower.endsWith('.pdf')) return '📄';
    if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg') || lower.endsWith('.webp') || lower.endsWith('.gif')) return '🖼️';
    if (lower.endsWith('.mp4') || lower.endsWith('.mkv') || lower.endsWith('.mov')) return '🎬';
    if (lower.endsWith('.mp3') || lower.endsWith('.wav') || lower.endsWith('.flac')) return '🎵';
    if (lower.endsWith('.zip') || lower.endsWith('.tar') || lower.endsWith('.gz')) return '📦';
    if (lower.endsWith('.doc') || lower.endsWith('.docx') || lower.endsWith('.txt') || lower.endsWith('.md')) return '📝';
    return '📄';
}

function formatBytes(bytes: number): string {
    if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let idx = 0;
    while (size >= 1024 && idx < units.length - 1) {
        size /= 1024;
        idx += 1;
    }
    return `${size.toFixed(size >= 10 || idx === 0 ? 0 : 1)} ${units[idx]}`;
}

function formatModified(unixSeconds: number): string {
    if (!unixSeconds) return 'Unknown';
    const when = new Date(unixSeconds * 1000);
    const deltaMs = Date.now() - when.getTime();
    if (deltaMs < 60_000) return 'Just now';
    if (deltaMs < 3_600_000) return `${Math.max(1, Math.floor(deltaMs / 60_000))} min ago`;
    if (deltaMs < 86_400_000) return `${Math.max(1, Math.floor(deltaMs / 3_600_000))} hr ago`;
    if (deltaMs < 604_800_000) return `${Math.max(1, Math.floor(deltaMs / 86_400_000))} day ago`;
    return when.toLocaleDateString();
}
