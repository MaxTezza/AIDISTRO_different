import React, { useState } from 'react';
import { getTodayEvents, getWeekEvents, type CalendarEvent } from '../kernel/dataServices';
import { MapPin, Clock } from 'lucide-react';

export const CalendarApp: React.FC = () => {
    const [view, setView] = useState<'today' | 'week'>('today');
    const todayEvents = getTodayEvents();
    const weekData = getWeekEvents();
    const todayIdx = new Date().getDay();

    return (
        <div className="h-full overflow-y-auto flex flex-col">
            {/* View Toggle */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/8">
                <h2 className="text-lg font-light text-white">
                    {view === 'today'
                        ? new Date().toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' })
                        : 'This Week'}
                </h2>
                <div className="flex bg-white/[0.05] rounded-lg overflow-hidden border border-white/10">
                    <button
                        onClick={() => setView('today')}
                        className={`px-3 py-1.5 text-xs font-medium transition-colors ${view === 'today' ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/60'
                            }`}
                    >
                        Today
                    </button>
                    <button
                        onClick={() => setView('week')}
                        className={`px-3 py-1.5 text-xs font-medium transition-colors ${view === 'week' ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/60'
                            }`}
                    >
                        Week
                    </button>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
                {view === 'today' ? (
                    <div className="space-y-3">
                        {todayEvents.length === 0 ? (
                            <div className="text-center py-12 text-white/30">
                                <p className="text-lg">No events today</p>
                                <p className="text-sm mt-1">Enjoy your free time!</p>
                            </div>
                        ) : (
                            todayEvents.map(evt => <EventCard key={evt.id} event={evt} />)
                        )}
                    </div>
                ) : (
                    <div className="space-y-4">
                        {weekData.map((dayData, i) => (
                            <div key={dayData.day}>
                                <div className={`text-xs font-semibold uppercase tracking-wider mb-2 ${i === todayIdx ? 'text-cyan-400' : 'text-white/30'
                                    }`}>
                                    {dayData.day} {i === todayIdx && '(Today)'}
                                </div>
                                {dayData.events.length > 0 ? (
                                    <div className="space-y-2 ml-3 border-l border-white/8 pl-4">
                                        {dayData.events.map(evt => <EventCard key={evt.id} event={evt} compact />)}
                                    </div>
                                ) : (
                                    <div className="text-xs text-white/20 ml-3 border-l border-white/5 pl-4 py-1">
                                        No events
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

const EventCard: React.FC<{ event: CalendarEvent; compact?: boolean }> = ({ event, compact }) => (
    <div className={`bg-white/[0.03] border border-white/8 rounded-xl ${compact ? 'p-3' : 'p-4'} flex items-start gap-3 hover:bg-white/[0.06] transition-colors`}>
        <div className="w-1 self-stretch rounded-full shrink-0" style={{ backgroundColor: event.color }} />
        <div className="flex-1 min-w-0">
            <div className={`font-medium text-white/80 ${compact ? 'text-xs' : 'text-sm'}`}>{event.title}</div>
            <div className="flex items-center gap-3 mt-1">
                <span className="flex items-center gap-1 text-xs text-white/35">
                    <Clock className="w-3 h-3" />
                    {event.time}{event.endTime ? ` – ${event.endTime}` : ''}
                </span>
                {event.location && (
                    <span className="flex items-center gap-1 text-xs text-white/35 truncate">
                        <MapPin className="w-3 h-3" /> {event.location}
                    </span>
                )}
            </div>
        </div>
        <span className={`text-[10px] px-2 py-0.5 rounded-full capitalize ${event.type === 'work' ? 'bg-indigo-500/20 text-indigo-300' :
            event.type === 'family' ? 'bg-amber-500/20 text-amber-300' :
                event.type === 'health' ? 'bg-red-500/20 text-red-300' :
                    'bg-emerald-500/20 text-emerald-300'
            }`}>
            {event.type}
        </span>
    </div>
);
