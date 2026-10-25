import { useEffect, useId, useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import { ArrowDown, ArrowUp, Menu, Volume2, LoaderCircle, Brain, FileDown, RefreshCw, Check, ChevronRight, ChevronsDown, Code, Copy, Download, FilePen, FilePlus, FileText, FolderCode, FolderOpen, Globe, Image as ImageIcon, Info, Keyboard, UserRound, ImagePlus, Lightbulb, Palette, PencilLine, ThumbsUp, MessageCircle, Paperclip, RotateCcw, Search, Settings, ShieldCheck, Sparkles, Square, SquarePen, SquareTerminal, Trash2, TriangleAlert, Undo2, Wrench, X, type LucideIcon } from 'lucide-react';
import { Markdown } from './markdown';
import { WKH_MARK_DARK, WKH_MARK_LIGHT } from './wkhLogo';
import './desktop.css';

// The JavaFX fallback window cannot blur what is behind an element, so it gets solid surfaces.
document.documentElement.dataset.shell = /JavaFX/.test(navigator.userAgent) ? 'javafx' : 'chromium';

declare global {
  interface Window {
    sulvanaHost?: {
      selectImage: () => string;
      saveImage: (filename: string) => string | boolean;
    };
    /** The Electron window's bridge (see electron-ui/preload.js). */
    sulvanaElectron?: { chooseFolder: () => Promise<string | null> };
  }
}

// A note marks an assistant message that is not a normal, complete answer.
type Note = 'error' | 'stopped' | 'empty' | 'interrupted';
type Message = {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  image?: string;
  attachment?: string;
  pending?: boolean;
  activity?: string;
  note?: Note;
  /** Raw output of a /terminal, /docs or /search command: shown exactly as returned. */
  plain?: boolean;
  /** The model's step-by-step thinking, shown separately and never sent back as history. */
  reasoning?: string;
  /** Web results and local notes the answer was based on. */
  sources?: Source[];
  /** The reply stopped because it reached the length limit. */
  cut?: boolean;
  /** Coding mode: the reply as it happened, prose and tool steps in order. */
  parts?: Part[];
  /** Coding mode: the task's id (for Undo) and the files it changed. */
  code?: CodeTask;
  /** The user rated or corrected this reply; it was saved as a training example. */
  feedback?: 'good' | 'corrected';
  /** The Khmer was written by the online translator from Sulvana's English answer. */
  translated?: 'google' | 'local';
};
type ModelChoice = { id: string; label: string; detail: string; available: boolean };
type CodeStep = { id: string; tool: string; title: string; status: 'running' | 'done' | 'error' | 'denied'; detail?: string };
type Part = { kind: 'text'; text: string } | { kind: 'step'; step: CodeStep };
type CodeTask = { task: string; root: string; changed: string[]; undone?: boolean };
/** A web result (url) or a section of a local Markdown note (file). */
type Source = { title: string; url?: string; file?: string };
type Conversation = { id: string; title: string; messages: Message[]; updatedAt?: number };

export type Theme = 'dark' | 'light' | 'oled' | 'sepia' | 'forest' | 'nord';
export type AccentColor = 'lilac' | 'sky' | 'mint' | 'peach' | 'pink' | 'butter' | 'coral' | 'teal' | 'custom';
export type BubbleStyle = 'accent' | 'neutral';

type Preferences = {
  temperature: number;
  maxTokens: number;
  language: string;
  theme: Theme;
  accent: AccentColor;
  customAccent: string;
  bubbleStyle: BubbleStyle;
  reasoning: boolean;
  code: boolean;
  codeRoot: string;
  textSize: TextSize;
  /** Interface size in percent, like a game's GUI scale: everything (text, buttons, sidebar) grows or shrinks. */
  uiScale: number;
  translate: Translator;
  translateAsked: boolean;
  uiLanguage: 'km' | 'en';
  autoSearch: boolean;
  /** Personalisation, like Claude's and ChatGPT's: how to address the user, about them, answer style, memories. */
  userName: string;
  aboutUser: string;
  instructions: string;
  responseStyle: ResponseStyle;
  memories: string[];
};

const THEMES: { id: Theme; nameEn: string; nameKm: string; color: string; border: string }[] = [
  { id: 'dark', nameEn: 'Dark', nameKm: 'ងងឹត', color: '#121015', border: '#2E2838' },
  { id: 'light', nameEn: 'Light', nameKm: 'ភ្លឺ', color: '#FFFAF3', border: '#EAE3F3' },
  { id: 'oled', nameEn: 'OLED', nameKm: 'ខ្មៅសុទ្ធ', color: '#000000', border: '#201C2B' },
  { id: 'sepia', nameEn: 'Sepia', nameKm: 'ក្រដាសចាស់', color: '#F4EBD9', border: '#E4D7C2' },
  { id: 'forest', nameEn: 'Forest', nameKm: 'ព្រៃបៃតង', color: '#0C1512', border: '#1F3A31' },
  { id: 'nord', nameEn: 'Nord', nameKm: 'រងាត្រជាក់', color: '#13171F', border: '#293649' },
];

const ACCENT_PRESETS: { id: AccentColor; nameEn: string; nameKm: string; color: string }[] = [
  { id: 'lilac', nameEn: 'Lilac', nameKm: 'ផ្កាត្របែកព្រៃ', color: '#8B6CF6' },
  { id: 'sky', nameEn: 'Sky', nameKm: 'ផ្ទៃមេឃ', color: '#3B82F6' },
  { id: 'mint', nameEn: 'Mint', nameKm: 'ជីអង្កាម', color: '#10B981' },
  { id: 'peach', nameEn: 'Peach', nameKm: 'ផ្លែប៉េស', color: '#F97316' },
  { id: 'pink', nameEn: 'Pink', nameKm: 'ផ្កាឈូក', color: '#EC4899' },
  { id: 'butter', nameEn: 'Butter', nameKm: 'លឿងទន់', color: '#F59E0B' },
  { id: 'coral', nameEn: 'Coral', nameKm: 'ផ្កាថ្ម', color: '#F43F5E' },
  { id: 'teal', nameEn: 'Teal', nameKm: 'បៃតងទឹកសមុទ្រ', color: '#14B8A6' },
];

function isLightTheme(theme: Theme): boolean {
  return theme === 'light' || theme === 'sepia';
}

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const clean = hex.replace('#', '').trim();
  if (clean.length === 3) {
    const r = parseInt(clean[0] + clean[0], 16);
    const g = parseInt(clean[1] + clean[1], 16);
    const b = parseInt(clean[2] + clean[2], 16);
    return isNaN(r) || isNaN(g) || isNaN(b) ? null : { r, g, b };
  }
  if (clean.length === 6) {
    const r = parseInt(clean.slice(0, 2), 16);
    const g = parseInt(clean.slice(2, 4), 16);
    const b = parseInt(clean.slice(4, 6), 16);
    return isNaN(r) || isNaN(g) || isNaN(b) ? null : { r, g, b };
  }
  return null;
}

function darkenRgb({ r, g, b }: { r: number; g: number; b: number }, factor = 0.35): string {
  return `rgb(${Math.max(0, Math.round(r * (1 - factor)))}, ${Math.max(0, Math.round(g * (1 - factor)))}, ${Math.max(0, Math.round(b * (1 - factor)))})`;
}

function lightenRgb({ r, g, b }: { r: number; g: number; b: number }, factor = 0.2): string {
  return `rgb(${Math.min(255, Math.round(r + (255 - r) * factor))}, ${Math.min(255, Math.round(g + (255 - g) * factor))}, ${Math.min(255, Math.round(b + (255 - b) * factor))})`;
}

type ResponseStyle = 'normal' | 'concise' | 'detailed' | 'formal' | 'friendly';
const RESPONSE_STYLES: ResponseStyle[] = ['normal', 'concise', 'detailed', 'formal', 'friendly'];
/** Better Khmer: who writes the Khmer. 'local' = NLLB on this computer, 'google' = Google Translate (online). */
type Translator = 'off' | 'local' | 'google';
type EngineStatus = { state: string; detail: string; approval?: ApprovalRequest | null };
type Dialog = 'settings' | 'tools' | 'delete' | 'improve' | null;
type StreamPayload = { prompt: string; image?: string; history: { role: string; content: string }[]; maxTokens: number; temperature: number; language: string; search?: boolean; reasoning?: boolean; translate?: Translator; autoSearch?: boolean; profile?: { name: string; about: string; instructions: string; style: ResponseStyle; memories: string[] }; code?: { root: string } };
type ApprovalRequest = { id: string; command: string; reason: string; timeout_seconds: number; kind?: 'read' | 'edit' | 'write' | 'command'; title?: string; diff?: string; allow_all?: boolean };
type Attachment = { name: string; data: string };
type Notice = { kind: 'error' | 'info'; text: string };
type RequestKind = 'chat' | 'image' | 'vision';

const STORAGE = 'sulvana.desktop.v1';
const LANGUAGES = ['Auto', 'ខ្មែរ (Khmer)', 'English', '中文 (Chinese)', 'ไทย (Thai)', 'Tiếng Việt (Vietnamese)', 'Français', '日本語 (Japanese)', 'العربية (Arabic)'];
// Khmer needs roughly 1.7 tokens per character, so the limits are generous.
const TOKEN_LIMITS = [512, 1024, 2048, 4096, 8192];
const LENGTH_NAMES: Record<number, string> = { 512: 'Short', 1024: 'Medium', 2048: 'Long', 4096: 'Very long', 8192: 'Longest' };
const LENGTH_NAMES_KM: Record<number, string> = { 512: 'ខ្លី', 1024: 'មធ្យម', 2048: 'វែង', 4096: 'វែងណាស់', 8192: 'វែងបំផុត' };
type TextSize = 'small' | 'default' | 'large';
/** A greeting for the time of day, with the user's name when they gave one: "Good evening, Han" / "សាយណ្ហសួស្តី Han". */
function greeting(language: 'km' | 'en', name: string, hour = new Date().getHours()): string {
  const [en, km] = hour < 5 ? ['Still up', 'យប់ជ្រៅហើយ'] : hour < 12 ? ['Good morning', 'អរុណសួស្តី']
    : hour < 17 ? ['Good afternoon', 'ទិវាសួស្តី'] : hour < 22 ? ['Good evening', 'សាយណ្ហសួស្តី'] : ['Still up', 'យប់ជ្រៅហើយ'];
  const who = name.trim();
  return language === 'km' ? `${km}${who ? ' ' + who : ''}!` : `${en}${who ? ', ' + who : ''}${en === 'Still up' ? '?' : ''}`;
}
type SettingsTab = 'you' | 'answers' | 'look' | 'share' | 'about';
const SETTINGS_TABS: { id: SettingsTab; icon: LucideIcon; tint: string; en: string; km: string; aboutEn: string; aboutKm: string }[] = [
  { id: 'you', icon: UserRound, tint: 'pink', en: 'You', km: 'អ្នក', aboutEn: 'Your name, how Sulvana answers you, and what it remembers.', aboutKm: 'ឈ្មោះរបស់អ្នក របៀបដែល Sulvana ឆ្លើយ និងអ្វីដែលវាចងចាំ។' },
  { id: 'answers', icon: Sparkles, tint: 'lilac', en: 'Answers', km: 'ចម្លើយ', aboutEn: 'Khmer tools, languages, search and the model.', aboutKm: 'ឧបករណ៍ខ្មែរ ភាសា ការស្វែងរក និងម៉ូដែល។' },
  { id: 'look', icon: Palette, tint: 'mint', en: 'Look', km: 'រូបរាង', aboutEn: 'Theme, colours and sizes. Changes show right away.', aboutKm: 'រូបរាង ពណ៌ និងទំហំ។ ការផ្លាស់ប្តូរបង្ហាញភ្លាមៗ។' },
  { id: 'share', icon: Globe, tint: 'sky', en: 'Sharing', km: 'ចែករំលែក', aboutEn: 'Let a friend use Sulvana through a private link.', aboutKm: 'អនុញ្ញាតឱ្យមិត្តប្រើ Sulvana តាមតំណឯកជន។' },
  { id: 'about', icon: Info, tint: 'butter', en: 'About', km: 'អំពី', aboutEn: 'Who made Sulvana, and handy shortcuts.', aboutKm: 'អ្នកបង្កើត Sulvana និងផ្លូវកាត់ដែលមានប្រយោជន៍។' },
];
// Interface size steps (percent), from compact to very large; Ctrl + / Ctrl − move one step, Ctrl 0 resets.
const UI_SCALES = [75, 90, 100, 110, 125, 150, 175, 200];
const DEFAULT_PREFERENCES: Preferences = {
  temperature: 0.4,
  maxTokens: 2048,
  language: 'Auto',
  theme: 'dark',
  accent: 'lilac',
  customAccent: '#8B6CF6',
  bubbleStyle: 'accent',
  reasoning: false,
  code: false,
  codeRoot: '',
  textSize: 'default',
  uiScale: 100,
  translate: 'local',
  translateAsked: false,
  uiLanguage: 'km',
  autoSearch: true,
  userName: '',
  aboutUser: '',
  instructions: '',
  responseStyle: 'normal',
  memories: []
};
const KHMER = /[\u1780-\u17FF]/;
const NOTE_TEXT: Record<Note, string> = {
  error: 'Something went wrong.',
  stopped: 'Stopped.',
  empty: 'No response was returned.',
  interrupted: 'Interrupted when Sulvana closed.',
};
const createId = () => globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`;
const newConversation = (): Conversation => ({ id: createId(), title: 'New chat', messages: [], updatedAt: Date.now() });

/** Chats saved by earlier versions stored placeholders as ordinary reply text. */
function legacyNote(text: string): Note | undefined {
  if (text.startsWith('Error: ')) return 'error';
  if (text === 'Stopped.') return 'stopped';
  if (text === 'No response was returned.') return 'empty';
  if (text === 'Interrupted when Sulvana closed.') return 'interrupted';
  return undefined;
}

function cleanSources(raw: unknown[]): Source[] {
  const seen = new Set<string>();
  const cleaned: Source[] = [];
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue;
    const src = item as Source;
    if (typeof src.title !== 'string') continue;
    const isUrl = /^https?:\/\//.test(String(src.url));
    const isNote = /^knowledge\/[^\n]{1,200}\.md$/.test(String(src.file));
    if (!isUrl && !isNote) continue;
    const key = (src.url || src.file || '').trim();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    cleaned.push(src.url ? { title: src.title.slice(0, 200), url: src.url } : { title: src.title.slice(0, 200), file: src.file });
    if (cleaned.length >= 11) break;
  }
  return cleaned;
}

function hostOf(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return url; }
}

/** "knowledge/cambodia-facts.md" → "Cambodia facts" */
function noteName(file: string): string {
  const name = (file.split('/').pop() || file).replace(/\.md$/i, '').replace(/[-_]+/g, ' ').trim();
  return name.charAt(0).toUpperCase() + name.slice(1);
}

function cleanMessage(raw: unknown): Message | null {
  if (!raw || typeof raw !== 'object') return null;
  const item = raw as Partial<Message>;
  if ((item.role !== 'user' && item.role !== 'assistant') || typeof item.text !== 'string') return null;
  const message: Message = { id: typeof item.id === 'string' ? item.id : createId(), role: item.role, text: item.text };
  if (typeof item.image === 'string' && (item.image.startsWith('/api/image?') || item.image.includes('/api/image?'))) message.image = item.image;
  if (typeof item.attachment === 'string') message.attachment = item.attachment;
  if (item.plain === true) message.plain = true;
  if (typeof item.reasoning === 'string' && item.reasoning) message.reasoning = item.reasoning;
  if (item.cut === true) message.cut = true;
  if (item.translated === 'google' || item.translated === 'local') message.translated = item.translated;
  if (item.feedback === 'good' || item.feedback === 'corrected') message.feedback = item.feedback;
  if (Array.isArray(item.sources)) message.sources = cleanSources(item.sources);
  if (Array.isArray(item.parts)) {
    const parts = item.parts.filter((part): part is Part => !!part && ((part.kind === 'text' && typeof part.text === 'string')
      || (part.kind === 'step' && !!part.step && typeof part.step.id === 'string' && typeof part.step.title === 'string')));
    // A step still "running" when the app closed did not finish.
    if (parts.length) message.parts = parts.map(part => part.kind === 'step' && part.step.status === 'running' ? { ...part, step: { ...part.step, status: 'error' } } : part);
  }
  const code = item.code;
  if (code && typeof code.task === 'string' && typeof code.root === 'string' && Array.isArray(code.changed)) {
    message.code = { task: code.task, root: code.root, changed: code.changed.filter(name => typeof name === 'string'), undone: code.undone === true || undefined };
  }
  if (item.role === 'assistant') {
    if (item.pending) message.note = message.text ? 'stopped' : 'interrupted';
    else if (item.note && item.note in NOTE_TEXT) message.note = item.note;
    else message.note = legacyNote(message.text);
  }
  return message;
}

function cleanPreferences(raw: unknown): Preferences {
  const saved = (raw && typeof raw === 'object' ? raw : {}) as Partial<Preferences>;
  // 0.7 was the old default; lower creativity gives fewer invented details in Khmer answers.
  const temperature = Number(saved.temperature) === 0.7 ? DEFAULT_PREFERENCES.temperature : Number(saved.temperature);
  return {
    temperature: Number.isFinite(temperature) ? Math.min(1.5, Math.max(0.1, temperature)) : DEFAULT_PREFERENCES.temperature,
    maxTokens: TOKEN_LIMITS.includes(Number(saved.maxTokens)) ? Number(saved.maxTokens) : DEFAULT_PREFERENCES.maxTokens,
    language: typeof saved.language === 'string' && saved.language.trim() ? saved.language.slice(0, 80) : DEFAULT_PREFERENCES.language,
    theme: THEMES.some(t => t.id === saved.theme) ? (saved.theme as Theme) : 'dark',
    accent: (saved.accent === 'custom' || ACCENT_PRESETS.some(a => a.id === saved.accent)) ? (saved.accent as AccentColor) : 'lilac',
    customAccent: typeof saved.customAccent === 'string' && /^#[0-9a-fA-F]{3,8}$/.test(saved.customAccent) ? saved.customAccent : '#8B6CF6',
    bubbleStyle: saved.bubbleStyle === 'neutral' ? 'neutral' : 'accent',
    reasoning: saved.reasoning === true,
    code: saved.code === true,
    codeRoot: typeof saved.codeRoot === 'string' ? saved.codeRoot.slice(0, 1000) : '',
    textSize: saved.textSize === 'small' || saved.textSize === 'large' ? saved.textSize : 'default',
    uiScale: UI_SCALES.includes(Number(saved.uiScale)) ? Number(saved.uiScale) : 100,
    // Google only after the user said yes (it sends their text to Google); the local translator needs no consent.
    translate: saved.translate === 'off' || saved.translate === 'local' ? saved.translate
      : (saved.translate === 'google' || (saved.translate as unknown) === true) && saved.translateAsked === true ? 'google' : 'local',
    translateAsked: saved.translateAsked === true,
    uiLanguage: saved.uiLanguage === 'en' ? 'en' : 'km',
    autoSearch: saved.autoSearch !== false,
    userName: typeof saved.userName === 'string' ? saved.userName.slice(0, 60) : '',
    aboutUser: typeof saved.aboutUser === 'string' ? saved.aboutUser.slice(0, 600) : '',
    instructions: typeof saved.instructions === 'string' ? saved.instructions.slice(0, 1500) : '',
    responseStyle: RESPONSE_STYLES.includes(saved.responseStyle as ResponseStyle) ? saved.responseStyle as ResponseStyle : 'normal',
    memories: Array.isArray(saved.memories) ? saved.memories.filter((item): item is string => typeof item === 'string' && !!item.trim()).map(item => item.slice(0, 200)).slice(0, 30) : [],
  };
}

function restore(): { conversations: Conversation[]; activeId: string; preferences: Preferences } {
  const first = newConversation();
  const fallback = { conversations: [first], activeId: first.id, preferences: DEFAULT_PREFERENCES };
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE) || 'null');
    if (!saved || typeof saved !== 'object') return fallback;
    const preferences = cleanPreferences(saved.preferences);
    const conversations: Conversation[] = (Array.isArray(saved.conversations) ? saved.conversations : [])
      .filter((chat: Conversation) => chat && typeof chat.id === 'string' && Array.isArray(chat.messages))
      .map((chat: Conversation) => ({
        id: chat.id,
        title: typeof chat.title === 'string' && chat.title.trim() ? chat.title : 'New chat',
        messages: chat.messages.map(cleanMessage).filter((message): message is Message => message !== null),
        updatedAt: typeof chat.updatedAt === 'number' ? chat.updatedAt : undefined,
      }));
    if (!conversations.length) return { ...fallback, preferences };
    return {
      conversations,
      activeId: conversations.some(chat => chat.id === saved.activeId) ? saved.activeId : conversations[0].id,
      preferences,
    };
  } catch {
    return fallback;
  }
}

const STEP_RESULT: Record<CodeStep['status'], string> = { running: 'interrupted', done: 'done', error: 'failed', denied: 'declined by the user' };

/** What the model is told about an earlier reply: in coding mode, its words plus the steps it took. */
function historyText(message: Message): string {
  const steps = (message.parts || []).flatMap(part => part.kind === 'step' ? [`- ${part.step.title} (${STEP_RESULT[part.step.status]})`] : []);
  if (!steps.length) return message.text;
  return `${message.text}\n\n[Steps taken]\n${steps.join('\n')}` + (message.code?.undone ? '\n[The user then undid these file changes.]' : '');
}

/** Only real exchanges go back to the model: no error text, placeholders or image-generation requests. */
function historyFor(messages: Message[]): { role: string; content: string }[] {
  const usable = (message: Message) => !message.pending && !!(message.text || message.parts?.length) && !message.image
    && (message.note === undefined || (message.note === 'stopped' && message.text !== NOTE_TEXT.stopped));
  const history: { role: string; content: string }[] = [];
  for (let index = 0; index < messages.length; index++) {
    const message = messages[index];
    if (message.role === 'user') {
      const reply = messages[index + 1];
      if (!reply || reply.role !== 'assistant' || !usable(reply)) continue;
      history.push({ role: 'user', content: message.text }, { role: 'assistant', content: historyText(reply) });
      index++;
    }
  }
  // The engine keeps as much of this as fits in its 64K-token memory.
  return history.slice(-400);
}

function decodeBase64(value: string): string {
  const bytes = Uint8Array.from(atob(value), char => char.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

class HttpError extends Error {
  status: number;
  constructor(status: number, message: string) { super(message); this.status = status; }
}

function eventParser(onEvent: (kind: string, data: string) => void) {
  let buffer = '';
  let complete = false;
  return {
    push(chunk: string, final = false) {
      buffer += chunk;
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      if (final && buffer) { lines.push(buffer); buffer = ''; }
      for (const line of lines) {
        const separator = line.indexOf('\t');
        if (separator < 0) continue;
        const kind = line.slice(0, separator);
        const data = decodeBase64(line.slice(separator + 1));
        onEvent(kind, data);
        if (kind === 'd' || ((kind === 'i' || kind === 'v') && JSON.parse(data).state === 'done')) complete = true;
      }
    },
    isComplete: () => complete,
  };
}

let memoryConfig: { tunnel: string; key: string } | null = null;

function getRemoteConfig(): { tunnel: string; key: string } {
  try {
    if (typeof window === 'undefined') return { tunnel: '', key: '' };
    const params = new URLSearchParams(window.location.search);
    const paramTunnel = params.get('tunnel');
    const paramKey = params.get('key');
    if (paramTunnel !== null || paramKey !== null) {
      const config = {
        tunnel: (paramTunnel ?? localStorage.getItem('sulvana.remote.tunnel') ?? '').trim(),
        key: (paramKey ?? localStorage.getItem('sulvana.remote.key') ?? '').trim(),
      };
      if (config.tunnel) {
        try { localStorage.setItem('sulvana.remote.tunnel', config.tunnel); } catch {}
        try { sessionStorage.setItem('sulvana.remote.tunnel', config.tunnel); } catch {}
      }
      if (config.key) {
        try { localStorage.setItem('sulvana.remote.key', config.key); } catch {}
        try { sessionStorage.setItem('sulvana.remote.key', config.key); } catch {}
      }
      memoryConfig = config;
      return config;
    }
    if (memoryConfig && memoryConfig.tunnel) return memoryConfig;
    const envTunnel = (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_URL ?? '';
    const envKey = (import.meta as unknown as { env?: Record<string, string> }).env?.VITE_API_KEY ?? '';
    let storedTunnel = '';
    let storedKey = '';
    try { storedTunnel = localStorage.getItem('sulvana.remote.tunnel') || ''; } catch {}
    if (!storedTunnel) { try { storedTunnel = sessionStorage.getItem('sulvana.remote.tunnel') || ''; } catch {} }
    try { storedKey = localStorage.getItem('sulvana.remote.key') || ''; } catch {}
    if (!storedKey) { try { storedKey = sessionStorage.getItem('sulvana.remote.key') || ''; } catch {} }
    const config = { tunnel: (storedTunnel || envTunnel).trim(), key: (storedKey || envKey).trim() };
    if (config.tunnel) memoryConfig = config;
    return config;
  } catch {
    return memoryConfig || { tunnel: '', key: '' };
  }
}

function api(path: string): string {
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  let { tunnel, key } = getRemoteConfig();
  if (!tunnel) return path;
  tunnel = tunnel.trim().replace(/\/+$/, '');
  if (!/^https?:\/\//i.test(tunnel)) tunnel = `https://${tunnel}`;
  const url = `${tunnel}${path}`;
  if (key) {
    const sep = url.includes('?') ? '&' : '?';
    return `${url}${sep}key=${encodeURIComponent(key)}`;
  }
  return url;
}

function apiHeaders(headers: Record<string, string> = {}): Record<string, string> {
  const { key } = getRemoteConfig();
  return key ? { ...headers, 'X-Sulvana-Key': key } : headers;
}

async function requestFetchStream(payload: StreamPayload, signal: AbortSignal, onEvent: (kind: string, data: string) => void): Promise<void> {
  const response = await fetch(api('/api/chat'), {
    method: 'POST', signal, headers: apiHeaders({ 'Content-Type': 'application/json' }), body: JSON.stringify(payload),
  });
  if (!response.ok) throw new HttpError(response.status, (await response.text()).trim() || 'Could not contact the local model.');
  const reader = response.body?.getReader();
  if (!reader) throw new Error('This WebView could not read the live model response.');
  const parser = eventParser(onEvent);
  const utf8 = new TextDecoder();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    parser.push(utf8.decode(value, { stream: true }));
  }
  parser.push(utf8.decode(), true);
  if (!parser.isComplete()) throw new Error('The local engine ended its reply early.');
}

function requestXhrStream(payload: StreamPayload, signal: AbortSignal, onEvent: (kind: string, data: string) => void): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    let read = 0;
    let settled = false;
    const parser = eventParser(onEvent);
    const finish = (error?: Error) => {
      if (settled) return;
      settled = true;
      signal.removeEventListener('abort', abortRequest);
      if (error) reject(error); else resolve();
    };
    const abortRequest = () => xhr.abort();
    const process = (final = false) => {
      const chunk = xhr.responseText.slice(read);
      read = xhr.responseText.length;
      parser.push(chunk, final);
    };
    xhr.open('POST', api('/api/chat'), true);
    const headers = apiHeaders({ 'Content-Type': 'application/json' });
    for (const [k, v] of Object.entries(headers)) xhr.setRequestHeader(k, v);
    xhr.onprogress = () => {
      try { if (xhr.status === 200) process(); }
      catch (error) { finish(error as Error); xhr.abort(); }
    };
    xhr.onload = () => {
      if (xhr.status !== 200) { finish(new HttpError(xhr.status, xhr.responseText.trim() || 'Could not contact the local model.')); return; }
      try { process(true); finish(parser.isComplete() ? undefined : new Error('The local engine ended its reply early.')); }
      catch (error) { finish(error as Error); }
    };
    xhr.onerror = () => finish(new Error('Connection to the local engine was lost.'));
    xhr.onabort = () => finish(new Error('Stopped.'));
    signal.addEventListener('abort', abortRequest, { once: true });
    try { xhr.send(JSON.stringify(payload)); }
    catch (error) { finish(error as Error); }
  });
}

function requestStream(payload: StreamPayload, signal: AbortSignal, onEvent: (kind: string, data: string) => void): Promise<void> {
  try {
    if (typeof ReadableStream === 'function' && typeof new Response('').body?.getReader === 'function') {
      return requestFetchStream(payload, signal, onEvent);
    }
  } catch { /* Older WebKit: use XHR. */ }
  return requestXhrStream(payload, signal, onEvent);
}

async function copyText(text: string): Promise<void> {
  try { await navigator.clipboard.writeText(text); return; }
  catch { /* JavaFX WebView can omit the Clipboard API. */ }
  const previous = document.activeElement as HTMLElement | null;
  const field = document.createElement('textarea');
  field.value = text;
  field.setAttribute('aria-hidden', 'true');
  field.style.position = 'fixed';
  field.style.opacity = '0';
  document.body.appendChild(field);
  field.select();
  const copied = document.execCommand('copy');
  field.remove();
  previous?.focus?.();
  if (!copied) throw new Error('Could not copy to the clipboard.');
}

// The Sulvana mark: a five-petal lotus (the towers of Angkor, seen as lotus buds) on a flat violet
// "cookie", the scalloped shape used across the WKH Labs website.
const LOTUS: [number, number, number, number][] = [[-64, 150, 40, 0.55], [64, 150, 40, 0.55], [-33, 205, 46, 0.78], [33, 205, 46, 0.78], [0, 262, 54, 1]];
const petal = (h: number, w: number) => `M0 ${-h}C${w * 0.9} ${-h * 0.62} ${w} ${-h * 0.3} ${w * 0.55} ${-h * 0.06}C${w * 0.3} ${h * 0.02} ${-w * 0.3} ${h * 0.02} ${-w * 0.55} ${-h * 0.06}C${-w} ${-h * 0.3} ${-w * 0.9} ${-h * 0.62} 0 ${-h}Z`;
const COOKIE = Array.from({ length: 180 }, (_, i) => {
  const t = i / 180 * Math.PI * 2, r = 238 * (1 + 0.05 * Math.cos(12 * t)) / 1.05;
  return (i ? 'L' : 'M') + (256 + r * Math.sin(t)).toFixed(1) + ' ' + (256 - r * Math.cos(t)).toFixed(1);
}).join('') + 'Z';

function Logo({ size }: { size: number }) {
  return <svg className="logo" width={size} height={size} viewBox="0 0 512 512" aria-hidden="true">
    <path d={COOKIE} fill="#8B6CF6" />
    <g transform="translate(256 386) scale(0.92)" fill="#fff">{LOTUS.map(([angle, height, width, opacity]) => <path key={angle} d={petal(height, width)} transform={`rotate(${angle})`} opacity={opacity} />)}</g>
  </svg>;
}

/** The model's thinking: open while it is being written, folded away once the answer starts. */
function Reasoning({ text, live }: { text: string; live: boolean }) {
  const [choice, setChoice] = useState<boolean | null>(null);
  const open = choice ?? live;
  return <div className={'reasoning' + (open ? ' open' : '') + (live ? ' live' : '')}>
    <button type="button" className="reasoning-toggle" aria-expanded={open} onClick={() => setChoice(!open)}><ChevronRight size={13} /><span>{live ? 'Reasoning…' : 'Reasoning'}</span></button>
    <div className="reasoning-body"><div><div className="message-body" dir="auto">{text}</div></div></div>
  </div>;
}

const STEP_ICONS: Record<string, LucideIcon> = {
  list_files: FolderOpen, read_file: FileText, search_files: Search, edit_file: FilePen, write_file: FilePlus, run_command: SquareTerminal,
};
const STEP_LABEL: Record<CodeStep['status'], string> = { running: 'Working…', done: '', error: 'Failed', denied: 'Declined' };

/** A unified diff with added and removed lines coloured. */
function DiffView({ text }: { text: string }) {
  return <pre className="diff-view" tabIndex={0}>{text.split('\n').map((line, index) => {
    const kind = line.startsWith('+++') || line.startsWith('---') ? 'file' : line.startsWith('@@') ? 'hunk' : line.startsWith('+') ? 'add' : line.startsWith('-') ? 'del' : '';
    return <span key={index} className={kind}>{line + '\n'}</span>;
  })}</pre>;
}

/** One tool step in coding mode, like a line in a terminal transcript. Edits and commands show their diff or output. */
function StepCard({ step }: { step: CodeStep }) {
  const [open, setOpen] = useState(() => ['edit_file', 'write_file', 'run_command'].includes(step.tool));
  const Icon = STEP_ICONS[step.tool] || Wrench;
  const diff = (step.tool === 'edit_file' || step.tool === 'write_file') && /^(---|\+\+\+|@@)/m.test(step.detail || '');
  return <div className={'code-step ' + step.status}>
    <button type="button" className="code-step-head" aria-expanded={step.detail ? open : undefined} onClick={() => setOpen(!open)} disabled={!step.detail}>
      <Icon size={14} aria-hidden="true" />
      <span className="code-step-title">{step.title}</span>
      {STEP_LABEL[step.status] && <span className="code-step-status">{STEP_LABEL[step.status]}</span>}
      {step.detail && <ChevronRight size={13} className="code-step-chevron" aria-hidden="true" />}
    </button>
    {open && step.detail && (diff ? <DiffView text={step.detail} /> : <pre className="code-step-output" tabIndex={0}>{step.detail}</pre>)}
  </div>;
}

/** Sidebar groups by last activity, like most chat apps. */
function dateGroup(time?: number): string {
  if (!time) return 'Earlier';
  const day = 86_400_000, start = new Date(); start.setHours(0, 0, 0, 0);
  if (time >= start.getTime()) return 'Today';
  if (time >= start.getTime() - day) return 'Yesterday';
  if (time >= start.getTime() - 7 * day) return 'Previous 7 days';
  return 'Earlier';
}
const GROUP_ORDER = ['Today', 'Yesterday', 'Previous 7 days', 'Earlier'];
const GROUP_KM: Record<string, string> = { Today: 'ថ្ងៃនេះ', Yesterday: 'ម្សិលមិញ', 'Previous 7 days': '៧ ថ្ងៃមុន', Earlier: 'មុននេះ' };
/** Interface language for the app's own labels (Settings → Interface language). Set on every render. */
let uiLanguage: 'km' | 'en' = 'km';
const L = (en: string, km: string) => uiLanguage === 'km' ? km : en;

/** A conversation as a Markdown document (images and tool steps summarised). */
function conversationMarkdown(chat: Conversation): string {
  const lines = [`# ${chat.title}`, '', `_Exported from Sulvana (WKH Labs) on ${new Date().toLocaleString()}_`, ''];
  for (const message of chat.messages) {
    if (message.pending) continue;
    lines.push(`## ${message.role === 'user' ? 'You' : 'Sulvana'}`, '');
    if (message.attachment) lines.push(`_Attached image: ${message.attachment}_`, '');
    if (message.parts) for (const part of message.parts) lines.push(part.kind === 'text' ? part.text.trim() : `- ${part.step.title} (${part.step.status})`);
    else lines.push(message.text || NOTE_TEXT[message.note || 'empty']);
    if (message.sources?.length) lines.push('', 'Sources: ' + message.sources.map(source => source.url || source.file).join(', '));
    lines.push('');
  }
  return lines.join('\n');
}

const FOCUSABLE = 'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Modal dialog with the keyboard behaviour people expect: focus moves in, Tab stays in, Escape closes, focus returns. */
function Modal({ title, onClose, children, className = '', dismissible = true, alert = false }: {
  title: string; onClose: () => void; children: ReactNode; className?: string; dismissible?: boolean; alert?: boolean;
}) {
  const panel = useRef<HTMLElement>(null);
  const close = useRef(onClose);
  close.current = onClose;
  const titleId = useId();
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const node = panel.current;
    const items = () => Array.from(node?.querySelectorAll<HTMLElement>(FOCUSABLE) || []);
    (node?.querySelector<HTMLElement>('[data-autofocus]') || items()[0] || node)?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close.current(); return; }
      if (event.key !== 'Tab') return;
      const list = items();
      if (!list.length) { event.preventDefault(); return; }
      const current = document.activeElement as HTMLElement | null;
      const outside = !current || !node?.contains(current);
      if (event.shiftKey && (outside || current === list[0])) { event.preventDefault(); list[list.length - 1].focus(); }
      else if (!event.shiftKey && (outside || current === list[list.length - 1])) { event.preventDefault(); list[0].focus(); }
    };
    document.addEventListener('keydown', onKey, true);
    return () => {
      document.removeEventListener('keydown', onKey, true);
      if (previous && document.contains(previous)) previous.focus();
    };
  }, []);
  return <div className={'modal-backdrop ' + className} onMouseDown={event => { if (dismissible && event.target === event.currentTarget) onClose(); }}>
    <section ref={panel} className={'modal' + (alert ? ' alert' : ' sheet')} role={alert ? 'alertdialog' : 'dialog'} aria-modal="true" aria-labelledby={titleId} tabIndex={-1}>
      <div className="modal-head">
        <h2 id={titleId}>{title}</h2>
        {dismissible && !alert && <button type="button" className="modal-close" onClick={onClose} aria-label="Close"><X size={15} /></button>}
      </div>
      {children}
    </section>
  </div>;
}

export default function DesktopApp() {
  const [initial] = useState(restore);
  const [conversations, setConversations] = useState<Conversation[]>(initial.conversations);
  const [activeId, setActiveId] = useState(initial.activeId);
  const [preferences, setPreferences] = useState<Preferences>(initial.preferences);
  const [customLanguage, setCustomLanguage] = useState(() => !LANGUAGES.includes(initial.preferences.language));
  const [status, setStatus] = useState<EngineStatus>({ state: 'loading', detail: 'Starting local AI…' });
  const [modelDetail, setModelDetail] = useState('');
  const [speed, setSpeed] = useState<number | null>(null);
  const [input, setInput] = useState('');
  const [attached, setAttached] = useState<Attachment | null>(null);
  const [streaming, setStreaming] = useState<{ chatId: string; kind: RequestKind } | null>(null);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [approval, setApproval] = useState<ApprovalRequest | null>(null);
  const [approvalSubmitting, setApprovalSubmitting] = useState(false);
  const [approvalError, setApprovalError] = useState('');
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [storageError, setStorageError] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  // Read aloud: which reply is loading or playing, and its audio.
  const [speaking, setSpeaking] = useState<{ id: string; state: 'loading' | 'playing' } | null>(null);
  const speechAudio = useRef<HTMLAudioElement | null>(null);
  const [restarting, setRestarting] = useState(false);
  const [searchOn, setSearchOn] = useState(false);
  // Phones: the chat list is a drawer opened from the top bar.
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [models, setModels] = useState<{ current: string | null; models: ModelChoice[] } | null>(null);
  const [improving, setImproving] = useState<{ id: string; text: string } | null>(null);
  const [query, setQuery] = useState('');
  const [renaming, setRenaming] = useState<{ id: string; title: string } | null>(null);
  const [atBottom, setAtBottom] = useState(true);
  const [remoteConfig, setRemoteConfig] = useState(() => getRemoteConfig());
  const [tunnelInput, setTunnelInput] = useState(() => getRemoteConfig().tunnel);
  const [keyInput, setKeyInput] = useState(() => getRemoteConfig().key);
  const [copiedLink, setCopiedLink] = useState(false);
  const [settingsTab, setSettingsTab] = useState<SettingsTab>('you');
  const searchBox = useRef<HTMLInputElement>(null);
  const workspace = useRef<HTMLElement>(null);
  const composerWrap = useRef<HTMLDivElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const composer = useRef<HTMLTextAreaElement>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const messageScroller = useRef<HTMLDivElement>(null);
  const followReply = useRef(true);
  const abort = useRef<AbortController | null>(null);
  const stopRequested = useRef(false);
  const pollNow = useRef<() => void>(() => undefined);
  const busyRef = useRef(false);
  const modelDetailRef = useRef('');
  const approvalSeenAt = useRef(0);
  const decidedApprovals = useRef(new Set<string>());
  const active = conversations.find(chat => chat.id === activeId) || conversations[0];
  const busy = streaming !== null;
  busyRef.current = busy;
  modelDetailRef.current = modelDetail;

  const isRemoteWeb = typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';
  const isRemote = isRemoteWeb || Boolean(remoteConfig.tunnel);
  const engineDown = status.state === 'fatal' || status.state === 'error' || status.state === 'offline';
  const ready = status.state === 'ready';
  // Progress messages from the engine end with an ellipsis; anything else is the model description.
  const progress = status.detail.trim().endsWith('…') ? status.detail.trim() : '';
  const adapter = /\+ LoRA ([A-Za-z0-9._+-]+)/.exec(modelDetail)?.[1];
  // The engine reports "<assistant name> • <model it is built on> • <GPU> • <quantisation>".
  const [modelName = 'Sulvana', builtOn = ''] = modelDetail ? modelDetail.split(' • ') : [];
  const baseModel = builtOn.replace(/ \+ LoRA .*$/, '');
  uiLanguage = preferences.uiLanguage;
  const statusText = engineDown ? (status.state === 'offline' ? L('Not connected', 'មិនបានភ្ជាប់') : L('Engine stopped', 'ម៉ាស៊ីនបានឈប់'))
    : status.state === 'loading' ? progress || 'Loading the model…'
      : streaming ? progress || (approval ? 'Waiting for you…' : streaming.kind === 'image' ? L('Creating image…', 'កំពុងបង្កើតរូបភាព…') : streaming.kind === 'vision' ? L('Reading image…', 'កំពុងមើលរូបភាព…') : L('Generating…', 'កំពុងសរសេរ…'))
        : ready ? L('Ready on GPU', 'រួចរាល់') : progress || L('Busy…', 'រវល់…');

  const focusComposer = () => { window.setTimeout(() => composer.current?.focus(), 0); };

  useEffect(() => {
    const live = conversations.some(chat => chat.messages.some(message => message.pending));
    const timer = window.setTimeout(() => {
      try {
        localStorage.setItem(STORAGE, JSON.stringify({ conversations, activeId, preferences }));
        setStorageError(false);
      } catch { setStorageError(true); }
    }, live ? 250 : 0);
    return () => window.clearTimeout(timer);
  }, [conversations, activeId, preferences]);
  useEffect(() => {
    document.documentElement.dataset.theme = preferences.theme;
    document.documentElement.dataset.accent = preferences.accent;
    document.documentElement.dataset.bubbleStyle = preferences.bubbleStyle;

    const style = document.documentElement.style;
    if (preferences.accent === 'custom' && preferences.customAccent) {
      const rgb = hexToRgb(preferences.customAccent);
      if (rgb) {
        const isLight = isLightTheme(preferences.theme);
        const primary = preferences.customAccent;
        const shade = darkenRgb(rgb, 0.35);
        const hover = lightenRgb(rgb, 0.15);
        const subtle = isLight ? `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.12)` : `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.2)`;
        const text = isLight ? darkenRgb(rgb, 0.25) : lightenRgb(rgb, 0.45);

        style.setProperty('--accent-primary', primary);
        style.setProperty('--accent-hover', hover);
        style.setProperty('--accent-subtle', subtle);
        style.setProperty('--accent-text', text);
        style.setProperty('--bubble-shade', shade);
        style.setProperty('--shade-accent', shade);
        style.setProperty('--btn-shade', isLight ? primary : shade);
        style.setProperty('--bg-user-msg', primary);
      }
    } else {
      style.removeProperty('--accent-primary');
      style.removeProperty('--accent-hover');
      style.removeProperty('--accent-subtle');
      style.removeProperty('--accent-text');
      style.removeProperty('--bubble-shade');
      style.removeProperty('--shade-accent');
      style.removeProperty('--btn-shade');
      style.removeProperty('--bg-user-msg');
    }
  }, [preferences.theme, preferences.accent, preferences.customAccent, preferences.bubbleStyle]);
  useEffect(() => { setApprovalError(''); if (approval) setDialog(null); }, [approval?.id]);
  useEffect(() => { if (followReply.current) bottom.current?.scrollIntoView({ block: 'end' }); }, [active.messages]);
  useEffect(() => { followReply.current = true; bottom.current?.scrollIntoView({ block: 'end' }); }, [activeId]);
  useEffect(() => { composer.current?.focus(); }, []);
  useEffect(() => { document.documentElement.dataset.textSize = preferences.textSize; }, [preferences.textSize]);
  // Interface size scales the whole window, like a game's GUI scale (CSS zoom on the root keeps the layout filling it).
  useEffect(() => {
    if (preferences.uiScale === 100) document.documentElement.style.removeProperty('zoom');
    else document.documentElement.style.setProperty('zoom', String(preferences.uiScale / 100));
  }, [preferences.uiScale]);
  const [scaleShown, setScaleShown] = useState(0);
  const scaleTimer = useRef<number | undefined>(undefined);
  const changeScale = (direction: -1 | 0 | 1) => {
    const index = UI_SCALES.indexOf(preferences.uiScale);
    const next = direction === 0 ? 100 : UI_SCALES[Math.min(UI_SCALES.length - 1, Math.max(0, (index < 0 ? 2 : index) + direction))];
    setPreferences(current => (current.uiScale === next ? current : { ...current, uiScale: next }));
    setScaleShown(next);
    window.clearTimeout(scaleTimer.current);
    scaleTimer.current = window.setTimeout(() => setScaleShown(0), 1400);
  };
  // Shortcuts: Escape stops reply, Ctrl+N new chat, Ctrl+K search chats, Ctrl+, settings, Ctrl+Shift+E export,
  // Ctrl + / Ctrl − / Ctrl 0 interface size.
  const shortcuts = useRef<(event: KeyboardEvent) => void>(() => undefined);
  shortcuts.current = (event: KeyboardEvent) => {
    if (event.key === 'Escape' && busyRef.current && !dialog && !approval) {
      event.preventDefault();
      stop();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && !event.altKey) {
      const zoom = event.key === '=' || event.key === '+' ? 1 : event.key === '-' || event.key === '_' ? -1 : event.key === '0' ? 0 : null;
      if (zoom !== null) { event.preventDefault(); changeScale(zoom); return; }
    }
    if (!(event.ctrlKey || event.metaKey) || dialog || approval) return;
    const key = event.key.toLowerCase();
    if (key === 'n' && !event.shiftKey) { event.preventDefault(); startChat(); }
    else if (key === 'k') { event.preventDefault(); searchBox.current?.focus(); searchBox.current?.select(); }
    else if (key === ',') { event.preventDefault(); setDialog('settings'); }
    else if (key === 'e' && event.shiftKey) { event.preventDefault(); exportChat(); }
  };
  useEffect(() => {
    const listener = (event: KeyboardEvent) => shortcuts.current(event);
    window.addEventListener('keydown', listener);
    return () => window.removeEventListener('keydown', listener);
  }, []);
  // The composer floats over the conversation, so the list needs to know how much room it takes.
  useLayoutEffect(() => {
    const node = composerWrap.current;
    if (!node || typeof ResizeObserver !== 'function') return;
    const apply = () => workspace.current?.style.setProperty('--composer-space', node.offsetHeight + 'px');
    apply();
    const observer = new ResizeObserver(apply);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  // Grow the message box with its text (up to 200 px). Measured again once fonts have loaded and on
  // resize: a measurement taken before layout settles is wrong and would stick until the user typed.
  const fitComposer = useRef(() => undefined as void);
  fitComposer.current = () => {
    const field = composer.current;
    if (!field) return;
    field.style.height = 'auto';
    field.style.height = Math.min(field.scrollHeight, 200) + 'px';
  };
  useLayoutEffect(() => { fitComposer.current(); }, [input]);
  useEffect(() => {
    const fit = () => fitComposer.current();
    const frame = requestAnimationFrame(fit);
    document.fonts?.ready.then(fit).catch(() => undefined);
    window.addEventListener('resize', fit);
    return () => { cancelAnimationFrame(frame); window.removeEventListener('resize', fit); };
  }, []);

  // The engine is polled faster while it is busy or starting, so the composer never waits on a stale state.
  useEffect(() => {
    let alive = true;
    let timer = 0;
    let running = false;
    const poll = async () => {
      window.clearTimeout(timer);
      if (running) return;
      running = true;
      const startedAt = performance.now();
      let next: EngineStatus;
      try {
        const target = api('/api/status');
        const res = await fetch(target, { headers: apiHeaders() });
        const body = await res.json() as EngineStatus;
        if (!res.ok) {
          next = { state: 'offline', detail: body?.detail || `Server returned HTTP ${res.status}` };
        } else if (!body || typeof body.state !== 'string') {
          throw new Error('Invalid JSON response');
        } else {
          next = { state: body.state, detail: typeof body.detail === 'string' ? body.detail : '', approval: body.approval };
        }
      } catch (err) {
        const targetHost = getRemoteConfig().tunnel || 'local engine';
        const msg = err instanceof Error ? err.message : String(err);
        next = { state: 'offline', detail: isRemote ? `Cannot reach ${targetHost} (${msg})` : 'The local service is not responding.' };
      }
      running = false;
      if (!alive) return;
      setStatus(previous => previous.state === next.state && previous.detail === next.detail ? previous : { state: next.state, detail: next.detail });
      // Only the engine's model description looks like "name • model • GPU • quantisation".
      if (next.state === 'ready' && next.detail.includes(' • ')) setModelDetail(next.detail);
      if (startedAt >= approvalSeenAt.current) {
        const pending = next.approval && typeof next.approval.id === 'string' && !decidedApprovals.current.has(next.approval.id) ? next.approval : null;
        setApproval(current => pending && current && current.id === pending.id
          ? (current.timeout_seconds === pending.timeout_seconds ? current : { ...current, timeout_seconds: pending.timeout_seconds })
          : pending);
      }
      timer = window.setTimeout(poll, busyRef.current || next.state !== 'ready' ? 700 : 2000);
    };
    pollNow.current = () => { void poll(); };
    void poll();
    return () => { alive = false; window.clearTimeout(timer); };
  }, []);

  const updateMessage = (chatId: string, id: string, change: (message: Message) => Message) => {
    setConversations(previous => previous.map(chat => chat.id === chatId
      ? { ...chat, messages: chat.messages.map(message => message.id === id ? change(message) : message) }
      : chat));
  };

  function saveRename() {
    if (!renaming) return;
    const title = renaming.title.trim().slice(0, 80);
    if (title) setConversations(previous => previous.map(chat => chat.id === renaming.id ? { ...chat, title } : chat));
    setRenaming(null);
  }

  function exportChat() {
    if (!active.messages.length) { setNotice({ kind: 'info', text: 'This conversation is empty, so there is nothing to export.' }); return; }
    const blob = new Blob([conversationMarkdown(active)], { type: 'text/markdown;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = (active.title.replace(/[\\/:*?"<>|]+/g, ' ').trim() || 'Sulvana chat').slice(0, 60) + '.md';
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(link.href), 10_000);
  }

  function selectChat(id: string) {
    setActiveId(id);
    setNotice(null);
    focusComposer();
  }

  function startChat() {
    const empty = conversations.find(chat => chat.messages.length === 0);
    if (empty) setActiveId(empty.id);
    else {
      const chat = newConversation();
      setConversations(previous => [chat, ...previous]);
      setActiveId(chat.id);
    }
    setInput(''); setAttached(null); setNotice(null);
    focusComposer();
  }

  function confirmDelete() {
    if (!deleteId || streaming?.chatId === deleteId) return;
    const remaining = conversations.filter(chat => chat.id !== deleteId);
    if (!remaining.length) remaining.push(newConversation());
    setConversations(remaining);
    if (activeId === deleteId) setActiveId(remaining[0].id);
    setDeleteId(null); setDialog(null);
    focusComposer();
  }

  async function attachFile(file?: File | null) {
    if (!file) return;
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type) || file.size > 10_000_000) {
      setNotice({ kind: 'error', text: 'Choose a PNG, JPEG, or WebP image under 10 MB.' }); return;
    }
    try {
      const data = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
      setAttached({ name: file.name || 'Pasted image', data }); setNotice(null);
    } catch { setNotice({ kind: 'error', text: 'Could not read the selected image.' }); }
    focusComposer();
  }

  function selectImage() {
    if (!window.sulvanaHost) { fileInput.current?.click(); return; }
    try {
      const selection = window.sulvanaHost.selectImage();
      if (selection) {
        const item = JSON.parse(selection);
        if (item.error) {
          setNotice({ kind: 'error', text: item.error === 'too_large' ? 'That image is larger than 10 MB. Choose a smaller one.' : 'Could not read the selected image.' });
        } else {
          setAttached({ name: decodeBase64(item.name64), data: item.data });
          setNotice(null);
        }
      }
    } catch { setNotice({ kind: 'error', text: 'Could not read the selected image.' }); }
    focusComposer();
  }

  function stop() {
    const controller = abort.current;
    if (!controller) return;
    stopRequested.current = true;
    if (approval) decidedApprovals.current.add(approval.id);
    approvalSeenAt.current = performance.now();
    setApproval(null);
    // Ask the engine to stop first so the reply ends cleanly; cut the connection if it does not.
    void fetch(api('/api/stop'), { method: 'POST', headers: apiHeaders() }).catch(() => undefined);
    window.setTimeout(() => controller.abort(), 1500);
    focusComposer();
  }

  async function decideApproval(decision: 'allow' | 'deny' | 'allow_all') {
    if (!approval || approvalSubmitting) return;
    const request = approval;
    setApprovalSubmitting(true);
    setApprovalError('');
    try {
      const response = await fetch(api('/api/approval'), {
        method: 'POST', headers: apiHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ id: request.id, decision }),
      });
      if (!response.ok && response.status !== 409) throw new Error('Could not send your decision.');
      decidedApprovals.current.add(request.id);
      approvalSeenAt.current = performance.now();
      setApproval(null);
      if (response.status === 409) setNotice({ kind: 'info', text: 'That permission request had already expired, so nothing was run.' });
    } catch (cause) {
      setApprovalError(cause instanceof Error ? cause.message : 'Could not send your decision.');
    } finally { setApprovalSubmitting(false); }
  }

  /** Coding mode works in one project folder. The Electron window can show a folder picker. */
  async function chooseProject(): Promise<string> {
    if (!window.sulvanaElectron) { setDialog('settings'); return ''; }
    try {
      const folder = await window.sulvanaElectron.chooseFolder();
      if (folder) setPreferences(current => ({ ...current, codeRoot: folder, code: true }));
      return folder || '';
    } catch { setNotice({ kind: 'error', text: 'Could not open the folder picker. Type the folder in Settings instead.' }); return ''; }
  }

  async function undoTask(chatId: string, message: Message) {
    if (!message.code || message.code.undone) return;
    try {
      const response = await fetch(api('/api/code/undo'), { method: 'POST', headers: apiHeaders({ 'Content-Type': 'application/json' }), body: JSON.stringify({ task: message.code.task }) });
      const text = await response.text();
      if (!response.ok) throw new Error(text || 'Could not undo these changes.');
      const restored: string[] = JSON.parse(text).restored || [];
      updateMessage(chatId, message.id, current => current.code ? { ...current, code: { ...current.code, undone: true } } : current);
      setNotice({ kind: 'info', text: restored.length ? `Restored ${restored.length} file${restored.length === 1 ? '' : 's'}: ${restored.join(', ')}` : 'There was nothing to restore.' });
    } catch (cause) {
      setNotice({ kind: 'error', text: cause instanceof Error ? cause.message : 'Could not undo these changes.' });
    }
  }

  // Settings: which model the engine runs. Switching restarts the engine with the other model.
  useEffect(() => {
    if (dialog !== 'settings') return;
    const current = getRemoteConfig();
    setTunnelInput(current.tunnel);
    setKeyInput(current.key);
    fetch(api('/api/models'), { cache: 'no-store', headers: apiHeaders() }).then(r => r.json()).then(setModels).catch(() => setModels(null));
  }, [dialog]);

  async function switchModel(id: string) {
    const choice = models?.models.find(m => m.id === id);
    if (!choice || !choice.available || busy) return;
    setModels(current => current ? { ...current, current: id } : current);
    setNotice({ kind: 'info', text: `Switching to ${choice.label}… this takes about a minute${id === 'sulvana-1.0-code' ? '. It answers slowly: it is a 27B model running mostly from system memory' : ''}.` });
    try {
      const response = await fetch(api('/api/model'), { method: 'POST', headers: apiHeaders({ 'Content-Type': 'application/json' }), body: JSON.stringify({ profile: id }) });
      if (!response.ok) throw new Error((await response.text()) || 'The model could not be started.');
      setModelDetail('');
    } catch (cause) {
      setNotice({ kind: 'error', text: cause instanceof Error ? cause.message : 'The model could not be started.' });
    } finally { pollNow.current(); }
  }

  /** Save a reply (as it is, or corrected by the user) as a training example in datasets/feedback/. */
  async function sendFeedback(message: Message, rating: 'good' | 'corrected', answer: string) {
    const position = active.messages.findIndex(item => item.id === message.id);
    const request = position > 0 ? active.messages[position - 1] : undefined;
    if (!request || request.role !== 'user') return;
    try {
      const response = await fetch(api('/api/feedback'), {
        method: 'POST', headers: apiHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ prompt: request.text, answer, rating, original: message.text, model: modelDetail, history: historyFor(active.messages.slice(0, position - 1)) }),
      });
      if (!response.ok) throw new Error();
      updateMessage(active.id, message.id, current => ({ ...current, feedback: rating, text: rating === 'corrected' ? answer : current.text }));
      setNotice({ kind: 'info', text: rating === 'good' ? 'Saved as a good example for training.' : 'Your correction was saved for training.' });
    } catch { setNotice({ kind: 'error', text: 'Could not save that example.' }); }
  }

  async function restartEngine() {
    if (restarting) return;
    setRestarting(true);
    try {
      const response = await fetch(api('/api/restart'), { method: 'POST', headers: apiHeaders() });
      if (!response.ok && response.status !== 409) throw new Error();
      setNotice(null);
    } catch {
      setNotice({ kind: 'error', text: 'Sulvana could not restart its engine. Close Sulvana and open it again.' });
    } finally {
      setRestarting(false);
      pollNow.current();
    }
  }

  function saveRemoteSettings(tunnel: string, key: string) {
    const cleanTunnel = tunnel.trim().replace(/\/+$/, '');
    const cleanKey = key.trim();
    try {
      if (cleanTunnel) localStorage.setItem('sulvana.remote.tunnel', cleanTunnel);
      else localStorage.removeItem('sulvana.remote.tunnel');
      if (cleanKey) localStorage.setItem('sulvana.remote.key', cleanKey);
      else localStorage.removeItem('sulvana.remote.key');
    } catch {}
    setRemoteConfig({ tunnel: cleanTunnel, key: cleanKey });
    setNotice({ kind: 'info', text: cleanTunnel ? 'Saved laptop connection settings.' : 'Reset to local host connection.' });
    pollNow.current();
  }

  function copyInviteLink() {
    const tunnel = (tunnelInput || remoteConfig.tunnel).trim().replace(/\/+$/, '');
    const key = (keyInput || remoteConfig.key).trim();
    if (!tunnel) {
      setNotice({ kind: 'error', text: 'Enter a tunnel URL first before copying the invite link.' });
      return;
    }
    const origin = typeof window !== 'undefined' ? window.location.origin : '';
    const link = `${origin}/?tunnel=${encodeURIComponent(tunnel)}${key ? `&key=${encodeURIComponent(key)}` : ''}`;
    navigator.clipboard.writeText(link).then(() => {
      setCopiedLink(true);
      setNotice({ kind: 'info', text: 'Friend invite link copied to clipboard!' });
      setTimeout(() => setCopiedLink(false), 2500);
    }).catch(() => {
      setNotice({ kind: 'error', text: 'Could not copy to clipboard.' });
    });
  }

  function saveImage(imageUrl: string) {
    const name = new URL(imageUrl, location.href).searchParams.get('name');
    if (!name) { setNotice({ kind: 'error', text: 'Could not find the generated image.' }); return; }
    try {
      if (window.sulvanaHost) {
        const result = window.sulvanaHost.saveImage(name);
        if (result === 'saved' || result === true) setNotice({ kind: 'info', text: 'Image saved.' });
        else if (result === 'missing') setNotice({ kind: 'error', text: 'That image file is no longer on this computer.' });
        else if (result === 'failed') setNotice({ kind: 'error', text: 'The image could not be saved there. Try another folder.' });
      } else {
        const link = document.createElement('a');
        link.href = imageUrl; link.download = name; link.click();
      }
    } catch { setNotice({ kind: 'error', text: 'Could not save the image.' }); }
  }

  function stopSpeaking() {
    speechAudio.current?.pause();
    if (speechAudio.current?.src) URL.revokeObjectURL(speechAudio.current.src);
    speechAudio.current = null;
    setSpeaking(null);
  }

  async function listen(message: Message) {
    if (speaking?.id === message.id) { stopSpeaking(); return; }
    stopSpeaking();
    setSpeaking({ id: message.id, state: 'loading' });
    try {
      const response = await fetch(api('/api/speak'), { method: 'POST', headers: apiHeaders({ 'Content-Type': 'application/json' }), body: JSON.stringify({ text: message.text }) });
      if (!response.ok) throw new Error(await response.text() || `HTTP ${response.status}`);
      const audio = new Audio(URL.createObjectURL(await response.blob()));
      speechAudio.current = audio;
      audio.onended = () => stopSpeaking();
      await audio.play();
      setSpeaking(current => current?.id === message.id ? { id: message.id, state: 'playing' } : current);
    } catch (cause) {
      setSpeaking(null);
      setNotice({ kind: 'error', text: L('Could not read aloud: ', 'មិនអាចអានឮៗបានទេ៖ ') + (cause instanceof Error ? cause.message : String(cause)) });
    }
  }

  async function copyMessage(message: Message) {
    try {
      await copyText(message.text);
      setCopiedId(message.id);
      window.setTimeout(() => setCopiedId(current => current === message.id ? null : current), 2000);
    } catch { setNotice({ kind: 'error', text: 'Could not copy that message.' }); }
  }

  /** Put the request that led to a failed reply back into the composer. */
  function retry(reply: Message) {
    const position = active.messages.findIndex(message => message.id === reply.id);
    const request = position > 0 ? active.messages[position - 1] : undefined;
    if (!request || request.role !== 'user') return;
    setInput(request.text);
    setNotice(request.attachment ? { kind: 'info', text: `Attach ${request.attachment} again before sending.` } : null);
    focusComposer();
  }

  /** Ask again: drop the last reply (and its request) and send the same request once more. */
  function regenerate(reply: Message) {
    const position = active.messages.findIndex(message => message.id === reply.id);
    const request = position > 0 ? active.messages[position - 1] : undefined;
    if (!request || request.role !== 'user' || busy) return;
    void send(request.text, request.id);
  }

  async function send(override?: string, replaceFrom?: string) {
    const draft = override ?? input;
    const attachment = override === undefined ? attached : null;
    const prompt = draft.trim() || (attachment ? 'Describe this image.' : '');
    if (!prompt || busy) return;
    if (!ready) {
      setNotice({ kind: 'info', text: engineDown ? 'Sulvana’s engine is not running. Restart it, then send your message.' : 'Sulvana is still getting ready. Your message is kept here.' });
      pollNow.current();
      return;
    }
    if (/^\/image\s*$/i.test(prompt)) { setNotice({ kind: 'error', text: 'Describe the image you want after /image.' }); return; }
    // "remember that …" / "ចងចាំថា …" saves a memory (Settings → Personalisation) that every later chat gets.
    const remember = override === undefined ? /^(?:please\s+)?remember(?:\s+that)?\s+(.{3,200})$/i.exec(prompt) || /^(?:សូម)?(?:ចងចាំ|ចាំ)(?:ថា)?\s*(.{3,200})$/.exec(prompt) : null;
    let memories = preferences.memories;
    if (remember && !memories.includes(remember[1].trim())) {
      memories = [...memories, remember[1].trim()].slice(-30);
      setPreferences(current => ({ ...current, memories }));
      setNotice({ kind: 'info', text: L('Saved to memory. See Settings → Personalisation.', 'បានរក្សាទុកក្នុងការចងចាំ។ មើលក្នុង ការកំណត់ → ផ្ទាល់ខ្លួន។') });
    }
    if (attachment && /^\/image\b/i.test(prompt)) { setNotice({ kind: 'error', text: 'Send the attached image separately from an /image request.' }); return; }
    const chatId = active.id;
    // Regenerating replaces the exchange from `replaceFrom` onwards.
    const cutAt = replaceFrom ? active.messages.findIndex(message => message.id === replaceFrom) : -1;
    const earlier = cutAt >= 0 ? active.messages.slice(0, cutAt) : active.messages;
    const firstMessage = earlier.length === 0;
    let kind: RequestKind = attachment ? 'vision' : /^\/image\b/i.test(prompt) ? 'image' : 'chat';
    const coding = preferences.code && kind === 'chat' && !prompt.startsWith('/');
    if (coding && !preferences.codeRoot) {
      setNotice({ kind: 'info', text: 'Choose the project folder Sulvana may work in, then send again.' });
      void chooseProject();
      return;
    }
    const user: Message = { id: createId(), role: 'user', text: prompt, attachment: attachment?.name };
    const assistant: Message = {
      id: createId(), role: 'assistant', text: '', pending: true,
      plain: /^\/(terminal|docs|search|calc|number)(\s|$)/i.test(prompt) || undefined,
      activity: kind === 'vision' ? 'Looking at your image…' : kind === 'image' ? 'Creating your image…' : coding ? 'Looking at your project…' : searchOn ? 'Searching the web…' : 'Thinking…',
    };
    const payload: StreamPayload = {
      prompt,
      image: attachment?.data,
      history: historyFor(earlier),
      maxTokens: preferences.maxTokens,
      temperature: preferences.temperature,
      language: preferences.language.trim() || 'Auto',
      search: (searchOn && kind === 'chat' && !coding) || undefined,
      reasoning: (preferences.reasoning && kind === 'chat') || undefined,
      translate: kind === 'chat' && !coding && preferences.translate !== 'off' ? preferences.translate : undefined,
      autoSearch: (preferences.autoSearch && kind === 'chat' && !coding) || undefined,
      profile: { name: preferences.userName, about: preferences.aboutUser, instructions: preferences.instructions, style: preferences.responseStyle, memories },
      code: coding ? { root: preferences.codeRoot } : undefined,
    };
    setConversations(previous => previous.map(chat => chat.id === chatId
      ? { ...chat, updatedAt: Date.now(), title: chat.messages.length ? chat.title : prompt.replace(/^\/image\s*/i, '').slice(0, 36) || 'New chat',
          messages: [...(cutAt >= 0 ? chat.messages.slice(0, cutAt) : chat.messages), user, assistant] }
      : chat));
    if (override === undefined) { setInput(''); setAttached(null); }
    setNotice(null); setSpeed(null); setSearchOn(false);
    setStreaming({ chatId, kind });
    followReply.current = true;
    window.setTimeout(() => bottom.current?.scrollIntoView({ block: 'end', behavior: 'smooth' }), 40);
    const controller = new AbortController();
    abort.current = controller;
    stopRequested.current = false;
    let reply = '';
    let imageUrl = '';
    let stopped = false;
    let finished = false;
    let approvalId = '';
    let thoughts = '';
    let sources: Source[] = [];
    let cut = false;
    let parts: Part[] = [];
    let codeTask: CodeTask | undefined;
    let translated: 'google' | 'local' | undefined;
    // In coding mode the reply text is the prose between steps, joined.
    const prose = () => parts.flatMap(part => part.kind === 'text' && part.text.trim() ? [part.text.trim()] : []).join('\n\n');
    try {
      await requestStream(payload, controller.signal, (event, data) => {
        let activity: string | undefined;
        if (event === 't') {
          if (coding) {
            const last = parts[parts.length - 1];
            parts = last && last.kind === 'text' ? [...parts.slice(0, -1), { kind: 'text', text: last.text + data }] : [...parts, { kind: 'text', text: data }];
            reply = prose();
          } else reply += data;
        }
        if (event === 'c') {
          const step = JSON.parse(data) as CodeStep;
          const at = parts.findIndex(part => part.kind === 'step' && part.step.id === step.id);
          parts = at >= 0 ? parts.map((part, index) => index === at ? { kind: 'step', step } : part) : [...parts, { kind: 'step', step }];
          activity = step.status === 'running' ? step.title + '…' : 'Thinking…';
        }
        // The reply started repeating itself; the app is writing it again from the start.
        if (event === 'x') { reply = ''; thoughts = ''; activity = 'Rewriting the answer…'; }
        if (event === 'r') { thoughts += data; activity = 'Reasoning…'; }
        if (event === 's') {
          const found = JSON.parse(data);
          // Notes arrive first; web results are added after them.
          sources = cleanSources([...sources, ...(Array.isArray(found.results) ? found.results : [])]);
          activity = found.query === 'Notes' ? 'Reading your notes…' : 'Reading the results…';
        }
        if (event === 'e') { finished = true; throw new Error(data); }
        if (event === 'p') {
          const request = JSON.parse(data) as ApprovalRequest;
          if (!request.id || !request.command) throw new Error('Invalid approval request from the local engine.');
          approvalId = request.id;
          approvalSeenAt.current = performance.now();
          setApproval(request);
          setApprovalError('');
          activity = 'Waiting for your decision…';
        }
        if (event === 'v' || event === 'i') {
          const update = JSON.parse(data);
          if (update.state === 'started') {
            // The engine also recognises plain-language image requests, so follow what it actually started.
            kind = event === 'i' ? 'image' : 'vision';
            activity = event === 'i' ? 'Creating your image…' : 'Looking at your image…';
            setStreaming({ chatId, kind });
          }
          if (update.state === 'done') finished = true;
          if (update.answer) reply = update.answer;
          if (update.image_path) {
            imageUrl = api('/api/image?name=' + encodeURIComponent((update.image_path || '').split('/').pop() || ''));
            reply = `Generated image: ${prompt.replace(/^\/image\s*/i, '')}`;
          }
        }
        if (event === 'd') {
          finished = true;
          const metrics = JSON.parse(data);
          if (metrics.tokens_per_second) setSpeed(metrics.tokens_per_second);
          stopped = Boolean(metrics.stopped);
          cut = Boolean(metrics.truncated);
          if (metrics.code && typeof metrics.code.task === 'string') codeTask = metrics.code;
          if (metrics.loop_guard_triggered) setNotice({ kind: 'info', text: 'Sulvana stopped a reply that had started repeating itself.' });
          if (typeof metrics.clean_reply === 'string') reply = metrics.clean_reply;
          translated = metrics.translated === 'google' || metrics.translated === 'local' ? metrics.translated : undefined;
        }
        updateMessage(chatId, assistant.id, message => ({ ...message, text: reply, reasoning: thoughts || undefined, sources: sources.length ? sources : undefined, image: imageUrl || undefined, parts: parts.length ? parts : undefined, activity: activity || message.activity }));
      });
      updateMessage(chatId, assistant.id, message => ({
        ...message, text: reply, reasoning: thoughts || undefined, sources: sources.length ? sources : undefined, cut: cut || undefined, translated,
        image: imageUrl || undefined, pending: false, activity: undefined, parts: parts.length ? parts : undefined, code: codeTask,
        note: stopped ? 'stopped' : reply || parts.length ? undefined : 'empty',
      }));
    } catch (cause) {
      const reason = cause instanceof Error ? cause.message : 'Unknown error';
      const cancelled = controller.signal.aborted || stopRequested.current;
      if (!cancelled && cause instanceof HttpError && cause.status === 409) {
        // Nothing was generated: give the draft back instead of leaving a failed exchange in the chat.
        setConversations(previous => previous.map(chat => chat.id === chatId
          ? { ...chat, title: firstMessage ? 'New chat' : chat.title, messages: cutAt >= 0 ? active.messages : chat.messages.filter(message => message.id !== user.id && message.id !== assistant.id) }
          : chat));
        if (override === undefined) setInput(current => current || draft);
        setAttached(current => current || attachment);
        setNotice({ kind: 'info', text: 'Sulvana is busy or still loading. Your message is back in the box — try again in a moment.' });
      } else {
        updateMessage(chatId, assistant.id, message => message.text || message.parts?.length || cancelled
          ? { ...message, pending: false, activity: undefined, note: 'stopped' }
          : { ...message, text: reason, pending: false, activity: undefined, note: 'error' });
        if (!cancelled && reply) setNotice({ kind: 'error', text: `The reply was cut off: ${reason}` });
      }
    } finally {
      if (abort.current === controller) abort.current = null;
      // The request is over, so any permission prompt it raised is void.
      if (approvalId) decidedApprovals.current.add(approvalId);
      approvalSeenAt.current = performance.now();
      setApproval(null);
      setStreaming(null);
      // The engine reports a finished request before it closes the stream, so it is ready again.
      if (finished) setStatus(previous => previous.state === 'generating' ? { state: 'ready', detail: modelDetailRef.current || previous.detail } : previous);
      pollNow.current();
      if (!document.activeElement || document.activeElement === document.body) focusComposer();
    }
  }

  const projectName = preferences.codeRoot.split('/').filter(Boolean).pop() || '';
  const composerHint = preferences.code && ready && !streaming ? (projectName ? `Coding in ${projectName} · edits and commands ask first` : 'Choose a project folder for coding mode')
    : searchOn && ready && !streaming ? L('Sulvana will search the web for this message.', 'Sulvana នឹងស្វែងរកតាមអ៊ីនធឺណិតសម្រាប់សារនេះ។')
    : engineDown ? L('Sulvana’s engine is not running.', 'ម៉ាស៊ីនរបស់ Sulvana មិនដំណើរការទេ។')
    : status.state === 'loading' ? L('Loading the model — you can start typing.', 'កំពុងផ្ទុកម៉ូដែល — អ្នកអាចចាប់ផ្តើមវាយបាន។')
      : streaming && streaming.chatId !== active.id ? L('Sulvana is replying in another conversation.', 'Sulvana កំពុងឆ្លើយក្នុងការសន្ទនាផ្សេង។')
        : 'Sulvana can make mistakes. Check important facts. · Sulvana អាចឆ្លើយខុស សូមផ្ទៀងផ្ទាត់ព័ត៌មានសំខាន់ៗ។';
  const rangeFill = `${((preferences.temperature - 0.1) / 1.4) * 100}%`;

  return <div className={'shell' + (drawerOpen ? ' drawer-open' : '') + (preferences.uiLanguage === 'km' ? ' ui-km' : '')}>
    {drawerOpen && <div className="drawer-backdrop" onClick={() => setDrawerOpen(false)} aria-hidden="true" />}
    {scaleShown > 0 && <div className="scale-toast" role="status" aria-live="polite" key={scaleShown}>{L('Interface size', 'ទំហំកម្មវិធី')} · {scaleShown}%</div>}
    <aside className="sidebar" onClick={event => { if ((event.target as HTMLElement).closest('.conversation > button:first-child, .new-chat')) setDrawerOpen(false); }}>
      <div className="sidebar-head">
        <div className="brand"><Logo size={32} /><div><strong>Sulvana</strong><small>{L('On this device', 'នៅលើកុំព្យូទ័រនេះ')}</small></div></div>
        <button type="button" className="new-chat" onClick={startChat} title="New chat" aria-label="New chat"><SquarePen size={17} /></button>
      </div>
      <div className="sidebar-search">
        <Search size={14} aria-hidden="true" />
        <input ref={searchBox} type="search" placeholder={L('Search chats  (Ctrl+K)', 'ស្វែងរកការសន្ទនា (Ctrl+K)')} aria-label="Search conversations" value={query}
          onChange={event => setQuery(event.target.value)} onKeyDown={event => { if (event.key === 'Escape') { setQuery(''); focusComposer(); } }} />
      </div>
      <nav className="conversation-list" aria-label="Conversations">{(() => {
        const needle = query.trim().toLocaleLowerCase();
        const shown = conversations.filter(chat => !needle || chat.title.toLocaleLowerCase().includes(needle)
          || chat.messages.some(message => message.text.toLocaleLowerCase().includes(needle)));
        if (!shown.length) return <p className="sidebar-empty">No conversation matches “{query}”.</p>;
        const groups = new Map<string, Conversation[]>();
        for (const chat of [...shown].sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0))) {
          const name = dateGroup(chat.updatedAt);
          groups.set(name, [...(groups.get(name) || []), chat]);
        }
        return GROUP_ORDER.filter(name => groups.has(name)).map(name => <section key={name} aria-label={uiLanguage === 'km' ? GROUP_KM[name] : name}>
          <div className="sidebar-heading">{uiLanguage === 'km' ? GROUP_KM[name] : name}</div>
          {groups.get(name)!.map(chat => {
            const live = streaming?.chatId === chat.id;
            return <div key={chat.id} className={'conversation' + (chat.id === activeId ? ' selected' : '')}>
              {renaming?.id === chat.id
                ? <input className="rename-input" autoFocus value={renaming.title} aria-label="Conversation name" maxLength={80}
                    onChange={event => setRenaming({ id: chat.id, title: event.target.value })} onBlur={saveRename}
                    onKeyDown={event => { if (event.key === 'Enter') saveRename(); else if (event.key === 'Escape') setRenaming(null); }} />
                : <button type="button" onClick={() => selectChat(chat.id)} onDoubleClick={() => setRenaming({ id: chat.id, title: chat.title })}
                    aria-current={chat.id === activeId ? 'true' : undefined} title={chat.title + ' (double-click to rename)'}>
                    <MessageCircle size={15} /><span>{chat.title}</span>{live && <i className="live-dot" role="img" aria-label="Replying" />}
                  </button>}
              <button type="button" className="delete-chat" aria-label={`Rename ${chat.title}`} title="Rename" onClick={() => setRenaming({ id: chat.id, title: chat.title })}><PencilLine size={13} /></button>
              <button type="button" className="delete-chat" aria-label={`Delete ${chat.title}`} title={live ? 'Wait for the reply to finish' : 'Delete conversation'} disabled={live} onClick={() => { setDeleteId(chat.id); setDialog('delete'); }}><Trash2 size={14} /></button>
            </div>;
          })}
        </section>);
      })()}</nav>
      <div className="sidebar-footer"><button type="button" onClick={() => setDialog('tools')}><ShieldCheck size={15} /> {L('Tools', 'ឧបករណ៍')}</button><div className="maker" title="Sulvana is made by WKH Labs: Wisdom · Khmer · Heritage"><img src={isLightTheme(preferences.theme) ? WKH_MARK_LIGHT : WKH_MARK_DARK} alt="" /><div><strong>WKH Labs</strong><span>Wisdom · Khmer · Heritage</span></div></div></div>
    </aside>
    <main className="workspace" ref={workspace}>
      <header className="topbar">
        <div className="model-info">
          <button type="button" className="icon-button drawer-toggle" aria-label="Show conversations" title="Conversations" onClick={() => setDrawerOpen(true)}><Menu size={17} /></button>
          <strong>{modelName}</strong>{baseModel && <span className="model-chip" title={`${modelName} is built on ${baseModel} and runs on this computer.`}>{baseModel}</span>}
          {adapter && <span className="model-chip adapter-chip" title={`WKH Labs Khmer fine-tune loaded on top of ${baseModel || 'the base model'} (${adapter.split('+').join(', ')})`}>Khmer-tuned</span>}
          {preferences.translate === 'google' && <span className="model-chip online-chip" title={L("Khmer tools use Google: your Khmer messages and Sulvana's replies are sent to Google. Choose 'This computer' in Settings to keep everything local.", 'ឧបករណ៍ភាសាខ្មែរកំពុងប្រើ Google៖ សារជាភាសាខ្មែររបស់អ្នក និងចម្លើយរបស់ Sulvana ត្រូវបានផ្ញើទៅ Google។ ជ្រើស «កុំព្យូទ័រនេះ» ក្នុងការកំណត់ ដើម្បីរក្សាទុកអ្វីៗទាំងអស់នៅលើកុំព្យូទ័រនេះ។')}><Globe size={11} /> {L('Google tools on', 'កំពុងប្រើឧបករណ៍ Google')}</span>}
        </div>
        <div className="topbar-right">
          <span className={'status-dot ' + (ready ? 'ready' : engineDown ? 'bad' : 'busy')} aria-hidden="true" title={statusText} />
          <span className="engine-state" role="status" title={status.detail + (speed !== null ? ` · ${L('last reply', 'ចម្លើយចុងក្រោយ')}: ${speed.toFixed(1)} tok/s` : '')}>{statusText}</span>
          <button type="button" className="icon-button plain" title="Export this chat as Markdown (Ctrl+Shift+E)" aria-label="Export chat" onClick={exportChat}><FileDown size={17} /></button>
          <button type="button" className="icon-button" title="Settings (Ctrl+,)" aria-label="Settings" onClick={() => setDialog('settings')}><Settings size={17} /></button>
        </div>
      </header>
      <div className="messages" ref={messageScroller} tabIndex={0} role="region" aria-label="Conversation" onScroll={() => {
        const pane = messageScroller.current;
        if (pane) { followReply.current = pane.scrollHeight - pane.scrollTop - pane.clientHeight < 100; setAtBottom(followReply.current); }
      }}>
        {active.messages.length === 0 ? <div className="empty">
          <span className="float-shape f1" aria-hidden="true" /><span className="float-shape f2" aria-hidden="true" />
          <span className="float-shape f3" aria-hidden="true" /><span className="float-shape f4" aria-hidden="true" />
          <div className="empty-icon"><Logo size={88} /></div>
          {uiLanguage === 'km'
            ? <><h1 lang="km" dir="auto">{greeting('km', preferences.userName)}</h1><p className="empty-khmer" lang="km">តើខ្ញុំអាចជួយអ្វីបាន?</p>
              <p lang="km">សួរអ្វីក៏បាន ភ្ជាប់រូបភាព ឬវាយ <code>/image</code> ដើម្បីបង្កើតរូបភាព។</p></>
            : <><h1 dir="auto">{greeting('en', preferences.userName)}</h1><p className="empty-khmer" lang="km">តើខ្ញុំអាចជួយអ្វីបាន?</p>
              <p>What are we working on? Ask anything, attach an image, or type <code>/image</code> to create one.</p></>}
          {!preferences.translateAsked && <div className="consent-card" role="region" aria-label="Khmer tools">
            <strong lang="km">ចង់បានភាសាខ្មែរល្អជាងនេះទេ?</strong>
            {uiLanguage === 'km'
              ? <p lang="km">Sulvana គិតជាភាសាអង់គ្លេស ហើយឧបករណ៍ភាសាខ្មែរនៅលើកុំព្យូទ័រនេះ សរសេរចម្លើយជាភាសាខ្មែរ។ ដើម្បីបានភាសាខ្មែរត្រឹមត្រូវជាងនេះ អ្នកអាចប្រើ<b>ឧបករណ៍ Google</b> ប៉ុន្តែសារជាភាសាខ្មែររបស់អ្នក និងចម្លើយរបស់ Sulvana នឹងត្រូវផ្ញើទៅ Google។ អ្នកអាចប្តូរវានៅពេលណាក៏បាន ក្នុងការកំណត់។</p>
              : <p>Sulvana thinks in English and Khmer tools on this computer write the answer in Khmer. For the most accurate Khmer you can use <b>Google's tools</b> instead, but your Khmer messages and Sulvana's replies are then sent to Google. You can change this any time in Settings.</p>}
            <div className="consent-actions">
              <button type="button" onClick={() => setPreferences(current => ({ ...current, translate: 'local', translateAsked: true }))}>{L('Keep it on this computer', 'រក្សាទុកនៅលើកុំព្យូទ័រនេះ')}</button>
              <button type="button" className="approve-button" onClick={() => setPreferences(current => ({ ...current, translate: 'google', translateAsked: true }))}>{L("Use Google's tools", 'ប្រើឧបករណ៍ Google')}</button>
            </div>
          </div>}
          <div className="suggestions">
            <button type="button" lang="km" onClick={() => { setInput('សូមសរសេរលិខិតមួយ ដើម្បី '); focusComposer(); }}><PencilLine size={17} /><span>សរសេរលិខិត</span><small>Write a letter</small></button>
            <button type="button" lang="km" onClick={() => { setInput('សូមសង្ខេបអត្ថបទនេះ៖\n\n'); focusComposer(); }}><FileText size={17} /><span>សង្ខេបអត្ថបទ</span><small>Summarise a text</small></button>
            <button type="button" lang="km" onClick={() => { setInput('សូមបកប្រែជាភាសាអង់គ្លេស៖ '); focusComposer(); }}><Globe size={17} /><span>បកប្រែ</span><small>Translate</small></button>
            <button type="button" lang="km" onClick={() => { setInput('សូមពន្យល់ឱ្យងាយយល់អំពី '); focusComposer(); }}><Lightbulb size={17} /><span>ពន្យល់គំនិត</span><small>Explain an idea</small></button>
            <button type="button" lang="km" onClick={() => { setInput('Help me write code for '); focusComposer(); }}><Code size={17} /><span>សរសេរកូដ</span><small>Write code</small></button>
            <button type="button" lang="km" onClick={() => { setInput('/image '); focusComposer(); }}><ImageIcon size={17} /><span>បង្កើតរូបភាព</span><small>Create an image</small></button>
          </div>
        </div> : <div className="message-column">
          {active.messages.map(message => {
            const failed = message.note === 'error' || message.note === 'empty' || message.note === 'interrupted';
            return <article className={'message ' + message.role + (failed ? ' failed' : '') + (KHMER.test(message.text) ? ' khmer' : '')} key={message.id} aria-busy={message.pending || undefined}>
              <div className={'message-name' + (message.role === 'user' ? ' visually-hidden' : '')}>{message.role === 'user' ? 'You' : 'Sulvana'}{message.pending ? <span className="thinking">{L('working', 'កំពុងគិត')}</span> : message.note === 'stopped' && message.text && message.text !== NOTE_TEXT.stopped ? <span className="thinking">{L('stopped early', 'បានឈប់មុន')}</span>
                : message.translated ? <span className="thinking" title={message.translated === 'google' ? L("Written with Google's Khmer tools (Settings → Khmer tools)", 'សរសេរដោយឧបករណ៍ភាសាខ្មែររបស់ Google (ការកំណត់ → ឧបករណ៍ភាសាខ្មែរ)') : L('Written with the Khmer tools on this computer (Settings → Khmer tools)', 'សរសេរដោយឧបករណ៍ភាសាខ្មែរនៅលើកុំព្យូទ័រនេះ (ការកំណត់ → ឧបករណ៍ភាសាខ្មែរ)')}>{message.translated === 'google' ? L('Khmer tools · Google', 'ឧបករណ៍ខ្មែរ · Google') : L('Khmer tools', 'ឧបករណ៍ខ្មែរ')}</span> : null}</div>
              {message.attachment && <div className="attachment-label"><ImagePlus size={14} />{message.attachment}</div>}
              {message.reasoning && <Reasoning text={message.reasoning} live={!!message.pending && !message.text} />}
              {message.note === 'error' ? <div className="message-body message-problem" dir="auto"><TriangleAlert size={15} aria-hidden="true" /><span>{message.text.replace(/^Error: /, '') || NOTE_TEXT.error}</span></div>
                : message.text && message.plain ? <pre className="tool-output" tabIndex={0}>{message.text}</pre>
                  : message.parts ? <div className="code-parts">{message.parts.map((part, index) => part.kind === 'step'
                    ? <StepCard key={part.step.id} step={part.step} />
                    : part.text.trim() ? <Markdown key={index} text={part.text.trim()} onCopy={copyText} /> : null)}
                    {message.pending && message.parts[message.parts.length - 1].kind === 'step' && <div className="message-body message-activity" dir="auto">{message.activity}</div>}</div>
                  : message.text ? <Markdown text={message.text} onCopy={copyText} />
                    : message.pending && message.reasoning ? null
                      : <div className={'message-body' + (message.pending ? ' message-activity' : ' message-placeholder')} dir="auto">{message.pending ? message.activity : NOTE_TEXT[message.note || 'empty']}</div>}
              {message.image && <div className="image-result"><img className="generated-image" src={message.image} alt={message.text} onError={event => { event.currentTarget.closest('.image-result')?.classList.add('missing'); }} /><span className="image-missing">This image file is no longer on this computer.</span><button type="button" className="image-save" onClick={() => saveImage(message.image!)}><Download size={14} /> Save image</button></div>}
              {message.sources && message.sources.length > 0 && <div className="sources"><span className="sources-label">{message.sources.some(source => source.url) ? <Globe size={12} /> : <FileText size={12} />}{L('Sources', 'ប្រភព')}</span>{message.sources.map((source, position) => source.url
                ? <a className="source" key={position} href={source.url} target="_blank" rel="noreferrer noopener" title={source.url}><b>{hostOf(source.url)}</b><span>{source.title}</span></a>
                : <span className="source source-note" key={position} title={source.file}><b><FileText size={11} />{noteName(source.file!)}</b><span dir="auto">{source.title}</span></span>)}</div>}
              {message.role === 'assistant' && !message.pending && <div className="message-actions">
                {!busy && !message.image && message.id === active.messages[active.messages.length - 1].id && <button type="button" className="copy-message" title="Ask again for a different answer" onClick={() => regenerate(message)}><RefreshCw size={13} />{L('Regenerate', 'ឆ្លើយម្តងទៀត')}</button>}
                {message.cut && !busy && message.id === active.messages[active.messages.length - 1].id && <button type="button" className="copy-message" onClick={() => void send(KHMER.test(message.text) ? 'សូមបន្តពីកន្លែងដែលអ្នកបានឈប់។' : 'Continue exactly where you left off, without repeating anything.')}><ChevronsDown size={13} />{L('Continue', 'បន្ត')}</button>}
                {message.code && message.code.changed.length > 0 && (message.code.undone
                  ? <span className="code-undone"><Undo2 size={13} />Changes undone</span>
                  : <button type="button" className="copy-message" title={`Restore ${message.code.changed.join(', ')} to how they were before this reply. Changes made by commands are not undone.`} disabled={busy} onClick={() => void undoTask(active.id, message)}><Undo2 size={13} />Undo {message.code.changed.length} file change{message.code.changed.length === 1 ? '' : 's'}</button>)}
                {message.text && !message.note && !message.plain && !message.image && !message.parts && (message.feedback
                  ? <span className="code-undone">{message.feedback === 'good' ? <ThumbsUp size={13} /> : <PencilLine size={13} />}{message.feedback === 'good' ? L('Saved as good', 'បានរក្សាទុកថាល្អ') : L('Correction saved', 'បានរក្សាទុកការកែ')}</span>
                  : <>
                    <button type="button" className="copy-message" title="Good answer: save it on this computer as a training example for Sulvana (not sent anywhere)" onClick={() => void sendFeedback(message, 'good', message.text)}><ThumbsUp size={13} />{L('Good', 'ល្អ')}</button>
                    <button type="button" className="copy-message" title="Correct this answer; the fixed version is saved on this computer for training (not sent anywhere)" onClick={() => { setImproving({ id: message.id, text: message.text }); setDialog('improve'); }}><PencilLine size={13} />{L('Improve', 'កែលម្អ')}</button>
                  </>)}
                {message.text && message.note !== 'error' && KHMER.test(message.text) && <button type="button" className={'copy-message' + (speaking?.id === message.id ? ' active' : '')}
                  title={L('Read this answer aloud (Khmer voice on this computer)', 'អានចម្លើយនេះឮៗ (សំឡេងខ្មែរនៅលើកុំព្យូទ័រនេះ)')} onClick={() => void listen(message)}>
                  {speaking?.id === message.id && speaking.state === 'loading' ? <LoaderCircle size={13} className="spin" /> : speaking?.id === message.id ? <Square size={11} fill="currentColor" /> : <Volume2 size={13} />}
                  {speaking?.id === message.id && speaking.state === 'playing' ? L('Stop', 'ឈប់') : L('Listen', 'ស្តាប់')}</button>}
                {message.text && message.note !== 'error' && <button type="button" className="copy-message" onClick={() => void copyMessage(message)}>{copiedId === message.id ? <Check size={13} /> : <Copy size={13} />}{copiedId === message.id ? L('Copied', 'បានចម្លង') : L('Copy', 'ចម្លង')}</button>}
                {(failed || (message.note === 'stopped' && (!message.text || message.text === NOTE_TEXT.stopped))) && <button type="button" className="copy-message" onClick={() => retry(message)}><RotateCcw size={13} />{L('Edit and retry', 'កែ ហើយសាកម្តងទៀត')}</button>}
              </div>}
            </article>;
          })}
          <div ref={bottom} />
          {!atBottom && <button type="button" className="jump-latest" onClick={() => { followReply.current = true; setAtBottom(true); bottom.current?.scrollIntoView({ block: 'end', behavior: 'smooth' }); }}><ArrowDown size={14} />{L('Latest', 'ចុងក្រោយ')}</button>}
        </div>}
      </div>
      <div className="composer-wrap" ref={composerWrap}>
        {engineDown && <div className="engine-banner" role="alert">
          <TriangleAlert size={18} aria-hidden="true" />
          <div>
            <strong>{status.state === 'offline' ? (isRemoteWeb && !remoteConfig.tunnel ? 'Connect to your laptop' : 'Sulvana is offline') : 'Sulvana’s engine stopped'}</strong>
            <span>
              {isRemoteWeb && !remoteConfig.tunnel
                ? 'Enter your laptop tunnel URL and access key in Settings, or open Sulvana with an invite link.'
                : (status.detail || 'The model is not running.')}
            </span>
          </div>
          {isRemote ? (
            <button type="button" onClick={() => setDialog('settings')}>Settings</button>
          ) : (
            <button type="button" onClick={() => void restartEngine()} disabled={restarting}>{restarting ? 'Restarting…' : 'Restart engine'}</button>
          )}
        </div>}
        <div className="composer">
          {attached && <div className="attached-preview"><img src={attached.data} alt="" /><span>{attached.name}</span><button type="button" onClick={() => { setAttached(null); focusComposer(); }} title="Remove image" aria-label={`Remove ${attached.name}`}><X size={13} /></button></div>}
          <textarea ref={composer} value={input} aria-label="Message Sulvana" onChange={event => setInput(event.target.value)}
            onKeyDown={event => {
              if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void send(); }
              else if (event.key === 'Escape' && busy) { event.preventDefault(); stop(); }
            }}
            onPaste={event => {
              const image = Array.from(event.clipboardData?.files || []).find(file => file.type.startsWith('image/'));
              if (image) { event.preventDefault(); void attachFile(image); }
            }}
            placeholder={L('Message Sulvana', 'សរសេរសារទៅ Sulvana…')} rows={1} dir="auto" />
          <div className="composer-actions">
            <div>
              <input ref={fileInput} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={event => { void attachFile(event.target.files?.[0]); event.target.value = ''; }} />
              <button type="button" className="chip-button" onClick={selectImage} title="Attach an image" disabled={busy}><Paperclip size={15} /> {L('Attach', 'ភ្ជាប់')}</button>
              <button type="button" className="chip-button" onClick={() => { setInput(value => value.startsWith('/image') ? value : '/image ' + value); focusComposer(); }} title="Create an image" disabled={busy}><Sparkles size={15} /> {L('Image', 'រូបភាព')}</button>
              <button type="button" className={'chip-button toggle' + (searchOn ? ' on' : '')} aria-pressed={searchOn} onClick={() => { setSearchOn(value => !value); focusComposer(); }} title="Search the web for this message" disabled={busy}><Globe size={15} /> {L('Search', 'ស្វែងរក')}</button>
              {!isRemote && <button type="button" className={'chip-button toggle' + (preferences.code ? ' on' : '')} aria-pressed={preferences.code} onClick={() => {
                if (isRemote) {
                  setNotice({ kind: 'info', text: 'Coding mode is disabled remotely to protect your laptop files.' });
                  return;
                }
                if (!preferences.code && !preferences.codeRoot) { setPreferences(current => ({ ...current, code: true })); void chooseProject(); }
                else setPreferences(current => ({ ...current, code: !current.code }));
                focusComposer();
              }} title={isRemote ? 'Coding mode is disabled remotely' : 'Coding mode: let Sulvana read and change files in a project folder'} disabled={busy}><Code size={15} /> {L('Code', 'កូដ')}</button>}
              {preferences.code && !isRemote && <button type="button" className="chip-button project-chip" onClick={() => void chooseProject()} title={preferences.codeRoot ? `Project: ${preferences.codeRoot} — click to change` : 'Choose a project folder'} disabled={busy}><FolderCode size={15} /> {projectName || 'Choose folder'}</button>}
              <button type="button" className={'chip-button toggle' + (preferences.reasoning ? ' on' : '')} aria-pressed={preferences.reasoning} onClick={() => { setPreferences(current => ({ ...current, reasoning: !current.reasoning })); focusComposer(); }} title="Think step by step before answering" disabled={busy}><Brain size={15} /> {L('Reason', 'គិតលម្អិត')}</button>
            </div>
            {busy
              ? <button type="button" className="send-button stop" onClick={stop} title="Stop (Esc)" aria-label="Stop"><Square size={11} fill="currentColor" /></button>
              : <button type="button" className="send-button" onClick={() => void send()} disabled={(!input.trim() && !attached) || !ready} title={ready ? 'Send (Enter)' : 'Sulvana is not ready yet'} aria-label="Send"><ArrowUp size={18} /></button>}
          </div>
        </div>
        {notice && <div className={'inline-notice ' + notice.kind} role={notice.kind === 'error' ? 'alert' : 'status'}><span>{notice.text}</span><button type="button" onClick={() => setNotice(null)} aria-label="Dismiss message"><X size={14} /></button></div>}
        {storageError && <div className="inline-notice error" role="alert"><span>Conversation history could not be saved. Storage may be full — delete old conversations to free space.</span></div>}
        <div className="composer-note">{composerHint}</div>
      </div>
    </main>
    {dialog === 'settings' && <Modal title={L('Settings', 'ការកំណត់')} onClose={() => setDialog(null)} className="settings-backdrop">
      <div className="settings-layout">
        <nav className="settings-nav" role="tablist" aria-label={L('Settings sections', 'ផ្នែកការកំណត់')}>
          {SETTINGS_TABS.map(tab => <button type="button" key={tab.id} role="tab" id={'settings-tab-' + tab.id} aria-selected={settingsTab === tab.id}
            aria-controls="settings-pane" className={'settings-tab tint-' + tab.tint} onClick={() => setSettingsTab(tab.id)}>
            <span className="settings-tab-icon"><tab.icon size={16} /></span><span>{L(tab.en, tab.km)}</span></button>)}
        </nav>
        <div className="settings-pane" id="settings-pane" role="tabpanel" aria-labelledby={'settings-tab-' + settingsTab} key={settingsTab}>
          {(() => { const tab = SETTINGS_TABS.find(item => item.id === settingsTab)!; return <header className="pane-head">
            <span className={'pane-icon tint-' + tab.tint}><tab.icon size={22} /></span>
            <div><h3>{L(tab.en, tab.km)}</h3><p>{L(tab.aboutEn, tab.aboutKm)}</p></div>
          </header>; })()}

          {settingsTab === 'you' && <>
            <div className="greeting-preview" aria-hidden="true">
              <span className="greeting-dot" />{L('Sulvana will greet you with', 'Sulvana នឹងស្វាគមន៍អ្នកថា')} <b dir="auto">{greeting(preferences.uiLanguage, preferences.userName)}</b>
            </div>
            <div className="form-group">
              <div className="form-row stacked">
                <label htmlFor="setting-name">{L('What should Sulvana call you?', 'តើ Sulvana គួរហៅអ្នកថាអ្វី?')}</label>
                <input id="setting-name" type="text" maxLength={60} data-autofocus placeholder={L('Your name or nickname', 'ឈ្មោះ ឬឈ្មោះហៅក្រៅរបស់អ្នក')} value={preferences.userName}
                  onChange={event => setPreferences(current => ({ ...current, userName: event.target.value }))} />
              </div>
              <div className="form-row stacked">
                <label htmlFor="setting-about">{L('About you', 'អំពីអ្នក')}</label>
                <textarea id="setting-about" rows={2} maxLength={600} dir="auto" placeholder={L('For example: Grade 8 student at Sisowath High School; I like science.', 'ឧទាហរណ៍៖ សិស្សថ្នាក់ទី៨ នៅវិទ្យាល័យព្រះស៊ីសុវត្ថិ ចូលចិត្តវិទ្យាសាស្ត្រ។')}
                  value={preferences.aboutUser} onChange={event => setPreferences(current => ({ ...current, aboutUser: event.target.value }))} />
              </div>
              <div className="form-row">
                <label htmlFor="setting-style">{L('Answer style', 'របៀបឆ្លើយ')}</label>
                <select id="setting-style" value={preferences.responseStyle} onChange={event => setPreferences(current => ({ ...current, responseStyle: event.target.value as ResponseStyle }))}>
                  {RESPONSE_STYLES.map(style => <option key={style} value={style}>{{
                    normal: L('Normal', 'ធម្មតា'), concise: L('Short', 'ខ្លី'), detailed: L('Detailed, like a teacher', 'លម្អិត ដូចគ្រូបង្រៀន'),
                    formal: L('Formal', 'ផ្លូវការ'), friendly: L('Friendly', 'រាក់ទាក់') }[style]}</option>)}
                </select>
              </div>
              <div className="form-row stacked">
                <label htmlFor="setting-instructions">{L('How should Sulvana answer?', 'តើ Sulvana គួរឆ្លើយបែបណា?')}</label>
                <textarea id="setting-instructions" rows={2} maxLength={1500} dir="auto" placeholder={L('For example: use simple words and give one example each time.', 'ឧទាហរណ៍៖ ប្រើពាក្យងាយៗ ហើយផ្ដល់ឧទាហរណ៍មួយរាល់ពេល។')}
                  value={preferences.instructions} onChange={event => setPreferences(current => ({ ...current, instructions: event.target.value }))} />
              </div>
            </div>
            <h4 className="pane-subhead">{L('Memory', 'ការចងចាំ')} <span className="count-pill">{preferences.memories.length}/30</span></h4>
            <div className="form-group">
              <div className="form-row stacked">
                {preferences.memories.length === 0
                  ? <p className="empty-memories">{L('Nothing saved yet. Say "remember that …" in any chat, and it is kept here and used in every chat.', 'មិនទាន់មានអ្វីត្រូវបានរក្សាទុកទេ។ និយាយថា «ចងចាំថា …» ក្នុងការសន្ទនាណាមួយ វានឹងត្រូវរក្សាទុកនៅទីនេះ ហើយប្រើក្នុងគ្រប់ការសន្ទនា។')}</p>
                  : <ul className="memory-list" aria-label={L('Memory', 'ការចងចាំ')}>{preferences.memories.map((memory, position) => <li key={position} dir="auto">
                    <span>{memory}</span>
                    <button type="button" aria-label={L('Forget this', 'បំភ្លេចវា')} title={L('Forget this', 'បំភ្លេចវា')}
                      onClick={() => setPreferences(current => ({ ...current, memories: current.memories.filter((_, index) => index !== position) }))}><X size={13} /></button>
                  </li>)}</ul>}
              </div>
            </div>
            <p className="form-note">{L('Kept only in this app. Sulvana gets these with every message.', 'រក្សាទុកតែនៅក្នុងកម្មវិធីនេះប៉ុណ្ណោះ។ Sulvana ទទួលបានព័ត៌មានទាំងនេះជាមួយសាររាល់ពេល។')}</p>
          </>}

          {settingsTab === 'answers' && <>
            <h4 className="pane-subhead">{L('Khmer tools', 'ឧបករណ៍ភាសាខ្មែរ')}</h4>
            <div className="choice-cards" role="radiogroup" aria-label={L('Khmer tools', 'ឧបករណ៍ភាសាខ្មែរ')}>
              {([['local', ShieldCheck, L('This computer', 'កុំព្យូទ័រនេះ'), L('Private. Nothing leaves your laptop.', 'ឯកជន។ គ្មានអ្វីចេញពីកុំព្យូទ័រទេ។')],
                ['google', Globe, 'Google', L('Most accurate, but your Khmer is sent to Google.', 'ត្រឹមត្រូវបំផុត ប៉ុន្តែភាសាខ្មែររបស់អ្នកត្រូវបានផ្ញើទៅ Google។')],
                ['off', PencilLine, L('Off', 'បិទ'), L('Sulvana writes Khmer itself, with more mistakes.', 'Sulvana សរសេរខ្មែរដោយខ្លួនឯង មានកំហុសច្រើនជាង។')]] as const).map(([choice, Icon, name, about]) =>
                <button type="button" key={choice} role="radio" aria-checked={preferences.translate === choice} className="choice-card"
                  onClick={() => setPreferences(current => ({ ...current, translate: choice, translateAsked: true }))}>
                  <span className="choice-icon"><Icon size={18} /></span><b>{name}</b><small>{about}</small>
                </button>)}
            </div>
            <div className="form-group">
              <div className="form-row">
                <label htmlFor="setting-language">{L('Reply language', 'ភាសាឆ្លើយតប')}</label>
                <select id="setting-language" value={customLanguage ? '__other' : preferences.language} onChange={event => {
                  const other = event.target.value === '__other';
                  setCustomLanguage(other);
                  setPreferences(current => ({ ...current, language: other ? '' : event.target.value }));
                }}>
                  {LANGUAGES.map(language => <option key={language} value={language}>{language === 'Auto' ? L('Automatic (Khmer first)', 'ស្វ័យប្រវត្តិ (ខ្មែរជាមុន)') : language}</option>)}
                  <option value="__other">{L('Other…', 'ផ្សេងទៀត…')}</option>
                </select>
              </div>
              {customLanguage && <div className="form-row">
                <input type="text" aria-label="Other reply language" maxLength={80} placeholder="Language name, for example Deutsch" value={preferences.language}
                  onChange={event => setPreferences(current => ({ ...current, language: event.target.value }))} />
              </div>}
              <div className="form-row">
                <span id="setting-auto-search" className="row-label">{L('Search when unsure', 'ស្វែងរកពេលមិនច្បាស់')}<small>{L('Looks facts up on the web first and lists the sources', 'ស្វែងរកតាមអ៊ីនធឺណិតជាមុន ហើយបង្ហាញប្រភព')}</small></span>
                <button type="button" role="switch" className="switch" aria-checked={preferences.autoSearch} aria-labelledby="setting-auto-search"
                  onClick={() => setPreferences(current => ({ ...current, autoSearch: !current.autoSearch }))} />
              </div>
              <div className="form-row stacked">
                <label htmlFor="setting-creativity">{L('Creativity', 'ភាពច្នៃប្រឌិត')} <span>{preferences.temperature <= 0.5 ? L('Precise', 'ច្បាស់លាស់') : preferences.temperature <= 0.9 ? L('Balanced', 'មធ្យម') : L('Creative', 'ច្នៃប្រឌិត')} · {preferences.temperature.toFixed(1)}</span></label>
                <input id="setting-creativity" type="range" min="0.1" max="1.5" step="0.1" value={preferences.temperature} style={{ '--range-fill': rangeFill } as CSSProperties}
                  onChange={event => setPreferences(current => ({ ...current, temperature: Number(event.target.value) }))} />
                <div className="range-ends"><span>{L('Precise', 'ច្បាស់លាស់')}</span><span>{L('Creative', 'ច្នៃប្រឌិត')}</span></div>
              </div>
              <div className="form-row">
                <label htmlFor="setting-length">{L('Maximum reply length', 'ប្រវែងចម្លើយ')}</label>
                <select id="setting-length" value={preferences.maxTokens} onChange={event => setPreferences(current => ({ ...current, maxTokens: Number(event.target.value) }))}>
                  {TOKEN_LIMITS.map(value => <option key={value} value={value}>{uiLanguage === 'km' ? LENGTH_NAMES_KM[value] : LENGTH_NAMES[value]}</option>)}
                </select>
              </div>
              <div className="form-row">
                <label htmlFor="setting-model">{L('Model', 'ម៉ូដែល')}</label>
                <select id="setting-model" value={models?.current || 'sulvana-2.0'} disabled={!models || busy} onChange={event => void switchModel(event.target.value)}>
                  {(models?.models || [{ id: 'sulvana-2.0', label: 'Sulvana 2.0', detail: '', available: true }]).map(choice =>
                    <option key={choice.id} value={choice.id} disabled={!choice.available}>{choice.label}{choice.available ? '' : ' (not downloaded)'}</option>)}
                </select>
              </div>
              {models && <p className="form-note model-note">{models.models.find(m => m.id === (models.current || 'sulvana-2.0'))?.detail}</p>}
              {!isRemote && <div className="form-row stacked">
                <label htmlFor="setting-project">{L('Coding project folder', 'ថតគម្រោងកូដ')}</label>
                <div className="project-field">
                  <input id="setting-project" type="text" spellCheck={false} placeholder="/home/you/projects/my-app" value={preferences.codeRoot}
                    onChange={event => setPreferences(current => ({ ...current, codeRoot: event.target.value.slice(0, 1000) }))} />
                  {window.sulvanaElectron && <button type="button" onClick={() => void chooseProject()}>Choose…</button>}
                </div>
              </div>}
            </div>
          </>}

          {settingsTab === 'look' && <>
            <div className={'look-preview bubbles-' + preferences.bubbleStyle} data-text-size={preferences.textSize} aria-hidden="true">
              <div className="preview-user">{L('How my crush?', 'ក្រាសខ្ញុំសុខសប្បាយទេ?')}</div>
              <div className="preview-bot"><span className="preview-name">Sulvana</span>{L('How would I know? Go ask them yourself!', 'ខ្ញុំដឹងម៉េចបាន? ទៅសួរគាត់ដោយខ្លួនឯងទៅ!')}</div>
            </div>
            <h4 className="pane-subhead">{L('Theme', 'រូបរាង')}</h4>
            <div className="theme-grid" role="radiogroup" aria-label={L('Base theme', 'រូបរាងមូលដ្ឋាន')}>
              {THEMES.map(theme => <button type="button" key={theme.id} role="radio" aria-checked={preferences.theme === theme.id}
                className={`theme-card theme-${theme.id} ${preferences.theme === theme.id ? 'active' : ''}`}
                onClick={() => setPreferences(current => ({ ...current, theme: theme.id }))}>
                <span className="theme-mini" style={{ background: theme.color, borderColor: theme.border }}>
                  <span className="mini-side" style={{ background: theme.border }} />
                  <span className="mini-bubble" />
                  <span className="mini-line" style={{ background: theme.border }} />
                </span>
                <span className="theme-name">{L(theme.nameEn, theme.nameKm)}</span>
              </button>)}
            </div>
            <h4 className="pane-subhead">{L('Accent colour', 'ពណ៌សង្កត់')}</h4>
            <div className="accent-palette" role="radiogroup" aria-label={L('Accent color', 'ពណ៌សង្កត់')}>
              {ACCENT_PRESETS.map(accent => {
                const active = preferences.accent === accent.id;
                return <button type="button" key={accent.id} role="radio" aria-checked={active} className={`accent-chip ${active ? 'active' : ''}`}
                  onClick={() => setPreferences(current => ({ ...current, accent: accent.id }))} title={L(accent.nameEn, accent.nameKm)}>
                  <span className="accent-chip-inner" style={{ backgroundColor: accent.color }}>{active && <Check size={14} color="#FFFFFF" strokeWidth={3} />}</span>
                </button>;
              })}
              <div className={`accent-chip custom-chip ${preferences.accent === 'custom' ? 'active' : ''}`} title={L('Custom Color', 'ពណ៌ផ្ទាល់ខ្លួន')}>
                <span className="accent-chip-inner" style={{ backgroundColor: preferences.customAccent || '#8B6CF6' }}><Palette size={14} className="custom-chip-icon" /></span>
                <input type="color" className="custom-color-input" aria-label={L('Pick custom accent color', 'ជ្រើសរើសពណ៌ផ្ទាល់ខ្លួន')} value={preferences.customAccent || '#8B6CF6'}
                  onChange={event => { const val = event.target.value; setPreferences(current => ({ ...current, accent: 'custom', customAccent: val })); }} />
              </div>
            </div>
            <div className="form-group">
              <div className="form-row">
                <span id="setting-bubble-style">{L('Your chat bubbles', 'ប្រអប់សាររបស់អ្នក')}</span>
                <div className="segmented" role="radiogroup" aria-labelledby="setting-bubble-style">
                  {(['accent', 'neutral'] as const).map(style => <button type="button" key={style} role="radio" aria-checked={preferences.bubbleStyle === style}
                    onClick={() => setPreferences(current => ({ ...current, bubbleStyle: style }))}>{style === 'accent' ? L('Colourful', 'ពណ៌ចម្រុះ') : L('Neutral', 'ស្រទន់')}</button>)}
                </div>
              </div>
              <div className="form-row stacked">
                <label htmlFor="setting-ui-scale">{L('Interface size', 'ទំហំកម្មវិធី')} <span>{preferences.uiScale}%</span></label>
                <div className="scale-control">
                  <button type="button" className="scale-step" aria-label={L('Smaller', 'តូចជាងនេះ')} disabled={preferences.uiScale === UI_SCALES[0]} onClick={() => changeScale(-1)}>A−</button>
                  <input id="setting-ui-scale" type="range" min="0" max={UI_SCALES.length - 1} step="1" value={UI_SCALES.indexOf(preferences.uiScale)}
                    aria-valuetext={`${preferences.uiScale}%`}
                    style={{ '--range-fill': `${(UI_SCALES.indexOf(preferences.uiScale) / (UI_SCALES.length - 1)) * 100}%` } as CSSProperties}
                    onChange={event => { const next = UI_SCALES[Number(event.target.value)]; if (next) setPreferences(current => ({ ...current, uiScale: next })); }} />
                  <button type="button" className="scale-step big" aria-label={L('Bigger', 'ធំជាងនេះ')} disabled={preferences.uiScale === UI_SCALES[UI_SCALES.length - 1]} onClick={() => changeScale(1)}>A+</button>
                  {preferences.uiScale !== 100 && <button type="button" className="scale-reset" onClick={() => changeScale(0)}>{L('Reset', 'កំណត់ឡើងវិញ')}</button>}
                </div>
              </div>
              <div className="form-row">
                <span id="setting-text-size">{L('Chat text size', 'ទំហំអក្សរសារ')}</span>
                <div className="segmented" role="radiogroup" aria-labelledby="setting-text-size">
                  {(['small', 'default', 'large'] as const).map(size => <button type="button" key={size} role="radio" aria-checked={preferences.textSize === size}
                    onClick={() => setPreferences(current => ({ ...current, textSize: size }))}>{size === 'small' ? L('Small', 'តូច') : size === 'default' ? L('Default', 'ធម្មតា') : L('Large', 'ធំ')}</button>)}
                </div>
              </div>
              <div className="form-row">
                <span id="setting-ui-language">{L('Interface language', 'ភាសាកម្មវិធី')}</span>
                <div className="segmented" role="radiogroup" aria-labelledby="setting-ui-language">
                  {(['km', 'en'] as const).map(language => <button type="button" key={language} role="radio" aria-checked={preferences.uiLanguage === language}
                    onClick={() => setPreferences(current => ({ ...current, uiLanguage: language }))}>{language === 'km' ? 'ខ្មែរ' : 'English'}</button>)}
                </div>
              </div>
            </div>
            <p className="form-note">{L('Shortcuts: Ctrl + and Ctrl − change the interface size, Ctrl 0 resets it.', 'ផ្លូវកាត់៖ Ctrl + និង Ctrl − ប្តូរទំហំកម្មវិធី, Ctrl 0 កំណត់ឡើងវិញ។')}</p>
          </>}

          {settingsTab === 'share' && <>
            <div className="share-steps">
              <div><span>1</span>{L('On the laptop, run ./share.sh', 'នៅលើកុំព្យូទ័រ ដំណើរការ ./share.sh')}</div>
              <div><span>2</span>{L('Copy the invite link it prints, or the one below', 'ចម្លងតំណអញ្ជើញដែលវាបង្ហាញ ឬតំណខាងក្រោម')}</div>
              <div><span>3</span>{L('Your friend opens it and can chat with Sulvana', 'មិត្តរបស់អ្នកបើកវា ហើយអាចជជែកជាមួយ Sulvana')}</div>
            </div>
            <div className="form-group">
              <div className="form-row stacked">
                <label htmlFor="setting-tunnel">{L('Tunnel address', 'អាសយដ្ឋានផ្លូវរូងក្រោមដី')} <span className={'link-state' + (remoteConfig.tunnel ? ' on' : '')}>{remoteConfig.tunnel ? L('Connected', 'បានភ្ជាប់') : L('This computer', 'កុំព្យូទ័រនេះ')}</span></label>
                <div className="project-field">
                  <input id="setting-tunnel" type="text" spellCheck={false} placeholder="https://xxxx.trycloudflare.com" value={tunnelInput}
                    onChange={event => setTunnelInput(event.target.value)} />
                </div>
              </div>
              <div className="form-row stacked">
                <label htmlFor="setting-key">{L('Access key', 'កូនសោចូលប្រើ')}</label>
                <div className="project-field">
                  <input id="setting-key" type="text" spellCheck={false} placeholder="Passphrase key" value={keyInput}
                    onChange={event => setKeyInput(event.target.value)} />
                  <button type="button" onClick={() => saveRemoteSettings(tunnelInput, keyInput)}>{L('Save', 'រក្សាទុក')}</button>
                  <button type="button" onClick={copyInviteLink} title="Copy invite link to share with your friend">{copiedLink ? L('Copied!', 'បានចម្លង!') : L('Copy link', 'ចម្លងតំណ')}</button>
                </div>
              </div>
            </div>
            <p className="form-note">{L('Friends can chat and search, but they cannot see your files, your computer or coding mode. You can read what they ask with ./share-logs.sh.',
              'មិត្តភក្តិអាចជជែក និងស្វែងរកបាន ប៉ុន្តែពួកគេមិនអាចមើលឯកសារ កុំព្យូទ័រ ឬរបៀបសរសេរកូដរបស់អ្នកបានទេ។ អ្នកអាចអានអ្វីដែលពួកគេសួរ ដោយប្រើ ./share-logs.sh។')}</p>
          </>}

          {settingsTab === 'about' && <>
            <div className="about-hero">
              <img src={isLightTheme(preferences.theme) ? WKH_MARK_LIGHT : WKH_MARK_DARK} alt="WKH Labs" />
              <div><strong>{modelName}</strong><span>{L('by WKH Labs · Wisdom · Khmer · Heritage', 'ដោយ WKH Labs · ប្រាជ្ញា · ខ្មែរ · បេតិកភណ្ឌ')}</span>
                {baseModel && <span>{L('Built on', 'បង្កើតលើ')} {baseModel}</span>}</div>
            </div>
            <div className="team-row">
              <span className="team-chip lead">Han<small>{L('made it', 'អ្នកបង្កើត')}</small></span>
              <span className="team-chip">Nisa<small>WKH</small></span>
              <span className="team-chip">Wanyu<small>WKH</small></span>
            </div>
            <h4 className="pane-subhead"><Keyboard size={15} /> {L('Keyboard shortcuts', 'ផ្លូវកាត់ក្តារចុច')}</h4>
            <div className="shortcut-list">
              {([['Enter', L('Send', 'ផ្ញើ')], ['Shift + Enter', L('New line', 'បន្ទាត់ថ្មី')], ['Esc', L('Stop a reply', 'បញ្ឈប់ចម្លើយ')],
                ['Ctrl + N', L('New chat', 'ការសន្ទនាថ្មី')], ['Ctrl + K', L('Search chats', 'ស្វែងរកការសន្ទនា')], ['Ctrl + ,', L('Settings', 'ការកំណត់')],
                ['Ctrl + Shift + E', L('Export this chat', 'នាំចេញការសន្ទនានេះ')], ['Ctrl + / Ctrl −', L('Interface size', 'ទំហំកម្មវិធី')]] as const).map(([keys, action]) =>
                <div key={keys}><span>{action}</span><kbd>{keys}</kbd></div>)}
            </div>
            <p className="form-note">{L('Sulvana runs on this computer and can make mistakes. Check important answers.', 'Sulvana ដំណើរការលើកុំព្យូទ័រនេះ ហើយអាចឆ្លើយខុស។ សូមពិនិត្យចម្លើយសំខាន់ៗ។')}</p>
          </>}
        </div>
      </div>
      <div className="modal-actions spread">
        <button type="button" onClick={() => { setPreferences(current => ({ ...DEFAULT_PREFERENCES, theme: current.theme, accent: current.accent, customAccent: current.customAccent, bubbleStyle: current.bubbleStyle, translate: current.translate, translateAsked: current.translateAsked, uiLanguage: current.uiLanguage,
          userName: current.userName, aboutUser: current.aboutUser, instructions: current.instructions, responseStyle: current.responseStyle, memories: current.memories })); setCustomLanguage(false); }}>{L('Reset to Defaults', 'កំណត់ដើមវិញ')}</button>
        <button type="button" className="approve-button" onClick={() => setDialog(null)}>{L('Done', 'រួចរាល់')}</button>
      </div>
    </Modal>}
    {dialog === 'tools' && <Modal title={L('Tools', 'ឧបករណ៍')} onClose={() => setDialog(null)}>
      <p>Sulvana can search local Markdown guides, search the public web when you ask, and run a small set of read only checks on this computer.</p>
      <div className="form-group">
        <div className="form-row"><span>Local documentation</span><em>Available</em></div>
        <div className="form-row"><span>{L('Public web search', 'ស្វែងរកតាមអ៊ីនធឺណិត')}</span><em className="online">{preferences.autoSearch ? L('Online · when asked or unsure', 'អនឡាញ · ពេលសួរ ឬមិនច្បាស់') : L('Online · when asked', 'អនឡាញ · ពេលសួរ')}</em></div>
        <div className="form-row"><span>{L('Read a link you send', 'អានតំណដែលអ្នកផ្ញើ')}</span><em className="online">{L('Online · when you send a link', 'អនឡាញ · ពេលផ្ញើតំណ')}</em></div>
        <div className="form-row"><span>{L('Calculator and Khmer number words', 'ម៉ាស៊ីនគិតលេខ និងលេខជាពាក្យខ្មែរ')}</span><em>/calc · /number</em></div>
        <div className="form-row"><span>{L('Khmer tools', 'ឧបករណ៍ភាសាខ្មែរ')}</span><em className={preferences.translate === 'google' ? 'online' : ''}>{preferences.translate === 'google' ? 'Online · Google' : preferences.translate === 'local' ? 'On this computer' : 'Off'}</em></div>
        <div className="form-row"><span>Read only terminal checks</span><em>Limited</em></div>
        <div className="form-row"><span>Coding mode (one project folder)</span><em>Asks first</em></div>
      </div>
      <p className="form-note">With <b>Code</b> on, Sulvana works in the project folder you chose: it reads and searches files on its own, but shows every edit as a diff and every command before it runs. Commands run in a sandbox with no network that can only change the project folder. Each reply's file edits can be undone.</p>
      <p className="form-note">Try <code>/calc 50000 - 3*8500</code>, <code>/number 37450</code>, <code>/search your question</code>, <code>/docs your topic</code>, or <code>/terminal nvidia-smi</code>. Paste a link into a message and Sulvana reads that page. Some extra read only inspections ask for one-time permission and show the exact command. File changes, installs, and arbitrary commands are blocked.</p>
      <div className="modal-actions"><button type="button" className="approve-button" onClick={() => setDialog(null)}>{L('Done', 'រួចរាល់')}</button></div>
    </Modal>}
    {dialog === 'improve' && improving && <Modal title="Improve this answer" onClose={() => { setDialog(null); setImproving(null); }} className="improve-backdrop">
      <p>Fix spelling, facts or wording, then save. The corrected answer is stored as a training example for the next fine-tune.</p>
      <textarea className="improve-text" data-autofocus dir="auto" value={improving.text} onChange={event => setImproving({ ...improving, text: event.target.value })} />
      <div className="modal-actions">
        <button type="button" onClick={() => { setDialog(null); setImproving(null); }}>Cancel</button>
        <button type="button" className="approve-button" disabled={!improving.text.trim()} onClick={() => {
          const message = active.messages.find(item => item.id === improving.id);
          if (message) void sendFeedback(message, 'corrected', improving.text.trim());
          setDialog(null); setImproving(null);
        }}>Save correction</button>
      </div>
    </Modal>}
    {dialog === 'delete' && <Modal title="Delete conversation?" alert onClose={() => { setDialog(null); setDeleteId(null); }}>
      <p>This removes “{conversations.find(chat => chat.id === deleteId)?.title || 'this conversation'}” and its chat history. Generated image files remain on disk.</p>
      <div className="modal-actions"><button type="button" data-autofocus onClick={() => { setDialog(null); setDeleteId(null); }}>Cancel</button><button type="button" className="danger-button" onClick={confirmDelete}>Delete</button></div>
    </Modal>}
    {approval && approval.kind && approval.kind !== 'read' && <Modal title={approval.kind === 'command' ? 'Run this command?' : approval.title || 'Allow this change?'} className="approval-backdrop code-approval" alert dismissible={false} onClose={() => void decideApproval('deny')}>
      {approval.kind === 'command'
        ? <><p>Sulvana wants to run this in <b>{projectName || 'your project'}</b>.</p><pre className="approval-command" tabIndex={0}>{approval.command}</pre></>
        : <><p>Sulvana wants to {approval.diff?.startsWith('--- /dev/null') ? 'create' : 'change'} <b>{approval.command}</b>.</p>{approval.diff && <DiffView text={approval.diff.split('\n').slice(2).join('\n')} />}</>}
      {approval.reason && <p className="approval-reason">{approval.reason}</p>}
      {approvalError && <div className="inline-notice error" role="alert"><span>{approvalError}</span></div>}
      <div className="modal-actions">
        <button type="button" data-autofocus disabled={approvalSubmitting} onClick={() => void decideApproval('deny')}>Deny</button>
        {approval.allow_all && <button type="button" disabled={approvalSubmitting} onClick={() => void decideApproval('allow_all')}>{approval.kind === 'command' ? 'Always allow this command' : 'Allow all edits'}</button>}
        <button type="button" className="approve-button" disabled={approvalSubmitting} onClick={() => void decideApproval('allow')}>{approval.kind === 'command' ? 'Run' : 'Allow'}</button>
      </div>
      {approval.allow_all && <p className="approval-expiry">{approval.kind === 'command' ? '“Always” lasts until this reply ends.' : '“Allow all edits” lasts until this reply ends.'} Escape denies.</p>}
    </Modal>}
    {approval && (!approval.kind || approval.kind === 'read') && <Modal title="Allow this read only check?" className="approval-backdrop" alert dismissible={false} onClose={() => void decideApproval('deny')}>
      <p>Sulvana wants to inspect this computer with one command. Permission applies only to this request.</p>
      <pre className="approval-command" tabIndex={0}>{approval.command}</pre>
      {approval.reason && <p className="approval-reason">Reason: {approval.reason}</p>}
      <p className="approval-expiry">This request expires in {approval.timeout_seconds || 60} seconds. Escape denies it.</p>
      {approvalError && <div className="inline-notice error" role="alert"><span>{approvalError}</span></div>}
      <div className="modal-actions">
        <button type="button" data-autofocus disabled={approvalSubmitting} onClick={() => void decideApproval('deny')}>Deny</button>
        <button type="button" className="approve-button" disabled={approvalSubmitting} onClick={() => void decideApproval('allow')}>Allow Once</button>
      </div>
    </Modal>}
  </div>;
}
