import { useState, type ReactNode } from 'react';
import { Check, Copy } from 'lucide-react';

// A deliberately small Markdown subset for model replies: fenced code, headings, lists,
// block quotes, rules, bold, italic and inline code. Links are shown as text because the
// desktop shell never navigates away from Sulvana.

type ListItem = { depth: number; marker: string; text: string };
type Block =
  | { type: 'code'; language: string; text: string }
  | { type: 'heading'; level: number; text: string }
  | { type: 'list'; items: ListItem[] }
  | { type: 'quote'; text: string }
  | { type: 'rule' }
  | { type: 'paragraph'; text: string };

const FENCE = /^\s*(```+|~~~+)\s*([\w.+#-]*)\s*$/;
const HEADING = /^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$/;
const RULE = /^\s{0,3}([-*_])(?:\s*\1){2,}\s*$/;
const ITEM = /^(\s*)([-*+]|\d{1,9}[.)])\s+(.*)$/;
const QUOTE = /^\s{0,3}>\s?(.*)$/;

function parse(source: string): Block[] {
  const lines = source.replace(/\r\n?/g, '\n').split('\n');
  const blocks: Block[] = [];
  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) { index++; continue; }
    const fence = FENCE.exec(line);
    if (fence) {
      // An unclosed fence is normal while a reply is still streaming: show it as code already.
      const closes = (candidate: string) => {
        const match = FENCE.exec(candidate);
        return !!match && !match[2] && match[1][0] === fence[1][0];
      };
      const body: string[] = [];
      index++;
      while (index < lines.length && !closes(lines[index])) body.push(lines[index++]);
      index++;
      blocks.push({ type: 'code', language: fence[2], text: body.join('\n') });
      continue;
    }
    const heading = HEADING.exec(line);
    if (heading) { blocks.push({ type: 'heading', level: heading[1].length, text: heading[2] }); index++; continue; }
    if (RULE.test(line)) { blocks.push({ type: 'rule' }); index++; continue; }
    if (QUOTE.test(line)) {
      const quoted: string[] = [];
      while (index < lines.length && QUOTE.test(lines[index])) quoted.push(QUOTE.exec(lines[index++])![1]);
      blocks.push({ type: 'quote', text: quoted.join('\n') });
      continue;
    }
    if (ITEM.test(line)) {
      const items: ListItem[] = [];
      while (index < lines.length && lines[index].trim() && !FENCE.test(lines[index])) {
        const item = ITEM.exec(lines[index]);
        if (item) {
          const marker = /\d/.test(item[2]) ? item[2].replace(')', '.') : '•';
          items.push({ depth: Math.min(4, Math.floor(item[1].replace(/\t/g, '  ').length / 2)), marker, text: item[3] });
        } else if (/^\s+\S/.test(lines[index])) {
          items[items.length - 1].text += '\n' + lines[index].trim();
        } else break;
        index++;
      }
      blocks.push({ type: 'list', items });
      continue;
    }
    const paragraph: string[] = [];
    while (index < lines.length && lines[index].trim() && !FENCE.test(lines[index]) && !HEADING.test(lines[index])
      && !RULE.test(lines[index]) && !QUOTE.test(lines[index]) && !(paragraph.length && ITEM.test(lines[index]))) {
      paragraph.push(lines[index++]);
    }
    blocks.push({ type: 'paragraph', text: paragraph.join('\n') });
  }
  return blocks;
}

const INLINE = /(`[^`\n]+`|\*\*[^\n]+?\*\*|\*[^*\n]+\*|\[[^\]\n]+\]\([^)\s]+\))/g;

function inline(text: string, depth = 0): ReactNode[] {
  return text.split(INLINE).map((piece, index) => {
    if (piece.length > 2 && piece.startsWith('`') && piece.endsWith('`')) {
      return <code className="inline-code" key={index}>{piece.slice(1, -1)}</code>;
    }
    if (piece.length > 4 && piece.startsWith('**') && piece.endsWith('**') && piece.slice(2, -2).trim()) {
      return <strong key={index}>{depth < 2 ? inline(piece.slice(2, -2), depth + 1) : piece.slice(2, -2)}</strong>;
    }
    if (piece.length > 2 && piece.startsWith('*') && piece.endsWith('*') && !piece.startsWith('**')) {
      const inner = piece.slice(1, -1);
      // "2 * 3 * 4" is arithmetic, not emphasis.
      if (inner === inner.trim()) return <em key={index}>{inner}</em>;
    }
    const link = /^\[([^\]\n]+)\]\(([^)\s]+)\)$/.exec(piece);
    if (link) {
      return <span key={index}><span className="md-link">{link[1]}</span>{link[2] !== link[1] && <span className="md-url"> ({link[2]})</span>}</span>;
    }
    return piece;
  });
}

function CodeBlock({ language, text, onCopy }: { language: string; text: string; onCopy: (text: string) => Promise<void> }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await onCopy(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch { /* The surrounding message still offers Copy. */ }
  };
  return <div className="code-block">
    <div className="code-heading">
      <span>{language || 'Code'}</span>
      <button type="button" onClick={() => void copy()} aria-label="Copy code">
        {copied ? <Check size={13} /> : <Copy size={13} />} {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
    <pre tabIndex={0}><code>{text}</code></pre>
  </div>;
}

export function Markdown({ text, onCopy }: { text: string; onCopy: (text: string) => Promise<void> }) {
  return <>{parse(text).map((block, index) => {
    switch (block.type) {
      case 'code':
        return <CodeBlock key={index} language={block.language} text={block.text} onCopy={onCopy} />;
      case 'heading': {
        const Tag = block.level <= 1 ? 'h3' : block.level === 2 ? 'h4' : 'h5';
        return <Tag className="md-heading" dir="auto" key={index}>{inline(block.text)}</Tag>;
      }
      case 'rule':
        return <hr className="md-rule" key={index} />;
      case 'quote':
        return <blockquote className="md-quote message-body" dir="auto" key={index}>{inline(block.text)}</blockquote>;
      case 'list':
        return <div className="md-list" role="list" key={index}>{block.items.map((item, position) =>
          <div className="md-item" role="listitem" style={{ marginInlineStart: item.depth * 18 }} key={position}>
            <span className="md-marker" aria-hidden={item.marker === '•'}>{item.marker}</span>
            <div className="message-body" dir="auto">{inline(item.text)}</div>
          </div>)}</div>;
      default:
        return <div className="message-body" dir="auto" key={index}>{inline(block.text)}</div>;
    }
  })}</>;
}
