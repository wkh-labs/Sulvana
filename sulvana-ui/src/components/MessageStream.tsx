import React, { useState, useRef, useEffect } from 'react';
import {
  Sparkles,
  Copy,
  Check,
  Download,
  Image as ImageIcon,
  Code2,
  Languages,
  Eye,
  Cpu,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import {
  ChatMessage,
  HardwareStatusState,
  LocalModel,
  VisionAttachment,
} from '../types/sulvana';
import { SAMPLE_VISION_ATTACHMENTS } from '../data/initialData';

interface MessageStreamProps {
  messages: ChatMessage[];
  activeModel: LocalModel;
  hardwareState: HardwareStatusState;
  onStarterPrompt: (prompt: string, attachment?: VisionAttachment) => void;
  onRecoverHardwareError: () => void;
  onOpenDownloads: () => void;
  javafxInspectorActive: boolean;
}

interface ParsedBlock {
  type: 'prose' | 'code';
  content: string;
  language?: string;
}

function parseMarkdownBlocks(raw: string): ParsedBlock[] {
  const blocks: ParsedBlock[] = [];
  const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = codeBlockRegex.exec(raw)) !== null) {
    if (match.index > lastIndex) {
      blocks.push({
        type: 'prose',
        content: raw.slice(lastIndex, match.index),
      });
    }
    blocks.push({
      type: 'code',
      language: match[1] || 'text',
      content: match[2].replace(/\n$/, ''),
    });
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < raw.length) {
    blocks.push({
      type: 'prose',
      content: raw.slice(lastIndex),
    });
  }

  return blocks;
}

function renderInlineFormatting(text: string): React.ReactNode[] {
  // Split by inline code `...` and bold **...**
  const tokens = text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
  return tokens.map((tok, i) => {
    if (tok.startsWith('`') && tok.endsWith('`') && tok.length > 2) {
      return (
        <code
          key={i}
          className="font-mono-tabular text-[13px] px-1.5 py-0.5 rounded border"
          style={{
            backgroundColor: 'var(--bg-code-block)',
            borderColor: 'var(--border-subtle)',
            color: 'var(--accent-primary)',
          }}
        >
          {tok.slice(1, -1)}
        </code>
      );
    }
    if (tok.startsWith('**') && tok.endsWith('**') && tok.length > 4) {
      return (
        <strong key={i} className="font-semibold" style={{ color: 'var(--text-primary)' }}>
          {tok.slice(2, -2)}
        </strong>
      );
    }
    return <React.Fragment key={i}>{tok}</React.Fragment>;
  });
}

const CodeBlockCard: React.FC<{
  language: string;
  code: string;
  javafxInspectorActive: boolean;
}> = ({ language, code, javafxInspectorActive }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      dir="ltr"
      className="relative my-3 rounded-lg border overflow-hidden text-left"
      style={{
        backgroundColor: 'var(--bg-code-block)',
        borderColor: 'var(--border-subtle)',
      }}
    >
      {javafxInspectorActive && (
        <span className="absolute top-1 right-24 z-20 px-1.5 py-0.2 text-[9px] font-mono-tabular rounded bg-[#E5A93C] text-[#141413] font-semibold">
          VBox.code-block-card
        </span>
      )}
      <div
        className="h-[34px] px-3 border-b flex items-center justify-between"
        style={{
          backgroundColor: 'var(--bg-code-header)',
          borderColor: 'var(--border-subtle)',
        }}
      >
        <span
          className="text-[11px] font-mono-tabular uppercase tracking-wider font-medium"
          style={{ color: 'var(--text-secondary)' }}
        >
          {language || 'code'}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className="h-[24px] px-2 rounded text-[11px] font-medium flex items-center gap-1.5 transition-colors cursor-pointer border"
          style={{
            backgroundColor: copied ? 'var(--accent-subtle)' : 'var(--bg-elevated)',
            borderColor: copied ? 'var(--accent-primary)' : 'var(--border-subtle)',
            color: copied ? 'var(--accent-primary)' : 'var(--text-secondary)',
          }}
        >
          {copied ? (
            <>
              <Check className="w-3 h-3" />
              <span>Copied ✓</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="p-3.5 overflow-x-auto text-[13px] font-mono-tabular leading-[1.55] m-0">
        <code>{code}</code>
      </pre>
    </div>
  );
};

export const MessageStream: React.FC<MessageStreamProps> = ({
  messages,
  activeModel,
  hardwareState,
  onStarterPrompt,
  onRecoverHardwareError,
  onOpenDownloads,
  javafxInspectorActive,
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);
  const [savedImageId, setSavedImageId] = useState<string | null>(null);
  const [copiedPromptId, setCopiedPromptId] = useState<string | null>(null);

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages]);

  const handleCopyMessage = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedMsgId(id);
    setTimeout(() => setCopiedMsgId(null), 2000);
  };

  const handleDownloadImage = (msgId: string, imageUrl: string, prompt: string) => {
    const link = document.createElement('a');
    link.href = imageUrl;
    const slug = prompt
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .slice(0, 32);
    link.download = `sulvana-${slug || 'generated'}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setSavedImageId(msgId);
    setTimeout(() => setSavedImageId(null), 2200);
  };

  return (
    <div
      ref={scrollContainerRef}
      className="relative flex-1 overflow-y-auto px-4 sm:px-6 py-6"
      style={{ backgroundColor: 'var(--bg-app-canvas)' }}
    >
      {javafxInspectorActive && (
        <span className="sticky top-0 left-2 z-30 inline-block mb-2 px-1.5 py-0.5 text-[10px] font-mono-tabular rounded bg-[#E5A93C] text-[#141413] font-semibold shadow">
          ScrollPane.chat-scroll-pane &gt; VBox.chat-message-list (maxWidth: 760px)
        </span>
      )}

      <div className="max-w-[760px] mx-auto space-y-5">
        {/* Human-Friendly Top Hardware Banner when in Warning / Error / Loading state */}
        {hardwareState === 'vram_warning' && (
          <div
            className="p-3.5 rounded-xl border flex items-start justify-between gap-3"
            style={{
              backgroundColor: 'rgba(217, 130, 43, 0.12)',
              borderColor: 'var(--status-warn)',
            }}
          >
            <div className="flex items-start gap-2.5">
              <AlertCircle
                className="w-4 h-4 shrink-0 mt-0.5"
                style={{ color: 'var(--status-warn)' }}
              />
              <div className="text-[13px] leading-snug">
                <p className="font-semibold">
                  Graphics memory is nearly full (7.8 / 8.0 GB VRAM)
                </p>
                <p className="mt-0.5 text-[12px]" style={{ color: 'var(--text-secondary)' }}>
                  Sulvana is automatically sharing layers with system RAM so your chat continues smoothly without crashing. Replies may be ~35% slower.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onRecoverHardwareError}
              className="shrink-0 h-[28px] px-2.5 rounded-lg border text-[11px] font-semibold cursor-pointer"
              style={{
                backgroundColor: 'var(--bg-elevated)',
                borderColor: 'var(--border-subtle)',
              }}
            >
              Optimize Memory
            </button>
          </div>
        )}

        {(hardwareState === 'error_backend' ||
          hardwareState === 'error_model_missing') && (
          <div
            className="p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3"
            style={{
              backgroundColor: 'rgba(217, 83, 79, 0.12)',
              borderColor: 'var(--status-error)',
            }}
          >
            <div className="flex items-start gap-3">
              <AlertCircle
                className="w-5 h-5 shrink-0 mt-0.5"
                style={{ color: 'var(--status-error)' }}
              />
              <div>
                <h4 className="text-[13px] font-semibold">
                  {hardwareState === 'error_model_missing'
                    ? `${activeModel.name} isn’t downloaded on this computer yet`
                    : 'The local Python AI engine paused unexpectedly'}
                </h4>
                <p
                  className="text-[12px] mt-0.5 leading-relaxed"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  {hardwareState === 'error_model_missing'
                    ? 'You can download this model in the Model Manager, or switch back to an installed model like Qwen 2.5 7B.'
                    : 'Your conversation history is safely saved on disk. Click Restart Local Engine to reconnect in about 2 seconds.'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {hardwareState === 'error_model_missing' && (
                <button
                  type="button"
                  onClick={onOpenDownloads}
                  className="h-[32px] px-3 rounded-lg text-[12px] font-semibold cursor-pointer"
                  style={{
                    backgroundColor: 'var(--accent-primary)',
                    color: 'var(--accent-text-on-solid)',
                  }}
                >
                  Open Downloads
                </button>
              )}
              <button
                type="button"
                onClick={onRecoverHardwareError}
                className="h-[32px] px-3 rounded-lg border text-[12px] font-semibold flex items-center gap-1.5 cursor-pointer"
                style={{
                  backgroundColor: 'var(--bg-elevated)',
                  borderColor: 'var(--border-subtle)',
                }}
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>
                  {hardwareState === 'error_model_missing'
                    ? 'Use Qwen 2.5 7B'
                    : 'Restart Local Engine'}
                </span>
              </button>
            </div>
          </div>
        )}

        {/* BRAND-NEW CHAT EMPTY STATE */}
        {messages.length === 0 ? (
          <div className="py-8 sm:py-12 flex flex-col items-center text-center">
            <div
              className="w-12 h-12 rounded-2xl border flex items-center justify-center mb-4"
              style={{
                backgroundColor: 'var(--accent-subtle)',
                borderColor: 'var(--accent-primary)',
              }}
            >
              <Sparkles
                className="w-6 h-6"
                style={{ color: 'var(--accent-primary)' }}
              />
            </div>

            <h1 className="text-[20px] font-semibold tracking-tight">
              Ready on your machine
            </h1>
            <p
              className="mt-1.5 text-[13px] max-w-[460px] leading-relaxed"
              style={{ color: 'var(--text-secondary)' }}
            >
              Running{' '}
              <span className="font-medium" style={{ color: 'var(--text-primary)' }}>
                {activeModel.name} ({activeModel.quantization})
              </span>{' '}
              privately on your GPU. Ask a question, attach an image to inspect, or type{' '}
              <code
                className="font-mono-tabular text-[12px] px-1.5 py-0.5 rounded"
                style={{
                  backgroundColor: 'var(--bg-elevated)',
                  color: 'var(--accent-primary)',
                }}
              >
                /image
              </code>{' '}
              to create art locally.
            </p>

            {/* 2x2 Grid of Actionable Starter Cards */}
            <div className="mt-7 w-full max-w-[640px] grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
              <button
                type="button"
                onClick={() =>
                  onStarterPrompt(
                    'Analyze the lighting, materials, and mood of this cliffside studio photo.',
                    SAMPLE_VISION_ATTACHMENTS[0]
                  )
                }
                className="group p-3.5 rounded-xl border transition-colors flex items-start gap-3 cursor-pointer text-left"
                style={{
                  backgroundColor: 'var(--bg-elevated)',
                  borderColor: 'var(--border-subtle)',
                }}
              >
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                  style={{
                    backgroundColor: 'var(--accent-subtle)',
                    color: 'var(--accent-primary)',
                  }}
                >
                  <Eye className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-[13px] font-semibold group-hover:underline">
                    Analyze an Attached Image
                  </div>
                  <p
                    className="text-[12px] mt-0.5 leading-snug"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Attach the Nordic cliffside studio photo and inspect its architectural palette
                  </p>
                </div>
              </button>

              <button
                type="button"
                onClick={() =>
                  onStarterPrompt(
                    '/image A quiet Nordic cliffside library overlooking a dark fjord at dusk with warm golden study lamps'
                  )
                }
                className="group p-3.5 rounded-xl border transition-colors flex items-start gap-3 cursor-pointer text-left"
                style={{
                  backgroundColor: 'var(--bg-elevated)',
                  borderColor: 'var(--border-subtle)',
                }}
              >
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                  style={{
                    backgroundColor: 'var(--accent-subtle)',
                    color: 'var(--accent-primary)',
                  }}
                >
                  <ImageIcon className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-[13px] font-semibold group-hover:underline">
                    Generate a Local Image (/image)
                  </div>
                  <p
                    className="text-[12px] mt-0.5 leading-snug"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Run a 4-step local diffusion pass and save the rendered artwork to disk
                  </p>
                </div>
              </button>

              <button
                type="button"
                onClick={() =>
                  onStarterPrompt(
                    'Write a clean JavaFX Task<Void> snippet that reads a Python SSE token stream and updates a TextFlow safely with Platform.runLater.'
                  )
                }
                className="group p-3.5 rounded-xl border transition-colors flex items-start gap-3 cursor-pointer text-left"
                style={{
                  backgroundColor: 'var(--bg-elevated)',
                  borderColor: 'var(--border-subtle)',
                }}
              >
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                  style={{
                    backgroundColor: 'var(--accent-subtle)',
                    color: 'var(--accent-primary)',
                  }}
                >
                  <Code2 className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-[13px] font-semibold group-hover:underline">
                    Draft JavaFX + Python Code
                  </div>
                  <p
                    className="text-[12px] mt-0.5 leading-snug"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Generate a non-blocking JavaFX SSE streaming reader with copyable code block
                  </p>
                </div>
              </button>

              <button
                type="button"
                onClick={() =>
                  onStarterPrompt(
                    'Show a short greeting and privacy summary in Khmer (ភាសាខ្មែរ), Arabic (العربية), Japanese (日本語), and English.'
                  )
                }
                className="group p-3.5 rounded-xl border transition-colors flex items-start gap-3 cursor-pointer text-left"
                style={{
                  backgroundColor: 'var(--bg-elevated)',
                  borderColor: 'var(--border-subtle)',
                }}
              >
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                  style={{
                    backgroundColor: 'var(--accent-subtle)',
                    color: 'var(--accent-primary)',
                  }}
                >
                  <Languages className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-[13px] font-semibold group-hover:underline">
                    Multi-Script Typography Test
                  </div>
                  <p
                    className="text-[12px] mt-0.5 leading-snug"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Test Khmer subscripts, Arabic RTL cursive, Japanese CJK, and English
                  </p>
                </div>
              </button>
            </div>
          </div>
        ) : (
          /* CONVERSATION MESSAGES */
          messages.map((msg) => {
            const isUser = msg.role === 'user';
            const isRtl = msg.direction === 'rtl';
            const parsedBlocks = parseMarkdownBlocks(msg.content);

            if (isUser) {
              return (
                <div
                  key={msg.id}
                  className="flex justify-end"
                >
                  <div
                    dir={isRtl ? 'rtl' : 'ltr'}
                    className="relative max-w-[580px] rounded-xl border px-4 py-3"
                    style={{
                      backgroundColor: 'var(--bg-user-msg)',
                      borderColor: 'var(--border-subtle)',
                    }}
                  >
                    {javafxInspectorActive && (
                      <span className="absolute -top-3 right-2 px-1.5 py-0.2 text-[9px] font-mono-tabular rounded bg-[#E5A93C] text-[#141413] font-semibold">
                        VBox.chat-bubble-user
                      </span>
                    )}

                    {/* Attached Vision Images inside User Message */}
                    {msg.attachments && msg.attachments.length > 0 && (
                      <div className="mb-2.5 flex flex-wrap gap-2">
                        {msg.attachments.map((att) => (
                          <div
                            key={att.id}
                            className="rounded-lg overflow-hidden border flex items-center gap-2.5 p-1.5 pr-3"
                            style={{
                              backgroundColor: 'var(--bg-elevated)',
                              borderColor: 'var(--border-subtle)',
                            }}
                          >
                            <img
                              src={att.url}
                              alt={att.name}
                              className="w-14 h-14 object-cover rounded-md shrink-0"
                            />
                            <div className="text-left min-w-0">
                              <div className="text-[12px] font-medium truncate max-w-[180px]">
                                {att.name}
                              </div>
                              <div
                                className="text-[11px] font-mono-tabular mt-0.5"
                                style={{ color: 'var(--text-muted)' }}
                              >
                                {att.dimensions} • {att.sizeLabel}
                              </div>
                              <span
                                className="inline-block mt-1 text-[10px] px-1.5 py-0.2 rounded font-medium"
                                style={{
                                  backgroundColor: 'var(--accent-subtle)',
                                  color: 'var(--accent-primary)',
                                }}
                              >
                                Vision Input
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* User Message Text */}
                    <div className="sulvana-message-prose whitespace-pre-wrap">
                      {msg.content}
                    </div>

                    <div
                      className="mt-1.5 flex items-center justify-end gap-2 text-[11px]"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      {msg.scriptLabel && <span>{msg.scriptLabel}</span>}
                      <span>{msg.timestamp}</span>
                    </div>
                  </div>
                </div>
              );
            }

            // ASSISTANT MESSAGE BLOCK
            return (
              <div
                key={msg.id}
                className="relative max-w-[720px] pt-1 pb-2"
              >
                {javafxInspectorActive && (
                  <span className="absolute -top-2 left-0 px-1.5 py-0.2 text-[9px] font-mono-tabular rounded bg-[#E5A93C] text-[#141413] font-semibold">
                    VBox.assistant-message-block
                  </span>
                )}

                {/* Assistant Meta Row */}
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <div
                      className="w-5 h-5 rounded-md flex items-center justify-center border"
                      style={{
                        backgroundColor: 'var(--accent-subtle)',
                        borderColor: 'var(--accent-primary)',
                      }}
                    >
                      <Cpu
                        className="w-3 h-3"
                        style={{ color: 'var(--accent-primary)' }}
                      />
                    </div>
                    <span className="text-[12px] font-semibold">
                      Sulvana
                    </span>
                    {msg.modelUsed && (
                      <span
                        className="text-[11px] font-mono-tabular px-1.5 py-0.2 rounded border"
                        style={{
                          backgroundColor: 'var(--bg-elevated)',
                          borderColor: 'var(--border-subtle)',
                          color: 'var(--text-secondary)',
                        }}
                      >
                        {msg.modelUsed}
                      </span>
                    )}
                    {msg.tokensPerSec && (
                      <span
                        className="text-[11px] font-mono-tabular"
                        style={{ color: 'var(--text-muted)' }}
                      >
                        {msg.tokensPerSec.toFixed(1)} tok/s
                      </span>
                    )}
                    {msg.scriptLabel && (
                      <span
                        className="text-[10px] px-1.5 py-0.2 rounded"
                        style={{
                          backgroundColor: 'var(--accent-subtle)',
                          color: 'var(--accent-primary)',
                        }}
                      >
                        {msg.scriptLabel}
                      </span>
                    )}
                  </div>

                  {/* Copy Entire Assistant Reply */}
                  <button
                    type="button"
                    onClick={() => handleCopyMessage(msg.id, msg.content)}
                    className="h-[24px] px-2 rounded text-[11px] font-medium flex items-center gap-1 transition-colors cursor-pointer"
                    style={{
                      color:
                        copiedMsgId === msg.id
                          ? 'var(--accent-primary)'
                          : 'var(--text-muted)',
                    }}
                    title="Copy assistant response"
                  >
                    {copiedMsgId === msg.id ? (
                      <>
                        <Check className="w-3 h-3" />
                        <span>Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>

                {/* Assistant Formatted Content */}
                <div
                  dir={isRtl ? 'rtl' : 'ltr'}
                  className="sulvana-message-prose space-y-2.5"
                >
                  {parsedBlocks.map((block, idx) => {
                    if (block.type === 'code') {
                      return (
                        <CodeBlockCard
                          key={idx}
                          language={block.language || 'code'}
                          code={block.content}
                          javafxInspectorActive={javafxInspectorActive}
                        />
                      );
                    }

                    // Prose paragraphs & lists
                    const lines = block.content.split('\n');
                    return (
                      <div key={idx} className="space-y-2">
                        {lines.map((line, lineIdx) => {
                          const trimmed = line.trim();
                          if (!trimmed) return null;

                          if (trimmed.startsWith('### ')) {
                            return (
                              <h3
                                key={lineIdx}
                                className="text-[16px] font-semibold pt-1"
                                style={{ color: 'var(--text-primary)' }}
                              >
                                {trimmed.replace('### ', '')}
                              </h3>
                            );
                          }

                          if (trimmed.startsWith('- ')) {
                            return (
                              <div
                                key={lineIdx}
                                className="flex items-start gap-2.5 pl-1"
                              >
                                <span
                                  className="mt-2.5 w-1.5 h-1.5 rounded-full shrink-0"
                                  style={{
                                    backgroundColor: 'var(--accent-primary)',
                                  }}
                                />
                                <div className="flex-1">
                                  {renderInlineFormatting(trimmed.slice(2))}
                                </div>
                              </div>
                            );
                          }

                          return (
                            <p key={lineIdx} className="m-0">
                              {renderInlineFormatting(line)}
                            </p>
                          );
                        })}
                      </div>
                    );
                  })}

                  {/* Streaming cursor indicator */}
                  {msg.isStreaming && (
                    <span
                      className="inline-block w-2 h-4 align-middle ml-1 rounded-xs animate-sulvana-pulse"
                      style={{ backgroundColor: 'var(--accent-primary)' }}
                    />
                  )}
                </div>

                {/* Generated Image Card (when /image or Generate Image action is used) */}
                {msg.generatedImage && (
                  <div
                    className="mt-3 max-w-[440px] rounded-xl border overflow-hidden"
                    style={{
                      backgroundColor: 'var(--bg-elevated)',
                      borderColor: 'var(--border-subtle)',
                    }}
                  >
                    {msg.generatedImage.status === 'generating' ? (
                      <div className="p-5 space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-[13px] font-semibold flex items-center gap-2">
                            <ImageIcon
                              className="w-4 h-4 animate-sulvana-pulse"
                              style={{ color: 'var(--accent-primary)' }}
                            />
                            <span>Generating image locally…</span>
                          </span>
                          <span
                            className="text-[12px] font-mono-tabular font-semibold"
                            style={{ color: 'var(--accent-primary)' }}
                          >
                            Step {msg.generatedImage.currentStep} /{' '}
                            {msg.generatedImage.stepsTotal}
                          </span>
                        </div>

                        {/* Step ProgressBar */}
                        <div
                          className="w-full h-2 rounded-full overflow-hidden border"
                          style={{
                            backgroundColor: 'var(--bg-input)',
                            borderColor: 'var(--border-subtle)',
                          }}
                        >
                          <div
                            className="h-full transition-all duration-300"
                            style={{
                              width: `${Math.round(
                                (msg.generatedImage.currentStep /
                                  msg.generatedImage.stepsTotal) *
                                  100
                              )}%`,
                              backgroundColor: 'var(--accent-primary)',
                            }}
                          />
                        </div>

                        <p
                          className="text-[12px] italic line-clamp-2"
                          style={{ color: 'var(--text-secondary)' }}
                        >
                          “{msg.generatedImage.prompt}”
                        </p>
                      </div>
                    ) : (
                      <div>
                        <div className="relative bg-black/20">
                          <img
                            src={msg.generatedImage.imageUrl}
                            alt={msg.generatedImage.prompt}
                            className="w-full h-[290px] object-cover block"
                          />
                          <span
                            className="absolute top-2.5 left-2.5 text-[10px] font-mono-tabular px-2 py-0.5 rounded-md font-medium"
                            style={{
                              backgroundColor: 'rgba(20, 20, 19, 0.82)',
                              color: '#F2F0EC',
                              border: '1px solid rgba(255,255,255,0.12)',
                            }}
                          >
                            {msg.generatedImage.resolution} • Seed{' '}
                            {msg.generatedImage.seed}
                          </span>
                        </div>

                        {/* Prompt & Save Image Action Row */}
                        <div className="p-3 space-y-2.5">
                          <p
                            className="text-[12px] line-clamp-2 leading-snug"
                            style={{ color: 'var(--text-secondary)' }}
                          >
                            <span
                              className="font-mono-tabular text-[11px] mr-1.5 px-1.5 py-0.2 rounded"
                              style={{
                                backgroundColor: 'var(--accent-subtle)',
                                color: 'var(--accent-primary)',
                              }}
                            >
                              /image
                            </span>
                            {msg.generatedImage.prompt}
                          </p>

                          <div className="flex items-center justify-between gap-2 pt-1">
                            <button
                              type="button"
                              onClick={() =>
                                handleDownloadImage(
                                  msg.id,
                                  msg.generatedImage!.imageUrl ||
                                    '/images/sulvana-lantern-forest.jpg',
                                  msg.generatedImage!.prompt
                                )
                              }
                              className="h-[32px] px-3 rounded-lg text-[12px] font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                              style={{
                                backgroundColor: 'var(--accent-primary)',
                                color: 'var(--accent-text-on-solid)',
                              }}
                            >
                              {savedImageId === msg.id ? (
                                <>
                                  <Check className="w-3.5 h-3.5" />
                                  <span>Saved to Pictures ✓</span>
                                </>
                              ) : (
                                <>
                                  <Download className="w-3.5 h-3.5" />
                                  <span>Save Image</span>
                                </>
                              )}
                            </button>

                            <button
                              type="button"
                              onClick={() => {
                                navigator.clipboard.writeText(
                                  `/image ${msg.generatedImage!.prompt}`
                                );
                                setCopiedPromptId(msg.id);
                                setTimeout(() => setCopiedPromptId(null), 2000);
                              }}
                              className="h-[32px] px-2.5 rounded-lg border text-[12px] font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
                              style={{
                                backgroundColor: 'var(--bg-input)',
                                borderColor: 'var(--border-subtle)',
                                color: 'var(--text-secondary)',
                              }}
                            >
                              {copiedPromptId === msg.id ? (
                                <>
                                  <Check
                                    className="w-3.5 h-3.5"
                                    style={{ color: 'var(--accent-primary)' }}
                                  />
                                  <span>Prompt Copied</span>
                                </>
                              ) : (
                                <>
                                  <Copy className="w-3.5 h-3.5" />
                                  <span>Copy Prompt</span>
                                </>
                              )}
                            </button>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
