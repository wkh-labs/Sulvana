import React, { useState } from 'react';
import {
  Plus,
  Search,
  MessageSquare,
  Trash2,
  ShieldCheck,
  Globe,
  Check,
  X,
} from 'lucide-react';
import { Conversation, ReplyLanguage } from '../types/sulvana';

interface SidebarRailProps {
  conversations: Conversation[];
  activeConversationId: string;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  onClearCurrentChat: () => void;
  onDeleteConversation: (id: string) => void;
  replyLanguage: ReplyLanguage;
  onQuickSwitchLanguage: (lang: ReplyLanguage) => void;
  javafxInspectorActive: boolean;
  compact800x600: boolean;
}

export const SidebarRail: React.FC<SidebarRailProps> = ({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewChat,
  onClearCurrentChat,
  onDeleteConversation,
  replyLanguage,
  onQuickSwitchLanguage,
  javafxInspectorActive,
  compact800x600,
}) => {
  const [filterText, setFilterText] = useState('');
  const [confirmClear, setConfirmClear] = useState(false);

  const filteredConversations = conversations.filter((conv) =>
    conv.title.toLowerCase().includes(filterText.toLowerCase())
  );

  const activeConv = conversations.find((c) => c.id === activeConversationId);
  const hasMessages = (activeConv?.messages.length ?? 0) > 0;

  return (
    <aside
      className={`relative shrink-0 flex flex-col border-r select-none transition-all ${
        compact800x600 ? 'w-[205px]' : 'w-[252px]'
      }`}
      style={{
        backgroundColor: 'var(--bg-sidebar)',
        borderColor: 'var(--border-subtle)',
      }}
    >
      {/* Optional JavaFX X-Ray label */}
      {javafxInspectorActive && (
        <span className="absolute top-1 right-2 z-40 px-1.5 py-0.5 text-[10px] font-mono-tabular rounded bg-[#E5A93C] text-[#141413] font-semibold shadow">
          VBox.sidebar-rail
        </span>
      )}

      {/* Primary Action: + New Chat */}
      <div className="p-3 pb-2">
        <button
          type="button"
          onClick={onNewChat}
          className="w-full h-[38px] rounded-lg font-semibold text-[13px] flex items-center justify-center gap-2 transition-colors cursor-pointer"
          style={{
            backgroundColor: 'var(--accent-primary)',
            color: 'var(--accent-text-on-solid)',
          }}
          title="Start a brand-new conversation (Ctrl+N)"
        >
          <Plus className="w-4 h-4 stroke-[2.2]" />
          <span>New Chat</span>
        </button>

        {/* Filter input */}
        <div
          className="mt-2.5 h-[32px] px-2.5 rounded-lg border flex items-center gap-2"
          style={{
            backgroundColor: 'var(--bg-input)',
            borderColor: 'var(--border-subtle)',
          }}
        >
          <Search
            className="w-3.5 h-3.5 shrink-0"
            style={{ color: 'var(--text-muted)' }}
          />
          <input
            type="text"
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            placeholder="Filter sessions…"
            className="w-full bg-transparent text-[12px] outline-none"
            style={{ color: 'var(--text-primary)' }}
          />
          {filterText && (
            <button
              type="button"
              onClick={() => setFilterText('')}
              className="cursor-pointer"
              style={{ color: 'var(--text-muted)' }}
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {/* Section Caption */}
      <div className="px-3.5 pt-1 pb-1.5 flex items-center justify-between">
        <span
          className="text-[11px] font-semibold uppercase tracking-wider"
          style={{ color: 'var(--text-muted)' }}
        >
          Conversations ({filteredConversations.length})
        </span>
      </div>

      {/* Scrollable Conversation List (ListView<Conversation>) */}
      <div className="flex-1 overflow-y-auto px-2 space-y-1">
        {filteredConversations.map((conv) => {
          const isSelected = conv.id === activeConversationId;
          return (
            <div
              key={conv.id}
              onClick={() => onSelectConversation(conv.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  onSelectConversation(conv.id);
                }
              }}
              className="group relative rounded-lg px-2.5 py-2.5 transition-colors cursor-pointer flex items-start justify-between gap-2 border"
              style={{
                backgroundColor: isSelected
                  ? 'var(--bg-elevated)'
                  : 'transparent',
                borderColor: isSelected
                  ? 'var(--border-subtle)'
                  : 'transparent',
                borderLeftWidth: isSelected ? '3px' : '1px',
                borderLeftColor: isSelected
                  ? 'var(--accent-primary)'
                  : 'transparent',
              }}
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <MessageSquare
                    className="w-3.5 h-3.5 shrink-0"
                    style={{
                      color: isSelected
                        ? 'var(--accent-primary)'
                        : 'var(--text-muted)',
                    }}
                  />
                  <span
                    className="text-[13px] font-medium truncate leading-snug"
                    style={{
                      color: isSelected
                        ? 'var(--text-primary)'
                        : 'var(--text-secondary)',
                    }}
                  >
                    {conv.title}
                  </span>
                </div>
                <div className="mt-1.5 flex items-center justify-between gap-1.5 pl-5">
                  <span
                    className="text-[11px]"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    {conv.updatedAt} • {conv.messages.length} msg
                  </span>
                  {conv.scriptBadge && (
                    <span
                      className="text-[10px] px-1.5 py-0.2 rounded font-medium shrink-0"
                      style={{
                        backgroundColor: isSelected
                          ? 'var(--accent-subtle)'
                          : 'var(--bg-app-canvas)',
                        color: isSelected
                          ? 'var(--accent-primary)'
                          : 'var(--text-secondary)',
                      }}
                    >
                      {conv.scriptBadge}
                    </span>
                  )}
                </div>
              </div>

              {conversations.length > 1 && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteConversation(conv.id);
                  }}
                  title="Delete conversation"
                  className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-black/20 transition-opacity cursor-pointer shrink-0"
                  style={{ color: 'var(--text-muted)' }}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Quick Script & Reply Language Switcher Bar */}
      <div
        className="px-3 py-2.5 border-t"
        style={{ borderColor: 'var(--border-subtle)' }}
      >
        <div className="flex items-center justify-between mb-1.5">
          <span
            className="text-[11px] font-medium flex items-center gap-1.5"
            style={{ color: 'var(--text-secondary)' }}
          >
            <Globe className="w-3 h-3" style={{ color: 'var(--accent-primary)' }} />
            <span>Reply Language</span>
          </span>
          <span
            className="text-[10px] font-mono-tabular"
            style={{ color: 'var(--text-muted)' }}
          >
            UTF-8 Multi-Script
          </span>
        </div>
        <select
          value={replyLanguage}
          onChange={(e) =>
            onQuickSwitchLanguage(e.target.value as ReplyLanguage)
          }
          className="w-full h-[30px] px-2 rounded-md border text-[12px] outline-none cursor-pointer"
          style={{
            backgroundColor: 'var(--bg-input)',
            borderColor: 'var(--border-subtle)',
            color: 'var(--text-primary)',
          }}
        >
          <option value="Auto-detect">Auto-detect Script</option>
          <option value="English">English</option>
          <option value="ខ្មែរ (Khmer)">ខ្មែរ (Khmer)</option>
          <option value="العربية (Arabic)">العربية (Arabic — RTL)</option>
          <option value="中文 (Chinese)">中文 (Chinese)</option>
          <option value="日本語 (Japanese)">日本語 (Japanese)</option>
        </select>
      </div>

      {/* Bottom Footer: Clear Current Chat + Local Privacy Badge */}
      <div
        className="p-3 border-t space-y-2"
        style={{ borderColor: 'var(--border-subtle)' }}
      >
        {!confirmClear ? (
          <button
            type="button"
            disabled={!hasMessages}
            onClick={() => setConfirmClear(true)}
            className="w-full h-[32px] px-2.5 rounded-lg border text-[12px] font-medium flex items-center justify-center gap-1.5 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            style={{
              backgroundColor: 'var(--bg-elevated)',
              borderColor: 'var(--border-subtle)',
              color: 'var(--text-secondary)',
            }}
            title="Clear all messages in the current conversation"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear Current Chat</span>
          </button>
        ) : (
          <div
            className="p-2 rounded-lg border space-y-1.5"
            style={{
              backgroundColor: 'rgba(217, 83, 79, 0.1)',
              borderColor: 'var(--status-error)',
            }}
          >
            <p className="text-[11px] font-medium text-center">
              Clear messages in this chat?
            </p>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => {
                  onClearCurrentChat();
                  setConfirmClear(false);
                }}
                className="flex-1 h-[26px] rounded text-[11px] font-semibold flex items-center justify-center gap-1 cursor-pointer"
                style={{
                  backgroundColor: 'var(--status-error)',
                  color: '#FFFFFF',
                }}
              >
                <Check className="w-3 h-3" />
                <span>Clear</span>
              </button>
              <button
                type="button"
                onClick={() => setConfirmClear(false)}
                className="flex-1 h-[26px] rounded border text-[11px] font-medium flex items-center justify-center gap-1 cursor-pointer"
                style={{
                  backgroundColor: 'var(--bg-elevated)',
                  borderColor: 'var(--border-subtle)',
                }}
              >
                <X className="w-3 h-3" />
                <span>Cancel</span>
              </button>
            </div>
          </div>
        )}

        <div
          className="flex items-center justify-center gap-1.5 pt-0.5 text-[11px]"
          style={{ color: 'var(--text-muted)' }}
        >
          <ShieldCheck
            className="w-3.5 h-3.5 shrink-0"
            style={{ color: 'var(--status-ready)' }}
          />
          <span>100% Local • Zero Cloud Telemetry</span>
        </div>
      </div>
    </aside>
  );
};
