import React, { useState, useEffect } from 'react';
import { Cpu, RefreshCw, CheckCircle, AlertTriangle, Download, Server, HardDrive, Wifi } from 'lucide-react';
import { runTerminalCommand } from '../native/api';

interface HardwareDevice {
    id: string;
    type: 'gpu' | 'network' | 'audio' | 'other';
    name: string;
    vendor: string;
    driverStatus: 'installed' | 'missing' | 'update_available' | 'unknown';
    recommendedPackage?: string;
}

export const DriverManagerApp: React.FC = () => {
    const [scanning, setScanning] = useState(false);
    const [devices, setDevices] = useState<HardwareDevice[]>([]);
    const [actionState, setActionState] = useState<{ id: string, action: 'installing' | 'updating' } | null>(null);

    const scanHardware = async () => {
        setScanning(true);
        try {
            // In a real Ubuntu environment, we would parse `ubuntu-drivers devices` or `lspci -knn`
            // For this implementation, we will simulate a realistic scan that takes a moment,
            // then return a mix of real data (if we can get it) or structured mock data 
            // to demonstrate the "Sanitized" UI concept.

            try {
                // Try to get actual PCI devices (very basic parse)
                const lspciOut = await runTerminalCommand('lspci');
                const parsedDevices: HardwareDevice[] = [];

                const lines = lspciOut.split('\n').filter(l => l.trim().length > 0);

                // We'll just grab the first VGA and Network controller to keep the UI clean
                const vga = lines.find(l => l.includes('VGA'));
                if (vga) {
                    parsedDevices.push({
                        id: 'vga-1',
                        type: 'gpu',
                        name: vga.split(': ')[1] || 'Unknown Display Controller',
                        vendor: vga.includes('NVIDIA') ? 'NVIDIA' : (vga.includes('AMD') ? 'AMD' : 'Intel'),
                        driverStatus: 'installed' // Assume installed by default unless we parse ubuntu-drivers
                    });
                }

                const net = lines.find(l => l.includes('Network'));
                if (net) {
                    parsedDevices.push({
                        id: 'net-1',
                        type: 'network',
                        name: net.split(': ')[1] || 'Unknown Network Controller',
                        vendor: net.includes('Intel') ? 'Intel' : (net.includes('Broadcom') ? 'Broadcom' : 'Generic'),
                        driverStatus: 'installed'
                    });
                }

                if (parsedDevices.length > 0) {
                    setDevices(parsedDevices);
                } else {
                    throw new Error("No primary devices found via lspci");
                }

            } catch (err) {
                console.error("Hardware scan failed:", err);
                setDevices([]);
            }
        } catch (error) {
            console.error("Hardware scan failed", error);
        } finally {
            setScanning(false);
        }
    };

    useEffect(() => {
        scanHardware();
    }, []);

    const handleDriverAction = async (device: HardwareDevice, action: 'installing' | 'updating') => {
        if (!device.recommendedPackage) return;

        setActionState({ id: device.id, action });
        try {
            // Native integration: This invokes the host's polkit to prompt for password and installs the driver
            await runTerminalCommand(`pkexec apt-get install -y ${device.recommendedPackage}`);

            // Update UI state
            setDevices(prev => prev.map(d =>
                d.id === device.id ? { ...d, driverStatus: 'installed' } : d
            ));
        } catch (err) {
            console.error(`Failed to ${action} driver for ${device.name}:`, err);
        } finally {
            setActionState(null);
        }
    };

    const getDeviceIcon = (type: HardwareDevice['type']) => {
        switch (type) {
            case 'gpu': return <Server className="w-6 h-6" />;
            case 'network': return <Wifi className="w-6 h-6" />;
            case 'audio': return <HardDrive className="w-6 h-6" />; // Using HardDrive as a generic component icon
            default: return <Cpu className="w-6 h-6" />;
        }
    };

    return (
        <div className="h-full flex flex-col bg-black/40">
            {/* Header */}
            <div className="p-6 border-b border-white/10 bg-white/5 flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-blue-500/20 rounded-xl border border-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.3)]">
                        <Cpu className="w-6 h-6 text-blue-400" />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-white tracking-wide">Hardware & Drivers</h2>
                        <p className="text-sm text-white/50">Automatic System Sanitization</p>
                    </div>
                </div>
                <button
                    onClick={scanHardware}
                    disabled={scanning}
                    className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-white/70 transition-colors disabled:opacity-50"
                    title="Rescan Hardware"
                >
                    <RefreshCw className={`w-5 h-5 ${scanning ? 'animate-spin' : ''}`} />
                </button>
            </div>

            {/* Content List */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar">
                {scanning && devices.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-white/50 gap-4">
                        <RefreshCw className="w-10 h-10 animate-spin text-blue-400" />
                        <span className="text-sm font-medium tracking-wide">Interrogating PCI Bus...</span>
                    </div>
                ) : (
                    devices.map(device => {
                        const isActing = actionState?.id === device.id;

                        return (
                            <div key={device.id} className="p-5 bg-white/5 border border-white/10 rounded-2xl flex flex-col gap-3 transition-opacity">
                                <div className="flex items-start justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className="p-3 bg-black/40 rounded-xl border border-white/5">
                                            {getDeviceIcon(device.type)}
                                        </div>
                                        <div>
                                            <h3 className="font-semibold text-white truncate max-w-[250px]">{device.name}</h3>
                                            <p className="text-xs text-white/50 uppercase tracking-widest mt-1">{device.vendor}</p>
                                        </div>
                                    </div>

                                    {/* Status Badge */}
                                    <div className="shrink-0 flex flex-col items-end gap-2">
                                        {device.driverStatus === 'installed' && (
                                            <div className="px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-[0_0_10px_rgba(52,211,153,0.1)]">
                                                <CheckCircle className="w-3.5 h-3.5" /> Operating Normally
                                            </div>
                                        )}
                                        {device.driverStatus === 'missing' && (
                                            <div className="px-3 py-1 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-[0_0_10px_rgba(248,113,113,0.1)] animate-pulse">
                                                <AlertTriangle className="w-3.5 h-3.5" /> Driver Missing
                                            </div>
                                        )}
                                        {device.driverStatus === 'update_available' && (
                                            <div className="px-3 py-1 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-[0_0_10px_rgba(251,191,36,0.1)]">
                                                <Download className="w-3.5 h-3.5" /> Optimize Device
                                            </div>
                                        )}

                                        {/* Action Button */}
                                        {device.driverStatus !== 'installed' && (
                                            <button
                                                onClick={() => handleDriverAction(device, device.driverStatus === 'missing' ? 'installing' : 'updating')}
                                                disabled={isActing}
                                                className={`px-4 py-2 mt-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2
                                                 ${device.driverStatus === 'missing'
                                                        ? 'bg-red-500/20 hover:bg-red-500/30 text-red-100 border border-red-500/30'
                                                        : 'bg-amber-500/20 hover:bg-amber-500/30 text-amber-100 border border-amber-500/30'
                                                    }
                                                 ${isActing ? 'opacity-50 cursor-not-allowed' : ''}
                                             `}
                                            >
                                                {isActing ? (
                                                    <>
                                                        <RefreshCw className="w-4 h-4 animate-spin" />
                                                        {actionState?.action === 'installing' ? 'Installing...' : 'Optimizing...'}
                                                    </>
                                                ) : (
                                                    actionState?.action === 'installing' || device.driverStatus === 'missing' ? 'Install Required Driver' : 'Apply Optimization'
                                                )}
                                            </button>
                                        )}
                                    </div>
                                </div>
                                {device.driverStatus !== 'installed' && !isActing && (
                                    <div className="mt-2 text-xs text-white/40 bg-black/20 p-3 rounded-lg border border-white/5">
                                        Automated Resolution: Execute <code className="text-blue-300 font-mono text-[10px] bg-blue-500/10 px-1 py-0.5 rounded ml-1">apt install {device.recommendedPackage}</code>
                                    </div>
                                )}
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
};
