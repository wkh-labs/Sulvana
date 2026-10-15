import { useState, useEffect, useRef } from 'react';
import {
  ChatMessage,
  Conversation,
  DownloadModelItem,
  HardwareStatusState,
  LocalModel,
  ReplyLanguage,
  SulvanaSettings,
  VisionAttachment,
} from './types/sulvana';
import {
  INITIAL_CONVERSATIONS,
  INITIAL_DOWNLOAD_ITEMS,
  LOCAL_MODELS,
} from './data/initialData';
import { TopStatusBar } from './components/TopStatusBar';
import { SidebarRail } from './components/SidebarRail';
import { MessageStream } from './components/MessageStream';
import { MessageComposer } from './components/MessageComposer';
import { DownloadsModal } from './components/DownloadsModal';
import { SettingsModal } from './components/SettingsModal';
import { DesignSpecModal } from './components/DesignSpecModal';

function detectScriptAndDirection(
  text: string,
  preferredLang: ReplyLanguage
): { direction: 'ltr' | 'rtl'; scriptLabel?: string } {
  if (/[\u0600-\u06FF]/.test(text) || preferredLang === 'العربية (Arabic)') {
    return { direction: 'rtl', scriptLabel: 'العربية (Arabic — RTL)' };
  }
  if (/[\u1780-\u17FF]/.test(text) || preferredLang === 'ខ្មែរ (Khmer)') {
    return { direction: 'ltr', scriptLabel: 'ខ្មែរ (Khmer)' };
  }
  if (/[\u3040-\u30FF]/.test(text) || preferredLang === '日本語 (Japanese)') {
    return { direction: 'ltr', scriptLabel: '日本語 (Japanese)' };
  }
  if (/[\u4E00-\u9FFF]/.test(text) || preferredLang === '中文 (Chinese)') {
    return { direction: 'ltr', scriptLabel: '中文 (Chinese)' };
  }
  return { direction: 'ltr' };
}

function buildContextualAssistantReply(
  prompt: string,
  attachments: VisionAttachment[],
  replyLanguage: ReplyLanguage,
  model: LocalModel,
  temperature: number
): { text: string; direction: 'ltr' | 'rtl'; scriptLabel?: string } {
  const lower = prompt.toLowerCase();

  // 1. Check if Arabic script in prompt or Reply Language set to Arabic
  if (/[\u0600-\u06FF]/.test(prompt) || replyLanguage === 'العربية (Arabic)') {
    return {
      direction: 'rtl',
      scriptLabel: 'العربية (Arabic — RTL)',
      text: `### إجابة محلية خاصة عبر ${model.name}

تمت معالجة رسالتك بالكامل داخل ذاكرة البطاقة الرسومية (**${model.vramRequiredGb} GB VRAM**) دون أي اتصال بالإنترنت:

- **حماية الخصوصية الكاملة**: لا تغادر ملفاتك أو محادثاتك جهازك الشخصي أبداً.
- **دعم اللغة العربية (RTL)**: يتم ضبط اتجاه الفقرات تلقائياً من اليمين إلى اليسار مع الحفاظ على اتصال الحروف ووضوح الخط عند ارتفاع سطر \`1.65\`.
- **درجة الإبداع الحالية (Temperature)**: مضبوطة على \`${temperature.toFixed(1)}\` لضمان إجابات دقيقة ومتوازنة.`,
    };
  }

  // 2. Check if Khmer script in prompt or Reply Language set to Khmer
  if (/[\u1780-\u17FF]/.test(prompt) || replyLanguage === 'ខ្មែរ (Khmer)') {
    return {
      direction: 'ltr',
      scriptLabel: 'ខ្មែរ (Khmer)',
      text: `### ការឆ្លើយតបពីប្រព័ន្ធម៉ាស៊ីនផ្ទាល់ខ្លួន (${model.name})

សំណួររបស់អ្នកត្រូវបានវិភាគដោយផ្ទាល់នៅលើកុំព្យូទ័ររបស់អ្នក ដោយប្រើប្រាស់អង្គចងចាំក្រាហ្វិក **${model.vramRequiredGb} GB VRAM**៖

- **សុវត្ថិភាពនិងឯកជនភាព**: ទិន្នន័យទាំងអស់ស្ថិតនៅក្នុងម៉ាស៊ីនរបស់អ្នកជានិច្ច មិនមានការបញ្ជូនចេញទៅក្រៅឡើយ។
- **ការរចនាសម្រាប់អក្សរខ្មែរ**: កម្មវិធី **Sulvana** រក្សាគម្លាតបន្ទាត់ \`1.65\` ដើម្បីឱ្យតួអក្សរខ្មែរ ស្រៈ និងជើងអក្សរបង្ហាញបានច្បាស់ល្អ ងាយស្រួលអានក្នុងរយៈពេលយូរ។`,
    };
  }

  // 3. Check if Multi-Script showcase prompt
  if (lower.includes('khmer') && lower.includes('arabic') && lower.includes('japanese')) {
    return {
      direction: 'ltr',
      scriptLabel: 'Multi-Script UTF-8',
      text: `### Multi-Script Typography & Local Privacy Verification

Sulvana renders complex scripts simultaneously with \`line-height: 1.65\` and zero artificial letter-spacing:

- **ខ្មែរ (Khmer)**: ប្រព័ន្ធ AI ក្នុងម៉ាស៊ីនផ្ទាល់ខ្លួន រក្សាការសម្ងាត់ទិន្នន័យរបស់អ្នក ១០០% ដោយមិនប្រើអ៊ីនធឺណិត។
- **العربية (Arabic)**: يعمل نموذج الذكاء الاصطناعي محلياً على جهازك لضمان الخصوصية التامة وسرعة الاستجابة.
- **日本語 (Japanese)**: すべての推論と画像生成はお使いのGPU上でローカルに実行され、外部に送信されません。
- **中文 (Chinese)**: 所有对话与图像分析均在本地显卡完成，无需云端连接，保障绝对隐私。`,
    };
  }

  // 4. Check if Japanese or Chinese
  if (/[\u3040-\u30FF]/.test(prompt) || replyLanguage === '日本語 (Japanese)') {
    return {
      direction: 'ltr',
      scriptLabel: '日本語 (Japanese)',
      text: `### ローカル推論レポート (${model.name})

お使いのマシン上で **${model.vramRequiredGb} GB VRAM** を使用してプライベートに処理されました：

- **完全なオフライン動作**: 会話データや添付画像は外部サーバーに一切送信されません。
- **高速ストリーミング**: 現在 **${model.speedTokPerSec} tok/s** の速度で応答を生成しています。`,
    };
  }

  if (/[\u4E00-\u9FFF]/.test(prompt) || replyLanguage === '中文 (Chinese)') {
    return {
      direction: 'ltr',
      scriptLabel: '中文 (Chinese)',
      text: `### 本地模型响应 (${model.name})

您的请求已在本地 GPU (**${model.vramRequiredGb} GB 显存**) 上安全处理完毕：

- **100% 本地隐私**: 没有任何文本或图像上传至云端。
- **响应设置**: 当前采样温度为 \`${temperature.toFixed(1)}\`，生成速度约为 **${model.speedTokPerSec} tok/s**。`,
    };
  }

  // 5. Check if Vision Attachment is present
  if (attachments.length > 0) {
    const att = attachments[0];
    return {
      direction: 'ltr',
      scriptLabel: 'Vision Analysis',
      text: `### Local Vision Inspection: \`${att.name}\`

Analyzed privately on your GPU using **Llama 3.2 11B Vision** (\`Q4_K_M\`):

- **Composition & Lighting**: High-contrast architectural framing pairing warm interior tungsten illumination (~2700K) against deep twilight slate shadows.
- **Material Palette**: Matte board-formed concrete, natural timber grain, and calm dark water reflections—ideal reference tones for a distraction-free desktop workspace.
- **Extracted UI Accent Tokens**: Primary surface \`#141413\`, elevated card \`#242422\`, and focal amber highlight \`#E5A93C\`.`,
    };
  }

  // 6. Check if Code / JavaFX request
  if (lower.includes('javafx') || lower.includes('code') || lower.includes('python')) {
    return {
      direction: 'ltr',
      text: `### Non-Blocking JavaFX SSE Token Reader

To keep the JavaFX UI responsive at 60fps while streaming tokens from your local Python backend, batch incoming chunks every **30ms** before calling \`Platform.runLater()\`:

\`\`\`java
public Task<Void> streamLocalReply(String prompt, Consumer<String> onTokenBatch) {
    return new Task<>() {
        @Override
        protected Void call() throws Exception {
            var request = HttpRequest.newBuilder()
                .uri(URI.create("http://127.0.0.1:8420/v1/chat/stream"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(prompt))
                .build();

            var client = HttpClient.newHttpClient();
            var response = client.send(request, HttpResponse.BodyHandlers.ofLines());

            StringBuilder batch = new StringBuilder();
            long lastFlush = System.currentTimeMillis();

            for (String line : (Iterable<String>) response.body()::iterator) {
                if (isCancelled()) break;
                if (line.startsWith("data: ")) {
                    batch.append(line.substring(6));
                    if (System.currentTimeMillis() - lastFlush >= 30) {
                        String chunk = batch.toString();
                        batch.setLength(0);
                        lastFlush = System.currentTimeMillis();
                        Platform.runLater(() -> onTokenBatch.accept(chunk));
                    }
                }
            }
            return null;
        }
    };
}
\`\`\`

- **Why this works**: Rather than triggering a scene graph layout pass on every single token, flushing every \`30ms\` matches a 33Hz visual cadence while keeping CPU usage under 3%.`,
    };
  }

  // Default helpful response
  return {
    direction: 'ltr',
    text: `### Processed Locally with ${model.name}

Your request ran privately on your GPU (**${model.vramRequiredGb.toFixed(1)} GB VRAM** allocated, temperature \`${temperature.toFixed(1)}\`):

- **Zero External Calls**: All prompt tokens and context remain in local memory.
- **Multi-Modal Ready**: You can attach a photo using **Attach Image** to inspect visual details, or prefix any prompt with \`/image\` to run the local 4-step diffusion pipeline.`,
  };
}

export function App() {
  const [models, setModels] = useState<LocalModel[]>(LOCAL_MODELS);
  const [activeModel, setActiveModel] = useState<LocalModel>(LOCAL_MODELS[0]);
  const [hardwareState, setHardwareState] =
    useState<HardwareStatusState>('ready');
  const [liveTokPerSec, setLiveTokPerSec] = useState<number>(
    LOCAL_MODELS[0].speedTokPerSec
  );

  const [conversations, setConversations] = useState<Conversation[]>(
    INITIAL_CONVERSATIONS
  );
  const [activeConversationId, setActiveConversationId] = useState<string>(
    INITIAL_CONVERSATIONS[0].id
  );

  const [stagedAttachments, setStagedAttachments] = useState<VisionAttachment[]>(
    []
  );

  const [downloadItems, setDownloadItems] = useState<DownloadModelItem[]>(
    INITIAL_DOWNLOAD_ITEMS
  );
  const [downloadsModalOpen, setDownloadsModalOpen] = useState(false);
  const [settingsModalOpen, setSettingsModalOpen] = useState(false);
  const [specModalOpen, setSpecModalOpen] = useState(false);
  const [javafxInspectorActive, setJavafxInspectorActive] = useState(false);
  const [compact800x600, setCompact800x600] = useState(false);

  const [settings, setSettings] = useState<SulvanaSettings>({
    replyLanguage: 'Auto-detect',
    temperature: 0.7,
    maxResponseLength: 2048,
    theme: 'dark',
    gpuLayersOffload: 'auto',
    compactWindowMode: false,
  });

  // Streaming / Image generation timer refs so Stop button can cancel cleanly
  const streamIntervalRef = useRef<number | null>(null);
  const activeStreamingMsgIdRef = useRef<string | null>(null);

  // Sync theme attribute on document root
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', settings.theme);
  }, [settings.theme]);

  // Background ticker for active downloads in the Model Manager
  useEffect(() => {
    const timer = window.setInterval(() => {
      setDownloadItems((prev) =>
        prev.map((item) => {
          if (item.status !== 'downloading') return item;
          const nextPercent = Math.min(100, item.percent + 1);
          const nextDownloaded = Number(
            ((nextPercent / 100) * item.totalSizeGb).toFixed(1)
          );
          if (nextPercent >= 100) {
            return {
              ...item,
              percent: 100,
              downloadedGb: item.totalSizeGb,
              speedMbPerSec: 0,
              etaText: 'Installed • Verified SHA256',
              status: 'completed',
            };
          }
          const remainingGb = Math.max(0.1, item.totalSizeGb - nextDownloaded);
          const secLeft = Math.round((remainingGb * 1024) / item.speedMbPerSec);
          const mins = Math.floor(secLeft / 60);
          const secs = secLeft % 60;
          return {
            ...item,
            percent: nextPercent,
            downloadedGb: nextDownloaded,
            etaText: mins > 0 ? `${mins}m ${secs}s left` : `${secs}s left`,
          };
        })
      );
    }, 1800);
    return () => clearInterval(timer);
  }, []);

  const activeConversation =
    conversations.find((c) => c.id === activeConversationId) || conversations[0];

  // Handle switching active model with realistic VRAM loading state
  const handleSelectModel = (model: LocalModel) => {
    setActiveModel(model);
    if (!model.installed) {
      setHardwareState('error_model_missing');
      setLiveTokPerSec(0);
      return;
    }

    setHardwareState('loading_model');
    setTimeout(() => {
      setHardwareState(model.vramRequiredGb > 8 ? 'vram_warning' : 'ready');
      setLiveTokPerSec(model.speedTokPerSec);
    }, 950);
  };

  // Start a brand-new empty chat (shows the clean Empty State)
  const handleNewChat = () => {
    handleStopGeneration();
    const newConv: Conversation = {
      id: `conv-${Date.now()}`,
      title: 'New Local Session',
      updatedAt: 'Just now',
      scriptBadge: 'Ready',
      messages: [],
    };
    setConversations((prev) => [newConv, ...prev]);
    setActiveConversationId(newConv.id);
    setStagedAttachments([]);
  };

  // Clear messages in the current conversation
  const handleClearCurrentChat = () => {
    handleStopGeneration();
    setConversations((prev) =>
      prev.map((c) =>
        c.id === activeConversationId
          ? { ...c, messages: [], updatedAt: 'Cleared just now' }
          : c
      )
    );
  };

  const handleDeleteConversation = (id: string) => {
    setConversations((prev) => {
      const remaining = prev.filter((c) => c.id !== id);
      if (id === activeConversationId && remaining.length > 0) {
        setActiveConversationId(remaining[0].id);
      }
      return remaining;
    });
  };

  const handleStopGeneration = () => {
    if (streamIntervalRef.current) {
      window.clearInterval(streamIntervalRef.current);
      streamIntervalRef.current = null;
    }
    if (activeStreamingMsgIdRef.current) {
      const stoppedId = activeStreamingMsgIdRef.current;
      setConversations((prev) =>
        prev.map((conv) => ({
          ...conv,
          messages: conv.messages.map((m) =>
            m.id === stoppedId
              ? {
                  ...m,
                  isStreaming: false,
                  content: m.content
                    ? `${m.content}\n\n*(Stopped by user)*`
                    : '*(Generation stopped by user)*',
                  generatedImage:
                    m.generatedImage && m.generatedImage.status === 'generating'
                      ? undefined
                      : m.generatedImage,
                }
              : m
          ),
        }))
      );
      activeStreamingMsgIdRef.current = null;
    }
    setHardwareState('ready');
  };

  const handleSendMessage = (
    rawText: string,
    attachments: VisionAttachment[]
  ) => {
    if (
      hardwareState === 'error_backend' ||
      hardwareState === 'error_model_missing'
    ) {
      return;
    }

    const trimmed = rawText.trim();
    const isImageCommand =
      trimmed.toLowerCase().startsWith('/image ') ||
      trimmed.toLowerCase() === '/image';

    const userScript = detectScriptAndDirection(trimmed, settings.replyLanguage);

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmed,
      timestamp: new Date().toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      }),
      direction: userScript.direction,
      scriptLabel: userScript.scriptLabel,
      attachments: attachments.length > 0 ? [...attachments] : undefined,
    };

    const assistantMsgId = `asst-${Date.now() + 1}`;
    activeStreamingMsgIdRef.current = assistantMsgId;

    setStagedAttachments([]);

    // Real local backend: streamed text, image generation, vision, and safe agent tools.
    const liveAssistantMsg: ChatMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: 'Just now',
      direction: userScript.direction,
      scriptLabel: userScript.scriptLabel,
      isStreaming: true,
      modelUsed: activeModel.name,
      tokensPerSec: liveTokPerSec,
    };
    setHardwareState(isImageCommand ? 'generating_image' : 'streaming');
    setConversations((prev) =>
      prev.map((conv) =>
        conv.id === activeConversationId
          ? {
              ...conv,
              title: conv.messages.length === 0 ? trimmed.slice(0, 34) : conv.title,
              updatedAt: 'Just now',
              messages: [...conv.messages, userMsg, liveAssistantMsg],
            }
          : conv
      )
    );
    void (async () => {
      const decode = (value: string) =>
        new TextDecoder().decode(
          Uint8Array.from(atob(value), (char) => char.charCodeAt(0))
        );
      let reply = '';
      try {
        const response = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            prompt: trimmed,
            maxTokens: Math.min(settings.maxResponseLength, 1024),
            temperature: settings.temperature,
            language: settings.replyLanguage,
          }),
        });
        if (!response.ok || !response.body) throw new Error(await response.text());
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let pending = '';
        while (true) {
          const { value, done } = await reader.read();
          pending += decoder.decode(value || new Uint8Array(), { stream: !done });
          const lines = pending.split('\n');
          pending = lines.pop() || '';
          for (const line of lines) {
            const [kind, encoded] = line.split('\t', 2);
            if (!kind || !encoded) continue;
            if (kind === 't') {
              reply += decode(encoded);
              setConversations((prev) => prev.map((conv) => ({
                ...conv,
                messages: conv.messages.map((message) => message.id === assistantMsgId ? { ...message, content: reply } : message),
              })));
            } else if (kind === 'i' || kind === 'v') {
              const event = JSON.parse(decode(encoded));
              if (event.answer) reply += event.answer;
              if (event.image_path) reply += `\n\nGenerated locally: ${event.image_path}`;
            } else if (kind === 'e') {
              throw new Error(decode(encoded));
            }
          }
          if (done) break;
        }
        setConversations((prev) => prev.map((conv) => ({
          ...conv,
          messages: conv.messages.map((message) => message.id === assistantMsgId ? { ...message, content: reply || 'Completed.', isStreaming: false } : message),
        })));
      } catch (error) {
        setConversations((prev) => prev.map((conv) => ({
          ...conv,
          messages: conv.messages.map((message) => message.id === assistantMsgId ? { ...message, content: `Local engine error: ${error instanceof Error ? error.message : 'Unknown error'}`, isStreaming: false } : message),
        })));
      } finally {
        activeStreamingMsgIdRef.current = null;
        setHardwareState('ready');
      }
    })();
    return;

    // CASE A: Local Image Generation (/image ...)
    if (isImageCommand) {
      const imagePrompt =
        trimmed.replace(/^\/image\s*/i, '').trim() ||
        'A serene twilight cedar forest with warm hand-blown amber glass lanterns';

      const chosenImageUrl =
        imagePrompt.toLowerCase().includes('nordic') ||
        imagePrompt.toLowerCase().includes('library') ||
        imagePrompt.toLowerCase().includes('cliff')
          ? '/images/sulvana-architecture-sketch.jpg'
          : '/images/sulvana-lantern-forest.jpg';

      const assistantImageMsg: ChatMessage = {
        id: assistantMsgId,
        role: 'assistant',
        content: 'Initializing local 4-step diffusion pipeline on GPU…',
        timestamp: 'Just now',
        direction: 'ltr',
        modelUsed: 'Flux.1 Schnell Local (FP8)',
        tokensPerSec: 39.4,
        generatedImage: {
          prompt: imagePrompt,
          imageUrl: chosenImageUrl,
          resolution: '1024 × 1024',
          stepsTotal: 4,
          currentStep: 1,
          seed: Math.floor(1000000 + Math.random() * 8999999),
          modelName: 'Flux.1 Schnell (FP8)',
          status: 'generating',
        },
      };

      setHardwareState('generating_image');
      setConversations((prev) =>
        prev.map((conv) =>
          conv.id === activeConversationId
            ? {
                ...conv,
                title:
                  conv.messages.length === 0
                    ? `Image: ${imagePrompt.slice(0, 28)}…`
                    : conv.title,
                updatedAt: 'Just now',
                scriptBadge: 'Image Gen',
                messages: [...conv.messages, userMsg, assistantImageMsg],
              }
            : conv
        )
      );

      let step = 1;
      streamIntervalRef.current = window.setInterval(() => {
        step += 1;
        if (step <= 4) {
          setConversations((prev) =>
            prev.map((conv) => ({
              ...conv,
              messages: conv.messages.map((m) =>
                m.id === assistantMsgId && m.generatedImage
                  ? {
                      ...m,
                      generatedImage: {
                        ...m.generatedImage,
                        currentStep: step,
                      },
                    }
                  : m
              ),
            }))
          );
        } else {
          if (streamIntervalRef.current) {
            clearInterval(streamIntervalRef.current);
            streamIntervalRef.current = null;
          }
          activeStreamingMsgIdRef.current = null;
          setHardwareState('ready');
          setConversations((prev) =>
            prev.map((conv) => ({
              ...conv,
              messages: conv.messages.map((m) =>
                m.id === assistantMsgId && m.generatedImage
                  ? {
                      ...m,
                      content: `Generated locally on your GPU in **3.4 seconds** (\`1024 × 1024\`, 4 steps). Click **Save Image** below to export to disk.`,
                      generatedImage: {
                        ...m.generatedImage,
                        currentStep: 4,
                        status: 'completed',
                        generationTimeSec: 3.4,
                      },
                    }
                  : m
              ),
            }))
          );
        }
      }, 520);

      return;
    }

    // CASE B: Standard or Vision Streaming Text Reply
    const replyData = buildContextualAssistantReply(
      trimmed,
      attachments,
      settings.replyLanguage,
      activeModel,
      settings.temperature
    );

    const initialAssistantMsg: ChatMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: 'Just now',
      direction: replyData.direction,
      scriptLabel: replyData.scriptLabel,
      isStreaming: true,
      modelUsed:
        attachments.length > 0
          ? 'Llama 3.2 11B Vision (Q4_K_M)'
          : `${activeModel.name} (${activeModel.quantization})`,
      tokensPerSec: activeModel.speedTokPerSec,
    };

    setHardwareState('streaming');
    setConversations((prev) =>
      prev.map((conv) =>
        conv.id === activeConversationId
          ? {
              ...conv,
              title:
                conv.messages.length === 0
                  ? trimmed.slice(0, 34)
                  : conv.title,
              updatedAt: 'Just now',
              scriptBadge:
                replyData.scriptLabel?.split(' ')[0] || conv.scriptBadge,
              messages: [...conv.messages, userMsg, initialAssistantMsg],
            }
          : conv
      )
    );

    // Stream chunks every 30ms (matching our JavaFX Platform.runLater batch note!)
    const fullText = replyData.text;
    let cursor = 0;
    const stepChars = 10;

    streamIntervalRef.current = window.setInterval(() => {
      cursor += stepChars;
      const slice = fullText.slice(0, cursor);
      const isDone = cursor >= fullText.length;

      setLiveTokPerSec(
        Number(
          (
            activeModel.speedTokPerSec +
            (Math.random() * 2.4 - 1.2)
          ).toFixed(1)
        )
      );

      setConversations((prev) =>
        prev.map((conv) => ({
          ...conv,
          messages: conv.messages.map((m) =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: slice,
                  isStreaming: !isDone,
                }
              : m
          ),
        }))
      );

      if (isDone) {
        if (streamIntervalRef.current) {
          clearInterval(streamIntervalRef.current);
          streamIntervalRef.current = null;
        }
        activeStreamingMsgIdRef.current = null;
        setHardwareState('ready');
      }
    }, 30);
  };

  // Download Queue handlers
  const handleTogglePauseResume = (id: string) => {
    setDownloadItems((prev) =>
      prev.map((item) => {
        if (item.id !== id) return item;
        if (item.status === 'downloading') {
          return {
            ...item,
            status: 'paused',
            speedMbPerSec: 0,
            etaText: `Paused at ${item.percent}%`,
          };
        }
        return {
          ...item,
          status: 'downloading',
          speedMbPerSec: 36.8,
          etaText: 'Resuming stream…',
        };
      })
    );
  };

  const handleStartDownload = (id: string) => {
    setDownloadItems((prev) =>
      prev.map((item) =>
        item.id === id
          ? {
              ...item,
              status: 'downloading',
              percent: 4,
              downloadedGb: Number((item.totalSizeGb * 0.04).toFixed(1)),
              speedMbPerSec: 41.2,
              etaText: 'Calculating ETA…',
            }
          : item
      )
    );
  };

  const handleCancelDownload = (id: string) => {
    setDownloadItems((prev) =>
      prev.map((item) =>
        item.id === id
          ? {
              ...item,
              status: 'available',
              percent: 0,
              downloadedGb: 0,
              speedMbPerSec: 0,
              etaText: 'Ready to download',
            }
          : item
      )
    );
  };

  const handleSimulateComplete = (id: string) => {
    setDownloadItems((prev) =>
      prev.map((item) =>
        item.id === id
          ? {
              ...item,
              status: 'completed',
              percent: 100,
              downloadedGb: item.totalSizeGb,
              speedMbPerSec: 0,
              etaText: 'Installed • Verified SHA256',
            }
          : item
      )
    );
  };

  const activeDownloads = downloadItems.filter(
    (d) => d.status === 'downloading'
  );
  const primaryActiveDownloadPercent =
    activeDownloads.length > 0 ? activeDownloads[0].percent : null;

  const isBusy =
    hardwareState === 'streaming' ||
    hardwareState === 'generating_image' ||
    hardwareState === 'loading_model';

  return (
    <div
      className={`w-screen h-screen overflow-hidden flex items-center justify-center ${
        compact800x600 ? 'bg-[#0A0A09] p-4' : ''
      }`}
    >
      {/* Root Desktop Window Frame (BorderPane.root-pane) */}
      <div
        className={`flex flex-col overflow-hidden transition-all ${
          compact800x600
            ? 'w-[800px] h-[600px] rounded-xl border shadow-2xl'
            : 'w-full h-full'
        }`}
        style={{
          backgroundColor: 'var(--bg-app-canvas)',
          borderColor: 'var(--border-subtle)',
          color: 'var(--text-primary)',
        }}
      >
        {/* TOP: Model & Hardware Status Bar */}
        <TopStatusBar
          models={models}
          activeModel={activeModel}
          onSelectModel={handleSelectModel}
          hardwareState={hardwareState}
          onSimulateHardwareState={(st) => setHardwareState(st)}
          liveTokPerSec={liveTokPerSec}
          activeDownloadsCount={activeDownloads.length}
          activeDownloadPercent={primaryActiveDownloadPercent}
          onOpenDownloads={() => setDownloadsModalOpen(true)}
          onOpenSettings={() => setSettingsModalOpen(true)}
          onOpenSpecModal={() => setSpecModalOpen(true)}
          javafxInspectorActive={javafxInspectorActive}
          onToggleJavafxInspector={() =>
            setJavafxInspectorActive((prev) => !prev)
          }
          compact800x600={compact800x600}
          onToggleCompact800x600={() => setCompact800x600((prev) => !prev)}
        />

        {/* MAIN WORKSPACE BODY: Left Sidebar Rail + Center Chat & Composer */}
        <div className="flex-1 flex min-h-0 overflow-hidden">
          <SidebarRail
            conversations={conversations}
            activeConversationId={activeConversation.id}
            onSelectConversation={(id) => {
              handleStopGeneration();
              setActiveConversationId(id);
            }}
            onNewChat={handleNewChat}
            onClearCurrentChat={handleClearCurrentChat}
            onDeleteConversation={handleDeleteConversation}
            replyLanguage={settings.replyLanguage}
            onQuickSwitchLanguage={(lang) =>
              setSettings((prev) => ({ ...prev, replyLanguage: lang }))
            }
            javafxInspectorActive={javafxInspectorActive}
            compact800x600={compact800x600}
          />

          {/* CENTER: Conversation Stream + Multi-Modal Composer */}
          <main className="flex-1 flex flex-col min-w-0 min-h-0">
            <MessageStream
              messages={activeConversation.messages}
              activeModel={activeModel}
              hardwareState={hardwareState}
              onStarterPrompt={(prompt, attachment) => {
                handleSendMessage(prompt, attachment ? [attachment] : []);
              }}
              onRecoverHardwareError={() => {
                if (hardwareState === 'error_model_missing') {
                  setModels((prev) =>
                    prev.map((m) =>
                      m.id === activeModel.id ? { ...m, installed: true } : m
                    )
                  );
                  setActiveModel(LOCAL_MODELS[0]);
                }
                setHardwareState('ready');
                setLiveTokPerSec(LOCAL_MODELS[0].speedTokPerSec);
              }}
              onOpenDownloads={() => setDownloadsModalOpen(true)}
              javafxInspectorActive={javafxInspectorActive}
            />

            <MessageComposer
              onSendMessage={handleSendMessage}
              isBusy={isBusy}
              onStopGeneration={handleStopGeneration}
              activeModel={activeModel}
              stagedAttachments={stagedAttachments}
              onStageAttachment={(att) =>
                setStagedAttachments((prev) => [...prev, att])
              }
              onRemoveAttachment={(id) =>
                setStagedAttachments((prev) =>
                  prev.filter((item) => item.id !== id)
                )
              }
              javafxInspectorActive={javafxInspectorActive}
            />
          </main>
        </div>

        {/* MODALS & SPECIFICATION OVERLAYS */}
        <DownloadsModal
          isOpen={downloadsModalOpen}
          onClose={() => setDownloadsModalOpen(false)}
          items={downloadItems}
          onTogglePauseResume={handleTogglePauseResume}
          onStartDownload={handleStartDownload}
          onCancelDownload={handleCancelDownload}
          onSimulateComplete={handleSimulateComplete}
        />

        <SettingsModal
          isOpen={settingsModalOpen}
          onClose={() => setSettingsModalOpen(false)}
          settings={settings}
          onUpdateSettings={(partial) =>
            setSettings((prev) => ({ ...prev, ...partial }))
          }
          onResetDefaults={() =>
            setSettings({
              replyLanguage: 'Auto-detect',
              temperature: 0.7,
              maxResponseLength: 2048,
              theme: 'dark',
              gpuLayersOffload: 'auto',
              compactWindowMode: false,
            })
          }
        />

        <DesignSpecModal
          isOpen={specModalOpen}
          onClose={() => setSpecModalOpen(false)}
          javafxInspectorActive={javafxInspectorActive}
          onToggleJavafxInspector={() =>
            setJavafxInspectorActive((prev) => !prev)
          }
        />
      </div>
    </div>
  );
}
export default App;
