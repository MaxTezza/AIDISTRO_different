import React, { useState, useEffect } from 'react';
import { useKernelStore } from '../kernel/store';
import {
    getCurrentWeather, getConditionMeta, getTodayEvents, getEmails, getUnreadCount, getDailyInsight, refreshWeather,
    type CalendarEvent
} from '../kernel/dataServices';
import {
    CloudSun, CalendarDays, Mail, Sparkles, ArrowRight,
    MapPin, Clock, ChevronRight
} from 'lucide-react';
import { FloatingAssistant3D, ResourceMonitor3D } from '../components/Interactive3DWidgets';

export const DesktopWidgets: React.FC = () => {
    const { userProfile, hasCompletedOnboarding, spawnApp, toggleGuide, apps } = useKernelStore();
    const [time, setTime] = useState(new Date());

    useEffect(() => {
        const timer = setInterval(() => setTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    useEffect(() => {
        refreshWeather().then(() => setTime(new Date())).catch(() => { });
    }, []);

    if (!hasCompletedOnboarding) return null;

    // Hide when apps are open
    const hasOpenApps = apps.some(a => a.state === 'running');
    if (hasOpenApps) return null;

    const weather = getCurrentWeather();
    const condMeta = getConditionMeta(weather.condition);
    const events = getTodayEvents();
    const unreadCount = getUnreadCount();
    const insight = getDailyInsight();

    const formattedTime = time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const formattedDate = time.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' });

    const greeting = (() => {
        const h = time.getHours();
        if (h < 12) return 'Good morning';
        if (h < 18) return 'Good afternoon';
        return 'Good evening';
    })();

    const accentColor = userProfile.accentColor || '#22d3ee';

    return (
        <div className="absolute inset-0 z-20 flex items-center justify-center pointer-events-none">
            <div className="pointer-events-auto w-full max-w-4xl mx-6">

                {/* Header — Clock + Greeting + 3D Monitor */}
                <div className="flex items-center justify-between mb-8">
                    <div className="flex-1 text-center">
                        <div className="text-7xl font-extralight text-white tracking-tight mb-1 drop-shadow-lg flex items-center justify-center gap-6">
                            {formattedTime}
                        </div>
                        <div className="text-base text-white/40 font-medium">{formattedDate}</div>
                        <h2 className="text-lg font-light text-white/60 mt-2">
                            {greeting}, <span style={{ color: accentColor }}>{userProfile.displayName || 'User'}</span>
                        </h2>
                    </div>
                </div>

                {/* 3D System Resource Monitor (Top Right) */}
                <div className="absolute top-8 right-8 mix-blend-screen drop-shadow-lg z-0">
                    <ResourceMonitor3D />
                </div>

                {/* Widget Grid */}
                <div className="grid grid-cols-3 gap-4">

                    {/* ── Weather Widget ── */}
                    <button
                        onClick={() => spawnApp('weather')}
                        className="bg-white/[0.04] backdrop-blur-2xl border border-white/10 rounded-2xl p-5 text-left hover:bg-white/[0.07] hover:border-white/15 transition-all group cursor-pointer"
                    >
                        <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2 text-white/40 text-xs font-semibold uppercase tracking-wider">
                                <CloudSun className="w-3.5 h-3.5" /> Weather
                            </div>
                            <ChevronRight className="w-3.5 h-3.5 text-white/20 group-hover:text-white/40 transition-colors" />
                        </div>
                        <div className="flex items-center gap-3 mb-3">
                            <span className="text-4xl">{condMeta.icon}</span>
                            <div>
                                <div className="text-3xl font-light text-white">{weather.temp}°</div>
                                <div className="text-xs text-white/40">{condMeta.label}</div>
                            </div>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-white/30">
                            <span>H: {weather.high}°</span>
                            <span>L: {weather.low}°</span>
                            <span>Feels {weather.feelsLike}°</span>
                        </div>
                        <p className="text-xs text-white/40 mt-2 leading-relaxed">{weather.description}</p>
                    </button>

                    {/* ── Calendar Widget ── */}
                    <button
                        onClick={() => spawnApp('calendar')}
                        className="bg-white/[0.04] backdrop-blur-2xl border border-white/10 rounded-2xl p-5 text-left hover:bg-white/[0.07] hover:border-white/15 transition-all group cursor-pointer"
                    >
                        <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2 text-white/40 text-xs font-semibold uppercase tracking-wider">
                                <CalendarDays className="w-3.5 h-3.5" /> Today
                            </div>
                            <span className="text-xs px-2 py-0.5 rounded-full text-white/60" style={{ backgroundColor: `${accentColor}30` }}>
                                {events.length} events
                            </span>
                        </div>
                        <div className="space-y-2.5">
                            {events.slice(0, 3).map(evt => (
                                <EventRow key={evt.id} event={evt} />
                            ))}
                            {events.length > 3 && (
                                <div className="text-xs text-white/30 flex items-center gap-1">
                                    +{events.length - 3} more <ChevronRight className="w-3 h-3" />
                                </div>
                            )}
                        </div>
                    </button>

                    {/* ── Email Widget ── */}
                    <button
                        onClick={() => spawnApp('email')}
                        className="bg-white/[0.04] backdrop-blur-2xl border border-white/10 rounded-2xl p-5 text-left hover:bg-white/[0.07] hover:border-white/15 transition-all group cursor-pointer"
                    >
                        <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2 text-white/40 text-xs font-semibold uppercase tracking-wider">
                                <Mail className="w-3.5 h-3.5" /> Inbox
                            </div>
                            {unreadCount > 0 && (
                                <span
                                    className="text-xs font-bold px-2 py-0.5 rounded-full text-black"
                                    style={{ backgroundColor: accentColor }}
                                >
                                    {unreadCount}
                                </span>
                            )}
                        </div>
                        <div className="space-y-2.5">
                            {getEmails().filter(e => !e.read).slice(0, 3).map(mail => (
                                <div key={mail.id} className="flex items-start gap-2">
                                    <div
                                        className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold text-white shrink-0 mt-0.5"
                                        style={{ backgroundColor: stringToColor(mail.from) }}
                                    >
                                        {mail.from[0]}
                                    </div>
                                    <div className="min-w-0">
                                        <div className="text-xs text-white/70 font-medium truncate">{mail.from}</div>
                                        <div className="text-xs text-white/35 truncate">{mail.subject}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </button>
                </div>

                {/* ── AI Insight Banner with 3D Assistant ── */}
                <div className="mt-4 relative group w-full">
                    {/* The 3D Floating Assistant Avatar */}
                    <div className="absolute -top-16 -left-12 z-10 transition-transform duration-500 hover:scale-110 drop-shadow-xl">
                        <FloatingAssistant3D />
                    </div>

                    <button
                        onClick={() => toggleGuide()}
                        className="w-full bg-white/[0.03] backdrop-blur-xl border border-white/8 rounded-2xl pl-24 pr-5 py-4 flex items-center gap-4 hover:bg-white/[0.06] transition-all cursor-pointer relative z-0 overflow-hidden"
                    >
                        <div className="flex-1 text-left relative z-10">
                            <p className="text-sm text-white/70 font-medium leading-relaxed">{insight.message}</p>
                        </div>
                        <div className="flex items-center gap-1.5 text-xs text-white/30 group-hover:text-white/50 transition-colors shrink-0 relative z-10">
                            <Sparkles className="w-3.5 h-3.5" style={{ color: accentColor }} />
                            Ask me anything
                            <ArrowRight className="w-3 h-3" />
                        </div>
                    </button>
                </div>
            </div>
        </div>
    );
};

// ─── Sub-components ───────────────────────────────────────

const EventRow: React.FC<{ event: CalendarEvent }> = ({ event }) => (
    <div className="flex items-center gap-2.5">
        <div className="w-0.5 h-8 rounded-full" style={{ backgroundColor: event.color }} />
        <div className="min-w-0 flex-1">
            <div className="text-xs text-white/70 font-medium truncate">{event.title}</div>
            <div className="flex items-center gap-2 text-[10px] text-white/35">
                <span className="flex items-center gap-0.5">
                    <Clock className="w-2.5 h-2.5" /> {event.time}
                </span>
                {event.location && (
                    <span className="flex items-center gap-0.5 truncate">
                        <MapPin className="w-2.5 h-2.5" /> {event.location}
                    </span>
                )}
            </div>
        </div>
    </div>
);

// Helpers
function stringToColor(str: string): string {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    const hue = Math.abs(hash % 360);
    return `hsl(${hue}, 50%, 40%)`;
}
