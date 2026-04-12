import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useKernelStore } from '../kernel/store';

// ─── Snap Zones ──────────────────────────────────────────
// Dragging a window to the edges snaps it to predefined layouts
type SnapZone = 'left' | 'right' | 'top' | null;

const SNAP_THRESHOLD = 20; // pixels from edge to trigger snap

function detectSnapZone(x: number, y: number): SnapZone {
    if (x <= SNAP_THRESHOLD) return 'left';
    if (x >= window.innerWidth - SNAP_THRESHOLD) return 'right';
    if (y <= SNAP_THRESHOLD) return 'top'; // maximize
    return null;
}

function getSnapBounds(zone: SnapZone): { x: number; y: number; width: number; height: number } | null {
    if (!zone) return null;
    const taskbarHeight = 70; // bottom taskbar
    const h = window.innerHeight - taskbarHeight;
    switch (zone) {
        case 'left': return { x: 0, y: 0, width: Math.floor(window.innerWidth / 2), height: h };
        case 'right': return { x: Math.floor(window.innerWidth / 2), y: 0, width: Math.floor(window.innerWidth / 2), height: h };
        case 'top': return { x: 0, y: 0, width: window.innerWidth, height: h };
        default: return null;
    }
}

// ─── Snap Preview Overlay ────────────────────────────────
// Shows a translucent preview where the window will land

export const SnapPreview: React.FC<{ zone: SnapZone }> = ({ zone }) => {
    if (!zone) return null;
    const bounds = getSnapBounds(zone);
    if (!bounds) return null;

    return (
        <div
            className="fixed z-[45] pointer-events-none transition-all duration-200 ease-out"
            style={{
                left: bounds.x + 6,
                top: bounds.y + 6,
                width: bounds.width - 12,
                height: bounds.height - 12,
                background: 'rgba(34, 211, 238, 0.08)',
                border: '2px solid rgba(34, 211, 238, 0.25)',
                borderRadius: '16px',
                backdropFilter: 'blur(4px)',
            }}
        />
    );
};

// ─── WindowPanel ─────────────────────────────────────────

interface DraggableWindowProps {
    id: string;
    title: string;
    children: React.ReactNode;
    isActive: boolean;
    onFocus: () => void;
    onClose: () => void;
    initialPos?: { x: number; y: number };
    // Store-bound position/size
    x: number;
    y: number;
    width?: number;
    height?: number;
    onUpdateBounds?: (bounds: { x?: number; y?: number; width?: number; height?: number }) => void;
}

export const WindowPanel: React.FC<DraggableWindowProps> = ({
    title, children, isActive, onFocus, onClose,
    x, y, width = 600, height = 400, onUpdateBounds
}) => {
    const [pos, setPos] = React.useState({ x, y });
    const [size, setSize] = React.useState({ width, height });
    const [isDragging, setIsDragging] = React.useState(false);
    const [snapZone, setSnapZone] = React.useState<SnapZone>(null);
    const [isSnapped, setIsSnapped] = React.useState(false);
    const [preSnapBounds, setPreSnapBounds] = React.useState<{ x: number; y: number; w: number; h: number } | null>(null);
    const [isMaximized, setIsMaximized] = React.useState(false);

    // Theme Engine bindings
    const { themeSettings } = useKernelStore();
    const isAnimationsEnabled = themeSettings.windowAnimationConfig !== 'none';
    const transitionConfig: any = themeSettings.windowAnimationConfig === 'spring'
        ? { type: 'spring', damping: 20, stiffness: 200 }
        : { type: 'tween', duration: 0.2 };

    const handleMouseDown = React.useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        onFocus();
        // If snapped, restore to floating on drag start
        if (isSnapped) {
            setPreSnapBounds(null);
            setIsSnapped(false);
            setIsMaximized(false);
            // Center window on cursor when unsnapping
            setSize({ width: 600, height: 400 });
            setPos({ x: e.clientX - 300, y: e.clientY - 20 });
        }
        setIsDragging(true);
    }, [onFocus, isSnapped]);

    const handleMouseUp = React.useCallback(() => {
        if (isDragging && snapZone) {
            // Snap the window
            const bounds = getSnapBounds(snapZone);
            if (bounds) {
                if (!isSnapped) {
                    setPreSnapBounds({ x: pos.x, y: pos.y, w: size.width, h: size.height });
                }
                setPos({ x: bounds.x, y: bounds.y });
                setSize({ width: bounds.width, height: bounds.height });
                setIsSnapped(true);
                setIsMaximized(snapZone === 'top');
                if (onUpdateBounds) {
                    onUpdateBounds(bounds);
                }
            }
        } else if (isDragging && onUpdateBounds) {
            onUpdateBounds({ x: pos.x, y: pos.y });
        }
        setIsDragging(false);
        setSnapZone(null);
    }, [isDragging, snapZone, pos, size, isSnapped, onUpdateBounds]);

    const handleMouseMove = React.useCallback((e: MouseEvent) => {
        if (isDragging) {
            const newX = pos.x + e.movementX;
            const newY = pos.y + e.movementY;
            setPos({ x: newX, y: Math.max(0, newY) });

            // Detect snap zones
            const zone = detectSnapZone(e.clientX, e.clientY);
            setSnapZone(zone);
        }
    }, [isDragging, pos]);

    // Double-click titlebar to maximize/restore
    const handleDoubleClick = React.useCallback(() => {
        if (isMaximized && preSnapBounds) {
            setPos({ x: preSnapBounds.x, y: preSnapBounds.y });
            setSize({ width: preSnapBounds.w, height: preSnapBounds.h });
            setIsSnapped(false);
            setIsMaximized(false);
            setPreSnapBounds(null);
        } else {
            const taskbarHeight = 70;
            setPreSnapBounds({ x: pos.x, y: pos.y, w: size.width, h: size.height });
            setPos({ x: 0, y: 0 });
            setSize({ width: window.innerWidth, height: window.innerHeight - taskbarHeight });
            setIsSnapped(true);
            setIsMaximized(true);
        }
    }, [isMaximized, preSnapBounds, pos, size]);

    React.useEffect(() => {
        if (isDragging) {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
        } else {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        }
        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isDragging, handleMouseMove, handleMouseUp]);

    const borderRadius = (isSnapped && (snapZone === 'top' || isMaximized)) ? '0px' : '16px';

    return (
        <AnimatePresence>
            {/* Snap Preview overlay */}
            {isDragging && <SnapPreview zone={snapZone} />}

            <motion.div
                initial={isAnimationsEnabled ? { opacity: 0, scale: 0.9, y: pos.y + 20 } : undefined}
                animate={{
                    opacity: themeSettings.windowOpacity,
                    scale: 1,
                    x: Math.max(0, pos.x),
                    y: Math.max(0, pos.y),
                    width: size.width,
                    height: size.height,
                    borderRadius
                }}
                exit={isAnimationsEnabled ? { opacity: 0, scale: 0.9, y: pos.y + 20 } : undefined}
                transition={isAnimationsEnabled ? transitionConfig : { duration: 0 }}
                className={`absolute glass-panel flex flex-col overflow-hidden
                    ${isActive ? 'shadow-[0_0_30px_rgba(34,211,238,0.15)] border-white/20 z-50' : 'shadow-lg border-white/5 z-10'}`}
                style={{
                    backdropFilter: `blur(${themeSettings.blurStrength}px)`,
                    WebkitBackdropFilter: `blur(${themeSettings.blurStrength}px)`,
                    background: `rgba(0, 0, 0, ${(1 - themeSettings.windowOpacity) * 0.5})`
                }}
                onClick={onFocus}
            >
                {/* Titlebar */}
                <div
                    className="h-10 bg-white/[0.03] border-b border-white/8 flex items-center justify-between px-4 cursor-move select-none shrink-0"
                    onMouseDown={handleMouseDown}
                    onDoubleClick={handleDoubleClick}
                >
                    <div className="font-medium text-sm text-white/70 tracking-wide">{title}</div>
                    <div className="flex items-center gap-1.5">
                        {/* Minimize (dot) */}
                        <button
                            onClick={(e) => { e.stopPropagation(); /* future minimize */ }}
                            className="w-3 h-3 rounded-full bg-amber-400/40 hover:bg-amber-400 transition-colors"
                            title="Minimize"
                        />
                        {/* Maximize */}
                        <button
                            onClick={(e) => { e.stopPropagation(); handleDoubleClick(); }}
                            className="w-3 h-3 rounded-full bg-green-400/40 hover:bg-green-400 transition-colors"
                            title={isMaximized ? "Restore" : "Maximize"}
                        />
                        {/* Close */}
                        <button
                            onClick={(e) => { e.stopPropagation(); onClose(); }}
                            className="w-3 h-3 rounded-full bg-red-400/40 hover:bg-red-500 transition-colors"
                            title="Close"
                        />
                    </div>
                </div>

                <div className="bg-transparent flex-1 overflow-auto text-gray-300">
                    {children}
                </div>
            </motion.div>
        </AnimatePresence>
    );
};
