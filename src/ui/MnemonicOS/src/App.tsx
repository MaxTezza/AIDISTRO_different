import { Shell } from './shell/Shell';
import { useKernelStore } from './kernel/store';
import { OmniCommandBar } from './shell/OmniCommandBar';

function App() {
  const { systemControls } = useKernelStore();
  const brightness = systemControls.brightness / 100;
  const nightMode = systemControls.nightMode;

  return (
    <div
      style={{
        filter: `brightness(${brightness})${nightMode ? ' sepia(0.3) saturate(0.8)' : ''}`,
        transition: 'filter 0.5s ease',
        width: '100%',
        height: '100%',
      }}
    >
      {/* Night mode warm overlay */}
      {nightMode && (
        <div
          className="fixed inset-0 pointer-events-none z-[9999]"
          style={{ backgroundColor: 'rgba(255, 140, 0, 0.08)' }}
        />
      )}
      <Shell />
      <OmniCommandBar />
    </div>
  );
}

export default App;
