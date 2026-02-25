import React, { useState } from 'react';
import { useKernelStore } from '../kernel/store';
import {
    Volume2, VolumeX, Sun, Moon, Wifi, WifiOff,
    Bluetooth, BluetoothOff, Battery, BatteryCharging,
    Monitor, ChevronDown, BellOff
} from 'lucide-react';

export const QuickSettings: React.FC = () => {
    const {
        systemControls, setVolume, setBrightness,
        toggleWifi, toggleBluetooth, toggleNightMode, toggleDoNotDisturb,
        userProfile
    } = useKernelStore();
    const [isOpen, setIsOpen] = useState(false);

    const accentColor = userProfile.accentColor || '#22d3ee';

    if (!isOpen) {
        // Collapsed: just show status icons in taskbar area
        return (
            <button
                onClick={() => setIsOpen(true)}
                className="flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-white/10 transition-colors text-white/50 hover:text-white/70"
            >
                {systemControls.wifi ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5 text-red-400" />}
                <VolumeIcon volume={systemControls.volume} />
                <BatteryIcon level={systemControls.battery} />
                <span className="text-[11px] font-medium">{systemControls.battery}%</span>
            </button>
        );
    }

    return (
        <>
            {/* Backdrop */}
            <div className="fixed inset-0 z-[130]" onClick={() => setIsOpen(false)} />

            {/* Panel */}
            <div className="fixed bottom-20 right-6 z-[135] w-80 bg-black/95 backdrop-blur-2xl border border-white/15 rounded-2xl shadow-[0_10px_50px_rgba(0,0,0,0.7)] overflow-hidden animate-in slide-in-from-bottom-5 fade-in duration-200">

                {/* Header */}
                <div className="px-5 pt-4 pb-2 flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-white">Quick Settings</h3>
                    <button
                        onClick={() => setIsOpen(false)}
                        className="text-white/30 hover:text-white/60 transition-colors"
                    >
                        <ChevronDown className="w-4 h-4" />
                    </button>
                </div>

                {/* Toggle Grid */}
                <div className="px-4 py-3 grid grid-cols-3 gap-2">
                    <ToggleTile
                        icon={systemControls.wifi ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
                        label="Wi-Fi"
                        sublabel={systemControls.wifi ? 'Connected' : 'Off'}
                        active={systemControls.wifi}
                        accentColor={accentColor}
                        onClick={toggleWifi}
                    />
                    <ToggleTile
                        icon={systemControls.bluetooth ? <Bluetooth className="w-4 h-4" /> : <BluetoothOff className="w-4 h-4" />}
                        label="Bluetooth"
                        sublabel={systemControls.bluetooth ? 'On' : 'Off'}
                        active={systemControls.bluetooth}
                        accentColor={accentColor}
                        onClick={toggleBluetooth}
                    />
                    <ToggleTile
                        icon={systemControls.nightMode ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
                        label="Night Mode"
                        sublabel={systemControls.nightMode ? 'On' : 'Off'}
                        active={systemControls.nightMode}
                        accentColor={accentColor}
                        onClick={toggleNightMode}
                    />
                    <ToggleTile
                        icon={<BellOff className="w-4 h-4" />}
                        label="Do Not Disturb"
                        sublabel={systemControls.doNotDisturb ? 'On' : 'Off'}
                        active={systemControls.doNotDisturb}
                        accentColor={accentColor}
                        onClick={toggleDoNotDisturb}
                    />
                    <ToggleTile
                        icon={<Monitor className="w-4 h-4" />}
                        label="Display"
                        sublabel={`${systemControls.brightness}%`}
                        active={false}
                        accentColor={accentColor}
                        onClick={() => { }}
                    />
                    <ToggleTile
                        icon={<BatteryIcon level={systemControls.battery} />}
                        label="Battery"
                        sublabel={`${systemControls.battery}%`}
                        active={systemControls.battery > 20}
                        accentColor={systemControls.battery > 20 ? '#10b981' : '#ef4444'}
                        onClick={() => { }}
                    />
                </div>

                {/* Sliders */}
                <div className="px-5 pb-4 space-y-4">
                    {/* Volume */}
                    <SliderControl
                        icon={<VolumeIcon volume={systemControls.volume} />}
                        label="Volume"
                        value={systemControls.volume}
                        onChange={setVolume}
                        accentColor={accentColor}
                    />
                    {/* Brightness */}
                    <SliderControl
                        icon={<Sun className="w-4 h-4" />}
                        label="Brightness"
                        value={systemControls.brightness}
                        onChange={setBrightness}
                        accentColor={accentColor}
                    />
                </div>
            </div>
        </>
    );
};

// ─── Sub-components ───────────────────────────────────────

const ToggleTile: React.FC<{
    icon: React.ReactNode;
    label: string;
    sublabel: string;
    active: boolean;
    accentColor: string;
    onClick: () => void;
}> = ({ icon, label, sublabel, active, accentColor, onClick }) => (
    <button
        onClick={onClick}
        className={`flex flex-col items-center gap-1 p-3 rounded-xl border transition-all ${active
                ? 'border-white/15'
                : 'bg-white/[0.03] border-white/5 hover:bg-white/[0.06]'
            }`}
        style={active ? { backgroundColor: `${accentColor}15`, borderColor: `${accentColor}30` } : {}}
    >
        <span style={active ? { color: accentColor } : { color: 'rgba(255,255,255,0.4)' }}>{icon}</span>
        <span className="text-[10px] text-white/60 font-medium leading-tight">{label}</span>
        <span className="text-[9px] text-white/30">{sublabel}</span>
    </button>
);

const SliderControl: React.FC<{
    icon: React.ReactNode;
    label: string;
    value: number;
    onChange: (v: number) => void;
    accentColor: string;
}> = ({ icon, label, value, onChange, accentColor }) => (
    <div className="flex items-center gap-3">
        <span className="text-white/40 shrink-0">{icon}</span>
        <div className="flex-1">
            <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] text-white/30 uppercase tracking-wider">{label}</span>
                <span className="text-[10px] text-white/50 font-mono">{value}%</span>
            </div>
            <input
                type="range"
                min="0"
                max="100"
                value={value}
                onChange={(e) => onChange(Number(e.target.value))}
                className="w-full h-1 rounded-full appearance-none cursor-pointer"
                style={{
                    background: `linear-gradient(to right, ${accentColor} ${value}%, rgba(255,255,255,0.1) ${value}%)`,
                }}
            />
        </div>
    </div>
);

const VolumeIcon: React.FC<{ volume: number }> = ({ volume }) => {
    if (volume === 0) return <VolumeX className="w-3.5 h-3.5" />;
    return <Volume2 className="w-3.5 h-3.5" />;
};

const BatteryIcon: React.FC<{ level: number }> = ({ level }) => {
    if (level > 90) return <BatteryCharging className="w-3.5 h-3.5 text-green-400" />;
    if (level > 20) return <Battery className="w-3.5 h-3.5" />;
    return <Battery className="w-3.5 h-3.5 text-red-400" />;
};
