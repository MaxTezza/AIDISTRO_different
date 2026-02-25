import React from 'react';
import { useKernelStore, type ThemeSettings } from '../kernel/store';
import { Palette, Box, Layers, Play } from 'lucide-react';

export const ThemeEngineApp: React.FC = () => {
    const { themeSettings, updateThemeSettings } = useKernelStore();

    const handleColorChange = (color: string) => {
        updateThemeSettings({ accentColor: color });
    };

    const handle3DStyleChange = (style: ThemeSettings['element3DStyle']) => {
        updateThemeSettings({ element3DStyle: style });
    };

    const handleAnimationChange = (anim: ThemeSettings['windowAnimationConfig']) => {
        updateThemeSettings({ windowAnimationConfig: anim });
    };

    const handleBlurChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        updateThemeSettings({ blurStrength: Number(e.target.value) });
    };

    const handleOpacityChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        updateThemeSettings({ windowOpacity: Number(e.target.value) });
    };

    const colors = ['#22d3ee', '#818cf8', '#f472b6', '#34d399', '#fbbf24', '#f87171'];
    const styles: ThemeSettings['element3DStyle'][] = ['glass', 'metallic', 'toon', 'wireframe', 'neon'];
    const animations: ThemeSettings['windowAnimationConfig'][] = ['spring', 'tween', 'none'];

    return (
        <div className="h-full flex flex-col pt-4 overflow-y-auto custom-scrollbar">
            <div className="px-6 mb-6 text-center">
                <h2 className="text-2xl font-light text-white flex items-center justify-center gap-2">
                    <Palette className="w-6 h-6 text-accent" style={{ color: themeSettings.accentColor }} />
                    Mnemonic Theme Engine
                </h2>
                <p className="text-sm text-white/50 mt-1">Plasma-grade Global UI Configuration</p>
            </div>

            <div className="flex-1 px-6 space-y-6 pb-6">

                {/* Accent Color Selection */}
                <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-3 text-white/80 font-medium">
                        <Palette className="w-4 h-4" /> Global Accent Color
                    </div>
                    <div className="flex gap-3 flex-wrap">
                        {colors.map(c => (
                            <button
                                key={c}
                                onClick={() => handleColorChange(c)}
                                className={`w-8 h-8 rounded-full border-2 transition-transform hover:scale-110 ${themeSettings.accentColor === c ? 'border-white scale-110 shadow-lg' : 'border-transparent'}`}
                                style={{ backgroundColor: c, boxShadow: themeSettings.accentColor === c ? `0 0 15px ${c}` : 'none' }}
                                aria-label={`Set color to ${c}`}
                            />
                        ))}
                    </div>
                </div>

                {/* 3D Element Compositing */}
                <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-3 text-white/80 font-medium">
                        <Box className="w-4 h-4" /> 3D Element Materials
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                        {styles.map(s => (
                            <button
                                key={s}
                                onClick={() => handle3DStyleChange(s)}
                                className={`px-3 py-2 rounded-lg text-sm border capitalize transition-colors ${themeSettings.element3DStyle === s
                                    ? 'bg-white/10 text-white'
                                    : 'border-white/5 bg-transparent text-white/40 hover:bg-white/5'}`}
                                style={{ borderColor: themeSettings.element3DStyle === s ? themeSettings.accentColor : '' }}
                            >
                                {s}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Glassmorphism Compositor */}
                <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-4 text-white/80 font-medium">
                        <Layers className="w-4 h-4" /> UI Compositor / Compositing
                    </div>

                    <div className="space-y-4">
                        <div>
                            <div className="flex justify-between text-xs text-white/50 mb-1">
                                <span>Background Blur</span>
                                <span>{themeSettings.blurStrength}px</span>
                            </div>
                            <input
                                type="range"
                                min="0" max="40"
                                value={themeSettings.blurStrength}
                                onChange={handleBlurChange}
                                className="w-full accent-white"
                                style={{ accentColor: themeSettings.accentColor }}
                            />
                        </div>

                        <div>
                            <div className="flex justify-between text-xs text-white/50 mb-1">
                                <span>Base Opacity</span>
                                <span>{Math.round(themeSettings.windowOpacity * 100)}%</span>
                            </div>
                            <input
                                type="range"
                                min="0.5" max="1" step="0.05"
                                value={themeSettings.windowOpacity}
                                onChange={handleOpacityChange}
                                className="w-full"
                                style={{ accentColor: themeSettings.accentColor }}
                            />
                        </div>
                    </div>
                </div>

                {/* Physics & Animations */}
                <div className="bg-black/20 border border-white/10 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-3 text-white/80 font-medium">
                        <Play className="w-4 h-4" /> Kinetic Animations
                    </div>
                    <div className="flex gap-2">
                        {animations.map(a => (
                            <button
                                key={a}
                                onClick={() => handleAnimationChange(a)}
                                className={`flex-1 px-2 py-1.5 rounded-lg text-xs border capitalize transition-colors ${themeSettings.windowAnimationConfig === a
                                    ? 'bg-white/10 text-white'
                                    : 'border-white/5 bg-transparent text-white/40 hover:bg-white/5'}`}
                                style={{ borderColor: themeSettings.windowAnimationConfig === a ? themeSettings.accentColor : '' }}
                            >
                                {a}
                            </button>
                        ))}
                    </div>
                </div>

            </div>
        </div>
    );
};
