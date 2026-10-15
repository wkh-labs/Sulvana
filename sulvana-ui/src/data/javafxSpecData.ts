export interface SpecSection {
  id: string;
  number: string;
  title: string;
  subtitle: string;
}

export const SPEC_SECTIONS: SpecSection[] = [
  {
    id: 'concept-tokens',
    number: '01',
    title: 'Design Concept & Color / Type System',
    subtitle: 'Warm Obsidian Studio palette, multi-script typography, and calm hardware telemetry.',
  },
  {
    id: 'screen-specs',
    number: '02',
    title: 'Screen-by-Screen UI Specification',
    subtitle: 'Exact spatial layout from 800×600 compact windows to 4K displays.',
  },
  {
    id: 'behavior-matrix',
    number: '03',
    title: 'Exact Component Behavior Matrix',
    subtitle: 'Loading, SSE streaming, /image diffusion, vision uploads, downloads, and human-friendly failures.',
  },
  {
    id: 'javafx-tree',
    number: '04',
    title: 'JavaFX Component Tree & CSS Mapping',
    subtitle: 'Direct Scene Graph hierarchy (BorderPane, VBox, HBox, ScrollPane) and -fx-* CSS rules.',
  },
  {
    id: 'impl-notes',
    number: '05',
    title: 'JavaFX + Python Implementation Notes',
    subtitle: 'Practical patterns for a solo developer: Platform.runLater batching, RTL/Khmer shaping, and SVGPath icons.',
  },
];

export const JAVAFX_SCENE_TREE_CODE = `BorderPane.root-pane (minWidth: 800, minHeight: 600, prefWidth: 1280, prefHeight: 820)
├── TOP: HBox.status-header-bar (prefHeight: 52px, alignment: CENTER_LEFT, spacing: 12px)
│   ├── HBox.brand-Identity-box
│   │   ├── StackPane.brand-badge (SVGPath.icon-sparkle)
│   │   └── Label.brand-title ("Sulvana")
│   ├── ComboBox<LocalModel>.model-selector-pill (prefHeight: 34px)
│   ├── HBox.hardware-telemetry-pill (spacing: 10px, alignment: CENTER_LEFT)
│   │   ├── Circle.status-dot (.status-ready | .status-busy | .status-warn | .status-error)
│   │   ├── Label.status-human-label ("Ready on GPU • 4.8 / 8.0 GB VRAM")
│   │   ├── ProgressBar.vram-mini-meter (prefWidth: 64px, prefHeight: 6px)
│   │   └── Label.speed-badge-mono ("46.4 tok/s")
│   ├── Region.header-spacer (HBox.setHgrow: ALWAYS)
│   └── HBox.header-utility-actions (spacing: 8px)
│       ├── Button.btn-secondary-pill ("Models & Downloads", badge: activeCount)
│       └── Button.btn-icon-ghost ("Settings", Tooltip: "Preferences (Ctrl+,)")
│
├── LEFT: VBox.sidebar-rail (prefWidth: 248px, minWidth: 200px, spacing: 8px)
│   ├── Button.btn-primary-amber.new-chat-btn ("+ New Chat", maxWidth: Infinity, prefHeight: 38px)
│   ├── TextField.sidebar-filter-input (promptText: "Filter conversations...")
│   ├── Label.sidebar-section-caption ("RECENT SESSIONS")
│   ├── ListView<Conversation>.conversation-list-view (VBox.setVgrow: ALWAYS)
│   │   └── ListCell.conversation-cell (HBox: VBox[Title + Meta], Label.script-tag)
│   └── VBox.sidebar-footer-panel (border-top: 1px #2E2D2A, padding: 12px)
│       ├── HBox.privacy-shield-row (SVGPath.icon-shield, Label: "100% Local • Offline Ready")
│       └── Button.btn-ghost-danger.clear-chat-btn ("Clear Current Chat")
│
└── CENTER: StackPane.workspace-stack
    ├── BorderPane.chat-main-container
    │   ├── TOP: HBox.error-banner-bar (managed & visible only on hardware/model warning)
    │   ├── CENTER: ScrollPane.chat-scroll-pane (fitToWidth: true, hbarPolicy: NEVER)
    │   │   └── StackPane.chat-scroll-Alignment-wrapper (alignment: TOP_CENTER)
    │   │       └── VBox.chat-message-list (maxWidth: 760px, spacing: 18px, padding: 24px)
    │   │           ├── [If Empty]: VBox.empty-state-card (Greeting + 2x2 GridPane Starter Cards)
    │   │           └── [For Each Message]: VBox.message-row-container
    │   │               ├── HBox.user-message-wrapper (alignment: CENTER_RIGHT)
    │   │               │   └── VBox.chat-bubble-user (maxWidth: 580px)
    │   │               │       ├── FlowPane.vision-attachment-row (ImageView thumbnails)
    │   │               │       └── TextFlow.message-body-text (lineSpacing: 6px)
    │   │               └── VBox.assistant-message-block (maxWidth: 720px, spacing: 10px)
    │   │                   ├── HBox.assistant-meta-header (Label.model-name, Label.tok-speed)
    │   │                   ├── TextFlow.message-body-text (NodeOrientation: LTR or RTL)
    │   │                   ├── VBox.code-block-card (HBox.code-header + TextArea.code-content)
    │   │                   └── VBox.generated-image-card (StackPane[ImageView] + HBox.image-actions)
    │   │
    │   └── BOTTOM: StackPane.composer-outer-wrapper (alignment: CENTER, padding: 12px 24px 18px)
    │       └── VBox.composer-box (maxWidth: 760px, background: #1E1E1C, radius: 12px)
    │           ├── HBox.attachment-staging-strip (visible when image attached or /image active)
    │           ├── TextArea.composer-textarea (wrapText: true, prefRowCount: 2..6)
    │           └── HBox.composer-action-bar (alignment: CENTER_LEFT, spacing: 8px)
    │               ├── Button.btn-tool-icon ("Attach Image", Tooltip: "Analyze photo locally")
    │               ├── ToggleButton.btn-mode-pill ("Generate Image", inserts "/image ")
    │               ├── Region.composer-spacer (HBox.setHgrow: ALWAYS)
    │               ├── Label.composer-hint-label ("Enter to send • Shift+Enter newline")
    │               └── StackPane.send-stop-action-slot
    │                   ├── Button.btn-primary-amber.send-btn ("Send")
    │                   └── Button.btn-danger-stop.stop-btn ("Stop")
    │
    └── [OVERLAYS]: StackPane.modal-backdrop (visible when Modal open)
        ├── VBox.modal-dialog-card.downloads-modal (prefWidth: 680px, maxHeight: 560px)
        └── VBox.modal-dialog-card.settings-modal (prefWidth: 520px, maxHeight: 520px)`;

export const JAVAFX_CSS_STYLESHEET = `/* ============================================================================
   SULVANA — JavaFX 21+ Stylesheet (sulvana-theme.css)
   Realistic flat vector styling • Zero expensive GaussianBlur passes
   ============================================================================ */

.root-pane {
    -fx-background-color: #141413;
    -fx-font-family: "Inter", "Segoe UI", "Noto Sans", "Noto Sans Khmer", "Noto Sans Arabic", "Noto Sans CJK JP", sans-serif;
    -fx-font-size: 14px;
}

/* Top Status & Hardware Header */
.status-header-bar {
    -fx-background-color: #1C1C1A;
    -fx-border-color: transparent transparent #2E2D2A transparent;
    -fx-border-width: 0 0 1px 0;
    -fx-padding: 0 16px;
}

.model-selector-pill {
    -fx-background-color: #242422;
    -fx-background-radius: 8px;
    -fx-border-color: #2E2D2A;
    -fx-border-radius: 8px;
    -fx-text-fill: #F2F0EC;
    -fx-padding: 4px 10px;
}
.model-selector-pill:hover {
    -fx-border-color: #E5A93C;
}

/* Left Sidebar Rail */
.sidebar-rail {
    -fx-background-color: #1C1C1A;
    -fx-border-color: transparent #2E2D2A transparent transparent;
    -fx-border-width: 0 1px 0 0;
    -fx-padding: 12px;
}

.conversation-cell {
    -fx-background-color: transparent;
    -fx-background-radius: 8px;
    -fx-padding: 8px 10px;
    -fx-text-fill: #A6A39B;
}
.conversation-cell:hover {
    -fx-background-color: #242422;
    -fx-text-fill: #F2F0EC;
}
.conversation-cell:selected {
    -fx-background-color: #242422;
    -fx-border-color: transparent transparent transparent #E5A93C;
    -fx-border-width: 0 0 0 3px;
    -fx-text-fill: #F2F0EC;
}

/* Chat Stream & Message Cards */
.chat-scroll-pane,
.chat-scroll-pane > .viewport {
    -fx-background-color: #141413;
}

.chat-bubble-user {
    -fx-background-color: #2A2926;
    -fx-background-radius: 12px;
    -fx-border-color: #2E2D2A;
    -fx-border-radius: 12px;
    -fx-padding: 12px 16px;
}

.code-block-card {
    -fx-background-color: #181816;
    -fx-background-radius: 8px;
    -fx-border-color: #2E2D2A;
    -fx-border-radius: 8px;
}

.code-header {
    -fx-background-color: #20201E;
    -fx-background-radius: 8px 8px 0 0;
    -fx-border-color: transparent transparent #2E2D2A transparent;
    -fx-padding: 6px 12px;
}

/* Multi-Modal Composer */
.composer-box {
    -fx-background-color: #1E1E1C;
    -fx-background-radius: 12px;
    -fx-border-color: #2E2D2A;
    -fx-border-radius: 12px;
    -fx-padding: 10px 12px;
}
.composer-box:focused-within {
    -fx-border-color: #E5A93C;
}

/* Primary Amber & Semantic Buttons */
.btn-primary-amber {
    -fx-background-color: #E5A93C;
    -fx-text-fill: #141413;
    -fx-font-weight: 600;
    -fx-background-radius: 8px;
    -fx-padding: 7px 14px;
    -fx-cursor: hand;
}
.btn-primary-amber:hover {
    -fx-background-color: #F0B84D;
}
.btn-primary-amber:disabled {
    -fx-opacity: 0.45;
}

.btn-danger-stop {
    -fx-background-color: rgba(217, 83, 79, 0.16);
    -fx-border-color: #D9534F;
    -fx-border-radius: 8px;
    -fx-background-radius: 8px;
    -fx-text-fill: #F2F0EC;
    -fx-font-weight: 600;
    -fx-padding: 7px 14px;
}

/* Progress Bars (VRAM & Model Downloads) */
.sulvana-progress-bar > .track {
    -fx-background-color: #181816;
    -fx-background-radius: 4px;
    -fx-border-color: #2E2D2A;
    -fx-border-radius: 4px;
}
.sulvana-progress-bar > .bar {
    -fx-background-color: #E5A93C;
    -fx-background-radius: 4px;
    -fx-background-insets: 0;
}`;
