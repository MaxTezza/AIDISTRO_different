export interface ConnectionInfo {
  protocol: string;
  destination: string;
  is_external: boolean;
}

export interface HostFileEntry {
  name: string;
  path: string;
  is_dir: boolean;
  size_bytes: number;
  modified_unix: number;
}

export interface WeatherForecastDayNative {
  day: string;
  high_f: number;
  low_f: number;
  condition: string;
}

export interface WeatherReportNative {
  temp_f: number;
  high_f: number;
  low_f: number;
  humidity: number;
  wind_mph: number;
  feels_like_f: number;
  condition: string;
  description: string;
  forecast: WeatherForecastDayNative[];
}

async function getInvoke() {
  const mod = await import('@tauri-apps/api/core').catch(() => ({ invoke: null as unknown as null }));
  return mod.invoke;
}

export async function runTerminalCommand(command: string): Promise<string> {
  const invoke = await getInvoke();
  if (!invoke) return 'Tauri API not available in browser.';
  return invoke<string>('run_terminal_command', { command });
}

export async function saveCanvas(content: string): Promise<void> {
  const invoke = await getInvoke();
  if (!invoke) return;
  await invoke('save_to_canvas', { content });
}

export async function getMediaFiles(): Promise<string[]> {
  const invoke = await getInvoke();
  if (!invoke) return [];
  return invoke<string[]>('get_media_files');
}

export async function pingHost(host?: string): Promise<number | null> {
  const invoke = await getInvoke();
  if (!invoke) return null;
  return invoke<number | null>('ping_host', { host });
}

export async function listEstablishedConnections(limit = 8): Promise<ConnectionInfo[]> {
  const invoke = await getInvoke();
  if (!invoke) return [];
  return invoke<ConnectionInfo[]>('list_established_connections', { limit });
}

export async function setSystemVolume(percent: number): Promise<string> {
  const invoke = await getInvoke();
  if (!invoke) return 'Tauri API not available in browser.';
  return invoke<string>('set_system_volume', { percent: Math.max(0, Math.min(100, Math.round(percent))) });
}

export async function toggleSystemMute(): Promise<string> {
  const invoke = await getInvoke();
  if (!invoke) return 'Tauri API not available in browser.';
  return invoke<string>('toggle_system_mute');
}

export async function listFiles(path?: string, limit = 300): Promise<HostFileEntry[]> {
  const invoke = await getInvoke();
  if (!invoke) return [];
  return invoke<HostFileEntry[]>('list_files', { path, limit });
}

export async function getWeatherReport(location?: string): Promise<WeatherReportNative> {
  try {
    // Notify AI Distro backend to keep provider active
    await fetch('http://127.0.0.1:17842/api/provider/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: 'weather', provider: 'default' })
    });
  } catch (e) {
    // Ignore error if backend is unavailable
  }

  const invoke = await getInvoke();
  if (!invoke) {
    throw new Error('Tauri API not available in browser.');
  }
  return invoke<WeatherReportNative>('get_weather_report', { location });
}
export async function setBrightness(percent: number): Promise<string> {
  const invoke = await getInvoke();
  if (!invoke) return 'Tauri API not available in browser.';
  return invoke<string>('set_brightness', { percent: Math.max(0, Math.min(100, Math.round(percent))) });
}

export async function toggleWifi(): Promise<string> {
  const invoke = await getInvoke();
  if (!invoke) return 'Tauri API not available in browser.';
  return invoke<string>('toggle_wifi');
}

export async function toggleBluetooth(): Promise<string> {
  const invoke = await getInvoke();
  if (!invoke) return 'Tauri API not available in browser.';
  return invoke<string>('toggle_bluetooth');
}

export async function toggleNightMode(): Promise<string> {
  const invoke = await getInvoke();
  if (!invoke) return 'Tauri API not available in browser.';
  return invoke<string>('toggle_night_mode');
}

export async function toggleDoNotDisturb(): Promise<string> {
  const invoke = await getInvoke();
  if (!invoke) return 'Tauri API not available in browser.';
  return invoke<string>('toggle_do_not_disturb');
}

export async function simulateSystemCrash(): Promise<string> {
  throw new Error('System unrecoverable error simulated. This is a deliberate artificial crash for MnemonicOS error handling testing.');
}

export async function captureScreenContext(): Promise<string> {
  try {
    const activeWindow = document.querySelector('.window-panel:not(.hidden)');
    if (activeWindow) {
      const textContext = activeWindow.textContent?.substring(0, 1000) || 'Blank Window';
      const windowTitle = activeWindow.querySelector('h2')?.textContent || 'Unknown App';
      return `Context Capture [Window: ${windowTitle}]: ${textContext}`;
    }
  } catch (e) {
    console.error(e)
  }

  return "Context Capture: Focus is on Empty Desktop.";
}
