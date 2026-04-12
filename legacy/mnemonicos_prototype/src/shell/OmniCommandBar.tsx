import React, { useState, useEffect, useRef } from 'react';
import { Mic, Search, Command } from 'lucide-react';
import { useKernelStore } from '../kernel/store';
import { setSystemVolume, toggleSystemMute } from '../native/api';

export const OmniCommandBar: React.FC = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [input, setInput] = useState('');
    const [isListening, setIsListening] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);
    const { spawnApp } = useKernelStore();

    // Global keyboard shortcut (Ctrl+Space or CMD+Space) to toggle
    useEffect(() => {
        const handleGlobalKeyDown = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.code === 'Space') {
                e.preventDefault();
                setIsOpen(prev => !prev);
            }
            if (e.key === 'Escape' && isOpen) {
                setIsOpen(false);
                setInput('');
            }
        };

        window.addEventListener('keydown', handleGlobalKeyDown);
        return () => window.removeEventListener('keydown', handleGlobalKeyDown);
    }, [isOpen]);

    useEffect(() => {
        if (isOpen && inputRef.current) {
            inputRef.current.focus();
        }
    }, [isOpen]);

    const handleExecuteIntent = async (e: React.FormEvent) => {
        e.preventDefault();
        const intent = input.trim().toLowerCase();
        if (!intent) return;

        setInput('');
        setIsOpen(false);

        // Intent Parser logic
        if (intent.includes('email') || intent.includes('mail')) {
            spawnApp('email', { compose: true, draftText: intent });
        } else if (intent.includes('music') || intent.includes('media') || intent.includes('song')) {
            spawnApp('media');
        } else if (intent.includes('settings') || intent.includes('control')) {
            spawnApp('settings');
        } else if (intent.includes('mute') || intent.includes('silence')) {
            await toggleSystemMute();
        } else if (intent.includes('volume') && /\d+/.test(intent)) {
            const match = intent.match(/\d+/);
            if (match) await setSystemVolume(Number(match[0]));
        } else if (intent.includes('store') || intent.includes('install')) {
            spawnApp('app-store');
        } else if (intent.includes('driver') || intent.includes('hardware')) {
            spawnApp('driver-manager');
        } else {
            // Default: It's an ambiguous thought, throw it onto the Universal Canvas
            spawnApp('canvas', { text: `User Intent: ${intent}\n\n(AI would process this generic thought here)` });
        }
    };

    if (!isOpen) {
        return (
            <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[100]">
                <button
                    onClick={() => setIsOpen(true)}
                    className="group flex items-center gap-3 px-5 py-3 bg-black/40 hover:bg-black/60 backdrop-blur-md border border-white/10 hover:border-white/30 rounded-full shadow-2xl transition-all duration-300"
                >
                    <div className="p-1.5 bg-accent/20 rounded-full group-hover:bg-accent/40 transition-colors">
                        <Mic className="w-4 h-4 text-accent" />
                    </div>
                    <span className="text-sm font-medium text-white/70 group-hover:text-white transition-colors">
                        Tell MnemonicOS... <span className="opacity-50 ml-2 border border-white/20 rounded px-1.5 py-0.5 text-[10px]">⌘ Space</span>
                    </span>
                </button>
            </div>
        );
    }

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center pointer-events-none">
            {/* Backdrop click to close */}
            <div
                className="absolute inset-0 bg-black/20 backdrop-blur-sm pointer-events-auto transition-opacity"
                onClick={() => setIsOpen(false)}
            />

            {/* Command Bar */}
            <div className="w-full max-w-2xl bg-black/80 backdrop-blur-xl border border-white/10 rounded-2xl shadow-[0_0_50px_rgba(0,0,0,0.5)] overflow-hidden pointer-events-auto animate-in zoom-in-95 duration-200">
                <form onSubmit={handleExecuteIntent} className="flex items-center p-4 border-b border-white/10">
                    <Command className="w-6 h-6 text-white/40 ml-2" />
                    <input
                        ref={inputRef}
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="What do you want to do?"
                        className="flex-1 bg-transparent text-white text-xl px-4 py-2 outline-none placeholder:text-white/30"
                    />
                    <button
                        type="button"
                        onClick={() => setIsListening(!isListening)}
                        className={`p-2 rounded-xl transition-colors ${isListening ? 'bg-red-500/20 text-red-400' : 'hover:bg-white/10 text-white/40 hover:text-white'}`}
                    >
                        <Mic className={`w-6 h-6 ${isListening ? 'animate-pulse' : ''}`} />
                    </button>
                </form>

                {/* Optional: Suggestions or Recent Context could go here in the future */}
                <div className="px-6 py-4 bg-white/5">
                    <div className="flex items-center gap-2 text-xs text-white/40 mb-3 uppercase tracking-widest font-bold">
                        <Search className="w-3.5 h-3.5" /> Intent Suggestions
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {['"Write an email to Mom"', '"Play some jazz"', '"Mute the volume"', '"Open the system settings"'].map((suggestion, idx) => (
                            <button
                                key={idx}
                                type="button"
                                onClick={() => {
                                    setInput(suggestion.replace(/["']/g, ""));
                                    inputRef.current?.focus();
                                }}
                                className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/60 hover:text-white text-sm transition-colors border border-white/5"
                            >
                                {suggestion}
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};
