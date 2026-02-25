import React from 'react';
import { useKernelStore } from '../kernel/store';
import { WindowPanel } from '../components/WindowPanel';
import { BrainCircuit, Image, AlertTriangle, Smartphone } from 'lucide-react';
import { PrivacyMoatApp } from './PrivacyMoatApp';
import { OnboardingWizard } from '../shell/OnboardingWizard';
import { MnemonicGuide } from '../shell/MnemonicGuide';
import { DesktopWidgets } from '../shell/DesktopWidgets';
import { CalendarApp } from '../apps/CalendarApp';
import { WeatherApp } from '../apps/WeatherApp';
import { EmailApp } from '../apps/EmailApp';
import { FileManagerApp } from '../apps/FileManagerApp';
import { ThemeEngineApp } from '../apps/ThemeEngineApp';
import { AppStoreApp } from '../apps/AppStoreApp';
import { DriverManagerApp } from '../apps/DriverManagerApp';
import { NotificationToast, NotificationPanel, useNotificationSeeder } from '../shell/NotificationCenter';
import { AppLauncherProvider } from '../shell/AppLauncher';
import { getMediaFiles, runTerminalCommand, saveCanvas, setSystemVolume, toggleSystemMute } from '../native/api';

const TerminalApp: React.FC = () => {
    const [history, setHistory] = React.useState<{ type: 'input' | 'output', text: string }[]>([]);
    const [input, setInput] = React.useState('');
    const bottomRef = React.useRef<HTMLDivElement>(null);

    React.useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [history]);

    const handleKeyDown = async (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && input.trim()) {
            const cmd = input.trim();
            setInput('');
            setHistory(prev => [...prev, { type: 'input', text: `user@mnemonicos:~$ ${cmd}` }]);

            try {
                const output = await runTerminalCommand(cmd);
                setHistory(prev => [...prev, { type: 'output', text: output }]);
            } catch (err: any) {
                setHistory(prev => [...prev, { type: 'output', text: `Error: ${err}` }]);
            }
        }
    };

    return (
        <div className="h-full bg-[#1e1e1e] p-4 font-mono text-sm overflow-y-auto flex flex-col rounded-b-xl border-t border-white/10" onClick={() => document.getElementById('terminal-input')?.focus()}>
            <div className="text-emerald-400 mb-2">Mnemonic OS Native Terminal Proxy</div>
            {history.map((h, i) => (
                <div key={i} className={`mb-1 whitespace-pre-wrap ${h.type === 'input' ? 'text-emerald-400' : 'text-white/80'}`}>
                    {h.text}
                </div>
            ))}
            <div className="flex text-emerald-400 mt-2">
                <span className="mr-2">user@mnemonicos:~$</span>
                <input
                    id="terminal-input"
                    type="text"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    className="flex-1 bg-transparent outline-none border-none text-white/90"
                    autoFocus
                    autoComplete="off"
                />
            </div>
            <div ref={bottomRef} />
        </div>
    );
};

const CanvasApp: React.FC<{ initialText?: string }> = ({ initialText }) => {
    const [text, setText] = React.useState(initialText || '');
    const [saving, setSaving] = React.useState(false);

    const handleSave = async () => {
        setSaving(true);
        try {
            await saveCanvas(text);
        } catch (err) {
            console.error("Failed to save to canvas:", err);
        }
        setSaving(false);
    };

    return (
        <div className="h-full p-4 flex flex-col gap-4">
            <div className="flex justify-between items-center">
                <h3 className="text-2xl font-light text-white font-serif">Universal Document Canvas</h3>
                <button onClick={handleSave} className="px-3 py-1 bg-white/10 hover:bg-white/20 transition-colors rounded text-xs">
                    {saving ? 'Saving...' : 'Save to Disk'}
                </button>
            </div>
            <p className="text-white/70">
                A fluid workspace breaking the traditional "App" boundaries.
            </p>
            <div className="flex-1 border-2 border-dashed border-white/20 rounded-xl overflow-hidden flex items-center justify-center bg-white/5 hover:bg-white/10 transition-colors p-4 group relative">
                <textarea
                    className="w-full h-full bg-transparent border-none outline-none resize-none text-white/90 placeholder-white/30"
                    placeholder="Type or drop content here to persist to native system..."
                    value={text}
                    onChange={e => setText(e.target.value)}
                    onBlur={handleSave}
                />
            </div>
        </div>
    );
};

const MediaApp: React.FC = () => {
    const [images, setImages] = React.useState<string[]>([]);
    const [loading, setLoading] = React.useState(true);

    React.useEffect(() => {
        const fetchMedia = async () => {
            try {
                const result = await getMediaFiles();
                setImages(result);
            } catch (err) {
                console.error("Failed to fetch media:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchMedia();
    }, []);

    return (
        <div className="h-full flex flex-col gap-2 relative overflow-y-auto overflow-x-hidden p-2">
            <div className="absolute top-0 right-0 p-2 text-xs bg-black/40 rounded-bl-lg backdrop-blur text-white/50 z-10">Host Directory: ~/Pictures</div>

            {loading ? (
                <div className="flex-1 flex items-center justify-center text-white/50 animate-pulse">Scanning Native Filesystem...</div>
            ) : images.length > 0 ? (
                <div className="grid grid-cols-2 gap-2 flex-1">
                    {images.map((src, idx) => (
                        <div key={idx} className={`bg-white/5 rounded-lg overflow-hidden flex items-center justify-center shadow-inner ${idx % 3 === 2 ? 'col-span-2' : ''}`}>
                            <img src={src} alt="Host Media" className="w-full h-full object-cover rounded-lg" />
                        </div>
                    ))}
                </div>
            ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-white/50 gap-2">
                    <Image className="w-8 h-8 opacity-50" />
                    <span>No images found in ~/Pictures</span>
                </div>
            )}
        </div>
    );
};

const SettingsApp: React.FC = () => {
    const [input, setInput] = React.useState('');
    const [feedback, setFeedback] = React.useState<string | null>(null);
    const { telegramToken, setTelegramToken } = useKernelStore();
    const [tempToken, setTempToken] = React.useState(telegramToken || '');
    const [bridgeStatus, setBridgeStatus] = React.useState<'disconnected' | 'connecting' | 'connected'>('disconnected');

    React.useEffect(() => {
        if (telegramToken && bridgeStatus === 'disconnected') {
            startBridge(telegramToken);
        }
    }, [telegramToken]);

    const startBridge = async (token: string) => {
        setBridgeStatus('connecting');
        try {
            await runTerminalCommand(`python3 /home/jmt3/AI_Distro/tools/shell/chatbot_bridge.py --token ${token} &`);
            setBridgeStatus('connected');
        } catch (err) {
            console.error("Failed to start bridge", err);
            setBridgeStatus('disconnected');
        }
    };

    const handleKeyDown = async (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && input.trim()) {
            const query = input.trim().toLowerCase();
            setInput('');

            let responseMsg = '';
            if (query.includes('mute') || query.includes('unmute') || query.includes('silence')) {
                responseMsg = 'Hardware audio mute toggled';
                try {
                    await toggleSystemMute();
                } catch (err) {
                    console.error("Hardware API error:", err);
                    setFeedback("Failed to toggle hardware mute.");
                    return;
                }
            } else if (query.includes('volume') && /\d+/.test(query)) {
                const match = query.match(/\d+/);
                if (match) {
                    try {
                        await setSystemVolume(Number(match[0]));
                        responseMsg = `Hardware audio volume set to ${match[0]}%`;
                    } catch (err) {
                        console.error("Hardware API error:", err);
                        setFeedback("Failed to set hardware volume.");
                        return;
                    }
                }
            } else {
                responseMsg = 'Intent not mapped to local hardware APIs yet.';
            }

            setFeedback(responseMsg);

            setTimeout(() => setFeedback(null), 4000);
        }
    };

    return (
        <div className="h-full flex flex-col pt-4 relative">
            <div className="text-center mb-6">
                <h3 className="text-xl font-medium mb-1">Natural Language System Settings</h3>
                <p className="text-sm text-white/40">Try: "Mute the audio" or "Set volume to 50"</p>
            </div>

            <div className="bg-black/30 rounded-xl p-2 mx-4 border border-white/10 focus-within:border-accent transition-colors flex items-center gap-2">
                <input
                    type="text"
                    onChange={(e) => setInput(e.target.value)}
                    value={input}
                    onKeyDown={handleKeyDown}
                    placeholder="e.g. My screen is entirely too bright"
                    className="bg-transparent border-none outline-none w-full text-white px-2 placeholder-white/30"
                />
            </div>

            {feedback && (
                <div className="mx-4 mt-4 text-center animate-in fade-in slide-in-from-bottom-2 duration-300">
                    <span className="bg-accent/20 text-accent px-4 py-2 rounded-full text-sm font-medium border border-accent/40 shadow-[0_0_15px_rgba(34,211,238,0.3)]">
                        {feedback}
                    </span>
                </div>
            )}

            <div className="mt-auto p-4 flex flex-col gap-4">
                <div className="flex flex-col gap-2 p-4 bg-white/5 border border-white/10 rounded-xl">
                    <h4 className="text-sm font-bold text-white flex items-center gap-2">
                        <Smartphone className="w-4 h-4 text-blue-400" /> Mobile Chatbot Bridge
                    </h4>
                    <p className="text-xs text-white/50 mb-2">Connect Telegram to control MnemonicOS remotely.</p>
                    <div className="flex items-center gap-2">
                        <input
                            type="password"
                            value={tempToken}
                            onChange={e => setTempToken(e.target.value)}
                            placeholder="Telegram Bot Token"
                            className="flex-1 bg-black/40 border border-white/10 rounded-lg py-1.5 px-3 text-xs text-white focus:border-blue-400 focus:outline-none transition-colors"
                        />
                        <button
                            onClick={() => {
                                setTelegramToken(tempToken);
                                startBridge(tempToken);
                            }}
                            className="px-3 py-1.5 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 text-xs font-bold rounded-lg transition-colors border border-blue-500/20 whitespace-nowrap"
                        >
                            {bridgeStatus === 'connected' ? 'Connected' : bridgeStatus === 'connecting' ? 'Connecting...' : 'Connect'}
                        </button>
                    </div>
                </div>

                <div className="flex items-center justify-center gap-2 text-yellow-400 opacity-80 bg-yellow-400/10 rounded-lg mb-4 p-2">
                    <AlertTriangle className="w-5 h-5" />
                    <span className="text-sm">No classic Control Panel found. Pure intent driven.</span>
                </div>
            </div>
        </div>
    );
};

export const AppCanvas: React.FC = () => {
    const { apps, activeAppId, focusApp, closeApp, spawnApp, updateAppBounds } = useKernelStore();

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault(); // Allow drops
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        const x = e.clientX;
        const y = e.clientY - 20; // Offset slightly so cursor isn't exactly at corner

        // 1. Check for files from local filesystem drag/drop
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file.type.startsWith('image/')) {
                spawnApp('media', { fileName: file.name }, { x, y });
            } else {
                spawnApp('canvas', { text: `Dropped File: ${file.name}` }, { x, y });
            }
            return;
        }

        // 2. Check for text/HTML (browser drag)
        const textData = e.dataTransfer.getData('text');
        if (textData) {
            spawnApp('canvas', { text: textData }, { x, y });
            return;
        }

        // Fallback
        spawnApp('canvas', { text: 'Empty Object Dropped' }, { x, y });
    };

    const renderAppContent = (type: string, data?: any) => {
        switch (type) {
            case 'ai-chat':
                return (
                    <div className="h-full flex flex-col items-center justify-center text-center gap-4">
                        <BrainCircuit className="w-16 h-16 text-accent animate-pulse" />
                        <h3 className="text-xl font-bold">Intent Executed</h3>
                        <p className="text-white/60">
                            The Mnemonic OS would typically resolve:<br />
                            <strong className="text-white text-lg">"{data?.query || 'No query'}"</strong>
                        </p>
                        <p className="text-sm mt-4 text-green-400 bg-green-500/20 px-4 py-2 rounded-lg border border-green-500/30">
                            Issue diagnosed and fixed silently in background.
                        </p>
                    </div>
                );
            case 'canvas':
                return <CanvasApp initialText={data?.text} />;
            case 'media':
                return <MediaApp />;
            case 'settings':
                return <SettingsApp />;
            case 'privacy-moat':
                return <PrivacyMoatApp />;
            case 'terminal':
                return <TerminalApp />;
            case 'calendar':
                return <CalendarApp />;
            case 'weather':
                return <WeatherApp />;
            case 'email':
                return <EmailApp />;
            case 'files':
                return <FileManagerApp />;
            case 'theme-engine':
                return <ThemeEngineApp />;
            case 'app-store':
                return <AppStoreApp />;
            case 'driver-manager':
                return <DriverManagerApp />;
            default:
                return <div>Generic Placeholder for {type}</div>;
        }
    };

    // Seed notifications after onboarding
    useNotificationSeeder();

    return (
        <AppLauncherProvider>
            <OnboardingWizard />
            <MnemonicGuide />
            <NotificationPanel />
            <NotificationToast />
            <DesktopWidgets />
            <div
                className="absolute inset-0 pointer-events-auto z-10"
                onDragOver={handleDragOver}
                onDrop={handleDrop}
            >
                {/* The invisible drop-catcher background */}
                <div className="absolute inset-0 z-0 bg-transparent" onClick={() => { }} />

                {apps.map((app) => (
                    <div key={app.id} className="pointer-events-auto absolute" style={{ zIndex: app.zIndex }}>
                        <WindowPanel
                            id={app.id}
                            title={app.title}
                            x={app.bounds.x}
                            y={app.bounds.y}
                            width={app.bounds.width}
                            height={app.bounds.height}
                            isActive={app.id === activeAppId}
                            onFocus={() => focusApp(app.id)}
                            onClose={() => closeApp(app.id)}
                            onUpdateBounds={(bounds) => updateAppBounds(app.id, bounds)}
                        >
                            {renderAppContent(app.type, app.data)}
                        </WindowPanel>
                    </div>
                ))}
            </div>
        </AppLauncherProvider>
    );
};
