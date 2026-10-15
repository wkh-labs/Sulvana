import {
  Conversation,
  DownloadModelItem,
  LocalModel,
  VisionAttachment,
} from '../types/sulvana';

export const LOCAL_MODELS: LocalModel[] = [
  {
    id: 'dolphin-3-llama-8b-q4',
    name: 'Dolphin 3.0 Llama 3.1 8B',
    quantization: 'Q4_K_M',
    capabilities: ['chat', 'code'],
    vramRequiredGb: 6.2,
    sizeGb: 4.9,
    speedTokPerSec: 24.0,
    installed: true,
    description:
      'Direct, capable local conversation model for English chat, coding, and agent-style research.',
    languagesSupported: ['English'],
  },
  {
    id: 'llama-3.2-11b-vision',
    name: 'Llama 3.2 11B Vision',
    quantization: 'Q4_K_M',
    capabilities: ['chat', 'vision', 'code'],
    vramRequiredGb: 6.4,
    sizeGb: 6.3,
    speedTokPerSec: 34.2,
    installed: true,
    description:
      'Local multimodal model that inspects attached photos, UI sketches, diagrams, and documents privately.',
    languagesSupported: ['English', 'العربية', '中文', '日本語'],
  },
  {
    id: 'flux-schnell-fp8',
    name: 'Flux.1 Schnell + Qwen Hybrid',
    quantization: 'FP8 / Q4',
    capabilities: ['chat', 'image-gen', 'vision'],
    vramRequiredGb: 7.4,
    sizeGb: 7.2,
    speedTokPerSec: 38.0,
    installed: true,
    description:
      'Unified local assistant paired with a 4-step local diffusion pipeline for instant /image creation.',
    languagesSupported: ['English', 'ខ្មែរ', 'العربية', '中文', '日本語'],
  },
  {
    id: 'deepseek-r1-14b',
    name: 'DeepSeek R1 Distill 14B',
    quantization: 'Q4_K_M',
    capabilities: ['chat', 'code'],
    vramRequiredGb: 9.2,
    sizeGb: 8.9,
    speedTokPerSec: 22.8,
    installed: false,
    description:
      'High-depth software architecture and mathematical reasoning model (requires 10+ GB VRAM or CPU split).',
    languagesSupported: ['English', '中文', '日本語'],
  },
];

export const SAMPLE_VISION_ATTACHMENTS: VisionAttachment[] = [
  {
    id: 'sample-arch-1',
    name: 'nordic-cliffside-studio.jpg',
    url: '/images/sulvana-architecture-sketch.jpg',
    dimensions: '1280 × 896',
    sizeLabel: '1.4 MB',
  },
  {
    id: 'sample-forest-2',
    name: 'amber-lantern-cedar-forest.jpg',
    url: '/images/sulvana-lantern-forest.jpg',
    dimensions: '1024 × 1024',
    sizeLabel: '1.8 MB',
  },
];

export const INITIAL_CONVERSATIONS: Conversation[] = [
  {
    id: 'conv-studio-main',
    title: 'Nordic Studio Lighting & Local Diffusion',
    updatedAt: 'Just now',
    scriptBadge: 'EN + Vision',
    pinned: true,
    messages: [
      {
        id: 'msg-1',
        role: 'user',
        timestamp: '10:14 AM',
        direction: 'ltr',
        attachments: [
          {
            id: 'att-nordic-1',
            name: 'nordic-cliffside-studio.jpg',
            url: '/images/sulvana-architecture-sketch.jpg',
            dimensions: '1280 × 896',
            sizeLabel: '1.4 MB',
          },
        ],
        content:
          'Analyze the architectural material balance and lighting temperature in this reference photo, then give me a compact JavaFX CSS snippet inspired by its warm graphite & amber palette.',
      },
      {
        id: 'msg-2',
        role: 'assistant',
        timestamp: '10:14 AM',
        direction: 'ltr',
        modelUsed: 'Llama 3.2 11B Vision (Q4_K_M)',
        tokensPerSec: 36.8,
        totalTokens: 284,
        content: `### Visual & Material Breakdown

The reference photograph balances **cool coastal slate** against **warm interior tungsten-amber light** (~2700K):

- **Primary Structure**: Board-formed matte concrete and charred larch timber absorb harsh twilight reflections, keeping the exterior calm and low-glare.
- **Focal Contrast**: The recessed library glazing acts as a warm beacon—drawing the eye immediately without saturating the surrounding cliffside.
- **UI Translation**: We can map the exterior basalt directly to \`#141413\` canvas surfaces and use the interior lamp glow (\`#E5A93C\`) exclusively for active focus rings and primary actions.

\`\`\`css
/* Sulvana Warm Obsidian — JavaFX Scene Stylesheet */
.root-pane {
    -fx-background-color: #141413;
    -fx-font-family: "Inter", "Segoe UI", "Noto Sans Khmer", "Noto Sans Arabic";
}

.chat-bubble-user {
    -fx-background-color: #2A2926;
    -fx-background-radius: 12px;
    -fx-border-color: #2E2D2A;
    -fx-border-radius: 12px;
    -fx-padding: 12px 16px;
}

.button-primary-amber {
    -fx-background-color: #E5A93C;
    -fx-text-fill: #141413;
    -fx-background-radius: 8px;
    -fx-font-weight: 600;
}
\`\`\``,
      },
      {
        id: 'msg-3',
        role: 'user',
        timestamp: '10:16 AM',
        direction: 'ltr',
        content:
          '/image A serene twilight cedar forest with warm hand-blown amber glass lanterns hanging from mossy branches, soft mist hovering over dark obsidian river stones',
      },
      {
        id: 'msg-4',
        role: 'assistant',
        timestamp: '10:16 AM',
        direction: 'ltr',
        modelUsed: 'Flux.1 Schnell Local (FP8)',
        tokensPerSec: 41.2,
        content:
          'Generated locally on your GPU in **3.8 seconds** using 4 diffusion steps (`1024 × 1024`, Seed `8492014`). No data left your machine.',
        generatedImage: {
          prompt:
            'A serene twilight cedar forest with warm hand-blown amber glass lanterns hanging from mossy branches, soft mist hovering over dark obsidian river stones',
          imageUrl: '/images/sulvana-lantern-forest.jpg',
          resolution: '1024 × 1024',
          stepsTotal: 4,
          currentStep: 4,
          seed: 8492014,
          modelName: 'Flux.1 Schnell (FP8 Local)',
          status: 'completed',
          generationTimeSec: 3.8,
        },
      },
    ],
  },
  {
    id: 'conv-khmer-script',
    title: 'ការសង្ខេបឯកសារបច្ចេកទេស (Khmer Script)',
    updatedAt: 'Yesterday',
    scriptBadge: 'ខ្មែរ KM',
    messages: [
      {
        id: 'msg-km-1',
        role: 'user',
        timestamp: '4:20 PM',
        direction: 'ltr',
        scriptLabel: 'ខ្មែរ (Khmer)',
        content:
          'សួស្តី Sulvana! សូមពន្យល់ពីអត្ថប្រយោជន៍នៃការប្រើប្រាស់ប្រព័ន្ធ AI ក្នុងម៉ាស៊ីនផ្ទាល់ខ្លួន (Local AI) សម្រាប់អ្នកសរសេរកម្មវិធី និងអ្នករចនា ដោយប្រើភាសាខ្មែរឱ្យបានច្បាស់លាស់។',
      },
      {
        id: 'msg-km-2',
        role: 'assistant',
        timestamp: '4:20 PM',
        direction: 'ltr',
        scriptLabel: 'ខ្មែរ (Khmer)',
        modelUsed: 'Qwen 2.5 7B Instruct (Q4_K_M)',
        tokensPerSec: 44.5,
        totalTokens: 196,
        content: `សួស្តី! ការប្រើប្រាស់ប្រព័ន្ធ **AI ក្នុងម៉ាស៊ីនផ្ទាល់ខ្លួន (Local AI)** ដូចជាកម្មវិធី **Sulvana** ផ្តល់នូវអត្ថប្រយោជន៍សំខាន់ៗដូចខាងក្រោម៖

- **ឯកជនភាពទិន្នន័យ ១០០% (Complete Privacy)**: រាល់សារ កូដកម្មវិធី និងរូបភាពទាំងអស់ត្រូវបានដំណើរការនៅលើកាតក្រាហ្វិក (GPU) ក្នុងកុំព្យូទ័ររបស់អ្នកផ្ទាល់ ដោយមិនបញ្ជូនទៅកាន់ម៉ាស៊ីនមេខាងក្រៅឡើយ។
- **ដំណើរការដោយមិនចាំបាច់មានអ៊ីនធឺណិត (Offline Reliability)**: អ្នកអាចសរសេរកូដ បកប្រែភាសា ឬបង្កើតរូបភាពបានគ្រប់ពេលវេលា ទោះបីជាគ្មានការតភ្ជាប់អ៊ីនធឺណិតក៏ដោយ។
- **ការគាំទ្រអក្សរខ្មែរយ៉ាងពេញលេញ**: ប្រព័ន្ធអក្សររបស់ Sulvana ប្រើប្រាស់គម្លាតបន្ទាត់ \`1.65\` និងមិនបង្រួមតួអក្សរ ដើម្បីរក្សាជើងអក្សរ និងស្រៈត្រួតគ្នាឱ្យអានបានច្បាស់ល្អ។`,
      },
    ],
  },
  {
    id: 'conv-arabic-rtl',
    title: 'تصميم واجهات المستخدم المحلية (Arabic RTL)',
    updatedAt: '2 days ago',
    scriptBadge: 'العربية AR',
    messages: [
      {
        id: 'msg-ar-1',
        role: 'user',
        timestamp: '7:05 PM',
        direction: 'rtl',
        scriptLabel: 'العربية (Arabic — RTL)',
        content:
          'مرحباً سولفانا، كيف يمكننا ضمان قراءة مريحة للنصوص العربية بجانب الأكواد البرمجية في تطبيق سطح مكتب مبني بـ JavaFX؟',
      },
      {
        id: 'msg-ar-2',
        role: 'assistant',
        timestamp: '7:05 PM',
        direction: 'rtl',
        scriptLabel: 'العربية (Arabic — RTL)',
        modelUsed: 'Qwen 2.5 7B Instruct (Q4_K_M)',
        tokensPerSec: 45.1,
        totalTokens: 210,
        content: `أهلاً بك! لضمان تجربة قراءة ممتازة للنصوص العربية في **Sulvana** مع الحفاظ على وضوح الأكواد البرمجية، نعتمد المبادئ التالية:

- **اتجاه النص التلقائي (RTL NodeOrientation)**: يتم ضبط حاوية الرسالة على \`NodeOrientation.RIGHT_TO_LEFT\` عند اكتشاف الأحرف العربية، بينما تبقى كتل الأكواد البرمجية (\`Code Blocks\`) من اليسار إلى اليمين \`LEFT_TO_RIGHT\`.
- **الحفاظ على اتصال الحروف**: عدم استخدام خاصية تباعد الأحرف (\`letter-spacing: 0px\`) نهائياً حتى لا تنفصل الحروف العربية المتصلة.
- **خطوط واضحة وعالية التباين**: استخدام خط **Noto Sans Arabic** و **Segoe UI** بارتفاع سطر مريح يبلغ \`1.65\`.`,
      },
    ],
  },
  {
    id: 'conv-cjk-multilingual',
    title: 'ローカルAI量子化とマルチスクリプト設計 (JP / ZH)',
    updatedAt: '3 days ago',
    scriptBadge: '日本語 / 中文',
    messages: [
      {
        id: 'msg-cjk-1',
        role: 'user',
        timestamp: '11:42 AM',
        direction: 'ltr',
        scriptLabel: '日本語 / 中文',
        content:
          'Q4_K_M量子化モデルが8GB VRAMのノートPCでどのように高速に動作するのか、日本語と中国語で簡潔にまとめてください。',
      },
      {
        id: 'msg-cjk-2',
        role: 'assistant',
        timestamp: '11:42 AM',
        direction: 'ltr',
        scriptLabel: '日本語 / 中文',
        modelUsed: 'Qwen 2.5 7B Instruct (Q4_K_M)',
        tokensPerSec: 47.9,
        totalTokens: 230,
        content: `### 日本語での概要 (Japanese Summary)
**Q4_K_M 量子化**は、モデルの重みを16ビット浮動小数点から4ビット表現に圧縮しつつ、重要なAttention層には高い精度を割り当てる方式です。これにより、7Bクラスのモデルを約 **4.8 GB の VRAM** に収めながら、毎秒45トークン以上の高速な応答を実現します。

### 中文简述 (Chinese Summary)
**Q4_K_M 量化技术**通过混合精度压缩权重，使 70 亿参数的本地模型仅需约 **4.8 GB 显存**即可流畅运行。所有推理完全在本地显卡完成，无需联网，兼顾了响应速度与数据隐私。`,
      },
    ],
  },
];

export const INITIAL_DOWNLOAD_ITEMS: DownloadModelItem[] = [
  {
    id: 'dl-mistral-small-24b',
    name: 'Mistral Small 3 24B Instruct',
    family: 'Mistral Architecture',
    quantization: 'Q4_K_M',
    format: 'GGUF',
    totalSizeGb: 14.2,
    downloadedGb: 9.1,
    percent: 64,
    speedMbPerSec: 38.4,
    etaText: '2m 15s left',
    status: 'downloading',
    capabilities: ['chat', 'code'],
    description:
      'High-precision multilingual assistant for drafting, code synthesis, and complex document analysis.',
    recommendedVramGb: 12,
  },
  {
    id: 'dl-sdxl-turbo-fp16',
    name: 'SDXL Lightning 4-Step Diffusion',
    family: 'Local Image Pipeline',
    quantization: 'FP16',
    format: 'Safetensors',
    totalSizeGb: 6.4,
    downloadedGb: 2.4,
    percent: 38,
    speedMbPerSec: 0,
    etaText: 'Paused at 38%',
    status: 'paused',
    capabilities: ['image-gen'],
    description:
      'Dedicated photographic & illustration image generation checkpoint for /image commands.',
    recommendedVramGb: 6,
  },
  {
    id: 'dl-qwen-2.5-7b',
    name: 'Qwen 2.5 7B Instruct',
    family: 'Qwen2 Architecture',
    quantization: 'Q4_K_M',
    format: 'GGUF',
    totalSizeGb: 4.7,
    downloadedGb: 4.7,
    percent: 100,
    speedMbPerSec: 0,
    etaText: 'Installed • Verified SHA256',
    status: 'completed',
    capabilities: ['chat', 'code'],
    description:
      'Default fast multi-script model supporting English, Khmer, Arabic, Chinese, and Japanese.',
    recommendedVramGb: 5,
  },
  {
    id: 'dl-llama-3.2-11b-vision',
    name: 'Llama 3.2 11B Vision Instruct',
    family: 'Llama 3.2 Multimodal',
    quantization: 'Q4_K_M',
    format: 'GGUF',
    totalSizeGb: 6.3,
    downloadedGb: 6.3,
    percent: 100,
    speedMbPerSec: 0,
    etaText: 'Installed • Verified SHA256',
    status: 'completed',
    capabilities: ['chat', 'vision', 'code'],
    description:
      'Inspects attached images, screenshots, and architectural sketches locally.',
    recommendedVramGb: 6.5,
  },
  {
    id: 'dl-gemma-3-12b-vision',
    name: 'Gemma 3 12B Multimodal',
    family: 'Gemma 3 Architecture',
    quantization: 'Q4_K_M',
    format: 'GGUF',
    totalSizeGb: 7.6,
    downloadedGb: 0,
    percent: 0,
    speedMbPerSec: 0,
    etaText: 'Ready to download',
    status: 'available',
    capabilities: ['chat', 'vision', 'code'],
    description:
      'Strong multilingual vision-language model with 128K context window and fast token generation.',
    recommendedVramGb: 8,
  },
];
