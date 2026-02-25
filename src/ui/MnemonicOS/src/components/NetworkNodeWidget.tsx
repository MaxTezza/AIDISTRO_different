import React from 'react';
import { Network, Laptop, Cpu, HardDrive } from 'lucide-react';
import { useKernelStore } from '../kernel/store';

export const NetworkNodeWidget: React.FC = () => {
    const { showNetworkNode, userProficiencyLevel } = useKernelStore();
    React.useEffect(() => {
        // Just keeping the node active watcher if they want to expand later
    }, [showNetworkNode, userProficiencyLevel]);

    if (!showNetworkNode || userProficiencyLevel < 2) return null;

    return (
        <div className="absolute top-20 right-6 w-80 glass-panel rounded-3xl p-5 animate-in slide-in-from-right-10 fade-in duration-500 z-[110] border border-emerald-500/30 shadow-[0_0_40px_rgba(16,185,129,0.15)] pointer-events-auto">
            <div className="flex items-center gap-2 text-emerald-400 mb-5 border-b border-emerald-500/20 pb-3">
                <Network className="w-5 h-5 animate-pulse" />
                <h3 className="font-bold tracking-widest text-sm uppercase">Liquid Node Cluster</h3>
            </div>

            <div className="flex flex-col gap-4">
                {/* Local Instance */}
                <div className="relative p-4 rounded-2xl bg-white/5 border border-white/10 overflow-hidden shadow-inner">
                    <div className="flex items-center justify-between mb-3 relative z-10">
                        <div className="flex items-center gap-2">
                            <Laptop className="w-5 h-5 text-white/80" />
                            <span className="text-sm font-semibold text-white/90">Local Terminal</span>
                        </div>
                        <span className="text-xs text-white/60 px-2.5 py-1 bg-black/60 rounded-md font-medium tracking-wide">Host</span>
                    </div>

                    <div className="flex items-center justify-between text-xs text-white/60 relative z-10 font-mono">
                        <div className="flex items-center gap-1">
                            <Cpu className="w-3.5 h-3.5" /> CPU: 12%
                        </div>
                        <div className="flex items-center gap-1">
                            <HardDrive className="w-3.5 h-3.5" /> Mem: 4.2GB
                        </div>
                    </div>
                    {/* Activity visualizer */}
                    <div className="absolute bottom-0 left-0 h-1 bg-gradient-to-r from-emerald-500/0 via-emerald-500/80 to-emerald-500 w-[12%] animate-pulse" />
                </div>
            </div>

            <div className="mt-5 pt-3 border-t border-emerald-500/20 text-[10px] text-emerald-500/40 text-center uppercase tracking-widest font-mono">
                Mnemonic Universal Fabric Layer
            </div>
        </div >
    );
};
