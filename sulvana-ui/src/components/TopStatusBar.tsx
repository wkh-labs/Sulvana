import React, { useState, useRef, useEffect } from 'react';
import {
  Cpu,
  Download,
  Settings,
  ChevronDown,
  Sparkles,
  Check,
  Layers,
  Maximize2,
  Minimize2,
  Eye,
  Sliders,
} from 'lucide-react';
import { HardwareStatusState, LocalModel } from '../types/sulvana';

interface TopStatusBarProps {
  models: LocalModel[];
  activeModel: LocalModel;
  onSelectModel: (model: LocalModel) => void;
  hardwareState: HardwareStatusState;
  onSimulateHardwareState: (state: HardwareStatusState) => void;
  liveTokPerSec: number;
  activeDownloadsCount: number;
  activeDownloadPercent: number | null;
  onOpenDownloads: () => void;
  onOpenSettings: () => void;
  onOpenSpecModal: () => void;
  javafxInspectorActive: boolean;
  onToggleJavafxInspector: () => void;
  compact800x600: boolean;
  onToggleCompact800x600: () => void;
}

export const TopStatusBar: React.FC<TopStatusBarProps> = ({
  models,
  activeModel,
  onSelectModel,
  hardwareState,
  onSimulateHardwareState,
  liveTokPerSec,
  activeDownloadsCount,
  activeDownloadPercent,
  onOpenDownloads,
  onOpenSettings,
  onOpenSpecModal,
  javafxInspectorActive,
  onToggleJavafxInspector,
  compact800x600,
  onToggleCompact800x600,
}) => {
  const [modelMenuOpen, setModelMenuOpen] = useState(false);
  const [simMenuOpen, setSimMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const simRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setModelMenuOpen(false);
      }
      if (simRef.current && !simRef.current.contains(e.target as Node)) {
        setSimMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const totalVramGb = 8.0;
  const usedVramGb =
    hardwareState === 'vram_warning'
      ? 7.8
      : hardwareState === 'error_backend' || hardwareState === 'error_model_missing'
      ? 0.4
      : activeModel.vramRequiredGb;

  const vramPercent = Math.min(100, Math.round((usedVramGb / totalVramGb) * 100));

  const getStatusDescriptor = () => {
    switch (hardwareState) {
      case 'ready':
        return {
          dotColor: 'var(--status-ready)',
          pulse: false,
          label: 'Ready on GPU',
          sublabel: `${usedVramGb.toFixed(1)} / ${totalVramGb.toFixed(1)} GB VRAM`,
        };
      case 'loading_model':
        return {
          dotColor: 'var(--status-busy)',
          pulse: true,
          label: `Loading ${activeModel.name.split(' ')[0]} into GPU memory…`,
          sublabel: 'Allocating tensors',
        };
      case 'streaming':
        return {
          dotColor: 'var(--status-busy)',
          pulse: true,
          label: 'Generating reply…',
          sublabel: `${usedVramGb.toFixed(1)} / ${totalVramGb.toFixed(1)} GB VRAM`,
        };
      case 'generating_image':
        return {
          dotColor: 'var(--status-busy)',
          pulse: true,
          label: 'Creating local image…',
          sublabel: 'Diffusion active on GPU',
        };
      case 'vram_warning':
        return {
          dotColor: 'var(--status-warn)',
          pulse: false,
          label: 'High VRAM — Sharing with system RAM',
          sublabel: '7.8 / 8.0 GB VRAM (Slower)',
        };
      case 'error_model_missing':
        return {
          dotColor: 'var(--status-error)',
          pulse: false,
          label: 'Model file not downloaded yet',
          sublabel: 'Open Downloads to install',
        };
      case 'error_backend':
        return {
          dotColor: 'var(--status-error)',
          pulse: false,
          label: 'Local AI engine paused',
          sublabel: 'Click Reconnect to resume',
        };
    }
  };

  const statusInfo = getStatusDescriptor();

  return (
    <header
      className="relative h-[52px] shrink-0 flex items-center justify-between px-3.5 select-none border-b transition-colors"
      style={{
        backgroundColor: 'var(--bg-sidebar)',
        borderColor: 'var(--border-subtle)',
      }}
    >
      {/* Optional JavaFX Scene Graph X-Ray Tag */}
      {javafxInspectorActive && (
        <span className="absolute -bottom-4 left-3 z-40 px-1.5 py-0.5 text-[10px] font-mono-tabular rounded bg-[#E5A93C] text-[#141413] font-semibold shadow">
          HBox.status-header-bar (prefHeight: 52px)
        </span>
      )}

      {/* Left: Brand Identity + Model Selector + Telemetry Pill */}
      <div className="flex items-center gap-2.5 min-w-0">
        {/* Brand Identity */}
        <div className="flex items-center gap-2 pr-1">
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center border"
            style={{
              backgroundColor: 'var(--accent-subtle)',
              borderColor: 'var(--accent-primary)',
            }}
          >
            <Sparkles className="w-3.5 h-3.5" style={{ color: 'var(--accent-primary)' }} />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-[14px] tracking-tight leading-none">
                Sulvana
              </span>
              <span
                className="text-[10px] font-mono-tabular px-1.5 py-0.5 rounded font-medium"
                style={{
                  backgroundColor: 'var(--bg-elevated)',
                  color: 'var(--text-secondary)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                LOCAL
              </span>
            </div>
          </div>
        </div>

        {/* Active Model Selector (ComboBox<LocalModel> equivalent) */}
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setModelMenuOpen((prev) => !prev)}
            title="Switch active local AI model"
            className="h-[34px] px-2.5 rounded-lg border flex items-center gap-2 text-left transition-colors cursor-pointer"
            style={{
              backgroundColor: 'var(--bg-elevated)',
              borderColor: modelMenuOpen ? 'var(--accent-primary)' : 'var(--border-subtle)',
            }}
          >
            <Cpu className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--accent-primary)' }} />
            <div className="flex items-center gap-1.5 truncate max-w-[160px] sm:max-w-[210px]">
              <span className="text-[13px] font-medium truncate">
                {activeModel.name}
              </span>
              <span
                className="text-[11px] font-mono-tabular px-1.5 py-0.2 rounded hidden sm:inline-block"
                style={{
                  backgroundColor: 'var(--bg-input)',
                  color: 'var(--text-secondary)',
                }}
              >
                {activeModel.quantization}
              </span>
            </div>
            <ChevronDown
              className="w-3.5 h-3.5 shrink-0"
              style={{ color: 'var(--text-secondary)' }}
            />
          </button>

          {modelMenuOpen && (
            <div
              className="absolute left-0 top-[40px] w-[350px] rounded-xl border p-1.5 z-50 shadow-xl"
              style={{
                backgroundColor: 'var(--bg-elevated)',
                borderColor: 'var(--border-subtle)',
              }}
            >
              <div
                className="px-2.5 py-1.5 text-[11px] font-semibold uppercase tracking-wider flex items-center justify-between"
                style={{ color: 'var(--text-muted)' }}
              >
                <span>Local Model Engine (GGUF / FP8)</span>
                <span>VRAM Est.</span>
              </div>
              <div className="space-y-1 mt-0.5">
                {models.map((m) => {
                  const isSelected = m.id === activeModel.id;
                  return (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => {
                        setModelMenuOpen(false);
                        onSelectModel(m);
                      }}
                      className="w-full text-left p-2.5 rounded-lg border transition-colors flex items-start justify-between gap-2 cursor-pointer"
                      style={{
                        backgroundColor: isSelected
                          ? 'var(--accent-subtle)'
                          : 'transparent',
                        borderColor: isSelected
                          ? 'var(--accent-primary)'
                          : 'transparent',
                      }}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[13px] font-semibold truncate">
                            {m.name}
                          </span>
                          <span
                            className="text-[10px] font-mono-tabular px-1.5 py-0.5 rounded"
                            style={{
                              backgroundColor: 'var(--bg-sidebar)',
                              color: 'var(--text-secondary)',
                            }}
                          >
                            {m.quantization}
                          </span>
                          {!m.installed && (
                            <span
                              className="text-[10px] px-1.5 py-0.5 rounded font-medium"
                              style={{
                                backgroundColor: 'rgba(217, 130, 43, 0.16)',
                                color: 'var(--status-warn)',
                              }}
                            >
                              Not Downloaded
                            </span>
                          )}
                        </div>
                        <p
                          className="text-[11px] mt-1 line-clamp-2 leading-snug"
                          style={{ color: 'var(--text-secondary)' }}
                        >
                          {m.description}
                        </p>
                        <div className="flex flex-wrap items-center gap-1 mt-1.5">
                          {m.capabilities.map((cap) => (
                            <span
                              key={cap}
                              className="text-[10px] px-1.5 py-0.2 rounded capitalize"
                              style={{
                                backgroundColor: 'var(--bg-sidebar)',
                                color: 'var(--text-secondary)',
                              }}
                            >
                              {cap === 'image-gen' ? 'Image Gen' : cap}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="flex flex-col items-end shrink-0">
                        <span
                          className="text-[11px] font-mono-tabular font-medium"
                          style={{
                            color:
                              m.vramRequiredGb > 8
                                ? 'var(--status-warn)'
                                : 'var(--text-primary)',
                          }}
                        >
                          {m.vramRequiredGb.toFixed(1)} GB
                        </span>
                        <span
                          className="text-[10px] font-mono-tabular mt-0.5"
                          style={{ color: 'var(--text-muted)' }}
                        >
                          ~{m.speedTokPerSec} tok/s
                        </span>
                        {isSelected && (
                          <Check
                            className="w-4 h-4 mt-1.5"
                            style={{ color: 'var(--accent-primary)' }}
                          />
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
              <div
                className="mt-1.5 pt-1.5 border-t flex items-center justify-between px-2 py-1"
                style={{ borderColor: 'var(--border-subtle)' }}
              >
                <span className="text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                  Need another GGUF or Vision model?
                </span>
                <button
                  type="button"
                  onClick={() => {
                    setModelMenuOpen(false);
                    onOpenDownloads();
                  }}
                  className="text-[11px] font-semibold cursor-pointer hover:underline"
                  style={{ color: 'var(--accent-primary)' }}
                >
                  Open Model Manager →
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Human-Friendly Hardware & VRAM Status Pill */}
        <div
          className="h-[34px] px-2.5 rounded-lg border flex items-center gap-2.5"
          style={{
            backgroundColor: 'var(--bg-app-canvas)',
            borderColor:
              hardwareState === 'error_backend' ||
              hardwareState === 'error_model_missing'
                ? 'var(--status-error)'
                : hardwareState === 'vram_warning'
                ? 'var(--status-warn)'
                : 'var(--border-subtle)',
          }}
          title="Local GPU & VRAM Status (Click Simulator on right to test states)"
        >
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${
              statusInfo.pulse ? 'animate-sulvana-pulse' : ''
            }`}
            style={{ backgroundColor: statusInfo.dotColor }}
          />
          <div className="flex items-center gap-2 text-[12px]">
            <span className="font-medium whitespace-nowrap">
              {statusInfo.label}
            </span>
            {!compact800x600 && (
              <>
                <span style={{ color: 'var(--text-muted)' }}>•</span>
                <span
                  className="font-mono-tabular text-[11px] whitespace-nowrap hidden md:inline"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  {statusInfo.sublabel}
                </span>
              </>
            )}
          </div>

          {/* Mini VRAM ProgressBar */}
          {!compact800x600 && (
            <div
              className="w-12 h-1.5 rounded-full overflow-hidden hidden lg:block border"
              style={{
                backgroundColor: 'var(--bg-elevated)',
                borderColor: 'var(--border-subtle)',
              }}
              title={`VRAM Usage: ${vramPercent}%`}
            >
              <div
                className="h-full transition-all duration-300"
                style={{
                  width: `${vramPercent}%`,
                  backgroundColor:
                    hardwareState === 'vram_warning'
                      ? 'var(--status-warn)'
                      : 'var(--accent-primary)',
                }}
              />
            </div>
          )}

          {/* Live Tokens/sec readout */}
          <span
            className="text-[11px] font-mono-tabular px-1.5 py-0.5 rounded hidden sm:inline-block"
            style={{
              backgroundColor: 'var(--bg-elevated)',
              color: 'var(--text-secondary)',
            }}
            title="Local generation speed in tokens per second"
          >
            {liveTokPerSec.toFixed(1)} tok/s
          </span>
        </div>
      </div>

      {/* Right Utility Actions */}
      <div className="flex items-center gap-1.5">
        {/* Interactive State Simulator Dropdown (for testing loading, VRAM warning, offline errors, 800x600) */}
        <div className="relative" ref={simRef}>
          <button
            type="button"
            onClick={() => setSimMenuOpen((prev) => !prev)}
            className="h-[32px] px-2.5 rounded-lg border text-[12px] font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
            style={{
              backgroundColor: simMenuOpen
                ? 'var(--accent-subtle)'
                : 'var(--bg-elevated)',
              borderColor: simMenuOpen
                ? 'var(--accent-primary)'
                : 'var(--border-subtle)',
              color: 'var(--text-secondary)',
            }}
            title="Test loading, VRAM pressure, error recovery, and 800×600 responsive layout"
          >
            <Sliders className="w-3.5 h-3.5" style={{ color: 'var(--accent-primary)' }} />
            <span className="hidden xl:inline">Test UI States</span>
          </button>

          {simMenuOpen && (
            <div
              className="absolute right-0 top-[38px] w-[270px] rounded-xl border p-1.5 z-50 shadow-xl"
              style={{
                backgroundColor: 'var(--bg-elevated)',
                borderColor: 'var(--border-subtle)',
              }}
            >
              <div
                className="px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider"
                style={{ color: 'var(--text-muted)' }}
              >
                Simulate Hardware & Window States
              </div>
              {(
                [
                  { id: 'ready', label: 'Ready on GPU (Normal)', dot: 'var(--status-ready)' },
                  {
                    id: 'loading_model',
                    label: 'Swapping Model into VRAM…',
                    dot: 'var(--status-busy)',
                  },
                  {
                    id: 'vram_warning',
                    label: 'High VRAM (CPU+GPU Split)',
                    dot: 'var(--status-warn)',
                  },
                  {
                    id: 'error_model_missing',
                    label: 'Error: Model File Missing',
                    dot: 'var(--status-error)',
                  },
                  {
                    id: 'error_backend',
                    label: 'Error: Python Engine Offline',
                    dot: 'var(--status-error)',
                  },
                ] as { id: HardwareStatusState; label: string; dot: string }[]
              ).map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    onSimulateHardwareState(item.id);
                    setSimMenuOpen(false);
                  }}
                  className="w-full px-2.5 py-1.5 rounded-lg text-left text-[12px] flex items-center justify-between hover:opacity-90 cursor-pointer"
                  style={{
                    backgroundColor:
                      hardwareState === item.id ? 'var(--accent-subtle)' : 'transparent',
                  }}
                >
                  <span className="flex items-center gap-2">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: item.dot }}
                    />
                    <span>{item.label}</span>
                  </span>
                  {hardwareState === item.id && (
                    <Check
                      className="w-3.5 h-3.5"
                      style={{ color: 'var(--accent-primary)' }}
                    />
                  )}
                </button>
              ))}

              <div
                className="my-1 border-t"
                style={{ borderColor: 'var(--border-subtle)' }}
              />

              <button
                type="button"
                onClick={() => {
                  onToggleCompact800x600();
                  setSimMenuOpen(false);
                }}
                className="w-full px-2.5 py-1.5 rounded-lg text-left text-[12px] flex items-center justify-between cursor-pointer"
                style={{
                  backgroundColor: compact800x600
                    ? 'var(--accent-subtle)'
                    : 'transparent',
                }}
              >
                <span className="flex items-center gap-2">
                  {compact800x600 ? (
                    <Maximize2 className="w-3.5 h-3.5" style={{ color: 'var(--accent-primary)' }} />
                  ) : (
                    <Minimize2 className="w-3.5 h-3.5" style={{ color: 'var(--text-secondary)' }} />
                  )}
                  <span>800×600 Minimum Window Frame</span>
                </span>
                {compact800x600 && (
                  <Check className="w-3.5 h-3.5" style={{ color: 'var(--accent-primary)' }} />
                )}
              </button>

              <button
                type="button"
                onClick={() => {
                  onToggleJavafxInspector();
                  setSimMenuOpen(false);
                }}
                className="w-full px-2.5 py-1.5 rounded-lg text-left text-[12px] flex items-center justify-between cursor-pointer"
                style={{
                  backgroundColor: javafxInspectorActive
                    ? 'var(--accent-subtle)'
                    : 'transparent',
                }}
              >
                <span className="flex items-center gap-2">
                  <Eye className="w-3.5 h-3.5" style={{ color: 'var(--accent-primary)' }} />
                  <span>JavaFX Container X-Ray Overlay</span>
                </span>
                {javafxInspectorActive && (
                  <Check className="w-3.5 h-3.5" style={{ color: 'var(--accent-primary)' }} />
                )}
              </button>
            </div>
          )}
        </div>

        {/* Models & Downloads Button */}
        <button
          type="button"
          onClick={onOpenDownloads}
          className="h-[32px] px-2.5 rounded-lg border text-[12px] font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
          style={{
            backgroundColor: 'var(--bg-elevated)',
            borderColor: 'var(--border-subtle)',
          }}
          title="Manage local models and active downloads"
        >
          <Download className="w-3.5 h-3.5" style={{ color: 'var(--accent-primary)' }} />
          <span className="hidden sm:inline">Models</span>
          {activeDownloadsCount > 0 && activeDownloadPercent !== null && (
            <span
              className="text-[11px] font-mono-tabular px-1.5 py-0.2 rounded font-semibold"
              style={{
                backgroundColor: 'var(--accent-subtle)',
                color: 'var(--accent-primary)',
              }}
            >
              {activeDownloadPercent}%
            </span>
          )}
        </button>

        {/* Settings Button */}
        <button
          type="button"
          onClick={onOpenSettings}
          className="h-[32px] px-2.5 rounded-lg border text-[12px] font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
          style={{
            backgroundColor: 'var(--bg-elevated)',
            borderColor: 'var(--border-subtle)',
          }}
          title="Reply language, temperature, max length, and theme settings"
        >
          <Settings className="w-3.5 h-3.5" style={{ color: 'var(--text-secondary)' }} />
          <span className="hidden md:inline">Settings</span>
        </button>

        {/* JavaFX Architecture & UI Spec Deliverable Button */}
        <button
          type="button"
          onClick={onOpenSpecModal}
          className="h-[32px] px-2.5 rounded-lg border text-[12px] font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
          style={{
            backgroundColor: 'var(--accent-subtle)',
            borderColor: 'var(--accent-primary)',
            color: 'var(--accent-primary)',
          }}
          title="View complete 5-part UI Specification & JavaFX + CSS Blueprint"
        >
          <Layers className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">UI Spec & JavaFX Tree</span>
        </button>
      </div>
    </header>
  );
};
