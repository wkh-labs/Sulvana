import React, { useState } from 'react';
import {
  X,
  Layers,
  Palette,
  Layout,
  Activity,
  Code,
  Wrench,
  Copy,
  Check,
  Eye,
} from 'lucide-react';
import {
  JAVAFX_CSS_STYLESHEET,
  JAVAFX_SCENE_TREE_CODE,
  SPEC_SECTIONS,
} from '../data/javafxSpecData';

interface DesignSpecModalProps {
  isOpen: boolean;
  onClose: () => void;
  javafxInspectorActive: boolean;
  onToggleJavafxInspector: () => void;
}

export const DesignSpecModal: React.FC<DesignSpecModalProps> = ({
  isOpen,
  onClose,
  javafxInspectorActive,
  onToggleJavafxInspector,
}) => {
  const [activeSection, setActiveSection] = useState<string>('concept-tokens');
  const [copiedBlock, setCopiedBlock] = useState<string | null>(null);

  if (!isOpen) return null;

  const copyText = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedBlock(id);
    setTimeout(() => setCopiedBlock(null), 2000);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6"
      style={{ backgroundColor: 'rgba(10, 10, 9, 0.78)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-[1040px] h-[88vh] rounded-2xl border flex flex-col overflow-hidden shadow-2xl"
        style={{
          backgroundColor: 'var(--bg-elevated)',
          borderColor: 'var(--border-subtle)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Header */}
        <div
          className="px-5 py-3.5 border-b flex items-center justify-between gap-3 shrink-0"
          style={{
            backgroundColor: 'var(--bg-sidebar)',
            borderColor: 'var(--border-subtle)',
          }}
        >
          <div className="flex items-center gap-2.5">
            <div
              className="w-8 h-8 rounded-lg border flex items-center justify-center"
              style={{
                backgroundColor: 'var(--accent-subtle)',
                borderColor: 'var(--accent-primary)',
              }}
            >
              <Layers
                className="w-4 h-4"
                style={{ color: 'var(--accent-primary)' }}
              />
            </div>
            <div>
              <h2 className="text-[15px] font-semibold">
                Sulvana — Complete UI Design Specification & JavaFX + CSS Blueprint
              </h2>
              <p
                className="text-[11px]"
                style={{ color: 'var(--text-secondary)' }}
              >
                Engineered for a solo developer building with JavaFX 21+ CSS & a Python local AI backend
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onToggleJavafxInspector}
              className="h-[32px] px-3 rounded-lg border text-[12px] font-semibold flex items-center gap-1.5 cursor-pointer"
              style={{
                backgroundColor: javafxInspectorActive
                  ? 'var(--accent-primary)'
                  : 'var(--bg-elevated)',
                borderColor: 'var(--accent-primary)',
                color: javafxInspectorActive
                  ? 'var(--accent-text-on-solid)'
                  : 'var(--accent-primary)',
              }}
            >
              <Eye className="w-3.5 h-3.5" />
              <span>
                {javafxInspectorActive
                  ? 'JavaFX X-Ray: ON'
                  : 'Toggle Live JavaFX X-Ray'}
              </span>
            </button>

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
        </div>

        {/* Body: Left Section Navigation + Right Deliverable Content */}
        <div className="flex-1 flex flex-col md:flex-row min-h-0">
          {/* Left Navigation Rail */}
          <div
            className="w-full md:w-[270px] shrink-0 border-b md:border-b-0 md:border-r p-3 space-y-1 overflow-y-auto"
            style={{
              backgroundColor: 'var(--bg-sidebar)',
              borderColor: 'var(--border-subtle)',
            }}
          >
            {SPEC_SECTIONS.map((sec) => {
              const active = activeSection === sec.id;
              const Icon =
                sec.id === 'concept-tokens'
                  ? Palette
                  : sec.id === 'screen-specs'
                  ? Layout
                  : sec.id === 'behavior-matrix'
                  ? Activity
                  : sec.id === 'javafx-tree'
                  ? Code
                  : Wrench;

              return (
                <button
                  key={sec.id}
                  type="button"
                  onClick={() => setActiveSection(sec.id)}
                  className="w-full p-2.5 rounded-xl border text-left transition-colors flex items-start gap-2.5 cursor-pointer"
                  style={{
                    backgroundColor: active
                      ? 'var(--accent-subtle)'
                      : 'transparent',
                    borderColor: active
                      ? 'var(--accent-primary)'
                      : 'transparent',
                  }}
                >
                  <Icon
                    className="w-4 h-4 shrink-0 mt-0.5"
                    style={{
                      color: active
                        ? 'var(--accent-primary)'
                        : 'var(--text-secondary)',
                    }}
                  />
                  <div>
                    <div className="text-[12px] font-semibold leading-snug">
                      {sec.number}. {sec.title}
                    </div>
                    <div
                      className="text-[11px] mt-0.5 leading-tight"
                      style={{ color: 'var(--text-secondary)' }}
                    >
                      {sec.subtitle}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Right Content Pane */}
          <div
            className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-6"
            style={{ backgroundColor: 'var(--bg-app-canvas)' }}
          >
            {/* DELIVERABLE 1: DESIGN CONCEPT & COLOR/TYPE SYSTEM */}
            {activeSection === 'concept-tokens' && (
              <div className="space-y-6">
                <div>
                  <span
                    className="text-[11px] font-mono-tabular uppercase tracking-wider px-2 py-0.5 rounded"
                    style={{
                      backgroundColor: 'var(--accent-subtle)',
                      color: 'var(--accent-primary)',
                    }}
                  >
                    Deliverable 01
                  </span>
                  <h3 className="text-[19px] font-semibold mt-1.5">
                    Design Concept & Color / Typography System
                  </h3>
                  <p
                    className="text-[13px] mt-1 leading-relaxed"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    <strong>“Warm Obsidian Studio”</strong> — Sulvana rejects cold neon sci-fi clichés and sterile chat clones in favor of a tactile, book-like studio workspace. Surfaces are separated by crisp <code>1px</code> solid borders (<code>#2E2D2A</code>) rather than expensive blur passes, ensuring 60fps rendering in JavaFX while keeping the conversation stream completely distraction-free.
                  </p>
                </div>

                {/* Color Token Grid */}
                <div>
                  <h4 className="text-[14px] font-semibold mb-2.5">
                    Color Token Palette (Dark Default + Light Theme)
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                    {[
                      {
                        token: '--bg-app-canvas',
                        dark: '#141413',
                        light: '#FAF9F5',
                        role: 'Primary reading & chat canvas',
                      },
                      {
                        token: '--bg-sidebar',
                        dark: '#1C1C1A',
                        light: '#F2EFE9',
                        role: 'Left rail & top status header',
                      },
                      {
                        token: '--bg-elevated',
                        dark: '#242422',
                        light: '#FFFFFF',
                        role: 'Cards, dropdowns, modals',
                      },
                      {
                        token: '--bg-user-msg',
                        dark: '#2A2926',
                        light: '#EFECE5',
                        role: 'User message bubble fill',
                      },
                      {
                        token: '--accent-primary',
                        dark: '#E5A93C',
                        light: '#C4841D',
                        role: 'Warm Amber Gold primary CTA & focus',
                      },
                      {
                        token: '--status-ready / warn / err',
                        dark: '#4E9F6E / #D9822B / #D9534F',
                        light: '#2E7D52 / #B86519 / #C23B37',
                        role: 'Calm semantic hardware & error indicators',
                      },
                    ].map((swatch) => (
                      <div
                        key={swatch.token}
                        className="p-3 rounded-xl border flex items-start gap-3"
                        style={{
                          backgroundColor: 'var(--bg-elevated)',
                          borderColor: 'var(--border-subtle)',
                        }}
                      >
                        <div
                          className="w-8 h-8 rounded-lg border shrink-0 mt-0.5"
                          style={{
                            backgroundColor: swatch.dark.split(' ')[0],
                            borderColor: 'var(--border-subtle)',
                          }}
                        />
                        <div className="min-w-0">
                          <div className="text-[12px] font-mono-tabular font-semibold">
                            {swatch.token}
                          </div>
                          <div
                            className="text-[11px] font-mono-tabular mt-0.5"
                            style={{ color: 'var(--accent-primary)' }}
                          >
                            Dark: {swatch.dark}
                          </div>
                          <div
                            className="text-[11px] mt-0.5"
                            style={{ color: 'var(--text-secondary)' }}
                          >
                            {swatch.role}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Multi-Script Typography Specification */}
                <div
                  className="p-4 rounded-xl border space-y-3"
                  style={{
                    backgroundColor: 'var(--bg-elevated)',
                    borderColor: 'var(--border-subtle)',
                  }}
                >
                  <h4 className="text-[14px] font-semibold">
                    Multi-Script Typography System (Khmer, Arabic, Chinese, Japanese, English)
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[12px]">
                    <div
                      className="p-3 rounded-lg border"
                      style={{
                        backgroundColor: 'var(--bg-sidebar)',
                        borderColor: 'var(--border-subtle)',
                      }}
                    >
                      <div className="font-semibold" style={{ color: 'var(--accent-primary)' }}>
                        Font Stack & Vertical Metrics
                      </div>
                      <p className="mt-1 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                        <code>"Inter", "Segoe UI", "Noto Sans", "Noto Sans Khmer", "Noto Sans Arabic", "Noto Sans CJK JP", sans-serif</code>. Message body text uses <strong>15px size</strong> with <strong>1.65 line-height</strong> (<code>-fx-line-spacing: 6px</code>) so tall Khmer consonant subscripts (ជើងអក្សរ) and Arabic vowel marks never clip.
                      </p>
                    </div>
                    <div
                      className="p-3 rounded-lg border"
                      style={{
                        backgroundColor: 'var(--bg-sidebar)',
                        borderColor: 'var(--border-subtle)',
                      }}
                    >
                      <div className="font-semibold" style={{ color: 'var(--accent-primary)' }}>
                        Script Shaping & Layout Rules
                      </div>
                      <p className="mt-1 leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                        • <strong>Zero Letter-Spacing</strong> on body text so Arabic cursive ligatures and Khmer clusters stay connected.<br />
                        • <strong>Bidirectional Support</strong>: Arabic paragraphs set <code>NodeOrientation.RIGHT_TO_LEFT</code> while keeping code blocks <code>LEFT_TO_RIGHT</code>.<br />
                        • <strong>Elastic Button Widths</strong>: All buttons use <code>min-width: Region.USE_PREF_SIZE</code> to expand for longer Khmer/Arabic labels.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* DELIVERABLE 2: COMPLETE SCREEN-BY-SCREEN UI SPECIFICATION */}
            {activeSection === 'screen-specs' && (
              <div className="space-y-5">
                <div>
                  <span
                    className="text-[11px] font-mono-tabular uppercase tracking-wider px-2 py-0.5 rounded"
                    style={{
                      backgroundColor: 'var(--accent-subtle)',
                      color: 'var(--accent-primary)',
                    }}
                  >
                    Deliverable 02
                  </span>
                  <h3 className="text-[19px] font-semibold mt-1.5">
                    Complete Screen-by-Screen UI Specification
                  </h3>
                </div>

                <div className="space-y-3 text-[13px]">
                  {[
                    {
                      screen: '1. Main Workspace Frame (BorderPane.root-pane)',
                      spec: 'Minimum window size 800×600; default 1280×820. Uses a distraction-free 3-zone architecture: Top Model & Hardware Status Bar (52px fixed height), Left Conversation Rail (248px width on desktop, 205px at 800×600), and Center Chat & Composer Column (max reading width 760px centered inside a full-height ScrollPane).',
                    },
                    {
                      screen: '2. Top Model & Hardware Status Bar (HBox.status-header-bar)',
                      spec: 'Left: Brand badge + Model Selector ComboBox showing model name, quantization (Q4_K_M / FP8), and VRAM requirement. Center-Left: Human-friendly Hardware Pill with semantic status dot (#4E9F6E Ready, #E5A93C Loading/Streaming, #D9822B High VRAM CPU+GPU split, #D9534F Error), plain-English status label, mini 64px VRAM ProgressBar, and tabular monospace tok/s speed badge. Right: Models & Downloads button (with live % badge when active) and Settings button.',
                    },
                    {
                      screen: '3. Left Conversation & Navigation Rail (VBox.sidebar-rail)',
                      spec: 'Top: Full-width Warm Amber "+ New Chat" primary button (38px height) and session filter TextField. Middle: Scrollable ListView of conversations displaying title, relative time, message count, and script badge (EN, ខ្មែរ, العربية, 日本語). Bottom: Quick Reply Language selector, "Clear Current Chat" button with inline 2-step confirmation, and local privacy reassurance badge.',
                    },
                    {
                      screen: '4. Center Chat Stream & Brand-New Chat Empty State',
                      spec: 'Empty State: Centered welcome card showing active local model and a 2×2 GridPane of actionable starter cards (Analyze Image, Generate Image /image, Write Code, Multi-Script Test). Active Chat: User messages sit right-aligned in #2A2926 cards (max-width 580px) with vision thumbnails above text. Assistant replies sit left-aligned in an open editorial layout (max-width 720px) with model/speed metadata, markdown headers/lists, copyable code cards (#181816), and generated 1024×1024 image cards with Save Image & Copy Prompt buttons.',
                    },
                    {
                      screen: '5. Multi-Modal Message Composer (VBox.composer-box)',
                      spec: 'Top Staging Strip (conditional): Shows 56×56px attached image preview with dimensions and × remove button, or an amber "/image Local Image Generation Mode" banner. Middle: Auto-wrapping TextArea (2 to 6 rows) with automatic RTL detection. Bottom Toolbar: Attach Image button, Generate Image toggle button, quick script pills, keyboard hint, and primary Send button (which transforms into a red-bordered Stop button during streaming).',
                    },
                    {
                      screen: '6. Model Manager & Downloads Modal (680px × 560px Overlay)',
                      spec: 'Header with local storage path (~/Sulvana/models/) and free NVMe space readout. Filter tabs (All, Active Queue, Installed). Each model row displays Name, Quantization, Format (GGUF/Safetensors), Recommended VRAM, Total Size, Downloaded GB, Percent, live MB/s speed, ETA, and Pause/Resume/Cancel or Download/Installed controls.',
                    },
                    {
                      screen: '7. Settings Modal (520px × 520px Overlay)',
                      spec: 'Clean single-column preferences dialog with 4 core controls: Theme (Dark Warm Obsidian vs. Light Warm Paper), Default Reply Language (Auto-detect, English, Khmer, Arabic, Chinese, Japanese), Temperature Slider (0.0 to 1.5 with Plain-English presets: 0.2 Precise, 0.7 Balanced, 1.2 Creative), and Maximum Response Length (512 to 8192 tokens).',
                    },
                  ].map((item) => (
                    <div
                      key={item.screen}
                      className="p-4 rounded-xl border"
                      style={{
                        backgroundColor: 'var(--bg-elevated)',
                        borderColor: 'var(--border-subtle)',
                      }}
                    >
                      <div
                        className="font-semibold text-[14px]"
                        style={{ color: 'var(--accent-primary)' }}
                      >
                        {item.screen}
                      </div>
                      <p
                        className="mt-1 leading-relaxed text-[12.5px]"
                        style={{ color: 'var(--text-secondary)' }}
                      >
                        {item.spec}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* DELIVERABLE 3: EXACT COMPONENT BEHAVIOR MATRIX */}
            {activeSection === 'behavior-matrix' && (
              <div className="space-y-5">
                <div>
                  <span
                    className="text-[11px] font-mono-tabular uppercase tracking-wider px-2 py-0.5 rounded"
                    style={{
                      backgroundColor: 'var(--accent-subtle)',
                      color: 'var(--accent-primary)',
                    }}
                  >
                    Deliverable 03
                  </span>
                  <h3 className="text-[19px] font-semibold mt-1.5">
                    Exact Component Behavior Specification
                  </h3>
                </div>

                <div className="grid grid-cols-1 gap-3 text-[12.5px]">
                  {[
                    {
                      state: 'Model Loading & Swapping',
                      trigger: 'User selects a new model from ComboBox.model-selector-pill',
                      visual:
                        'Top status dot turns pulsing Warm Amber (#E5A93C); label reads "Loading [Model] into GPU memory…". Composer Send button disables temporarily.',
                      completion:
                        'Once Python backend confirms weights are in VRAM, dot turns Sage Green (#4E9F6E), VRAM bar updates to new GB footprint, and composer re-enables.',
                    },
                    {
                      state: 'Token Streaming & Stop Generation',
                      trigger: 'User clicks Send or presses Enter',
                      visual:
                        'User message appends immediately; Assistant block mounts with a pulsing amber block cursor. Send button morphs into a red-bordered "Stop" button. Live tok/s updates in header.',
                      completion:
                        'Clicking Stop aborts the HTTP SSE stream, preserves all tokens generated so far, appends "[Stopped by user]", and restores the Send button.',
                    },
                    {
                      state: 'Vision Image Attachment',
                      trigger: 'User clicks "Attach Image" and picks a PNG/JPG/WEBP',
                      visual:
                        'Composer staging strip reveals a 56×56px thumbnail, filename, dimensions, and × remove button. If a non-vision model is active, Sulvana notes automatic local vision routing.',
                      completion:
                        'On Send, thumbnail embeds inside the User Message card and the vision model analyzes the image locally.',
                    },
                    {
                      state: 'Local Image Generation (/image)',
                      trigger: 'User clicks "Generate Image" pill or types "/image [prompt]"',
                      visual:
                        'Composer border highlights in Warm Amber and shows "Local Image Generation Mode (/image)". On Send, Assistant mounts a 440px progress card showing "Generating image locally — Step X / 4" with a smooth ProgressBar.',
                      completion:
                        'Rendered image replaces the progress placeholder with resolution/seed badge and primary "Save Image" (FileChooser) + "Copy Prompt" buttons.',
                    },
                    {
                      state: 'Model Downloads & Pause/Resume',
                      trigger: 'User opens Models & Downloads modal and starts/pauses a download',
                      visual:
                        'Row displays live percentage, downloaded/total GB, MB/s speed, and ETA. Top header "Models" button also shows a compact percentage badge when modal is closed.',
                      completion:
                        'Clicking Pause halts the stream and preserves the .part file; Resume continues from the exact byte offset via HTTP Range header. At 100%, SHA256 is verified and badge turns green "Installed ✓".',
                    },
                    {
                      state: 'Human-Friendly Failure & High VRAM States',
                      trigger: 'VRAM exceeds 92%, model file is missing, or Python engine disconnects',
                      visual:
                        'Never shows raw Python tracebacks. High VRAM shows an Ochre (#D9822B) banner explaining automatic CPU+GPU RAM sharing. Offline engine or missing model shows a calm Terracotta (#D9534F) banner.',
                      completion:
                        'One-click recovery button ("Optimize Memory", "Open Downloads", or "Restart Local Engine") resolves the state directly.',
                    },
                  ].map((row) => (
                    <div
                      key={row.state}
                      className="p-4 rounded-xl border space-y-2"
                      style={{
                        backgroundColor: 'var(--bg-elevated)',
                        borderColor: 'var(--border-subtle)',
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <span
                          className="font-semibold text-[14px]"
                          style={{ color: 'var(--accent-primary)' }}
                        >
                          {row.state}
                        </span>
                        <span
                          className="text-[11px] font-mono-tabular px-2 py-0.5 rounded"
                          style={{
                            backgroundColor: 'var(--bg-sidebar)',
                            color: 'var(--text-secondary)',
                          }}
                        >
                          {row.trigger}
                        </span>
                      </div>
                      <p style={{ color: 'var(--text-primary)' }}>
                        <strong>UI Feedback:</strong> {row.visual}
                      </p>
                      <p style={{ color: 'var(--text-secondary)' }}>
                        <strong>Completion / Recovery:</strong> {row.completion}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* DELIVERABLE 4: PRACTICAL JAVAFX COMPONENT TREE & CSS MAPPING */}
            {activeSection === 'javafx-tree' && (
              <div className="space-y-5">
                <div>
                  <span
                    className="text-[11px] font-mono-tabular uppercase tracking-wider px-2 py-0.5 rounded"
                    style={{
                      backgroundColor: 'var(--accent-subtle)',
                      color: 'var(--accent-primary)',
                    }}
                  >
                    Deliverable 04
                  </span>
                  <h3 className="text-[19px] font-semibold mt-1.5">
                    Practical JavaFX Component Tree & CSS Class Mapping
                  </h3>
                  <p
                    className="text-[13px] mt-1"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Every panel in Sulvana maps 1-to-1 to standard JavaFX containers (<code>BorderPane</code>, <code>VBox</code>, <code>HBox</code>, <code>ScrollPane</code>, <code>StackPane</code>, <code>ListView</code>, <code>ProgressBar</code>) styled with flat vector CSS.
                  </p>
                </div>

                {/* Scene Graph Tree */}
                <div
                  className="rounded-xl border overflow-hidden"
                  style={{
                    backgroundColor: 'var(--bg-code-block)',
                    borderColor: 'var(--border-subtle)',
                  }}
                >
                  <div
                    className="px-4 py-2.5 border-b flex items-center justify-between"
                    style={{
                      backgroundColor: 'var(--bg-code-header)',
                      borderColor: 'var(--border-subtle)',
                    }}
                  >
                    <span className="text-[12px] font-mono-tabular font-semibold">
                      SulvanaRootView.fxml / Scene Graph Hierarchy
                    </span>
                    <button
                      type="button"
                      onClick={() => copyText('tree', JAVAFX_SCENE_TREE_CODE)}
                      className="h-[26px] px-2.5 rounded border text-[11px] font-medium flex items-center gap-1.5 cursor-pointer"
                      style={{
                        backgroundColor: 'var(--bg-elevated)',
                        borderColor: 'var(--border-subtle)',
                      }}
                    >
                      {copiedBlock === 'tree' ? (
                        <>
                          <Check className="w-3 h-3" style={{ color: 'var(--accent-primary)' }} />
                          <span>Copied ✓</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span>Copy Tree</span>
                        </>
                      )}
                    </button>
                  </div>
                  <pre className="p-4 text-[12px] font-mono-tabular overflow-x-auto leading-[1.55] m-0">
                    <code>{JAVAFX_SCENE_TREE_CODE}</code>
                  </pre>
                </div>

                {/* Ready-to-use JavaFX CSS Stylesheet */}
                <div
                  className="rounded-xl border overflow-hidden"
                  style={{
                    backgroundColor: 'var(--bg-code-block)',
                    borderColor: 'var(--border-subtle)',
                  }}
                >
                  <div
                    className="px-4 py-2.5 border-b flex items-center justify-between"
                    style={{
                      backgroundColor: 'var(--bg-code-header)',
                      borderColor: 'var(--border-subtle)',
                    }}
                  >
                    <span className="text-[12px] font-mono-tabular font-semibold">
                      sulvana-theme.css (JavaFX 21+ Stylesheet)
                    </span>
                    <button
                      type="button"
                      onClick={() => copyText('css', JAVAFX_CSS_STYLESHEET)}
                      className="h-[26px] px-2.5 rounded border text-[11px] font-medium flex items-center gap-1.5 cursor-pointer"
                      style={{
                        backgroundColor: 'var(--bg-elevated)',
                        borderColor: 'var(--border-subtle)',
                      }}
                    >
                      {copiedBlock === 'css' ? (
                        <>
                          <Check className="w-3 h-3" style={{ color: 'var(--accent-primary)' }} />
                          <span>Copied ✓</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span>Copy JavaFX CSS</span>
                        </>
                      )}
                    </button>
                  </div>
                  <pre className="p-4 text-[12px] font-mono-tabular overflow-x-auto leading-[1.55] m-0">
                    <code>{JAVAFX_CSS_STYLESHEET}</code>
                  </pre>
                </div>
              </div>
            )}

            {/* DELIVERABLE 5: SOLO-DEVELOPER IMPLEMENTATION NOTES */}
            {activeSection === 'impl-notes' && (
              <div className="space-y-5">
                <div>
                  <span
                    className="text-[11px] font-mono-tabular uppercase tracking-wider px-2 py-0.5 rounded"
                    style={{
                      backgroundColor: 'var(--accent-subtle)',
                      color: 'var(--accent-primary)',
                    }}
                  >
                    Deliverable 05
                  </span>
                  <h3 className="text-[19px] font-semibold mt-1.5">
                    Practical JavaFX + Python Implementation Notes
                  </h3>
                  <p
                    className="text-[13px] mt-1"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    High-leverage architectural choices that save weeks of frontend engineering while keeping Sulvana fast and reliable.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 text-[12.5px]">
                  <div
                    className="p-4 rounded-xl border space-y-2"
                    style={{
                      backgroundColor: 'var(--bg-elevated)',
                      borderColor: 'var(--border-subtle)',
                    }}
                  >
                    <h4
                      className="font-semibold text-[14px]"
                      style={{ color: 'var(--accent-primary)' }}
                    >
                      1. Smooth 30ms Batched Token Streaming
                    </h4>
                    <p className="leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                       connect JavaFX’s <code>java.net.http.HttpClient</code> to a local Python FastAPI Server-Sent Events (SSE) endpoint (<code>http://127.0.0.1:8420/v1/chat/stream</code>). Buffer incoming tokens on a background thread and flush them to the UI via <code>Platform.runLater()</code> every <strong>30ms</strong>. This prevents JavaFX layout thrashing at 60+ tok/s.
                    </p>
                  </div>

                  <div
                    className="p-4 rounded-xl border space-y-2"
                    style={{
                      backgroundColor: 'var(--bg-elevated)',
                      borderColor: 'var(--border-subtle)',
                    }}
                  >
                    <h4
                      className="font-semibold text-[14px]"
                      style={{ color: 'var(--accent-primary)' }}
                    >
                      2. Smart ScrollPane Auto-Scroll Lock
                    </h4>
                    <p className="leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                      Bind <code>chatMessageList.heightProperty()</code> to set <code>scrollPane.setVvalue(1.0)</code> <em>only</em> when the user is already near the bottom (<code>vvalue &gt; 0.92</code>). If the user scrolls up to read earlier code while a reply streams, auto-scroll pauses automatically.
                    </p>
                  </div>

                  <div
                    className="p-4 rounded-xl border space-y-2"
                    style={{
                      backgroundColor: 'var(--bg-elevated)',
                      borderColor: 'var(--border-subtle)',
                    }}
                  >
                    <h4
                      className="font-semibold text-[14px]"
                      style={{ color: 'var(--accent-primary)' }}
                    >
                      3. Multi-Script & RTL Detection in 6 Lines
                    </h4>
                    <p className="leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                      Inspect the first 64 characters of each paragraph for Unicode Arabic ranges (<code>\u0600-\u06FF</code>). When matched, set <code>textFlow.setNodeOrientation(NodeOrientation.RIGHT_TO_LEFT)</code> while keeping <code>VBox.code-block-card</code> locked to <code>LEFT_TO_RIGHT</code>.
                    </p>
                  </div>

                  <div
                    className="p-4 rounded-xl border space-y-2"
                    style={{
                      backgroundColor: 'var(--bg-elevated)',
                      borderColor: 'var(--border-subtle)',
                    }}
                  >
                    <h4
                      className="font-semibold text-[14px]"
                      style={{ color: 'var(--accent-primary)' }}
                    >
                      4. Crisp Vector Icons via CSS -fx-shape
                    </h4>
                    <p className="leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                      Avoid bundling multi-resolution PNG icon assets. Use a standard JavaFX <code>Region</code> with <code>-fx-shape: "M..."</code> SVG path strings and <code>-fx-background-color: -text-secondary</code>. Icons scale cleanly on 100%–250% DPI displays and change color automatically on hover or theme switch.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
