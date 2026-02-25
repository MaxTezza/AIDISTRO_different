import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertOctagon, RefreshCw } from 'lucide-react';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    isTranslating: boolean;
    translatedExplanation: string | null;
}

export class GlobalErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null,
        isTranslating: false,
        translatedExplanation: null
    };

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error, isTranslating: true, translatedExplanation: null };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('Uncaught error:', error, errorInfo);
        this.translateErrorWithAI(error);
    }

    private async translateErrorWithAI(error: Error) {
        // Here we hit the local AI Distro shell to ask for plain English explanation
        try {
            const rawTrace = error.stack || error.message;

            const response = await fetch('http://127.0.0.1:17842/api/agent/request', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: `A system UI crash occurred. The user is non-technical. Do not show them stack traces. Briefly apologize and explain what broke in 1 simple sentence, and offer a 1 sentence fix. Here is the raw trace: ${rawTrace.substring(0, 500)}`
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.setState({
                    isTranslating: false,
                    translatedExplanation: data.text || "Something went wrong internally, but it shouldn't happen again."
                });
            } else {
                throw new Error("AI Backend returned error");
            }
        } catch (err) {
            console.error(err);
            // Fallback if local AI is dead
            this.setState({
                isTranslating: false,
                translatedExplanation: "We hit a snag loading this screen. It's not your fault, we just need to restart the interface."
            });
        }
    }

    private resetError = () => {
        this.setState({ hasError: false, error: null, translatedExplanation: null, isTranslating: false });
    }

    public render() {
        if (this.state.hasError) {
            return (
                <div className="fixed inset-0 z-[9999] bg-red-950/90 backdrop-blur-xl flex items-center justify-center p-6 font-sans">
                    <div className="max-w-md w-full bg-black/60 border border-red-500/30 rounded-3xl p-8 shadow-2xl flex flex-col items-center text-center animate-in zoom-in-95 duration-300">
                        <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center mb-6">
                            <AlertOctagon className="w-10 h-10 text-red-500" />
                        </div>

                        <h1 className="text-2xl font-bold text-white mb-2 tracking-tight">Oops. That wasn't supposed to happen.</h1>

                        <div className="w-full bg-white/5 border border-white/10 rounded-xl p-6 mb-8 mt-4 min-h-[120px] flex items-center justify-center">
                            {this.state.isTranslating ? (
                                <div className="flex flex-col items-center text-white/50 space-y-3 gap-2">
                                    <RefreshCw className="w-6 h-6 animate-spin text-accent" />
                                    <p className="text-sm font-medium tracking-wide">Mnemonic AI is digesting the crash log...</p>
                                </div>
                            ) : (
                                <p className="text-white/80 text-lg leading-relaxed font-serif">
                                    {this.state.translatedExplanation}
                                </p>
                            )}
                        </div>

                        <button
                            onClick={this.resetError}
                            className="w-full py-4 bg-white text-black font-bold rounded-xl hover:bg-white/90 transition-colors shadow-lg active:scale-[0.98]"
                        >
                            Restart Desktop Interface
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}
