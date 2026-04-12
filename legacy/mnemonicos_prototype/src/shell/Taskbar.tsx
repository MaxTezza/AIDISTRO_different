import React from 'react';
import { useKernelStore } from '../kernel/store';
import {
    Search,
    Settings,
    TerminalSquare,
    Image as ImageIcon,
    History,
    BrainCircuit,
    PenTool,
    Cpu,
    ShieldAlert,
    ChevronUp,
    Network,
    Sparkles,
    X,
    Power,
    Bot,
    CalendarDays,
    CloudSun,
    Mail,
    FolderOpen,
    Palette,
    ShoppingBag
} from 'lucide-react';
import { getUnreadCount } from '../kernel/dataServices';
import { NotificationBell } from './NotificationCenter';
import { QuickSettings } from './QuickSettings';
import { useAppLauncher } from './AppLauncher';

export const Taskbar: React.FC = () => {
    const {
        spawnApp,
        takeSnapshot,
        historySnapshot,
        rewindToSnapshot,
        userProficiencyLevel,
        setProficiencyLevel,
        showNetworkNode,
        toggleNetworkNode,
        automationSuggestion,
        clearAutomationSuggestion,
        executeMacro,
        isGuideOpen,
        toggleGuide
    } = useKernelStore();
    const { openLauncher } = useAppLauncher();

    const cycleProficiency = () => {
        setProficiencyLevel(userProficiencyLevel === 3 ? 1 : userProficiencyLevel + 1);
    };

    // UI based on Adaptive Complexity Level
    const isLevel1 = userProficiencyLevel === 1; // "Grandma Mode"
    const isLevel3 = userProficiencyLevel === 3; // "Power User"

    return (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-[100] flex flex-col items-center gap-4 transition-all duration-700">

            {/* Main Dock */}
            <div className={`glass-panel rounded-3xl p-3 flex items-center gap-4 shadow-[0_10px_40px_rgba(0,0,0,0.5)] transition-all duration-500
            ${isLevel1 ? 'border-4 border-white/40 scale-110' : 'border border-white/20'}`}
            >

                {/* Adaptive Complexity Toggler (Hidden setting) */}
                <button
                    onClick={cycleProficiency}
                    className="w-8 h-8 rounded-xl bg-white/5 hover:bg-white/20 flex flex-col items-center justify-center gap-0.5 text-white/50 hover:text-white transition-colors absolute -left-12 top-1/2 -translate-y-1/2"
                    title={`Proficiency Level: ${userProficiencyLevel} (Click to Cycle)`}
                >
                    <ChevronUp className="w-4 h-4" />
                    <span className="text-[10px] font-bold leading-none">{userProficiencyLevel}</span>
                </button>

                {/* Level 1: Extreme Simplicity */}
                {isLevel1 && (
                    <>
                        <button onClick={() => spawnApp('canvas')} className="min-w-[120px] p-4 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center gap-3 hover:scale-105 transition-transform font-bold text-lg shadow-lg">
                            <PenTool className="w-8 h-8" /> Write
                        </button>
                        <button onClick={() => spawnApp('media')} className="min-w-[120px] p-4 rounded-xl bg-gradient-to-br from-green-500 to-green-700 flex items-center gap-3 hover:scale-105 transition-transform font-bold text-lg shadow-lg">
                            <ImageIcon className="w-8 h-8" /> Photos
                        </button>
                        <button className="min-w-[120px] p-4 rounded-xl bg-gradient-to-br from-purple-500 to-purple-700 flex items-center gap-3 hover:scale-105 transition-transform font-bold text-lg shadow-lg">
                            <BrainCircuit className="w-8 h-8" /> Help
                        </button>
                    </>
                )}

                {/* Level 2 & 3: Intent Router + Timeline */}
                {!isLevel1 && (
                    <>
                        {/* Universal Intent Button with AI Observer Bubble */}
                        <div className="relative">
                            {/* "Show, Don't Code" Observer Bubble */}
                            {automationSuggestion === 'close_all' && (
                                <div className="absolute bottom-[120%] left-1/2 -translate-x-1/2 mb-4 w-[280px] p-4 glass-panel border border-accent/40 rounded-2xl shadow-[0_10px_30px_rgba(34,211,238,0.2)] animate-in slide-in-from-bottom-2 fade-in duration-500 z-50">
                                    <div className="flex items-start justify-between mb-2">
                                        <div className="flex items-center gap-2 text-accent font-bold text-sm">
                                            <Sparkles className="w-4 h-4 animate-pulse" />
                                            AI Observer
                                        </div>
                                        <button onClick={clearAutomationSuggestion} className="text-white/40 hover:text-white transition-colors">
                                            <X className="w-4 h-4" />
                                        </button>
                                    </div>
                                    <p className="text-xs text-white/80 mb-3 leading-relaxed">
                                        I noticed you are manually closing several windows. Would you like me to close the remaining ones for you?
                                    </p>
                                    <button
                                        onClick={() => executeMacro('close_all')}
                                        className="w-full py-2 bg-gradient-to-r from-accent to-blue-600 hover:opacity-90 rounded-xl text-xs font-bold shadow-lg transition-transform active:scale-95 text-white"
                                    >
                                        Execute Macro (Close All)
                                    </button>
                                    {/* Arrow pointing to Intent button */}
                                    <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-4 h-4 rotate-45 border-b border-r border-accent/40 bg-[#1a1a2e]" />
                                </div>
                            )}

                            <button
                                onClick={openLauncher}
                                className="w-12 h-12 rounded-2xl bg-gradient-to-br from-accent to-blue-600 flex items-center justify-center hover:scale-110 active:scale-95 transition-all shadow-[0_0_15px_rgba(34,211,238,0.5)] group relative z-10"
                                title="App Launcher"
                            >
                                <Search className="text-white w-6 h-6 group-hover:rotate-90 transition-transform duration-500" />
                            </button>
                        </div>

                        <div className="w-px h-8 bg-white/20 mx-2" />

                        {/* Core Apps */}
                        <button onClick={() => spawnApp('canvas')} className="p-3 rounded-lg hover:bg-white/10 text-white/70 hover:text-white transition-colors" title="Universal Canvas">
                            <TerminalSquare className="w-6 h-6" />
                        </button>
                        <button onClick={() => spawnApp('media')} className="p-3 rounded-lg hover:bg-white/10 text-white/70 hover:text-white transition-colors" title="Media Graph">
                            <ImageIcon className="w-6 h-6" />
                        </button>
                        <button onClick={() => spawnApp('settings')} className="p-3 rounded-lg hover:bg-white/10 text-white/70 hover:text-white transition-colors" title="Settings">
                            <Settings className="w-6 h-6" />
                        </button>
                        <button onClick={() => spawnApp('theme-engine')} className="p-3 rounded-lg hover:bg-white/10 text-white/70 hover:text-white transition-colors" title="Theme Engine">
                            <Palette className="w-6 h-6" />
                        </button>
                        <button onClick={() => spawnApp('app-store')} className="p-3 rounded-lg hover:bg-white/10 text-emerald-400/80 hover:text-emerald-400 transition-colors" title="Software Center">
                            <ShoppingBag className="w-6 h-6" />
                        </button>
                        <button onClick={() => spawnApp('driver-manager')} className="p-3 rounded-lg hover:bg-white/10 text-blue-400/80 hover:text-blue-400 transition-colors" title="Hardware Sanitizer">
                            <Cpu className="w-6 h-6" />
                        </button>
                        <button onClick={() => spawnApp('files')} className="p-3 rounded-lg hover:bg-white/10 text-white/70 hover:text-white transition-colors" title="Files">
                            <FolderOpen className="w-6 h-6" />
                        </button>

                        <div className="w-px h-8 bg-white/20 mx-2" />

                        {/* Daily Life */}
                        <button onClick={() => spawnApp('calendar')} className="p-3 rounded-lg hover:bg-white/10 text-white/70 hover:text-white transition-colors" title="Calendar">
                            <CalendarDays className="w-6 h-6" />
                        </button>
                        <button onClick={() => spawnApp('weather')} className="p-3 rounded-lg hover:bg-white/10 text-white/70 hover:text-white transition-colors" title="Weather">
                            <CloudSun className="w-6 h-6" />
                        </button>
                        <div className="relative">
                            <button onClick={() => spawnApp('email')} className="p-3 rounded-lg hover:bg-white/10 text-white/70 hover:text-white transition-colors" title="Email">
                                <Mail className="w-6 h-6" />
                            </button>
                            {getUnreadCount() > 0 && (
                                <span className="absolute top-1.5 right-1.5 w-4 h-4 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center">
                                    {getUnreadCount()}
                                </span>
                            )}
                        </div>

                        <div className="w-px h-8 bg-white/20 mx-2" />

                        <button onClick={toggleGuide} className={`p-3 rounded-lg transition-colors ${isGuideOpen ? 'bg-accent/20 text-accent shadow-[0_0_15px_rgba(34,211,238,0.3)]' : 'hover:bg-white/10 text-white/70 hover:text-white'}`} title="Mnemonic Guide">
                            <Bot className="w-6 h-6" />
                        </button>

                        <NotificationBell />

                        {/* Level 3: Power User Additions */}
                        {isLevel3 && (
                            <>
                                <div className="w-px h-6 bg-white/10 mx-1" />
                                <button onClick={() => spawnApp('terminal')} className="p-3 rounded-lg hover:bg-white/10 text-red-400 hover:text-red-300 transition-colors" title="System Scripting">
                                    <Cpu className="w-6 h-6" />
                                </button>
                                <button onClick={() => spawnApp('privacy-moat')} className="p-3 rounded-lg hover:bg-white/10 text-orange-400 hover:text-orange-300 transition-colors" title="Honeypot Network Monitor">
                                    <ShieldAlert className="w-6 h-6" />
                                </button>
                                <button onClick={toggleNetworkNode} className={`p-3 rounded-lg hover:bg-white/10 transition-colors ${showNetworkNode ? 'text-emerald-400 bg-white/10 shadow-[0_0_15px_rgba(16,185,129,0.3)]' : 'text-emerald-500/50 hover:text-emerald-400'}`} title="Liquid Computing Node">
                                    <Network className="w-6 h-6" />
                                </button>
                            </>
                        )}

                        <div className="w-px h-8 bg-white/20 mx-2" />

                        {/* Power / Shutdown Button */}
                        <button onClick={() => window.close()} className="p-3 rounded-lg hover:bg-red-500/20 text-red-500/70 hover:text-red-400 transition-colors" title="Shutdown Mnemonic OS">
                            <Power className="w-6 h-6" />
                        </button>

                        <div className="w-px h-8 bg-white/20 mx-2" />

                        {/* Time Travel Timeline Prototype */}
                        <div className="flex items-center gap-2 group relative">
                            <button
                                onClick={() => takeSnapshot()}
                                className="p-3 rounded-lg hover:bg-white/10 text-white/70 hover:text-white transition-colors hover:text-accent"
                                title="Manual Timeline Snapshot"
                            >
                                <History className="w-6 h-6" />
                            </button>

                            {/* Timeline Hover Menu */}
                            <div className="absolute bottom-full mb-4 left-1/2 -translate-x-1/2 hidden group-hover:flex bg-black/80 backdrop-blur-md border border-white/10 rounded-xl p-2 gap-1 w-max">
                                <span className="text-xs text-white/50 px-2 flex items-center">State Graph:</span>
                                {historySnapshot.map((_, i) => (
                                    <button
                                        key={i}
                                        onClick={() => rewindToSnapshot(i)}
                                        className="w-6 h-6 rounded-md bg-white/10 hover:bg-accent text-xs transition-colors"
                                        title={`Rewind to state ${i}`}
                                    >
                                        {i}
                                    </button>
                                ))}
                                {historySnapshot.length === 0 && <span className="text-xs text-white/30 italic px-2">No history</span>}
                            </div>
                        </div>
                    </>
                )}

            </div>

            {/* Quick Settings - always visible, right of dock */}
            <div className="fixed bottom-4 right-4 z-[100]">
                <QuickSettings />
            </div>
        </div>
    );
};
