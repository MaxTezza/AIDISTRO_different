import React, { useEffect, useState } from 'react';
import { useKernelStore, type OSNotification } from '../kernel/store';
import { Bell, X, Moon, Sun, Sparkles, Mail, CalendarDays, Shield, Cpu } from 'lucide-react';

// ─── Notification Generator ──────────────────────────────
// After onboarding, the OS generates smart, contextual notifications
// in plain language with actionable solutions

function generateInitialNotifications(): Omit<OSNotification, 'id' | 'time' | 'read' | 'dismissed'>[] {
    return [];
}

// ─── Toast Popup ─────────────────────────────────────────
// Brief, non-intrusive popup that slides in and auto-dismisses

export const NotificationToast: React.FC = () => {
    const { notifications, focusMode, dismissNotification, markNotificationRead } = useKernelStore();
    const [visibleToast, setVisibleToast] = useState<OSNotification | null>(null);
    const [fadingOut, setFadingOut] = useState(false);

    useEffect(() => {
        if (focusMode) return;
        const unread = notifications.filter(n => !n.read && !n.dismissed);
        if (unread.length > 0 && !visibleToast) {
            const latest = unread[0];
            setVisibleToast(latest);
            markNotificationRead(latest.id);

            // Auto-dismiss after 5 seconds
            const timer = setTimeout(() => {
                setFadingOut(true);
                setTimeout(() => {
                    setVisibleToast(null);
                    setFadingOut(false);
                }, 300);
            }, 5000);

            return () => clearTimeout(timer);
        }
    }, [notifications, focusMode]);

    if (!visibleToast) return null;

    return (
        <div className={`fixed top-6 right-6 z-[200] w-80 transition-all duration-300 ${fadingOut ? 'opacity-0 translate-y-[-10px]' : 'opacity-100 animate-in slide-in-from-right-5 fade-in'}`}>
            <div className="bg-black/90 backdrop-blur-2xl border border-white/15 rounded-2xl p-4 shadow-[0_10px_40px_rgba(0,0,0,0.6)]">
                <div className="flex items-start gap-3">
                    <span className="text-xl mt-0.5">{visibleToast.icon}</span>
                    <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-white mb-0.5">{visibleToast.title}</div>
                        <div className="text-xs text-white/50 leading-relaxed">{visibleToast.body}</div>
                        {visibleToast.action && (
                            <button
                                onClick={() => {
                                    handleAction(visibleToast.action!.handler);
                                    dismissNotification(visibleToast.id);
                                    setVisibleToast(null);
                                }}
                                className="mt-2 px-3 py-1.5 bg-cyan-500/20 text-cyan-300 text-xs font-medium rounded-lg hover:bg-cyan-500/30 transition-colors"
                            >
                                {visibleToast.action.label}
                            </button>
                        )}
                    </div>
                    <button
                        onClick={() => {
                            dismissNotification(visibleToast.id);
                            setVisibleToast(null);
                        }}
                        className="text-white/20 hover:text-white/50 transition-colors p-0.5"
                    >
                        <X className="w-3.5 h-3.5" />
                    </button>
                </div>
            </div>
        </div>
    );
};

// ─── Notification Panel ──────────────────────────────────
// Full notification center, slides in from right

export const NotificationPanel: React.FC = () => {
    const {
        notifications, isNotificationPanelOpen, focusMode,
        toggleNotificationPanel, toggleFocusMode,
        dismissNotification, markNotificationRead, clearAllNotifications,
        spawnApp
    } = useKernelStore();

    if (!isNotificationPanelOpen) return null;

    const active = notifications.filter(n => !n.dismissed);
    const unreadCount = active.filter(n => !n.read).length;

    const categoryIcon = (cat: OSNotification['category']) => {
        switch (cat) {
            case 'email': return <Mail className="w-3 h-3" />;
            case 'calendar': return <CalendarDays className="w-3 h-3" />;
            case 'system': return <Shield className="w-3 h-3" />;
            case 'ai': return <Sparkles className="w-3 h-3" />;
            case 'update': return <Cpu className="w-3 h-3" />;
        }
    };

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 z-[140] bg-black/20 backdrop-blur-sm"
                onClick={toggleNotificationPanel}
            />
            {/* Panel */}
            <div className="fixed top-0 right-0 bottom-0 w-96 z-[145] bg-black/95 backdrop-blur-2xl border-l border-white/10 shadow-[-10px_0_40px_rgba(0,0,0,0.5)] flex flex-col animate-in slide-in-from-right duration-300">
                {/* Header */}
                <div className="p-5 border-b border-white/8 flex items-center justify-between">
                    <div>
                        <h2 className="text-base font-semibold text-white">Notifications</h2>
                        {unreadCount > 0 && (
                            <span className="text-xs text-white/30">{unreadCount} new</span>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                        {/* Focus Mode Toggle */}
                        <button
                            onClick={toggleFocusMode}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${focusMode
                                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                                : 'bg-white/[0.04] text-white/40 border border-white/8 hover:text-white/60'
                                }`}
                            title={focusMode ? 'Focus mode is on — notifications are paused' : 'Turn on focus mode'}
                        >
                            {focusMode ? <Moon className="w-3 h-3" /> : <Sun className="w-3 h-3" />}
                            {focusMode ? 'Focus On' : 'Focus'}
                        </button>
                        <button
                            onClick={toggleNotificationPanel}
                            className="p-1.5 rounded-lg text-white/30 hover:text-white/60 hover:bg-white/10 transition-colors"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                </div>

                {/* Notifications List */}
                <div className="flex-1 overflow-y-auto">
                    {active.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full text-white/20">
                            <Bell className="w-10 h-10 mb-3" />
                            <p className="text-sm">All clear — nothing needs your attention</p>
                        </div>
                    ) : (
                        <div className="p-3 space-y-2">
                            {active.map(notif => (
                                <div
                                    key={notif.id}
                                    className={`p-4 rounded-xl border transition-all ${notif.read
                                        ? 'bg-white/[0.02] border-white/5'
                                        : 'bg-white/[0.04] border-white/10'
                                        }`}
                                    onClick={() => markNotificationRead(notif.id)}
                                >
                                    <div className="flex items-start gap-3">
                                        <span className="text-lg mt-0.5">{notif.icon}</span>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-0.5">
                                                <span className={`text-sm font-medium ${notif.read ? 'text-white/50' : 'text-white'}`}>
                                                    {notif.title}
                                                </span>
                                                {!notif.read && (
                                                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0" />
                                                )}
                                            </div>
                                            <p className="text-xs text-white/40 leading-relaxed mb-2">{notif.body}</p>

                                            {/* Solution / Action button */}
                                            {notif.action && (
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        handleAction(notif.action!.handler, spawnApp);
                                                        dismissNotification(notif.id);
                                                    }}
                                                    className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-500/15 text-cyan-300 text-xs font-medium rounded-lg hover:bg-cyan-500/25 transition-colors border border-cyan-500/20"
                                                >
                                                    <Sparkles className="w-3 h-3" />
                                                    {notif.action.label}
                                                </button>
                                            )}

                                            <div className="flex items-center gap-2 mt-2 text-[10px] text-white/20">
                                                <span className="flex items-center gap-1">
                                                    {categoryIcon(notif.category)}
                                                    {notif.category}
                                                </span>
                                                <span>·</span>
                                                <span>{formatTimeAgo(notif.time)}</span>
                                            </div>
                                        </div>
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                dismissNotification(notif.id);
                                            }}
                                            className="text-white/15 hover:text-white/40 transition-colors p-1"
                                            title="Dismiss"
                                        >
                                            <X className="w-3 h-3" />
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer */}
                {active.length > 0 && (
                    <div className="p-4 border-t border-white/8">
                        <button
                            onClick={clearAllNotifications}
                            className="w-full py-2 text-xs text-white/30 hover:text-white/50 transition-colors"
                        >
                            Clear all
                        </button>
                    </div>
                )}
            </div>
        </>
    );
};

// ─── Notification Bell (Taskbar) ─────────────────────────

export const NotificationBell: React.FC = () => {
    const { notifications, toggleNotificationPanel, focusMode } = useKernelStore();
    const unreadCount = notifications.filter(n => !n.read && !n.dismissed).length;

    return (
        <div className="relative">
            <button
                onClick={toggleNotificationPanel}
                className={`p-3 rounded-lg transition-colors ${focusMode
                    ? 'text-purple-400 hover:bg-purple-500/10'
                    : 'hover:bg-white/10 text-white/70 hover:text-white'
                    }`}
                title={focusMode ? 'Focus mode — notifications paused' : 'Notifications'}
            >
                <Bell className="w-6 h-6" />
            </button>
            {unreadCount > 0 && !focusMode && (
                <span className="absolute top-1.5 right-1.5 min-w-[16px] h-4 px-1 bg-cyan-400 text-black text-[9px] font-bold rounded-full flex items-center justify-center">
                    {unreadCount}
                </span>
            )}
            {focusMode && (
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-purple-400 rounded-full" />
            )}
        </div>
    );
};

// ─── Notification Seeder ─────────────────────────────────
// Hook to seed notifications after onboarding

export const useNotificationSeeder = () => {
    const { hasCompletedOnboarding, notifications, pushNotification } = useKernelStore();
    const [seeded, setSeeded] = useState(false);

    useEffect(() => {
        if (hasCompletedOnboarding && !seeded && notifications.length === 0) {
            setSeeded(true);
            const initial = generateInitialNotifications();
            // Stagger the notifications to feel natural
            initial.forEach((notif, i) => {
                setTimeout(() => pushNotification(notif), 1000 + i * 2000);
            });
        }
    }, [hasCompletedOnboarding, seeded]);
};

// ─── Helpers ─────────────────────────────────────────────

function handleAction(handler: string, spawnApp?: (type: any) => void) {
    const spawn = spawnApp || useKernelStore.getState().spawnApp;
    switch (handler) {
        case 'update_calendar_soccer':
            // AI "handles it" — just acknowledge
            useKernelStore.getState().pushNotification({
                title: 'Calendar updated',
                body: 'I moved soccer practice to Field B. Everything else on your schedule stays the same.',
                icon: '✅',
                category: 'ai',
            });
            break;
        case 'set_reminder_standup':
            useKernelStore.getState().pushNotification({
                title: 'Reminder set',
                body: 'I\'ll remind you 5 minutes before your Team Standup at 8:55 AM.',
                icon: '⏰',
                category: 'ai',
            });
            break;
        case 'open_calendar':
            spawn('calendar');
            break;
        case 'open_email_hr':
            spawn('email');
            break;
        default:
            break;
    }
}

function formatTimeAgo(timestamp: number): string {
    const diff = Math.floor((Date.now() - timestamp) / 1000);
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
}
