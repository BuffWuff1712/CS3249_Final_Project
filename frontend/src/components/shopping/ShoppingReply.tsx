import { Fragment, type ReactNode } from "react";

function inline(text: string): ReactNode {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) => part.startsWith("**") && part.endsWith("**") ? <strong key={index}>{part.slice(2, -2)}</strong> : <Fragment key={index}>{part}</Fragment>);
}

export function ShoppingReply({ text }: { text: string }) {
  // Existing saved answers also become readable without changing their wording.
  let lines = text.split(/\r?\n/);
  if (!lines.some(line => /^\s*(?:[-*•]|\d+[.)])\s+/.test(line)) && text.length > 280) {
    const sentences = text.split(/(?<=[.!?])\s+(?=[A-Z])/);
    if (sentences.length >= 3) lines = [sentences[0], "", ...sentences.slice(1, -1).map(sentence => `- ${sentence}`), "", sentences.at(-1)!];
  }
  const blocks: ReactNode[] = [];
  let items: string[] = [], paragraphs: string[] = [];
  function flush() {
    if (paragraphs.length) { blocks.push(<p key={blocks.length}>{inline(paragraphs.join("\n"))}</p>); paragraphs = []; }
    if (items.length) { blocks.push(<ul key={blocks.length}>{items.map((item, index) => <li key={index}>{inline(item)}</li>)}</ul>); items = []; }
  }
  for (const line of lines) {
    const bullet = line.match(/^\s*(?:[-*•]|\d+[.)])\s+(.+)$/);
    if (bullet) { if (paragraphs.length) flush(); items.push(bullet[1]); }
    else if (!line.trim()) flush();
    else { if (items.length) flush(); paragraphs.push(line); }
  }
  flush();
  return <div className="cui-chat-answer">{blocks}</div>;
}
