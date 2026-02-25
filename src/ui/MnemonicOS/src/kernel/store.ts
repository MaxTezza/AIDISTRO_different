import { create } from 'zustand';
import { setSystemVolume, setBrightness, toggleWifi, toggleBluetooth, toggleNightMode, toggleDoNotDisturb } from '../native/api';

// --- User Profile ---
export interface UserProfile {
    displayName: string;
    hostname: string;
    timezone: string;
    theme: 'dark' | 'light';
    accentColor: string;
    privacyMode: 'standard' | 'strict' | 'paranoid';
}

// --- Theme Settings ---
export interface ThemeSettings {
    accentColor: string;
    blurStrength: number;
    windowOpacity: number;
    element3DStyle: 'wireframe' | 'toon' | 'glass' | 'metallic' | 'neon';
    windowAnimationConfig: 'spring' | 'tween' | 'none';
}

// --- Notification ---
export interface OSNotification {
    id: string;
    title: string;          // Plain language, no jargon
    body: string;           // Human-friendly description
    icon: string;           // Emoji
    category: 'email' | 'calendar' | 'system' | 'ai' | 'update';
    action?: { label: string; handler: string };  // One-tap action
    time: number;           // timestamp
    read: boolean;
    dismissed: boolean;
}

// --- Types ---
export type AppState = 'running' | 'background' | 'closed';
export type AppType = 'canvas' | 'media' | 'settings' | 'ai-chat' | 'terminal' | 'privacy-moat' | 'calendar' | 'weather' | 'email' | 'files' | 'theme-engine' | 'app-store' | 'driver-manager';

export interface MnemonicApp {
    id: string; // Unique instance ID
    type: AppType;
    title: string;
    state: AppState;
    bounds: { x: number; y: number; width: number; height: number };
    zIndex: number;
    data?: any; // App specific data
}

interface KernelState {
    apps: MnemonicApp[];
    activeAppId: string | null;
    historySnapshot: MnemonicApp[][];

    // Adaptive Complexity
    userProficiencyLevel: number; // 1 = Beginner, 2 = Standard, 3 = Power User

    // Liquid Computing
    showNetworkNode: boolean;

    // Invisible AI (Show, Don't Code)
    actionLog: { type: string; timestamp: number }[];
    automationSuggestion: string | null;

    // Phase 10: Onboarding & Guide
    hasCompletedOnboarding: boolean;
    isGuideOpen: boolean;
    userProfile: UserProfile;

    // Phase 4: Extreme 3D Customizability
    themeSettings: ThemeSettings;

    // Notifications
    notifications: OSNotification[];
    isNotificationPanelOpen: boolean;
    focusMode: boolean;

    // System Controls
    systemControls: {
        volume: number;         // 0-100
        brightness: number;     // 0-100
        wifi: boolean;
        bluetooth: boolean;
        nightMode: boolean;
        battery: number;        // 0-100 (simulated)
        doNotDisturb: boolean;
    };

    // Actions
    spawnApp: (type: AppType, initialData?: any, initialPos?: { x: number; y: number }) => string;
    closeApp: (id: string) => void;
    focusApp: (id: string) => void;
    updateAppBounds: (id: string, bounds: Partial<MnemonicApp['bounds']>) => void;

    // The "Time Travel" Feature
    takeSnapshot: () => void;
    rewindToSnapshot: (index: number) => void;

    // Adaptive Complexity Action
    setProficiencyLevel: (level: number) => void;

    // Liquid Computing Action
    toggleNetworkNode: () => void;

    // "Show, Don't Code" Actions
    clearAutomationSuggestion: () => void;
    executeMacro: (macroType: string) => void;

    // Phase 10 Actions
    completeOnboarding: () => void;
    toggleGuide: () => void;
    setUserProfile: (profile: Partial<UserProfile>) => void;

    // System Control Actions
    setVolume: (v: number) => void;
    setBrightness: (b: number) => void;
    toggleWifi: () => void;
    toggleBluetooth: () => void;
    toggleNightMode: () => void;
    toggleDoNotDisturb: () => void;

    // Notification Actions
    pushNotification: (notif: Omit<OSNotification, 'id' | 'time' | 'read' | 'dismissed'>) => void;
    dismissNotification: (id: string) => void;
    markNotificationRead: (id: string) => void;
    clearAllNotifications: () => void;
    toggleNotificationPanel: () => void;
    toggleFocusMode: () => void;

    // Theme Actions
    updateThemeSettings: (settings: Partial<ThemeSettings>) => void;

    // Mobile Bridge
    telegramToken: string | null;
    setTelegramToken: (token: string | null) => void;
}

const generateId = () => Math.random().toString(36).substring(2, 9);

type PersistedKernelState = Pick<
    KernelState,
    'userProficiencyLevel' | 'showNetworkNode' | 'hasCompletedOnboarding' | 'isGuideOpen' | 'userProfile' | 'notifications' | 'isNotificationPanelOpen' | 'focusMode' | 'systemControls' | 'themeSettings' | 'telegramToken'
>;

const PERSIST_KEY = 'mnemonicos_kernel_state_v1';

function getDefaultProfile(): UserProfile {
    return {
        displayName: '',
        hostname: 'mnemonic-os',
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
        theme: 'dark',
        accentColor: '#22d3ee',
        privacyMode: 'standard',
    };
}

function getDefaultSystemControls() {
    return {
        volume: 65,
        brightness: 80,
        wifi: true,
        bluetooth: true,
        nightMode: false,
        battery: 87,
        doNotDisturb: false,
    };
}

function getDefaultThemeSettings(): ThemeSettings {
    return {
        accentColor: '#22d3ee',
        blurStrength: 20,
        windowOpacity: 0.85,
        element3DStyle: 'glass',
        windowAnimationConfig: 'spring',
    };
}

function readPersistedState(): Partial<PersistedKernelState> {
    if (typeof window === 'undefined') return {};
    try {
        const raw = window.localStorage.getItem(PERSIST_KEY);
        if (!raw) return {};
        const parsed = JSON.parse(raw) as Partial<PersistedKernelState>;
        const staleSeedTitles = new Set([
            'Your Wi-Fi is connected',
            'New email from Coach Martinez',
            'Meeting in 2 hours',
            'Your system is up to date',
            'It might rain Thursday',
            'Open Enrollment closes Friday',
        ]);
        if (Array.isArray(parsed.notifications)) {
            parsed.notifications = parsed.notifications.filter((n) => !staleSeedTitles.has(n.title));
        }
        return parsed;
    } catch {
        return {};
    }
}

function writePersistedState(state: KernelState) {
    if (typeof window === 'undefined') return;
    const payload: PersistedKernelState = {
        userProficiencyLevel: state.userProficiencyLevel,
        showNetworkNode: state.showNetworkNode,
        hasCompletedOnboarding: state.hasCompletedOnboarding,
        isGuideOpen: state.isGuideOpen,
        userProfile: state.userProfile,
        notifications: state.notifications,
        isNotificationPanelOpen: state.isNotificationPanelOpen,
        focusMode: state.focusMode,
        systemControls: state.systemControls,
        themeSettings: state.themeSettings,
        telegramToken: state.telegramToken,
    };
    try {
        window.localStorage.setItem(PERSIST_KEY, JSON.stringify(payload));
    } catch {
        // Ignore storage write failures.
    }
}

const persisted = readPersistedState();

export const useKernelStore = create<KernelState>((set, get) => ({
    apps: [],
    activeAppId: null,
    historySnapshot: [],
    userProficiencyLevel: persisted.userProficiencyLevel ?? 2,
    showNetworkNode: persisted.showNetworkNode ?? false,

    // Adaptive behavior defaults
    actionLog: [],
    automationSuggestion: null,

    hasCompletedOnboarding: persisted.hasCompletedOnboarding ?? false,
    isGuideOpen: persisted.isGuideOpen ?? false,
    userProfile: persisted.userProfile ?? getDefaultProfile(),
    notifications: persisted.notifications ?? [],
    isNotificationPanelOpen: persisted.isNotificationPanelOpen ?? false,
    focusMode: persisted.focusMode ?? false,
    systemControls: persisted.systemControls ?? getDefaultSystemControls(),
    themeSettings: persisted.themeSettings ?? getDefaultThemeSettings(),
    telegramToken: persisted.telegramToken ?? null,

    spawnApp: (type, initialData, initialPos) => {
        const newId = generateId();
        const topZ = get().apps.length > 0 ? Math.max(...get().apps.map(a => a.zIndex)) + 1 : 1;

        // Default starting bounds
        const defaultBounds = {
            x: initialPos?.x ?? (window.innerWidth / 2 - 300 + (Math.random() * 40 - 20)),
            y: initialPos?.y ?? (window.innerHeight / 2 - 200 + (Math.random() * 40 - 20)),
            width: 600,
            height: 400
        };

        const newApp: MnemonicApp = {
            id: newId,
            type,
            title: type.charAt(0).toUpperCase() + type.slice(1).replace('-', ' '),
            state: 'running',
            bounds: defaultBounds,
            zIndex: topZ,
            data: initialData
        };

        get().takeSnapshot(); // Record state before change

        set((state) => ({
            apps: [...state.apps, newApp],
            activeAppId: newId
        }));

        return newId;
    },

    closeApp: (id) => {
        get().takeSnapshot();
        const now = Date.now();

        set((state) => {
            // Track the action
            const newLog = [...state.actionLog, { type: 'APP_CLOSE', timestamp: now }];
            // Keep log small
            if (newLog.length > 20) newLog.shift();

            // "Show, Don't Code" Pattern Detection
            // If the user closed 3 items in the last 15 seconds, and there are still apps open...
            const recentCloses = newLog.filter(log => log.type === 'APP_CLOSE' && (now - log.timestamp) < 15000);

            let suggestion = state.automationSuggestion;
            const remainingAppsCount = state.apps.length - 1; // Subtract the one being closed right now

            if (recentCloses.length >= 3 && remainingAppsCount > 0 && !suggestion) {
                suggestion = 'close_all';
            }

            return {
                apps: state.apps.filter(app => app.id !== id),
                activeAppId: state.activeAppId === id ? null : state.activeAppId,
                actionLog: newLog,
                automationSuggestion: suggestion
            };
        });
    },

    focusApp: (id) => {
        set((state) => {
            const highestZLevel = state.apps.length > 0 ? Math.max(...state.apps.map(a => a.zIndex)) : 0;
            return {
                apps: state.apps.map(app =>
                    app.id === id ? { ...app, zIndex: highestZLevel + 1 } : app
                ),
                activeAppId: id
            };
        });
    },

    updateAppBounds: (id, newBounds) => {
        set((state) => ({
            apps: state.apps.map(app =>
                app.id === id ? { ...app, bounds: { ...app.bounds, ...newBounds } } : app
            )
        }));
    },

    takeSnapshot: () => {
        set((state) => {
            // Keep only last 10 versions for memory sake
            const newHistory = [...state.historySnapshot, [...state.apps]];
            if (newHistory.length > 10) newHistory.shift();
            return { historySnapshot: newHistory };
        });
    },

    rewindToSnapshot: (index) => {
        set((state) => {
            if (index >= 0 && index < state.historySnapshot.length) {
                return {
                    apps: [...state.historySnapshot[index]],
                    historySnapshot: state.historySnapshot.slice(0, index) // erase future timelines
                };
            }
            return state;
        });
    },

    setProficiencyLevel: (level) => set({ userProficiencyLevel: Math.max(1, Math.min(3, level)) }),
    toggleNetworkNode: () => set((state) => ({ showNetworkNode: !state.showNetworkNode })),

    clearAutomationSuggestion: () => set({ automationSuggestion: null }),

    executeMacro: (macroType) => {
        if (macroType === 'close_all') {
            get().takeSnapshot();
            set({
                apps: [],
                activeAppId: null,
                automationSuggestion: null,
                actionLog: [] // Reset log so it doesn't immediately fire again
            });
        }
    },

    completeOnboarding: () => set({ hasCompletedOnboarding: true }),
    toggleGuide: () => set((state) => ({ isGuideOpen: !state.isGuideOpen })),
    setUserProfile: (profile) => set((state) => ({ userProfile: { ...state.userProfile, ...profile } })),

    // Notification Actions
    pushNotification: (notif) => {
        const newNotif: OSNotification = {
            ...notif,
            id: generateId(),
            time: Date.now(),
            read: false,
            dismissed: false,
        };
        set((state) => ({
            notifications: [newNotif, ...state.notifications].slice(0, 50) // Cap at 50
        }));
    },
    dismissNotification: (id) => set((state) => ({
        notifications: state.notifications.map(n => n.id === id ? { ...n, dismissed: true } : n)
    })),
    markNotificationRead: (id) => set((state) => ({
        notifications: state.notifications.map(n => n.id === id ? { ...n, read: true } : n)
    })),
    clearAllNotifications: () => set({ notifications: [] }),
    toggleNotificationPanel: () => set((state) => ({ isNotificationPanelOpen: !state.isNotificationPanelOpen })),
    toggleFocusMode: () => set((state) => ({ focusMode: !state.focusMode })),

    // System Control Actions
    setVolume: (v) => {
        setSystemVolume(v).catch(() => { });
        set((state) => ({
            systemControls: { ...state.systemControls, volume: Math.max(0, Math.min(100, v)) }
        }));
    },
    setBrightness: (b) => {
        setBrightness(b).catch(() => { });
        set((state) => ({
            systemControls: { ...state.systemControls, brightness: Math.max(10, Math.min(100, b)) }
        }));
    },
    toggleWifi: () => {
        toggleWifi().catch(() => { });
        set((state) => ({
            systemControls: { ...state.systemControls, wifi: !state.systemControls.wifi }
        }));
    },
    toggleBluetooth: () => {
        toggleBluetooth().catch(() => { });
        set((state) => ({
            systemControls: { ...state.systemControls, bluetooth: !state.systemControls.bluetooth }
        }));
    },
    toggleNightMode: () => {
        toggleNightMode().catch(() => { });
        set((state) => ({
            systemControls: { ...state.systemControls, nightMode: !state.systemControls.nightMode }
        }));
    },
    toggleDoNotDisturb: () => {
        toggleDoNotDisturb().catch(() => { });
        set((state) => ({
            systemControls: { ...state.systemControls, doNotDisturb: !state.systemControls.doNotDisturb }
        }));
    }, // <-- Notice the comma added here

    // Theme Actions
    updateThemeSettings: (settings) => set((state) => ({
        themeSettings: { ...state.themeSettings, ...settings }
    })),

    // Mobile Bridge
    setTelegramToken: (token) => set({ telegramToken: token }),
}));

useKernelStore.subscribe((state) => {
    writePersistedState(state);
});
