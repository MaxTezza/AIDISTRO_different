import React, { useEffect, useState } from 'react';
import { ShieldAlert, Activity, Wifi, CheckCircle2 } from 'lucide-react';
import { listEstablishedConnections } from '../native/api';

export const PrivacyMoatApp: React.FC = () => {
    const [logs, setLogs] = useState<{ id: string, text: string, type: 'fake' | 'intercept' }[]>([]);

    useEffect(() => {
        let active = true;

        const pollNetwork = async () => {
            if (!active) return;
            try {
                const connections = await listEstablishedConnections(8);
                if (connections.length === 0) {
                    setLogs([{ id: '1', text: 'No active ESTABLISHED connections found on host layer.', type: 'fake' }]);
                } else {
                    const parsedLogs = connections.map((conn) => ({
                        id: Math.random().toString(),
                        text: `[${conn.protocol}] Established -> ${conn.destination}`,
                        type: conn.is_external ? 'intercept' as const : 'fake' as const,
                    }));
                    if (active) setLogs(parsedLogs);
                }
            } catch (err) {
                console.error("Failed to poll host network architecture", err);
            }

            if (active) {
                setTimeout(pollNetwork, 2000);
            }
        };

        pollNetwork();

        return () => { active = false; };
    }, []);

    return (
        <div className="h-full flex flex-col pt-2 font-mono text-sm relative">
            <div className="absolute top-2 right-4 opacity-10">
                <ShieldAlert className="w-48 h-48" />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between mx-4 mb-4 border-b border-cyan-500/30 pb-2">
                <div className="flex items-center gap-2 text-cyan-400">
                    <Activity className="w-5 h-5" />
                    <h3 className="font-bold tracking-widest uppercase">Host Network Connections</h3>
                </div>
                <div className="flex items-center gap-1 text-xs text-green-400">
                    <CheckCircle2 className="w-4 h-4" /> Monitoring Active
                </div>
            </div>

            <div className="px-4 text-white/50 mb-2 font-sans text-xs">
                Real-time active TCP connections retrieved from host OS via Tauri API (ss/netstat).
            </div>

            {/* Terminal Log */}
            <div className="flex-1 bg-black/60 rounded-xl mx-4 mb-4 p-3 border border-white/5 overflow-hidden flex flex-col justify-end">
                <div className="flex flex-col gap-1 w-full justify-end min-h-full">
                    {logs.map(log => (
                        <div key={log.id} className={`flex items-start gap-2 animate-in fade-in slide-in-from-bottom-2 duration-300 ${log.type === 'intercept' ? 'text-cyan-400' : 'text-white/80'
                            }`}>
                            <span className="opacity-50 mt-0.5">{">"}</span>
                            <span>{log.text}</span>
                        </div>
                    ))}
                    {logs.length === 0 && (
                        <div className="text-white/30 italic flex items-center gap-2">
                            <Wifi className="w-4 h-4 animate-pulse" /> Scanning connections...
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
