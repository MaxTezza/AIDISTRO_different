import React, { useEffect, useState } from 'react';
import { Taskbar } from './Taskbar';
import { AppCanvas } from '../canvas/AppCanvas';
import { NetworkNodeWidget } from '../components/NetworkNodeWidget';
import { useKernelStore } from '../kernel/store';

export const Shell: React.FC = () => {
    const [mounted, setMounted] = useState(false);
    const { userProfile } = useKernelStore();

    const osName = userProfile.displayName.trim()
        ? `${userProfile.displayName.trim()} OS`
        : 'Mnemonic OS';

    useEffect(() => {
        setMounted(true);
    }, []);

    return (
        <div className="relative w-screen h-screen overflow-hidden text-white font-sans bg-bg-dark">

            {/* Live Mnemonic background mimicking the "Soul Drive" state */}
            <div className="absolute inset-0 z-0">
                <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-primary-start rounded-full blur-[120px] opacity-20 animate-pulse transition-all duration-1000" />
                <div className="absolute bottom-1/4 right-1/4 w-[600px] h-[600px] bg-accent rounded-full blur-[150px] opacity-10" />

                {/* Ambient overlay */}
                <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-5 mix-blend-overlay" />
            </div>

            {mounted && (
                <>
                    <div className="absolute top-4 left-4 z-0 text-white/30 text-sm font-light select-none tracking-widest uppercase">
                        {osName} <span className="opacity-50 mx-1">•</span> Liquid Computing Node 01
                    </div>

                    {/* 
                 The Canvas takes up the full space natively. The Taskbar sits on top. 
                 The traditional paradigm of desktop icons is replaced by Intent/Search.
               */}
                    <AppCanvas />
                    <Taskbar />
                    <NetworkNodeWidget />
                </>
            )}

        </div>
    );
};
