import React, { useState, useRef, useEffect } from 'react';
import { useKernelStore } from '../kernel/store';
import { answerQuestion } from '../kernel/dataServices';
import { Bot, User, X, Send, Mic, MicOff, Sparkles } from 'lucide-react';

type Message = { id: string; role: 'user' | 'guide'; text: string; typing?: boolean };

// Filler phrases the AI uses while "thinking" to mask latency
const FILLERS = [
    "Let me check that for you...",
    "One sec, pulling that up...",
    "Good question — looking into it now...",
    "Hmm, let me think about that...",
    "Sure thing, checking your data...",
    "On it — give me just a moment...",
];

export const MnemonicGuide: React.FC = () => {
    const { isGuideOpen, toggleGuide, userProfile } = useKernelStore();
    const displayName = userProfile.displayName || 'there';

    const [messages, setMessages] = useState<Message[]>([
        {
            id: '0',
            role: 'guide',
            text: `Hey ${displayName}! I'm your personal assistant. Ask me anything — what to wear today, your schedule, unread emails, or just chat. You can also tap the mic to talk.`
        }
    ]);
    const [input, setInput] = useState('');
    const [isListening, setIsListening] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);
    const recognitionRef = useRef<any>(null);

    useEffect(() => {
        if (isGuideOpen) {
            setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
        }
    }, [messages, isGuideOpen]);

    // Web Speech API setup
    useEffect(() => {
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (SpeechRecognition) {
            const recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';

            recognition.onresult = (event: any) => {
                const transcript = event.results[0][0].transcript;
                setInput(transcript);
                setIsListening(false);
                // Auto-send voice input
                setTimeout(() => {
                    processMessage(transcript);
                }, 200);
            };

            recognition.onerror = () => setIsListening(false);
            recognition.onend = () => setIsListening(false);

            recognitionRef.current = recognition;
        }
    }, []);

    const toggleVoice = () => {
        if (!recognitionRef.current) return;
        if (isListening) {
            recognitionRef.current.stop();
            setIsListening(false);
        } else {
            recognitionRef.current.start();
            setIsListening(true);
        }
    };

    const processMessage = (text: string) => {
        const userText = text.trim();
        if (!userText) return;

        const userMsg: Message = { id: Date.now().toString(), role: 'user', text: userText };
        setMessages(prev => [...prev, userMsg]);
        setInput('');

        // Show filler immediately (masks latency)
        const filler = FILLERS[Math.floor(Math.random() * FILLERS.length)];
        const fillerMsg: Message = { id: (Date.now() + 1).toString(), role: 'guide', text: filler, typing: true };
        setMessages(prev => [...prev, fillerMsg]);

        // Simulate AI "working" then replace filler with real answer
        const thinkTime = 800 + Math.random() * 600; // 800-1400ms feels realistic
        setTimeout(async () => {
            const answer = await answerQuestion(userText);
            setMessages(prev =>
                prev.map(m => m.id === fillerMsg.id ? { ...m, text: answer, typing: false } : m)
            );
        }, thinkTime);
    };

    const handleSend = () => {
        processMessage(input);
    };

    if (!isGuideOpen) return null;

    const accentColor = userProfile.accentColor || '#22d3ee';

    return (
        <div className="fixed bottom-24 right-6 w-96 h-[480px] bg-black/95 backdrop-blur-2xl border border-white/15 rounded-2xl shadow-[0_0_60px_rgba(0,0,0,0.8)] flex flex-col z-[150] overflow-hidden animate-in slide-in-from-bottom-10 fade-in">
            {/* Header */}
            <div className="p-4 border-b border-white/10 flex items-center justify-between" style={{ background: `linear-gradient(135deg, ${accentColor}15, transparent)` }}>
                <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-xl flex items-center justify-center" style={{ backgroundColor: `${accentColor}20` }}>
                        <Sparkles className="w-4 h-4" style={{ color: accentColor }} />
                    </div>
                    <div>
                        <h3 className="font-semibold text-white text-sm">Mnemonic</h3>
                        <div className="text-[10px] text-white/30">Your personal assistant</div>
                    </div>
                </div>
                <button onClick={toggleGuide} className="text-white/40 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-white/10">
                    <X className="w-4 h-4" />
                </button>
            </div>

            {/* Quick Actions */}
            <div className="px-4 py-2.5 border-b border-white/5 flex gap-2 overflow-x-auto">
                {[
                    "What should I wear?",
                    "What's on my schedule?",
                    "Any emails?",
                    "What's the weather?",
                ].map(q => (
                    <button
                        key={q}
                        onClick={() => processMessage(q)}
                        className="shrink-0 px-3 py-1.5 bg-white/[0.04] border border-white/8 rounded-full text-[11px] text-white/50 hover:text-white/80 hover:bg-white/[0.08] transition-all"
                    >
                        {q}
                    </button>
                ))}
            </div>

            {/* Chat History */}
            <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
                {messages.map(msg => (
                    <div key={msg.id} className={`flex gap-2.5 max-w-[88%] ${msg.role === 'user' ? 'ml-auto flex-row-reverse' : ''}`}>
                        <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-1 ${msg.role === 'user' ? 'bg-white/15' : ''}`}
                            style={msg.role === 'guide' ? { backgroundColor: `${accentColor}20` } : {}}>
                            {msg.role === 'user' ? <User className="w-3 h-3 text-white/60" /> : <Bot className="w-3 h-3" style={{ color: accentColor }} />}
                        </div>
                        <div className={`p-3 rounded-2xl text-sm leading-relaxed ${msg.role === 'user'
                            ? 'bg-white/10 text-white rounded-tr-sm'
                            : `bg-white/[0.04] border border-white/8 text-white/80 rounded-tl-sm`
                            } ${msg.typing ? 'animate-pulse' : ''}`}>
                            {msg.text.split('\n').map((line, i) => (
                                <React.Fragment key={i}>
                                    {line}
                                    {i < msg.text.split('\n').length - 1 && <br />}
                                </React.Fragment>
                            ))}
                        </div>
                    </div>
                ))}
                <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="p-3 border-t border-white/8 bg-black/50">
                <div className="flex items-center gap-2 bg-white/[0.04] rounded-2xl px-3 py-2 border border-white/8 focus-within:border-white/20 transition-colors">
                    {/* Mic button */}
                    <button
                        onClick={toggleVoice}
                        className={`p-1.5 rounded-full transition-all ${isListening
                            ? 'bg-red-500/20 text-red-400 animate-pulse'
                            : 'text-white/30 hover:text-white/60 hover:bg-white/10'
                            }`}
                        title={isListening ? 'Stop listening' : 'Voice input'}
                    >
                        {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                    </button>

                    <input
                        type="text"
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleSend()}
                        placeholder={isListening ? 'Listening...' : 'Ask me anything...'}
                        className="flex-1 bg-transparent border-none outline-none text-sm text-white placeholder-white/30"
                    />

                    <button
                        onClick={handleSend}
                        disabled={!input.trim()}
                        className="p-1.5 rounded-full disabled:opacity-20 hover:bg-white/10 transition-all"
                        style={{ color: accentColor }}
                    >
                        <Send className="w-4 h-4" />
                    </button>
                </div>
            </div>
        </div>
    );
};
