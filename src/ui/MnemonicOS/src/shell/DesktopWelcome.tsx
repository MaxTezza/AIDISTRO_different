import React, { useState, useEffect } from 'react';
import { useKernelStore } from '../kernel/store';
import {
    TerminalSquare, Image as ImageIcon, Settings, Bot,
    Grip, Lightbulb, ArrowRight
} from 'lucide-react';

export const DesktopWelcome: React.FC = () => {
    const { userProfile, hasCompletedOnboarding, spawnApp, toggleGuide } = useKernelStore();
    const [time, setTime] = useState(new Date());
    const [dismissed, setDismissed] = useState(false);
    const [tipIndex] = useState(Math.floor(Math.random() * 4));

    useEffect(() => {
        const timer = setInterval(() => setTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    // Don't show before onboarding, or if dismissed
    if (!hasCompletedOnboarding || dismissed) return null;

    const osName = userProfile.displayName.trim()
        ? `${userProfile.displayName.trim()} OS`
        : 'Mnemonic OS';

    const greeting = (() => {
        const h = time.getHours();
        if (h < 12) return 'Good morning';
        if (h < 18) return 'Good afternoon';
        return 'Good evening';
    })();

    const formattedTime = time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const formattedDate = time.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' });

    const quickActions = [
        { label: 'Canvas', icon: <TerminalSquare className="w-6 h-6" />, action: () => spawnApp('canvas'), color: '#8b5cf6' },
        { label: 'Media', icon: <ImageIcon className="w-6 h-6" />, action: () => spawnApp('media'), color: '#10b981' },
        { label: 'Settings', icon: <Settings className="w-6 h-6" />, action: () => spawnApp('settings'), color: '#f59e0b' },
        { label: 'Guide', icon: <Bot className="w-6 h-6" />, action: () => toggleGuide(), color: userProfile.accentColor },
    ];

    const tips = [
        'Drag and drop any file onto the desktop to open it instantly.',
        'Type natural language commands in the search bar — like "Mute my audio".',
        'Click the Guide bot icon anytime you need help understanding the interface.',
        'Your system adapts — the more you use it, the smarter it gets.',
    ];

    return (
        <div className="absolute inset-0 z-20 flex items-center justify-center pointer-events-none">
            <div className="pointer-events-auto w-full max-w-lg mx-4 animate-in fade-in zoom-in-95 duration-700">

                {/* Main Welcome Card */}
                <div
                    className="bg-white/[0.04] backdrop-blur-2xl border border-white/10 rounded-3xl overflow-hidden shadow-[0_0_60px_rgba(0,0,0,0.4)]"
                >
                    {/* Clock Header */}
                    <div className="pt-10 pb-6 text-center">
                        <div className="text-6xl font-extralight text-white tracking-tight mb-1">{formattedTime}</div>
                        <div className="text-sm text-white/40 font-medium">{formattedDate}</div>
                    </div>

                    {/* Greeting */}
                    <div className="text-center pb-6 px-8">
                        <h2 className="text-xl font-light text-white">
                            {greeting}, <span style={{ color: userProfile.accentColor }}>{userProfile.displayName || 'User'}</span>
                        </h2>
                        <p className="text-sm text-white/40 mt-1">Welcome to {osName}</p>
                    </div>

                    {/* Quick Actions Grid */}
                    <div className="px-8 pb-6">
                        <div className="grid grid-cols-4 gap-3">
                            {quickActions.map((qa) => (
                                <button
                                    key={qa.label}
                                    onClick={() => { qa.action(); setDismissed(true); }}
                                    className="flex flex-col items-center gap-2 p-4 rounded-2xl bg-white/[0.03] border border-white/5 hover:bg-white/[0.08] hover:border-white/15 transition-all group"
                                >
                                    <div
                                        className="w-12 h-12 rounded-xl flex items-center justify-center transition-transform group-hover:scale-110"
                                        style={{ backgroundColor: `${qa.color}15`, color: qa.color }}
                                    >
                                        {qa.icon}
                                    </div>
                                    <span className="text-xs text-white/50 group-hover:text-white/80 transition-colors">{qa.label}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Tip of the Day */}
                    <div className="mx-8 mb-6 p-4 rounded-xl bg-white/[0.03] border border-white/5 flex items-start gap-3">
                        <Lightbulb className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                        <div>
                            <div className="text-xs font-semibold text-white/50 mb-1 uppercase tracking-wider">Tip</div>
                            <p className="text-sm text-white/60 leading-relaxed">{tips[tipIndex]}</p>
                        </div>
                    </div>

                    {/* Dismiss */}
                    <div className="px-8 pb-8 flex items-center justify-between">
                        <div className="flex items-center gap-1.5 text-xs text-white/20">
                            <Grip className="w-3 h-3" />
                            <span>Drag items here to get started</span>
                        </div>
                        <button
                            onClick={() => setDismissed(true)}
                            className="flex items-center gap-1.5 text-sm text-white/40 hover:text-white transition-colors"
                        >
                            Dismiss <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
