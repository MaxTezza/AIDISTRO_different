import React, { useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, MeshDistortMaterial, Edges } from '@react-three/drei';
import * as THREE from 'three';
import { useKernelStore, type ThemeSettings } from '../kernel/store';

// A dynamic material that responds to the global KDE-style theme config
const getThemedMaterial = (themeStyle: ThemeSettings['element3DStyle'], accentColor: string) => {
    switch (themeStyle) {
        case 'wireframe':
            return <meshBasicMaterial color={accentColor} wireframe={true} />;
        case 'toon':
            return <meshToonMaterial color={accentColor} />;
        case 'glass':
            return (
                <MeshDistortMaterial
                    color={accentColor}
                    envMapIntensity={1}
                    clearcoat={1}
                    clearcoatRoughness={0.1}
                    metalness={0.1}
                    roughness={0.1}
                    transmission={0.9}
                    opacity={1}
                    transparent
                    distort={0.3}
                    speed={2}
                />
            );
        case 'metallic':
            return <meshStandardMaterial color={accentColor} metalness={1} roughness={0.2} />;
        case 'neon':
            return <meshBasicMaterial color={accentColor} toneMapped={false} />;
        default:
            return <meshStandardMaterial color={accentColor} />;
    }
};

interface AssistantProps {
    accentColor: string;
    styleType: ThemeSettings['element3DStyle'];
}

const AssistantMesh: React.FC<AssistantProps> = ({ accentColor, styleType }) => {
    const meshRef = useRef<THREE.Mesh>(null);
    const [hovered, setHovered] = useState(false);
    const [clicked, setClicked] = useState(false);

    useFrame((_state, delta) => {
        if (meshRef.current) {
            meshRef.current.rotation.x += delta * (hovered ? 0.5 : 0.2);
            meshRef.current.rotation.y += delta * (hovered ? 0.8 : 0.3);

            // Interaction scale pop
            const targetScale = clicked ? 1.4 : (hovered ? 1.2 : 1);
            meshRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.1);
        }
    });

    return (
        <Float speed={2} rotationIntensity={1} floatIntensity={2}>
            <mesh
                ref={meshRef}
                onPointerOver={(e) => { e.stopPropagation(); setHovered(true); document.body.style.cursor = 'pointer'; }}
                onPointerOut={() => { setHovered(false); document.body.style.cursor = 'auto'; }}
                onClick={(e) => { e.stopPropagation(); setClicked(!clicked); }}
            >
                {/* A futuristic abstract icosahedron as the AI mascot */}
                <icosahedronGeometry args={[1, 1]} />
                {getThemedMaterial(styleType, accentColor)}
                {styleType === 'neon' && <Edges color="white" />}
            </mesh>
        </Float>
    );
};

export const FloatingAssistant3D: React.FC = () => {
    const { themeSettings } = useKernelStore();

    return (
        <div className="w-48 h-48 pointer-events-auto">
            <Canvas camera={{ position: [0, 0, 4], fov: 50 }}>
                <ambientLight intensity={0.5} />
                <directionalLight position={[10, 10, 5]} intensity={1.5} />
                <pointLight position={[-10, -10, -10]} intensity={0.5} color={themeSettings.accentColor} />

                <AssistantMesh
                    accentColor={themeSettings.accentColor}
                    styleType={themeSettings.element3DStyle}
                />
            </Canvas>
        </div>
    );
};

// A 3D System Resource visualizer that spins based on activity
const ResourceMesh: React.FC<AssistantProps> = ({ accentColor, styleType }) => {
    const meshRef = useRef<THREE.Mesh>(null);

    useFrame((_state, delta) => {
        if (meshRef.current) {
            // Spin constantly to represent "processing"
            meshRef.current.rotation.y += delta * 1.5;
            meshRef.current.rotation.z += delta * 0.5;
        }
    });

    return (
        <Float speed={3} rotationIntensity={0.5} floatIntensity={0.5}>
            <mesh ref={meshRef}>
                <torusKnotGeometry args={[0.8, 0.2, 100, 16]} />
                {getThemedMaterial(styleType, accentColor)}
            </mesh>
        </Float>
    );
};

export const ResourceMonitor3D: React.FC = () => {
    const { themeSettings } = useKernelStore();

    return (
        <div className="w-32 h-32 pointer-events-auto opacity-80 hover:opacity-100 transition-opacity cursor-crosshair">
            <Canvas camera={{ position: [0, 0, 3], fov: 40 }}>
                <ambientLight intensity={1} />
                <spotLight position={[5, 5, 5]} angle={0.15} penumbra={1} />

                <ResourceMesh
                    accentColor={themeSettings.accentColor}
                    styleType={themeSettings.element3DStyle}
                />
            </Canvas>
        </div>
    );
};
