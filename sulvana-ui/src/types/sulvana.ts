export type HardwareStatusState =
  | 'ready'
  | 'loading_model'
  | 'streaming'
  | 'generating_image'
  | 'vram_warning'
  | 'error_backend'
  | 'error_model_missing';

export type ReplyLanguage =
  | 'Auto-detect'
  | 'English'
  | 'ខ្មែរ (Khmer)'
  | 'العربية (Arabic)'
  | '中文 (Chinese)'
  | '日本語 (Japanese)';

export interface LocalModel {
  id: string;
  name: string;
  quantization: string;
  capabilities: ('chat' | 'vision' | 'image-gen' | 'code')[];
  vramRequiredGb: number;
  sizeGb: number;
  speedTokPerSec: number;
  installed: boolean;
  description: string;
  languagesSupported: string[];
}

export interface VisionAttachment {
  id: string;
  name: string;
  url: string;
  dimensions: string;
  sizeLabel: string;
}

export interface GeneratedImagePayload {
  prompt: string;
  imageUrl?: string;
  resolution: string;
  stepsTotal: number;
  currentStep: number;
  seed: number;
  modelName: string;
  status: 'generating' | 'completed' | 'failed';
  generationTimeSec?: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system_notice';
  content: string;
  timestamp: string;
  direction?: 'ltr' | 'rtl';
  scriptLabel?: string;
  attachments?: VisionAttachment[];
  generatedImage?: GeneratedImagePayload;
  isStreaming?: boolean;
  tokensPerSec?: number;
  totalTokens?: number;
  modelUsed?: string;
  errorState?: {
    title: string;
    explanation: string;
    recoveryActionLabel: string;
    recoveryType: 'retry' | 'switch_cpu_split' | 'open_downloads';
  };
}

export interface Conversation {
  id: string;
  title: string;
  updatedAt: string;
  scriptBadge?: string;
  pinned?: boolean;
  messages: ChatMessage[];
}

export type DownloadItemStatus =
  | 'downloading'
  | 'paused'
  | 'completed'
  | 'available'
  | 'failed';

export interface DownloadModelItem {
  id: string;
  name: string;
  family: string;
  quantization: string;
  format: 'GGUF' | 'Safetensors';
  totalSizeGb: number;
  downloadedGb: number;
  percent: number;
  speedMbPerSec: number;
  etaText: string;
  status: DownloadItemStatus;
  capabilities: ('chat' | 'vision' | 'image-gen' | 'code')[];
  description: string;
  recommendedVramGb: number;
  errorReason?: string;
}

export interface SulvanaSettings {
  replyLanguage: ReplyLanguage;
  temperature: number;
  maxResponseLength: 512 | 1024 | 2048 | 4096 | 8192;
  theme: 'dark' | 'light';
  gpuLayersOffload: 'auto' | 'gpu_only' | 'cpu_fallback';
  compactWindowMode: boolean;
}
