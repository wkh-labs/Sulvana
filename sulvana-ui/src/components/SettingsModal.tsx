import React from 'react';
import {
  X,
  Settings,
  Globe,
  Thermometer,
  AlignLeft,
  Moon,
  Sun,
  RotateCcw,
} from 'lucide-react';
import { ReplyLanguage, SulvanaSettings } from '../types/sulvana';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: SulvanaSettings;
  onUpdateSettings: (partial: Partial<SulvanaSettings>) => void;
  onResetDefaults: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  settings,
  onUpdateSettings,
  onResetDefaults,
}) => {
  if (!isOpen) return null;

  const getTemperatureDescription = (temp: number) => {
    if (temp <= 0.3) return 'Precise & deterministic — ideal for coding, math, and technical summaries.';
    if (temp <= 0.8) return 'Balanced — natural conversational flow with reliable accuracy.';
    return 'Creative & expressive — great for brainstorming, fiction, and varied phrasing.';
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: 'rgba(10, 10, 9, 0.72)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-[520px] rounded-2xl border flex flex-col overflow-hidden shadow-2xl"
        style={{
          backgroundColor: 'var(--bg-elevated)',
          borderColor: 'var(--border-subtle)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div
          className="px-5 py-4 border-b flex items-center justify-between"
          style={{
            backgroundColor: 'var(--bg-sidebar)',
            borderColor: 'var(--border-subtle)',
          }}
        >
          <div className="flex items-center gap-2">
            <Settings
              className="w-4 h-4"
              style={{ color: 'var(--accent-primary)' }}
            />
            <h2 className="text-[16px] font-semibold">Sulvana Preferences</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-lg border flex items-center justify-center cursor-pointer"
            style={{
              backgroundColor: 'var(--bg-elevated)',
              borderColor: 'var(--border-subtle)',
              color: 'var(--text-secondary)',
            }}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Settings Controls Body */}
        <div className="p-5 space-y-5 overflow-y-auto max-h-[75vh]">
          {/* 1. Theme Selection */}
          <div className="space-y-2">
            <label className="text-[13px] font-semibold flex items-center gap-2">
              {settings.theme === 'dark' ? (
                <Moon className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
              ) : (
                <Sun className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
              )}
              <span>Appearance Theme</span>
            </label>
            <div className="grid grid-cols-2 gap-2.5">
              <button
                type="button"
                onClick={() => onUpdateSettings({ theme: 'dark' })}
                className="p-3 rounded-xl border text-left transition-colors flex items-center justify-between cursor-pointer"
                style={{
                  backgroundColor:
                    settings.theme === 'dark'
                      ? 'var(--accent-subtle)'
                      : 'var(--bg-sidebar)',
                  borderColor:
                    settings.theme === 'dark'
                      ? 'var(--accent-primary)'
                      : 'var(--border-subtle)',
                }}
              >
                <div>
                  <div className="text-[13px] font-semibold">
                    Dark (Default)
                  </div>
                  <div
                    className="text-[11px]"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Warm Obsidian #141413
                  </div>
                </div>
                <span className="w-5 h-5 rounded-full bg-[#141413] border border-[#E5A93C]" />
              </button>

              <button
                type="button"
                onClick={() => onUpdateSettings({ theme: 'light' })}
                className="p-3 rounded-xl border text-left transition-colors flex items-center justify-between cursor-pointer"
                style={{
                  backgroundColor:
                    settings.theme === 'light'
                      ? 'var(--accent-subtle)'
                      : 'var(--bg-sidebar)',
                  borderColor:
                    settings.theme === 'light'
                      ? 'var(--accent-primary)'
                      : 'var(--border-subtle)',
                }}
              >
                <div>
                  <div className="text-[13px] font-semibold">
                    Light Studio
                  </div>
                  <div
                    className="text-[11px]"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Warm Paper #FAF9F5
                  </div>
                </div>
                <span className="w-5 h-5 rounded-full bg-[#FAF9F5] border border-[#C4841D]" />
              </button>
            </div>
          </div>

          {/* 2. Reply Language */}
          <div className="space-y-1.5">
            <label className="text-[13px] font-semibold flex items-center gap-2">
              <Globe className="w-4 h-4" style={{ color: 'var(--accent-primary)' }} />
              <span>Default Reply Language</span>
            </label>
            <p
              className="text-[12px]"
              style={{ color: 'var(--text-secondary)' }}
            >
              Choose how Sulvana responds, or let it automatically match the script you write in.
            </p>
            <select
              value={settings.replyLanguage}
              onChange={(e) =>
                onUpdateSettings({
                  replyLanguage: e.target.value as ReplyLanguage,
                })
              }
              className="w-full h-[38px] px-3 rounded-lg border text-[13px] outline-none cursor-pointer"
              style={{
                backgroundColor: 'var(--bg-input)',
                borderColor: 'var(--border-subtle)',
                color: 'var(--text-primary)',
              }}
            >
              <option value="Auto-detect">Auto-detect (Match User Script)</option>
              <option value="English">English</option>
              <option value="ខ្មែរ (Khmer)">ខ្មែរ (Khmer)</option>
              <option value="العربية (Arabic)">العربية (Arabic — RTL)</option>
              <option value="中文 (Chinese)">中文 (Chinese)</option>
              <option value="日本語 (Japanese)">日本語 (Japanese)</option>
            </select>
          </div>

          {/* 3. Temperature Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-[13px] font-semibold flex items-center gap-2">
                <Thermometer
                  className="w-4 h-4"
                  style={{ color: 'var(--accent-primary)' }}
                />
                <span>Creativity (Temperature)</span>
              </label>
              <span
                className="font-mono-tabular text-[12px] font-semibold px-2 py-0.5 rounded border"
                style={{
                  backgroundColor: 'var(--accent-subtle)',
                  borderColor: 'var(--accent-primary)',
                  color: 'var(--accent-primary)',
                }}
              >
                {settings.temperature.toFixed(1)}
              </span>
            </div>

            <input
              type="range"
              min={0}
              max={1.5}
              step={0.1}
              value={settings.temperature}
              onChange={(e) =>
                onUpdateSettings({ temperature: parseFloat(e.target.value) })
              }
              className="w-full accent-[#E5A93C] cursor-pointer"
            />

            <div className="flex items-center justify-between text-[11px]" style={{ color: 'var(--text-muted)' }}>
              <button
                type="button"
                onClick={() => onUpdateSettings({ temperature: 0.2 })}
                className="hover:underline cursor-pointer"
              >
                0.2 Precise
              </button>
              <button
                type="button"
                onClick={() => onUpdateSettings({ temperature: 0.7 })}
                className="hover:underline cursor-pointer"
              >
                0.7 Balanced
              </button>
              <button
                type="button"
                onClick={() => onUpdateSettings({ temperature: 1.2 })}
                className="hover:underline cursor-pointer"
              >
                1.2 Creative
              </button>
            </div>

            <p
              className="text-[12px] leading-snug"
              style={{ color: 'var(--text-secondary)' }}
            >
              {getTemperatureDescription(settings.temperature)}
            </p>
          </div>

          {/* 4. Maximum Response Length */}
          <div className="space-y-2">
            <label className="text-[13px] font-semibold flex items-center gap-2">
              <AlignLeft
                className="w-4 h-4"
                style={{ color: 'var(--accent-primary)' }}
              />
              <span>Maximum Response Length (Tokens)</span>
            </label>
            <p
              className="text-[12px]"
              style={{ color: 'var(--text-secondary)' }}
            >
              Limits how long a single reply can be so GPU memory remains responsive.
            </p>
            <div className="grid grid-cols-5 gap-1.5">
              {(
                [
                  { val: 512, label: '512', desc: 'Short' },
                  { val: 1024, label: '1024', desc: 'Normal' },
                  { val: 2048, label: '2048', desc: 'Detailed' },
                  { val: 4096, label: '4096', desc: 'Long' },
                  { val: 8192, label: '8192', desc: 'Max' },
                ] as const
              ).map((opt) => {
                const active = settings.maxResponseLength === opt.val;
                return (
                  <button
                    key={opt.val}
                    type="button"
                    onClick={() =>
                      onUpdateSettings({ maxResponseLength: opt.val })
                    }
                    className="py-2 px-1.5 rounded-lg border text-center transition-colors cursor-pointer"
                    style={{
                      backgroundColor: active
                        ? 'var(--accent-subtle)'
                        : 'var(--bg-sidebar)',
                      borderColor: active
                        ? 'var(--accent-primary)'
                        : 'var(--border-subtle)',
                    }}
                  >
                    <div
                      className="text-[12px] font-mono-tabular font-semibold"
                      style={{
                        color: active
                          ? 'var(--accent-primary)'
                          : 'var(--text-primary)',
                      }}
                    >
                      {opt.label}
                    </div>
                    <div
                      className="text-[10px]"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      {opt.desc}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div
          className="px-5 py-3.5 border-t flex items-center justify-between"
          style={{
            backgroundColor: 'var(--bg-sidebar)',
            borderColor: 'var(--border-subtle)',
          }}
        >
          <button
            type="button"
            onClick={onResetDefaults}
            className="h-[32px] px-3 rounded-lg border text-[12px] font-medium flex items-center gap-1.5 cursor-pointer"
            style={{
              backgroundColor: 'var(--bg-elevated)',
              borderColor: 'var(--border-subtle)',
              color: 'var(--text-secondary)',
            }}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Defaults</span>
          </button>

          <button
            type="button"
            onClick={onClose}
            className="h-[34px] px-5 rounded-lg text-[12px] font-semibold cursor-pointer"
            style={{
              backgroundColor: 'var(--accent-primary)',
              color: 'var(--accent-text-on-solid)',
            }}
          >
            Save & Close
          </button>
        </div>
      </div>
    </div>
  );
};
