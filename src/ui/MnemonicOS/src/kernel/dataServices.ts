/**
 * dataServices.ts — Unified data layer for Mnemonic OS.
 *
 * Weather is backed by host-native tooling (via Tauri). Calendar/email are
 * still local fixtures until provider integrations are wired.
 */

import { getWeatherReport } from '../native/api';

// ─── Weather ──────────────────────────────────────────────

export interface WeatherCondition {
    temp: number;           // °F
    high: number;
    low: number;
    condition: 'sunny' | 'cloudy' | 'rainy' | 'partly-cloudy' | 'stormy' | 'snowy';
    humidity: number;       // %
    wind: number;           // mph
    feelsLike: number;
    description: string;
}

export interface ForecastDay {
    day: string;       // "Mon", "Tue", etc.
    high: number;
    low: number;
    condition: WeatherCondition['condition'];
}

const CONDITIONS_META: Record<WeatherCondition['condition'], { icon: string; label: string }> = {
    'sunny': { icon: '☀️', label: 'Sunny' },
    'partly-cloudy': { icon: '⛅', label: 'Partly Cloudy' },
    'cloudy': { icon: '☁️', label: 'Cloudy' },
    'rainy': { icon: '🌧️', label: 'Rainy' },
    'stormy': { icon: '⛈️', label: 'Stormy' },
    'snowy': { icon: '❄️', label: 'Snow' },
};

export function getConditionMeta(c: WeatherCondition['condition']) {
    return CONDITIONS_META[c];
}

const FALLBACK_WEATHER: WeatherCondition = {
    temp: 67,
    high: 68,
    low: 49,
    condition: 'sunny',
    humidity: 45,
    wind: 8,
    feelsLike: 65,
    description: 'Weather data unavailable. Showing local fallback values.',
};

const FALLBACK_FORECAST: ForecastDay[] = [
    { day: 'Mon', high: 72, low: 54, condition: 'sunny' },
    { day: 'Tue', high: 70, low: 53, condition: 'partly-cloudy' },
    { day: 'Wed', high: 65, low: 48, condition: 'rainy' },
    { day: 'Thu', high: 63, low: 46, condition: 'cloudy' },
    { day: 'Fri', high: 69, low: 51, condition: 'sunny' },
];

let weatherCache: WeatherCondition = FALLBACK_WEATHER;
let forecastCache: ForecastDay[] = FALLBACK_FORECAST;
let lastWeatherFetch = 0;
let weatherInFlight: Promise<void> | null = null;

function toDayLabel(isoDate: string): string {
    const parsed = new Date(`${isoDate}T12:00:00`);
    if (Number.isNaN(parsed.getTime())) return isoDate;
    return parsed.toLocaleDateString([], { weekday: 'short' });
}

function toCondition(value: string): WeatherCondition['condition'] {
    if (value === 'sunny' || value === 'partly-cloudy' || value === 'cloudy' || value === 'rainy' || value === 'stormy' || value === 'snowy') {
        return value;
    }
    return 'partly-cloudy';
}

export async function refreshWeather(location?: string, maxAgeMs = 10 * 60 * 1000): Promise<void> {
    const now = Date.now();
    if (now - lastWeatherFetch < maxAgeMs && weatherCache !== FALLBACK_WEATHER) {
        return;
    }
    if (weatherInFlight) {
        return weatherInFlight;
    }

    weatherInFlight = (async () => {
        try {
            const report = await getWeatherReport(location);
            weatherCache = {
                temp: report.temp_f,
                high: report.high_f,
                low: report.low_f,
                condition: toCondition(report.condition),
                humidity: report.humidity,
                wind: report.wind_mph,
                feelsLike: report.feels_like_f,
                description: report.description,
            };
            forecastCache = report.forecast.slice(0, 5).map((day) => ({
                day: toDayLabel(day.day),
                high: day.high_f,
                low: day.low_f,
                condition: toCondition(day.condition),
            }));
            lastWeatherFetch = Date.now();
        } catch {
            // Keep fallback values if native weather retrieval fails.
        } finally {
            weatherInFlight = null;
        }
    })();

    return weatherInFlight;
}

export function getCurrentWeather(): WeatherCondition {
    return weatherCache;
}

export function get5DayForecast(): ForecastDay[] {
    return forecastCache;
}

// ─── Calendar ─────────────────────────────────────────────

export interface CalendarEvent {
    id: string;
    title: string;
    time: string;          // "9:00 AM"
    endTime?: string;      // "10:00 AM"
    location?: string;
    type: 'work' | 'personal' | 'family' | 'health';
    color: string;
}

function safeReadJson<T>(key: string, fallback: T): T {
    if (typeof window === 'undefined') return fallback;
    try {
        const raw = window.localStorage.getItem(key);
        if (!raw) return fallback;
        const parsed = JSON.parse(raw);
        return parsed as T;
    } catch {
        return fallback;
    }
}

// Updated to fetch real calendar events via HTTP AI Distro API
export function getTodayEvents(): CalendarEvent[] {
    const cached = safeReadJson<CalendarEvent[]>('mnemonicos_calendar_today', []);
    if (cached.length > 0) {
        return cached;
    }
    // Fetch asynchronously and cache
    (async () => {
        try {
            const res = await fetch('http://127.0.0.1:17842/api/calendar/data');
            const data = await res.json();
            if (data.status === 'ok' && data.events) {
                const formatted = data.events.map((ev: any, i: number) => ({
                    id: String(i),
                    title: ev.title,
                    time: ev.time,
                    type: 'work',
                    color: '#4A90E2',
                }));
                window.localStorage.setItem('mnemonicos_calendar_today', JSON.stringify(formatted));
            }
        } catch (e) {
            console.error('Failed to fetch Calendar events from AI Distro:', e);
        }
    })();
    return [];
}


export function getNextEvent(): CalendarEvent | null {
    const events = getTodayEvents();
    const now = new Date();
    const currentMinutes = now.getHours() * 60 + now.getMinutes();

    for (const evt of events) {
        const [timePart, ampm] = evt.time.split(' ');
        const [h, m] = timePart.split(':').map(Number);
        const hours24 = ampm === 'PM' && h !== 12 ? h + 12 : ampm === 'AM' && h === 12 ? 0 : h;
        const evtMinutes = hours24 * 60 + m;
        if (evtMinutes > currentMinutes) return evt;
    }
    return null;
}

export function getWeekEvents(): { day: string; events: CalendarEvent[] }[] {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const today = new Date().getDay();
    return days.map((day, i) => ({
        day,
        events: i === today ? getTodayEvents() : [],
    }));
}

// ─── Email ────────────────────────────────────────────────

export interface Email {
    id: string;
    from: string;
    fromEmail: string;
    subject: string;
    preview: string;
    body: string;
    time: string;
    read: boolean;
    starred: boolean;
}

// Updated to fetch real emails via HTTP AI Distro API
export function getEmails(): Email[] {
    // Try to read cached emails
    const cached = safeReadJson<Email[]>('mnemonicos_email_cache', []);
    if (cached.length > 0) {
        return cached;
    }
    // If no cached data, fetch asynchronously (fire-and-forget)
    (async () => {
        try {
            const res = await fetch('http://127.0.0.1:17842/api/email/data');
            const data = await res.json();
            if (data.status === 'ok' && data.emails) {
                const formatted: Email[] = data.emails.map((m: any, i: number) => ({
                    id: String(i),
                    from: m.sender.split(' <')[0].replace(/"/g, ''),
                    fromEmail: m.sender.includes('<') ? m.sender.split('<')[1].replace('>', '') : m.sender,
                    subject: m.subject,
                    preview: m.subject.substring(0, 50) + '...',
                    body: m.subject, // no body text in router output currently
                    time: new Date().toLocaleTimeString([], { hour: 'numeric', minute: 'numeric' }),
                    read: true,
                    starred: false,
                }));
                window.localStorage.setItem('mnemonicos_email_cache', JSON.stringify(formatted));
            }
        } catch (e) {
            console.error('Failed to fetch Gmail messages from AI Distro:', e);
        }
    })();
    return [];
}


export function getUnreadCount(): number {
    return getEmails().filter(e => !e.read).length;
}

// ─── AI Context Engine ───────────────────────────────────

export interface AIInsight {
    message: string;
    icon: string;
    type: 'weather' | 'schedule' | 'email' | 'general';
}

export function getDailyInsight(): AIInsight {
    const weather = getCurrentWeather();
    const events = getTodayEvents();
    const unread = getUnreadCount();

    if (events.length > 0 && weather.low < 60) {
        const firstEvent = events[0];
        return {
            message: `It may drop to ${weather.low}°F later. Your next event is ${firstEvent.title} at ${firstEvent.time}.`,
            icon: '🧥',
            type: 'weather',
        };
    }

    if (unread > 0) {
        return {
            message: `You have ${unread} unread email${unread > 1 ? 's' : ''}.`,
            icon: '📬',
            type: 'email',
        };
    }

    return {
        message: `${weather.description} You have ${events.length} events on your calendar today.`,
        icon: '✨',
        type: 'general',
    };
}

/**
 * Answer a contextual question by cross-referencing data sources
 */
export async function answerQuestion(query: string): Promise<string> {
    const q = query.toLowerCase();
    const weather = getCurrentWeather();
    const events = getTodayEvents();
    const emails = getEmails();
    const unread = emails.filter(e => !e.read);
    const nextEvt = getNextEvent();
    const condMeta = getConditionMeta(weather.condition);

    // "What should I wear?"
    if (q.includes('wear') || q.includes('dress') || q.includes('outfit') || q.includes('clothes')) {
        const eveningEvent = events.find(e => {
            const [timePart, ampm] = e.time.split(' ');
            const [h] = timePart.split(':').map(Number);
            return ampm === 'PM' && h >= 4;
        });

        let advice = `Right now it's ${weather.temp}°F and ${condMeta.label.toLowerCase()}. `;
        if (weather.temp > 75) {
            advice += 'Light clothes — shorts and a t-shirt are perfect. ';
        } else if (weather.temp > 60) {
            advice += 'Comfortable layers. A light long sleeve should work. ';
        } else {
            advice += 'It\'s chilly — grab a jacket or sweater. ';
        }

        if (eveningEvent) {
            advice += `\n\nHeads up: You have "${eveningEvent.title}" at ${eveningEvent.time}`;
            if (eveningEvent.location) advice += ` at ${eveningEvent.location}`;
            advice += `. It\'ll be around ${weather.low}°F by then`;
            if (weather.low < 60) {
                advice += ' — definitely bring a warm layer for you and the kids.';
            } else {
                advice += '.';
            }
        }

        return advice;
    }

    // Schedule questions
    if (q.includes('schedule') || q.includes('calendar') || q.includes('today') || q.includes('plans') || q.includes('busy')) {
        if (events.length === 0) return 'Your day is clear — no events scheduled!';
        let response = `You have ${events.length} events today:\n\n`;
        events.forEach(e => {
            response += `• ${e.time} — ${e.title}`;
            if (e.location) response += ` (${e.location})`;
            response += '\n';
        });
        return response;
    }

    // Next event
    if (q.includes('next') && (q.includes('meeting') || q.includes('event') || q.includes('appointment'))) {
        if (!nextEvt) return 'No more events today. You\'re free!';
        let r = `Your next event is "${nextEvt.title}" at ${nextEvt.time}`;
        if (nextEvt.location) r += ` in ${nextEvt.location}`;
        r += '.';
        return r;
    }

    // Email questions
    if (q.includes('email') || q.includes('mail') || q.includes('inbox') || q.includes('messages')) {
        if (unread.length === 0) return 'Your inbox is clear — no unread emails!';
        let r = `You have ${unread.length} unread email${unread.length > 1 ? 's' : ''}:\n\n`;
        unread.forEach(e => {
            r += `• **${e.from}**: ${e.subject}\n`;
        });
        return r;
    }

    // Weather
    if (q.includes('weather') || q.includes('temperature') || q.includes('cold') || q.includes('hot') || q.includes('rain') || q.includes('outside')) {
        return `It's ${weather.temp}°F and ${condMeta.label.toLowerCase()} ${condMeta.icon}. High of ${weather.high}°, low of ${weather.low}°. ${weather.description}`;
    }

    // System controls — import store lazily to avoid circular deps
    const storeModule = await import('./store');
    const store = storeModule.useKernelStore.getState();

    // Volume control
    if (q.includes('volume') || q.includes('mute') || q.includes('sound') || q.includes('loud') || q.includes('quiet')) {
        if (q.includes('mute') || q.includes('off') || q.includes('silent')) {
            store.setVolume(0);
            return 'Done — I muted the volume for you. Just ask when you want it back.';
        } else if (q.includes('up') || q.includes('louder') || q.includes('raise') || q.includes('increase')) {
            store.setVolume(Math.min(100, store.systemControls.volume + 20));
            return `Volume turned up to ${Math.min(100, store.systemControls.volume + 20)}%.`;
        } else if (q.includes('down') || q.includes('lower') || q.includes('quieter') || q.includes('decrease') || q.includes('quiet')) {
            store.setVolume(Math.max(0, store.systemControls.volume - 20));
            return `Volume turned down to ${Math.max(0, store.systemControls.volume - 20)}%.`;
        } else if (q.includes('max') || q.includes('full') || q.includes('100')) {
            store.setVolume(100);
            return 'Volume set to maximum. 🔊';
        }
        return `Your volume is currently at ${store.systemControls.volume}%. Want me to change it?`;
    }

    // Brightness control
    if (q.includes('brightness') || q.includes('bright') || q.includes('dim') || q.includes('screen')) {
        if (q.includes('up') || q.includes('brighter') || q.includes('raise') || q.includes('increase')) {
            store.setBrightness(Math.min(100, store.systemControls.brightness + 20));
            return `Screen brightness increased to ${Math.min(100, store.systemControls.brightness + 20)}%.`;
        } else if (q.includes('down') || q.includes('dim') || q.includes('lower') || q.includes('decrease')) {
            store.setBrightness(Math.max(10, store.systemControls.brightness - 20));
            return `Screen dimmed to ${Math.max(10, store.systemControls.brightness - 20)}%.`;
        }
        return `Brightness is at ${store.systemControls.brightness}%. Want me to adjust it?`;
    }

    // Night mode
    if (q.includes('night') || q.includes('blue light') || q.includes('eye')) {
        store.toggleNightMode();
        const nowOn = !store.systemControls.nightMode;
        return nowOn
            ? 'Night mode is on — the screen is warmer now to reduce blue light. Easier on your eyes! 🌙'
            : 'Night mode turned off — back to normal colors.';
    }

    // Wi-Fi
    if (q.includes('wifi') || q.includes('wi-fi') || q.includes('internet') || q.includes('network')) {
        if (q.includes('off') || q.includes('disconnect') || q.includes('disable')) {
            if (store.systemControls.wifi) store.toggleWifi();
            return 'Wi-Fi disconnected. You\'re offline now. Let me know when you want to reconnect.';
        } else if (q.includes('on') || q.includes('connect') || q.includes('enable')) {
            if (!store.systemControls.wifi) store.toggleWifi();
            return 'Wi-Fi connected! You\'re back online. 📶';
        }
        return store.systemControls.wifi
            ? 'Wi-Fi is on and connected. Everything looks good.'
            : 'Wi-Fi is currently off. Want me to turn it on?';
    }

    // Bluetooth
    if (q.includes('bluetooth')) {
        store.toggleBluetooth();
        const nowOn = !store.systemControls.bluetooth;
        return nowOn
            ? 'Bluetooth is on. Your devices can connect now.'
            : 'Bluetooth turned off.';
    }

    // Fallback
    return `I can help with your schedule, weather, emails, outfit advice, or system controls. Try "What's on my calendar?", "Turn down the brightness", or "Mute the volume".`;
}
