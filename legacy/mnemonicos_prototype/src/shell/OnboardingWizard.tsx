import React, { useState } from 'react';
import { useKernelStore } from '../kernel/store';
import type { UserProfile } from '../kernel/store';
import {
    Sparkles, Globe, User, Palette, ShieldCheck, Rocket,
    ArrowRight, ArrowLeft, Check, Monitor, Sun, Moon,
    Bot, Download
} from 'lucide-react';

const TIMEZONES = [
    'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
    'America/Anchorage', 'Pacific/Honolulu', 'America/Phoenix',
    'America/Toronto', 'America/Vancouver', 'America/Mexico_City',
    'Europe/London', 'Europe/Paris', 'Europe/Berlin', 'Europe/Moscow',
    'Asia/Tokyo', 'Asia/Shanghai', 'Asia/Kolkata', 'Asia/Dubai',
    'Australia/Sydney', 'Pacific/Auckland', 'Africa/Cairo', 'Africa/Lagos',
    'America/Sao_Paulo', 'America/Argentina/Buenos_Aires',
];

const ACCENT_COLORS = [
    { name: 'Cyan', hex: '#22d3ee' },
    { name: 'Violet', hex: '#8b5cf6' },
    { name: 'Rose', hex: '#f43f5e' },
    { name: 'Amber', hex: '#f59e0b' },
    { name: 'Emerald', hex: '#10b981' },
    { name: 'Sky', hex: '#0ea5e9' },
    { name: 'Pink', hex: '#ec4899' },
    { name: 'Orange', hex: '#f97316' },
];

const TOTAL_STEPS = 8;

export const OnboardingWizard: React.FC = () => {
    const { completeOnboarding, setProficiencyLevel, setUserProfile, hasCompletedOnboarding } = useKernelStore();
    const [step, setStep] = useState(1);

    // Local form state
    const [displayName, setDisplayName] = useState('');
    const [hostname, setHostname] = useState('mnemonic-os');
    const [timezone, setTimezone] = useState(
        Intl.DateTimeFormat().resolvedOptions().timeZone || 'America/New_York'
    );
    const [theme, setTheme] = useState<'dark' | 'light'>('dark');
    const [accentColor, setAccentColor] = useState('#22d3ee');
    const [privacyMode, setPrivacyMode] = useState<UserProfile['privacyMode']>('standard');
    const [proficiency, setProficiency] = useState(2);

    // AI Distro integration state
    const [persona, setPersona] = useState<'max' | 'alfred'>('max');
    const [starterPreset, setStarterPreset] = useState<'light' | 'balanced' | 'rich'>('balanced');

    if (hasCompletedOnboarding) return null;

    const canProceed = () => {
        if (step === 3) return displayName.trim().length > 0;
        return true;
    };

    const handleComplete = async () => {
        setUserProfile({ displayName, hostname, timezone, theme, accentColor, privacyMode });
        setProficiencyLevel(proficiency);

        try {
            await fetch('http://127.0.0.1:17842/api/persona/set', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ preset: persona })
            });
            await fetch('http://127.0.0.1:17842/api/onboarding', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ state: { completed: true, preset: starterPreset } })
            });
        } catch (err) {
            console.error('AI Distro backend error', err);
        }

        completeOnboarding();
    };

    const next = () => { if (step < TOTAL_STEPS && canProceed()) setStep(step + 1); };
    const back = () => { if (step > 1) setStep(step - 1); };

    const progressPct = (step / TOTAL_STEPS) * 100;
    const osName = displayName.trim() ? `${displayName.trim()} OS` : 'Mnemonic OS';

    return (
        <div className="fixed inset-0 z-[999] bg-black flex items-center justify-center">
            {/* Background gradient */}
            <div className="absolute inset-0 bg-gradient-to-br from-[#0a0a1a] via-[#0f0f2e] to-[#1a0a2e] opacity-90" />
            <div className="absolute inset-0 overflow-hidden">
                <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-3xl animate-pulse" />
                <div className="absolute bottom-1/3 right-1/4 w-80 h-80 rounded-full blur-3xl animate-pulse" style={{ backgroundColor: `${accentColor}10` }} />
            </div>

            <div className="relative w-full max-w-2xl mx-4">
                {/* Progress bar */}
                <div className="mb-6">
                    <div className="flex items-center justify-between text-xs text-white/40 mb-2 px-1">
                        <span>Step {step} of {TOTAL_STEPS}</span>
                        <span>{Math.round(progressPct)}%</span>
                    </div>
                    <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                        <div
                            className="h-full rounded-full transition-all duration-500 ease-out"
                            style={{ width: `${progressPct}%`, backgroundColor: accentColor }}
                        />
                    </div>
                </div>

                {/* Card */}
                <div className="bg-white/[0.04] backdrop-blur-2xl border border-white/10 rounded-3xl overflow-hidden shadow-[0_0_80px_rgba(0,0,0,0.5)]">
                    <div className="p-8 md:p-10 min-h-[420px] flex flex-col">

                        {/* === Step 1: Welcome === */}
                        {step === 1 && (
                            <div className="flex-1 flex flex-col items-center text-center justify-center">
                                <div className="w-20 h-20 rounded-full flex items-center justify-center mb-6" style={{ backgroundColor: `${accentColor}20` }}>
                                    <Sparkles className="w-10 h-10 animate-pulse" style={{ color: accentColor }} />
                                </div>
                                <h2 className="text-3xl font-light text-white mb-3">Welcome to Mnemonic OS</h2>
                                <p className="text-white/50 text-base max-w-md leading-relaxed mb-6">
                                    Let's set up your system. This will only take a moment.
                                </p>
                                <div className="flex items-center gap-6 text-white/30 text-sm">
                                    <div className="flex items-center gap-2"><Globe className="w-4 h-4" /> Region</div>
                                    <div className="flex items-center gap-2"><User className="w-4 h-4" /> Account</div>
                                    <div className="flex items-center gap-2"><Palette className="w-4 h-4" /> Appearance</div>
                                    <div className="flex items-center gap-2"><ShieldCheck className="w-4 h-4" /> Privacy</div>
                                </div>
                            </div>
                        )}

                        {/* === Step 2: Timezone === */}
                        {step === 2 && (
                            <div className="flex-1 flex flex-col">
                                <div className="flex items-center gap-3 mb-6">
                                    <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: `${accentColor}20` }}>
                                        <Globe className="w-5 h-5" style={{ color: accentColor }} />
                                    </div>
                                    <div>
                                        <h2 className="text-xl font-medium text-white">Where are you?</h2>
                                        <p className="text-sm text-white/40">Select your timezone for accurate clock display.</p>
                                    </div>
                                </div>
                                <div className="flex-1 overflow-y-auto max-h-[280px] rounded-xl border border-white/10 bg-black/30">
                                    {TIMEZONES.map((tz) => (
                                        <button
                                            key={tz}
                                            onClick={() => setTimezone(tz)}
                                            className={`w-full text-left px-4 py-3 text-sm border-b border-white/5 transition-colors ${timezone === tz
                                                ? 'text-white font-medium'
                                                : 'text-white/50 hover:text-white hover:bg-white/5'
                                                }`}
                                            style={timezone === tz ? { backgroundColor: `${accentColor}15` } : {}}
                                        >
                                            <div className="flex items-center justify-between">
                                                <span>{tz.replace(/_/g, ' ')}</span>
                                                {timezone === tz && <Check className="w-4 h-4" style={{ color: accentColor }} />}
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* === Step 3: User Account === */}
                        {step === 3 && (
                            <div className="flex-1 flex flex-col">
                                <div className="flex items-center gap-3 mb-6">
                                    <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: `${accentColor}20` }}>
                                        <User className="w-5 h-5" style={{ color: accentColor }} />
                                    </div>
                                    <div>
                                        <h2 className="text-xl font-medium text-white">Create your account</h2>
                                        <p className="text-sm text-white/40">Choose a display name and device hostname.</p>
                                    </div>
                                </div>

                                <div className="space-y-5">
                                    <div>
                                        <label className="block text-sm font-medium text-white/60 mb-2">Your Name *</label>
                                        <input
                                            type="text"
                                            value={displayName}
                                            onChange={(e) => setDisplayName(e.target.value)}
                                            placeholder="e.g. Max"
                                            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-white/30 outline-none focus:border-white/30 transition-colors"
                                            autoFocus
                                        />
                                        {displayName.trim() && (
                                            <p className="text-sm mt-3 font-medium" style={{ color: accentColor }}>
                                                Your OS will be named: <span className="text-white">{displayName.trim()} OS</span>
                                            </p>
                                        )}
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium text-white/60 mb-2">Device Hostname</label>
                                        <input
                                            type="text"
                                            value={hostname}
                                            onChange={(e) => setHostname(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                                            placeholder="e.g. my-laptop"
                                            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-white/30 outline-none focus:border-white/30 transition-colors font-mono text-sm"
                                        />
                                        <p className="text-xs text-white/30 mt-1">This is how your device identifies itself on the network.</p>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* === Step 4: Appearance === */}
                        {step === 4 && (
                            <div className="flex-1 flex flex-col">
                                <div className="flex items-center gap-3 mb-6">
                                    <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: `${accentColor}20` }}>
                                        <Palette className="w-5 h-5" style={{ color: accentColor }} />
                                    </div>
                                    <div>
                                        <h2 className="text-xl font-medium text-white">Appearance</h2>
                                        <p className="text-sm text-white/40">Choose your window style and accent color.</p>
                                    </div>
                                </div>

                                {/* Theme Toggle */}
                                <label className="block text-sm font-medium text-white/60 mb-3">Window Theme</label>
                                <div className="grid grid-cols-2 gap-3 mb-6">
                                    {[
                                        { id: 'dark' as const, label: 'Dark', icon: <Moon className="w-5 h-5" /> },
                                        { id: 'light' as const, label: 'Light', icon: <Sun className="w-5 h-5" /> },
                                    ].map((t) => (
                                        <button
                                            key={t.id}
                                            onClick={() => setTheme(t.id)}
                                            className={`flex items-center gap-3 p-4 rounded-xl border transition-all ${theme === t.id
                                                ? 'border-white/30 bg-white/10'
                                                : 'border-white/10 bg-white/[0.02] hover:border-white/20'
                                                }`}
                                        >
                                            <div className={theme === t.id ? 'text-white' : 'text-white/40'}>{t.icon}</div>
                                            <span className={theme === t.id ? 'text-white font-medium' : 'text-white/50'}>{t.label}</span>
                                            {theme === t.id && <Check className="w-4 h-4 ml-auto" style={{ color: accentColor }} />}
                                        </button>
                                    ))}
                                </div>

                                {/* Accent Color Grid */}
                                <label className="block text-sm font-medium text-white/60 mb-3">Accent Color</label>
                                <div className="grid grid-cols-4 gap-3">
                                    {ACCENT_COLORS.map((c) => (
                                        <button
                                            key={c.hex}
                                            onClick={() => setAccentColor(c.hex)}
                                            className={`flex flex-col items-center gap-2 p-3 rounded-xl border transition-all ${accentColor === c.hex
                                                ? 'border-white/30 bg-white/10'
                                                : 'border-white/5 hover:border-white/15'
                                                }`}
                                        >
                                            <div
                                                className="w-8 h-8 rounded-full shadow-lg"
                                                style={{ backgroundColor: c.hex, boxShadow: accentColor === c.hex ? `0 0 20px ${c.hex}60` : 'none' }}
                                            />
                                            <span className="text-xs text-white/50">{c.name}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* === Step 5: Privacy === */}
                        {step === 5 && (
                            <div className="flex-1 flex flex-col">
                                <div className="flex items-center gap-3 mb-6">
                                    <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: `${accentColor}20` }}>
                                        <ShieldCheck className="w-5 h-5" style={{ color: accentColor }} />
                                    </div>
                                    <div>
                                        <h2 className="text-xl font-medium text-white">Privacy & Interface</h2>
                                        <p className="text-sm text-white/40">Configure data handling and complexity level.</p>
                                    </div>
                                </div>

                                <label className="block text-sm font-medium text-white/60 mb-3">Privacy Mode</label>
                                <div className="space-y-3 mb-6">
                                    {[
                                        { id: 'standard' as const, title: 'Standard', desc: 'Basic telemetry. System functions normally.' },
                                        { id: 'strict' as const, title: 'Strict', desc: 'No telemetry. Privacy Moat generates decoy traffic.' },
                                        { id: 'paranoid' as const, title: 'Paranoid', desc: 'All traffic sandboxed. Digital Decoy active at all times.' },
                                    ].map((p) => (
                                        <button
                                            key={p.id}
                                            onClick={() => setPrivacyMode(p.id)}
                                            className={`w-full text-left p-4 rounded-xl border flex items-start gap-3 transition-all ${privacyMode === p.id
                                                ? 'border-white/30 bg-white/10'
                                                : 'border-white/10 bg-white/[0.02] hover:border-white/20'
                                                }`}
                                        >
                                            <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center mt-0.5 shrink-0 ${privacyMode === p.id ? 'border-white' : 'border-white/30'
                                                }`}>
                                                {privacyMode === p.id && <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: accentColor }} />}
                                            </div>
                                            <div>
                                                <div className="font-medium text-white text-sm">{p.title}</div>
                                                <div className="text-xs text-white/40 mt-0.5">{p.desc}</div>
                                            </div>
                                        </button>
                                    ))}
                                </div>

                                <label className="block text-sm font-medium text-white/60 mb-3">Interface Complexity</label>
                                <div className="grid grid-cols-2 gap-3">
                                    {[
                                        { level: 2, title: 'Standard', desc: 'Clean, focused UI', icon: <Monitor className="w-4 h-4" /> },
                                        { level: 3, title: 'Power User', desc: 'Terminal, Network Node, Moat', icon: <Rocket className="w-4 h-4" /> },
                                    ].map((opt) => (
                                        <button
                                            key={opt.level}
                                            onClick={() => setProficiency(opt.level)}
                                            className={`p-3 rounded-xl border text-left transition-all ${proficiency === opt.level
                                                ? 'border-white/30 bg-white/10'
                                                : 'border-white/10 bg-white/[0.02] hover:border-white/20'
                                                }`}
                                        >
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className={proficiency === opt.level ? 'text-white' : 'text-white/40'}>{opt.icon}</span>
                                                <span className={`text-sm font-medium ${proficiency === opt.level ? 'text-white' : 'text-white/50'}`}>{opt.title}</span>
                                            </div>
                                            <p className="text-xs text-white/30">{opt.desc}</p>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* === Step 6: Persona === */}
                        {step === 6 && (
                            <div className="flex-1 flex flex-col">
                                <div className="flex items-center gap-3 mb-6">
                                    <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: `${accentColor}20` }}>
                                        <Bot className="w-5 h-5" style={{ color: accentColor }} />
                                    </div>
                                    <div>
                                        <h2 className="text-xl font-medium text-white">Assistant Persona</h2>
                                        <p className="text-sm text-white/40">Choose your AI Distro assistant personality.</p>
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-3 mb-6">
                                    {[
                                        { id: 'max' as const, title: 'Max', desc: 'Direct, focused, and efficient' },
                                        { id: 'alfred' as const, title: 'Alfred', desc: 'Courteous and conversational' },
                                    ].map((p) => (
                                        <button
                                            key={p.id}
                                            onClick={() => setPersona(p.id)}
                                            className={`p-4 rounded-xl border text-left flex flex-col gap-1 transition-all ${persona === p.id
                                                ? 'border-white/30 bg-white/10'
                                                : 'border-white/10 bg-white/[0.02] hover:border-white/20'
                                                }`}
                                        >
                                            <div className="flex items-center justify-between">
                                                <span className={`font-medium ${persona === p.id ? 'text-white' : 'text-white/50'}`}>{p.title}</span>
                                                {persona === p.id && <Check className="w-4 h-4 ml-auto" style={{ color: accentColor }} />}
                                            </div>
                                            <span className="text-xs text-white/40">{p.desc}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* === Step 7: Starter Setup === */}
                        {step === 7 && (
                            <div className="flex-1 flex flex-col">
                                <div className="flex items-center gap-3 mb-6">
                                    <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: `${accentColor}20` }}>
                                        <Download className="w-5 h-5" style={{ color: accentColor }} />
                                    </div>
                                    <div>
                                        <h2 className="text-xl font-medium text-white">Starter Setup</h2>
                                        <p className="text-sm text-white/40">Select your initial app and service configuration.</p>
                                    </div>
                                </div>

                                <div className="space-y-3 mb-6">
                                    {[
                                        { id: 'light' as const, title: 'Lightweight', desc: 'Minimal setup (Browser, Notes)' },
                                        { id: 'balanced' as const, title: 'Balanced', desc: 'Standard desktop experience (Dev tools, Office, media)' },
                                        { id: 'rich' as const, title: 'Feature Rich', desc: 'Install all available apps and services' },
                                    ].map((s) => (
                                        <button
                                            key={s.id}
                                            onClick={() => setStarterPreset(s.id)}
                                            className={`w-full text-left p-4 rounded-xl border flex items-start gap-3 transition-all ${starterPreset === s.id
                                                ? 'border-white/30 bg-white/10'
                                                : 'border-white/10 bg-white/[0.02] hover:border-white/20'
                                                }`}
                                        >
                                            <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center mt-0.5 shrink-0 ${starterPreset === s.id ? 'border-white' : 'border-white/30'
                                                }`}>
                                                {starterPreset === s.id && <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: accentColor }} />}
                                            </div>
                                            <div>
                                                <div className="font-medium text-white text-sm">{s.title}</div>
                                                <div className="text-xs text-white/40 mt-0.5">{s.desc}</div>
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* === Step 8: Summary & Finish === */}
                        {step === 8 && (
                            <div className="flex-1 flex flex-col items-center text-center justify-center">
                                <div className="w-16 h-16 rounded-full flex items-center justify-center mb-5" style={{ backgroundColor: `${accentColor}20` }}>
                                    <Rocket className="w-8 h-8" style={{ color: accentColor }} />
                                </div>
                                <h2 className="text-2xl font-light text-white mb-2">Welcome to <span style={{ color: accentColor }}>{osName}</span></h2>
                                <p className="text-white/40 text-sm mb-8 max-w-sm">
                                    Your system is configured. Here's a summary of your choices:
                                </p>
                                <div className="w-full max-w-sm bg-white/5 rounded-xl border border-white/10 divide-y divide-white/5 text-left text-sm max-h-[160px] overflow-y-auto">
                                    <div className="flex justify-between px-4 py-3">
                                        <span className="text-white/40">Timezone</span>
                                        <span className="text-white/80 font-medium">{timezone.replace(/_/g, ' ')}</span>
                                    </div>
                                    <div className="flex justify-between px-4 py-3">
                                        <span className="text-white/40">Hostname</span>
                                        <span className="text-white/80 font-mono">{hostname}</span>
                                    </div>
                                    <div className="flex justify-between px-4 py-3">
                                        <span className="text-white/40">Theme</span>
                                        <span className="text-white/80 capitalize">{theme}</span>
                                    </div>
                                    <div className="flex justify-between items-center px-4 py-3">
                                        <span className="text-white/40">Accent</span>
                                        <div className="flex items-center gap-2">
                                            <div className="w-4 h-4 rounded-full" style={{ backgroundColor: accentColor }} />
                                            <span className="text-white/80">{ACCENT_COLORS.find(c => c.hex === accentColor)?.name}</span>
                                        </div>
                                    </div>
                                    <div className="flex justify-between px-4 py-3">
                                        <span className="text-white/40">Privacy</span>
                                        <span className="text-white/80 capitalize">{privacyMode}</span>
                                    </div>
                                    <div className="flex justify-between px-4 py-3">
                                        <span className="text-white/40">Persona</span>
                                        <span className="text-white/80 capitalize">{persona}</span>
                                    </div>
                                    <div className="flex justify-between px-4 py-3">
                                        <span className="text-white/40">Starter Setup</span>
                                        <span className="text-white/80 capitalize">{starterPreset}</span>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Navigation Footer */}
                    <div className="px-8 md:px-10 pb-8 flex items-center justify-between">
                        {step > 1 ? (
                            <button onClick={back} className="flex items-center gap-2 text-white/40 hover:text-white text-sm transition-colors">
                                <ArrowLeft className="w-4 h-4" /> Back
                            </button>
                        ) : <div />}

                        {step < TOTAL_STEPS ? (
                            <button
                                onClick={next}
                                disabled={!canProceed()}
                                className="flex items-center gap-2 px-6 py-2.5 rounded-full font-medium text-sm text-black transition-all disabled:opacity-30 disabled:cursor-not-allowed hover:brightness-110"
                                style={{ backgroundColor: accentColor }}
                            >
                                Continue <ArrowRight className="w-4 h-4" />
                            </button>
                        ) : (
                            <button
                                onClick={handleComplete}
                                className="flex items-center gap-2 px-6 py-2.5 rounded-full font-medium text-sm text-black transition-all hover:brightness-110"
                                style={{ backgroundColor: accentColor }}
                            >
                                Start {osName} <Rocket className="w-4 h-4" />
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
