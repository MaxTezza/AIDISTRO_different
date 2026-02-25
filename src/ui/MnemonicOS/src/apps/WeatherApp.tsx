import React from 'react';
import {
    getCurrentWeather, getConditionMeta, get5DayForecast, refreshWeather,
} from '../kernel/dataServices';
import { Wind, Droplets, Thermometer, Eye } from 'lucide-react';

export const WeatherApp: React.FC = () => {
    const [, forceRender] = React.useState(0);

    React.useEffect(() => {
        let mounted = true;
        refreshWeather().finally(() => {
            if (mounted) forceRender((n) => n + 1);
        });
        return () => {
            mounted = false;
        };
    }, []);

    const weather = getCurrentWeather();
    const condMeta = getConditionMeta(weather.condition);
    const forecast = get5DayForecast();

    return (
        <div className="h-full overflow-y-auto p-6 bg-gradient-to-b from-blue-900/30 to-transparent">
            {/* Current Conditions */}
            <div className="flex items-start gap-6 mb-8">
                <div>
                    <span className="text-6xl block mb-2">{condMeta.icon}</span>
                </div>
                <div>
                    <div className="text-5xl font-extralight text-white">{weather.temp}°F</div>
                    <div className="text-lg text-white/50 mt-1">{condMeta.label}</div>
                    <p className="text-sm text-white/40 mt-2 max-w-xs">{weather.description}</p>
                </div>
            </div>

            {/* Details Grid */}
            <div className="grid grid-cols-4 gap-3 mb-8">
                <DetailCard icon={<Thermometer className="w-4 h-4" />} label="Feels Like" value={`${weather.feelsLike}°`} />
                <DetailCard icon={<Wind className="w-4 h-4" />} label="Wind" value={`${weather.wind} mph`} />
                <DetailCard icon={<Droplets className="w-4 h-4" />} label="Humidity" value={`${weather.humidity}%`} />
                <DetailCard icon={<Eye className="w-4 h-4" />} label="High / Low" value={`${weather.high}° / ${weather.low}°`} />
            </div>

            {/* 5-Day Forecast */}
            <h3 className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-3">5-Day Forecast</h3>
            <div className="grid grid-cols-5 gap-2">
                {forecast.map(day => (
                    <div key={day.day} className="bg-white/[0.04] border border-white/8 rounded-xl p-3 text-center">
                        <div className="text-xs text-white/50 font-medium mb-2">{day.day}</div>
                        <div className="text-2xl mb-2">{getConditionMeta(day.condition).icon}</div>
                        <div className="text-xs text-white/70">{day.high}°</div>
                        <div className="text-xs text-white/30">{day.low}°</div>
                    </div>
                ))}
            </div>
        </div>
    );
};

const DetailCard: React.FC<{ icon: React.ReactNode; label: string; value: string }> = ({ icon, label, value }) => (
    <div className="bg-white/[0.04] border border-white/8 rounded-xl p-3">
        <div className="flex items-center gap-1.5 text-white/30 mb-1">{icon}<span className="text-[10px] uppercase tracking-wider">{label}</span></div>
        <div className="text-sm text-white/80 font-medium">{value}</div>
    </div>
);
