import React, { useState, useRef } from 'react';
import {
  Send,
  Square,
  Paperclip,
  Image as ImageIcon,
  X,
  Sparkles,
  Upload,
} from 'lucide-react';
import { LocalModel, VisionAttachment } from '../types/sulvana';
import { SAMPLE_VISION_ATTACHMENTS } from '../data/initialData';

interface MessageComposerProps {
  onSendMessage: (text: string, attachments: VisionAttachment[]) => void;
  isBusy: boolean;
  onStopGeneration: () => void;
  activeModel: LocalModel;
  stagedAttachments: VisionAttachment[];
  onStageAttachment: (att: VisionAttachment) => void;
  onRemoveAttachment: (id: string) => void;
  javafxInspectorActive: boolean;
}

export const MessageComposer: React.FC<MessageComposerProps> = ({
  onSendMessage,
  isBusy,
  onStopGeneration,
  activeModel,
  stagedAttachments,
  onStageAttachment,
  onRemoveAttachment,
  javafxInspectorActive,
}) => {
  const [inputText, setInputText] = useState('');
  const [attachPopoverOpen, setAttachPopoverOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isImageGenCommand =
    inputText.trimStart().toLowerCase().startsWith('/image ') ||
    inputText.trim().toLowerCase() === '/image';

  const handleToggleImageMode = () => {
    if (isImageGenCommand) {
      setInputText((prev) => prev.replace(/^\/image\s*/i, ''));
    } else {
      setInputText((prev) => `/image ${prev.trimStart()}`);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const objectUrl = URL.createObjectURL(file);
    const sizeKb = Math.max(1, Math.round(file.size / 1024));
    const sizeLabel =
      sizeKb > 1024 ? `${(sizeKb / 1024).toFixed(1)} MB` : `${sizeKb} KB`;

    onStageAttachment({
      id: `upload-${Date.now()}`,
      name: file.name,
      url: objectUrl,
      dimensions: 'Local Image',
      sizeLabel,
    });
    setAttachPopoverOpen(false);
    e.target.value = '';
  };

  const handleSend = () => {
    if (isBusy) return;
    if (!inputText.trim() && stagedAttachments.length === 0) return;

    const finalPrompt =
      !inputText.trim() && stagedAttachments.length > 0
        ? 'Please describe this image and highlight key details.'
        : inputText;

    onSendMessage(finalPrompt, stagedAttachments);
    setInputText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Detect Arabic script in input for automatic RTL orientation in composer
  const isInputRtl = /[\u0600-\u06FF]/.test(inputText);

  return (
    <div
      className="relative shrink-0 px-4 sm:px-6 pt-2 pb-4 border-t"
      style={{
        backgroundColor: 'var(--bg-app-canvas)',
        borderColor: 'var(--border-subtle)',
      }}
    >
      {javafxInspectorActive && (
        <span className="absolute -top-3 left-6 z-30 px-1.5 py-0.5 text-[10px] font-mono-tabular rounded bg-[#E5A93C] text-[#141413] font-semibold shadow">
          VBox.composer-box (maxWidth: 760px)
        </span>
      )}

      <div className="max-w-[760px] mx-auto">
        {/* Composer Main Card */}
        <div
          className="rounded-xl border transition-colors p-2.5"
          style={{
            backgroundColor: 'var(--bg-input)',
            borderColor: isImageGenCommand
              ? 'var(--accent-primary)'
              : 'var(--border-subtle)',
          }}
        >
          {/* Staging Area: Attached Image Previews OR /image Active Banner */}
          {(stagedAttachments.length > 0 || isImageGenCommand) && (
            <div
              className="mb-2.5 pb-2.5 border-b flex flex-wrap items-center gap-2.5"
              style={{ borderColor: 'var(--border-subtle)' }}
            >
              {/* Vision Attachment Previews */}
              {stagedAttachments.map((att) => (
                <div
                  key={att.id}
                  className="relative group flex items-center gap-2.5 p-1.5 pr-2.5 rounded-lg border"
                  style={{
                    backgroundColor: 'var(--bg-elevated)',
                    borderColor: 'var(--border-subtle)',
                  }}
                >
                  <img
                    src={att.url}
                    alt={att.name}
                    className="w-12 h-12 rounded-md object-cover shrink-0"
                  />
                  <div className="min-w-0">
                    <div className="text-[12px] font-medium truncate max-w-[160px]">
                      {att.name}
                    </div>
                    <div
                      className="text-[10px] font-mono-tabular"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      {att.dimensions} • {att.sizeLabel}
                    </div>
                    <span
                      className="inline-block mt-0.5 text-[10px] px-1.5 py-0.1 rounded font-medium"
                      style={{
                        backgroundColor: 'var(--accent-subtle)',
                        color: 'var(--accent-primary)',
                      }}
                    >
                      Ready for Vision Analysis
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => onRemoveAttachment(att.id)}
                    className="w-5 h-5 rounded-full flex items-center justify-center hover:bg-black/30 cursor-pointer"
                    style={{ color: 'var(--text-secondary)' }}
                    title="Remove attached image"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}

              {/* /image Mode Active Pill */}
              {isImageGenCommand && (
                <div
                  className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg border text-[12px]"
                  style={{
                    backgroundColor: 'var(--accent-subtle)',
                    borderColor: 'var(--accent-primary)',
                    color: 'var(--accent-primary)',
                  }}
                >
                  <Sparkles className="w-3.5 h-3.5 shrink-0" />
                  <span className="font-semibold">
                    Local Image Generation Mode (/image)
                  </span>
                  <span
                    className="text-[11px] hidden sm:inline"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    • Renders 1024×1024 on GPU
                  </span>
                  <button
                    type="button"
                    onClick={handleToggleImageMode}
                    className="ml-1 hover:opacity-80 cursor-pointer"
                    title="Exit image generation mode"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Auto-growing / Multi-script TextArea */}
          <textarea
            dir={isInputRtl ? 'rtl' : 'ltr'}
            rows={2}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isImageGenCommand
                ? 'Describe the image you want Sulvana to paint locally (e.g., /image A misty cedar forest with warm amber glass lanterns)…'
                : stagedAttachments.length > 0
                ? 'Ask a question about the attached image, or press Send for a full visual breakdown…'
                : 'Ask anything privately, attach an image, or type /image to create art…'
            }
            className="w-full bg-transparent resize-none outline-none sulvana-message-prose text-[14px] placeholder:opacity-60"
            style={{ color: 'var(--text-primary)' }}
          />

          {/* Bottom Composer Action Bar */}
          <div className="mt-2 pt-1.5 flex flex-wrap items-center justify-between gap-2">
            {/* Left Tool Controls: Attach Image + Generate Image + Quick Script Pills */}
            <div className="flex items-center gap-1.5 flex-wrap">
              {/* Hidden File Input */}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={handleFileChange}
                className="hidden"
              />

              {/* Attach Image Button + Sample Picker Popover */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setAttachPopoverOpen((prev) => !prev)}
                  className="h-[32px] px-2.5 rounded-lg border text-[12px] font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
                  style={{
                    backgroundColor:
                      stagedAttachments.length > 0
                        ? 'var(--accent-subtle)'
                        : 'var(--bg-elevated)',
                    borderColor:
                      stagedAttachments.length > 0
                        ? 'var(--accent-primary)'
                        : 'var(--border-subtle)',
                    color:
                      stagedAttachments.length > 0
                        ? 'var(--accent-primary)'
                        : 'var(--text-secondary)',
                  }}
                  title="Attach an image for local vision analysis"
                >
                  <Paperclip className="w-3.5 h-3.5" />
                  <span>Attach Image</span>
                </button>

                {attachPopoverOpen && (
                  <div
                    className="absolute bottom-[38px] left-0 w-[290px] rounded-xl border p-2 z-50 shadow-xl"
                    style={{
                      backgroundColor: 'var(--bg-elevated)',
                      borderColor: 'var(--border-subtle)',
                    }}
                  >
                    <div className="flex items-center justify-between px-1.5 py-1">
                      <span
                        className="text-[11px] font-semibold uppercase tracking-wider"
                        style={{ color: 'var(--text-muted)' }}
                      >
                        Attach Image for Vision AI
                      </span>
                      <button
                        type="button"
                        onClick={() => setAttachPopoverOpen(false)}
                        className="cursor-pointer"
                        style={{ color: 'var(--text-muted)' }}
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="w-full mt-1 p-2 rounded-lg border text-left text-[12px] font-medium flex items-center gap-2 transition-colors cursor-pointer"
                      style={{
                        backgroundColor: 'var(--bg-input)',
                        borderColor: 'var(--border-subtle)',
                      }}
                    >
                      <Upload
                        className="w-4 h-4 shrink-0"
                        style={{ color: 'var(--accent-primary)' }}
                      />
                      <div>
                        <div>Upload from computer…</div>
                        <div
                          className="text-[10px]"
                          style={{ color: 'var(--text-muted)' }}
                        >
                          PNG, JPG, WEBP processed locally
                        </div>
                      </div>
                    </button>

                    <div
                      className="mt-2 mb-1 px-1.5 text-[10px] font-semibold uppercase tracking-wider"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      Or try a studio sample image:
                    </div>
                    <div className="space-y-1">
                      {SAMPLE_VISION_ATTACHMENTS.map((sample) => (
                        <button
                          key={sample.id}
                          type="button"
                          onClick={() => {
                            onStageAttachment(sample);
                            setAttachPopoverOpen(false);
                          }}
                          className="w-full p-1.5 rounded-lg flex items-center gap-2.5 text-left hover:opacity-90 cursor-pointer"
                          style={{ backgroundColor: 'var(--bg-input)' }}
                        >
                          <img
                            src={sample.url}
                            alt={sample.name}
                            className="w-9 h-9 rounded object-cover shrink-0"
                          />
                          <div className="min-w-0 flex-1">
                            <div className="text-[12px] font-medium truncate">
                              {sample.name}
                            </div>
                            <div
                              className="text-[10px] font-mono-tabular"
                              style={{ color: 'var(--text-muted)' }}
                            >
                              {sample.dimensions} • {sample.sizeLabel}
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Generate Image Mode Button (/image) */}
              <button
                type="button"
                onClick={handleToggleImageMode}
                className="h-[32px] px-2.5 rounded-lg border text-[12px] font-medium flex items-center gap-1.5 transition-colors cursor-pointer"
                style={{
                  backgroundColor: isImageGenCommand
                    ? 'var(--accent-subtle)'
                    : 'var(--bg-elevated)',
                  borderColor: isImageGenCommand
                    ? 'var(--accent-primary)'
                    : 'var(--border-subtle)',
                  color: isImageGenCommand
                    ? 'var(--accent-primary)'
                    : 'var(--text-secondary)',
                }}
                title="Generate an image locally (/image)"
              >
                <ImageIcon className="w-3.5 h-3.5" />
                <span>Generate Image</span>
              </button>

              {/* Quick Multi-Script Input Helpers (Khmer, Arabic, CJK) */}
              <div className="hidden md:flex items-center gap-1 pl-1">
                <button
                  type="button"
                  onClick={() =>
                    setInputText(
                      'សូមសរសេរកំណត់ត្រាសង្ខេបអំពីការរចនាកម្មវិធីកុំព្យូទ័រដែលងាយស្រួលប្រើប្រាស់។'
                    )
                  }
                  className="h-[26px] px-2 rounded text-[11px] border cursor-pointer transition-colors"
                  style={{
                    backgroundColor: 'var(--bg-elevated)',
                    borderColor: 'var(--border-subtle)',
                    color: 'var(--text-secondary)',
                  }}
                  title="Insert sample Khmer prompt"
                >
                  ខ្មែរ
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setInputText(
                      'اكتب ملخصاً قصيراً حول أهمية الخصوصية في تطبيقات الذكاء الاصطناعي المحلية.'
                    )
                  }
                  className="h-[26px] px-2 rounded text-[11px] border cursor-pointer transition-colors"
                  style={{
                    backgroundColor: 'var(--bg-elevated)',
                    borderColor: 'var(--border-subtle)',
                    color: 'var(--text-secondary)',
                  }}
                  title="Insert sample Arabic RTL prompt"
                >
                  العربية
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setInputText(
                      'ローカルAIがオフライン環境でどのようにプライバシーを守るか説明してください。'
                    )
                  }
                  className="h-[26px] px-2 rounded text-[11px] border cursor-pointer transition-colors"
                  style={{
                    backgroundColor: 'var(--bg-elevated)',
                    borderColor: 'var(--border-subtle)',
                    color: 'var(--text-secondary)',
                  }}
                  title="Insert sample Japanese prompt"
                >
                  日本語
                </button>
              </div>
            </div>

            {/* Right: Keyboard Hint + Send / Stop Primary Action */}
            <div className="flex items-center gap-2.5 ml-auto">
              <span
                className="text-[11px] hidden sm:inline"
                style={{ color: 'var(--text-muted)' }}
              >
                {activeModel.name.split(' ')[0]} • Enter to send
              </span>

              {isBusy ? (
                <button
                  type="button"
                  onClick={onStopGeneration}
                  className="h-[34px] px-3.5 rounded-lg border font-semibold text-[12px] flex items-center gap-1.5 transition-colors cursor-pointer"
                  style={{
                    backgroundColor: 'rgba(217, 83, 79, 0.16)',
                    borderColor: 'var(--status-error)',
                    color: 'var(--text-primary)',
                  }}
                  title="Stop generation immediately (Esc)"
                >
                  <Square
                    className="w-3.5 h-3.5 fill-current"
                    style={{ color: 'var(--status-error)' }}
                  />
                  <span>Stop</span>
                </button>
              ) : (
                <button
                  type="button"
                  disabled={!inputText.trim() && stagedAttachments.length === 0}
                  onClick={handleSend}
                  className="h-[34px] px-4 rounded-lg font-semibold text-[12px] flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{
                    backgroundColor: 'var(--accent-primary)',
                    color: 'var(--accent-text-on-solid)',
                  }}
                  title="Send message (Enter)"
                >
                  <span>{isImageGenCommand ? 'Create Image' : 'Send'}</span>
                  <Send className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
