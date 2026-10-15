import React, { useState } from 'react';
import {
  X,
  Download,
  Pause,
  Play,
  CheckCircle2,
  HardDrive,
  RotateCcw,
  Trash2,
  Cpu,
} from 'lucide-react';
import { DownloadModelItem } from '../types/sulvana';

interface DownloadsModalProps {
  isOpen: boolean;
  onClose: () => void;
  items: DownloadModelItem[];
  onTogglePauseResume: (id: string) => void;
  onStartDownload: (id: string) => void;
  onCancelDownload: (id: string) => void;
  onSimulateComplete: (id: string) => void;
}

export const DownloadsModal: React.FC<DownloadsModalProps> = ({
  isOpen,
  onClose,
  items,
  onTogglePauseResume,
  onStartDownload,
  onCancelDownload,
  onSimulateComplete,
}) => {
  const [activeTab, setActiveTab] = useState<'all' | 'active' | 'installed'>('all');

  if (!isOpen) return null;

  const filteredItems = items.filter((item) => {
    if (activeTab === 'active') {
      return (
        item.status === 'downloading' ||
        item.status === 'paused' ||
        item.status === 'failed'
      );
    }
    if (activeTab === 'installed') {
      return item.status === 'completed';
    }
    return true;
  });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: 'rgba(10, 10, 9, 0.72)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-[680px] max-h-[86vh] rounded-2xl border flex flex-col overflow-hidden shadow-2xl"
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
          <div>
            <h2 className="text-[16px] font-semibold flex items-center gap-2">
              <Download
                className="w-4 h-4"
                style={{ color: 'var(--accent-primary)' }}
              />
              <span>Local Model Manager & Downloads</span>
            </h2>
            <p
              className="text-[12px] mt-0.5"
              style={{ color: 'var(--text-secondary)' }}
            >
              Models are stored locally on your machine in{' '}
              <code className="font-mono-tabular text-[11px]">
                ~/Sulvana/models/
              </code>{' '}
              and run offline.
            </p>
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

        {/* Filter Tabs + Disk Telemetry Bar */}
        <div
          className="px-5 py-2.5 border-b flex flex-wrap items-center justify-between gap-2"
          style={{
            backgroundColor: 'var(--bg-app-canvas)',
            borderColor: 'var(--border-subtle)',
          }}
        >
          <div className="flex items-center gap-1">
            {(
              [
                { id: 'all', label: `All Models (${items.length})` },
                {
                  id: 'active',
                  label: `Active Queue (${
                    items.filter(
                      (i) => i.status === 'downloading' || i.status === 'paused'
                    ).length
                  })`,
                },
                {
                  id: 'installed',
                  label: `Installed (${
                    items.filter((i) => i.status === 'completed').length
                  })`,
                },
              ] as const
            ).map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className="h-[28px] px-3 rounded-lg text-[12px] font-medium transition-colors cursor-pointer"
                style={{
                  backgroundColor:
                    activeTab === tab.id ? 'var(--accent-subtle)' : 'transparent',
                  color:
                    activeTab === tab.id
                      ? 'var(--accent-primary)'
                      : 'var(--text-secondary)',
                  border:
                    activeTab === tab.id
                      ? '1px solid var(--accent-primary)'
                      : '1px solid transparent',
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div
            className="flex items-center gap-1.5 text-[11px] font-mono-tabular"
            style={{ color: 'var(--text-secondary)' }}
          >
            <HardDrive className="w-3.5 h-3.5" style={{ color: 'var(--accent-primary)' }} />
            <span>142.8 GB free on local NVMe</span>
          </div>
        </div>

        {/* Model Download List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {filteredItems.map((item) => {
            const isDownloading = item.status === 'downloading';
            const isPaused = item.status === 'paused';
            const isCompleted = item.status === 'completed';
            const isAvailable = item.status === 'available';

            return (
              <div
                key={item.id}
                className="p-4 rounded-xl border transition-colors"
                style={{
                  backgroundColor: 'var(--bg-sidebar)',
                  borderColor: isDownloading
                    ? 'var(--accent-primary)'
                    : 'var(--border-subtle)',
                }}
              >
                {/* Top Row: Model Name, Quantization, Size, and Action Buttons */}
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[14px] font-semibold">
                        {item.name}
                      </span>
                      <span
                        className="text-[11px] font-mono-tabular px-1.5 py-0.5 rounded border"
                        style={{
                          backgroundColor: 'var(--bg-elevated)',
                          borderColor: 'var(--border-subtle)',
                          color: 'var(--text-secondary)',
                        }}
                      >
                        {item.quantization} • {item.format}
                      </span>
                      <span
                        className="text-[11px] font-mono-tabular flex items-center gap-1"
                        style={{ color: 'var(--text-muted)' }}
                      >
                        <Cpu className="w-3 h-3" />
                        Rec. {item.recommendedVramGb} GB VRAM
                      </span>
                    </div>

                    <p
                      className="text-[12px] mt-1 leading-snug"
                      style={{ color: 'var(--text-secondary)' }}
                    >
                      {item.description}
                    </p>
                  </div>

                  {/* Action Controls depending on Download Status */}
                  <div className="flex items-center gap-2 shrink-0">
                    {(isDownloading || isPaused) && (
                      <>
                        <button
                          type="button"
                          onClick={() => onTogglePauseResume(item.id)}
                          className="h-[32px] px-3 rounded-lg border text-[12px] font-semibold flex items-center gap-1.5 cursor-pointer"
                          style={{
                            backgroundColor: isPaused
                              ? 'var(--accent-primary)'
                              : 'var(--bg-elevated)',
                            borderColor: isPaused
                              ? 'var(--accent-primary)'
                              : 'var(--border-subtle)',
                            color: isPaused
                              ? 'var(--accent-text-on-solid)'
                              : 'var(--text-primary)',
                          }}
                        >
                          {isPaused ? (
                            <>
                              <Play className="w-3.5 h-3.5 fill-current" />
                              <span>Resume</span>
                            </>
                          ) : (
                            <>
                              <Pause className="w-3.5 h-3.5" />
                              <span>Pause</span>
                            </>
                          )}
                        </button>

                        <button
                          type="button"
                          onClick={() => onSimulateComplete(item.id)}
                          className="h-[32px] px-2.5 rounded-lg border text-[11px] font-medium cursor-pointer"
                          style={{
                            backgroundColor: 'var(--bg-elevated)',
                            borderColor: 'var(--border-subtle)',
                            color: 'var(--text-secondary)',
                          }}
                          title="Finish download immediately for demo testing"
                        >
                          Finish Now
                        </button>

                        <button
                          type="button"
                          onClick={() => onCancelDownload(item.id)}
                          className="h-[32px] w-[32px] rounded-lg border flex items-center justify-center cursor-pointer"
                          style={{
                            backgroundColor: 'var(--bg-elevated)',
                            borderColor: 'var(--border-subtle)',
                            color: 'var(--text-muted)',
                          }}
                          title="Cancel download"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </>
                    )}

                    {isCompleted && (
                      <div className="flex items-center gap-2">
                        <span
                          className="h-[30px] px-2.5 rounded-lg text-[12px] font-semibold flex items-center gap-1.5"
                          style={{
                            backgroundColor: 'rgba(78, 159, 110, 0.15)',
                            color: 'var(--status-ready)',
                            border: '1px solid rgba(78, 159, 110, 0.35)',
                          }}
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Installed</span>
                        </span>
                      </div>
                    )}

                    {isAvailable && (
                      <button
                        type="button"
                        onClick={() => onStartDownload(item.id)}
                        className="h-[32px] px-3.5 rounded-lg text-[12px] font-semibold flex items-center gap-1.5 cursor-pointer"
                        style={{
                          backgroundColor: 'var(--accent-primary)',
                          color: 'var(--accent-text-on-solid)',
                        }}
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Download ({item.totalSizeGb.toFixed(1)} GB)</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Progress Bar & Telemetry Strip (shown for Downloading, Paused, or Completed) */}
                {(isDownloading || isPaused || isCompleted) && (
                  <div className="mt-3 pt-2.5 border-t space-y-1.5" style={{ borderColor: 'var(--border-subtle)' }}>
                    <div className="flex items-center justify-between text-[12px] font-mono-tabular">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                          {item.percent}%
                        </span>
                        <span style={{ color: 'var(--text-secondary)' }}>
                          ({item.downloadedGb.toFixed(1)} GB / {item.totalSizeGb.toFixed(1)} GB)
                        </span>
                      </div>

                      <div className="flex items-center gap-3">
                        {isDownloading && (
                          <span style={{ color: 'var(--accent-primary)' }}>
                            {item.speedMbPerSec.toFixed(1)} MB/s
                          </span>
                        )}
                        <span style={{ color: 'var(--text-secondary)' }}>
                          {item.etaText}
                        </span>
                      </div>
                    </div>

                    {/* Full-width JavaFX ProgressBar */}
                    <div
                      className="w-full h-2 rounded-full overflow-hidden border"
                      style={{
                        backgroundColor: 'var(--bg-app-canvas)',
                        borderColor: 'var(--border-subtle)',
                      }}
                    >
                      <div
                        className="h-full transition-all duration-300"
                        style={{
                          width: `${item.percent}%`,
                          backgroundColor: isCompleted
                            ? 'var(--status-ready)'
                            : isPaused
                            ? 'var(--text-muted)'
                            : 'var(--accent-primary)',
                        }}
                      />
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Modal Footer */}
        <div
          className="px-5 py-3 border-t flex items-center justify-between text-[12px]"
          style={{
            backgroundColor: 'var(--bg-sidebar)',
            borderColor: 'var(--border-subtle)',
            color: 'var(--text-secondary)',
          }}
        >
          <span className="flex items-center gap-1.5">
            <RotateCcw className="w-3.5 h-3.5" style={{ color: 'var(--accent-primary)' }} />
            <span>Interrupted downloads automatically resume from their last byte offset.</span>
          </span>
          <button
            type="button"
            onClick={onClose}
            className="h-[32px] px-4 rounded-lg font-semibold cursor-pointer"
            style={{
              backgroundColor: 'var(--bg-elevated)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-primary)',
            }}
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
