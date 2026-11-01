import { Fragment, type ReactNode } from "react";

function inline(text: string): ReactNode {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) => part.startsWith("**") && part.endsWith("**") ? <strong key={index}>{part.slice(2, -2)}</strong> : <Fragment key={index}>{part}</Fragment>);
}

function tableCells(line: string) {
  return line.trim().replace(/^\||\|$/g, "").split(/(?<!\\)\|/).map(cell => cell.trim().replace(/\\([\\|])/g, "$1"));
}

export function ShoppingReply({ text }: { text: string }) {
  // Existing saved answers also become readable without changing their wording.
  let lines = text.split(/\r?\n/);
  if (!lines.some(line => line.trim().startsWith("|")) && !lines.some(line => /^\s*(?:[-*•]|\d+[.)])\s+/.test(line)) && text.length > 280) {
    const sentences = text.split(/(?<=[.!?])\s+(?=[A-Z])/);
    if (sentences.length >= 3) lines = [sentences[0], "", ...sentences.slice(1, -1).map(sentence => `- ${sentence}`), "", sentences.at(-1)!];
  }
  const blocks: ReactNode[] = [];
  let items: string[] = [], paragraphs: string[] = [];
  function flush() {
    if (paragraphs.length) { blocks.push(<p key={blocks.length}>{inline(paragraphs.join("\n"))}</p>); paragraphs = []; }
    if (items.length) { blocks.push(<ul key={blocks.length}>{items.map((item, index) => <li key={index}>{inline(item)}</li>)}</ul>); items = []; }
  }
  for (let index = 0; index < lines.length; index++) {
    const line = lines[index];
    const headers = tableCells(line);
    const divider = lines[index + 1];
    if (line.trim().startsWith("|") && divider && tableCells(divider).length === headers.length && tableCells(divider).every(cell => /^:?-{3,}:?$/.test(cell))) {
      flush();
      const rows: string[][] = [];
      index += 2;
      while (index < lines.length && lines[index].trim().startsWith("|") && tableCells(lines[index]).length === headers.length) rows.push(tableCells(lines[index++]));
      index--;
      blocks.push(<div className="cui-reply-table" key={blocks.length}><table aria-label="Matching model options"><thead><tr>{headers.map((header, column) => <th scope="col" key={column}>{inline(header)}</th>)}</tr></thead><tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, column) => <td key={column}><span className="cui-reply-cell-label" aria-hidden="true">{headers[column]}</span>{inline(cell)}</td>)}</tr>)}</tbody></table></div>);
      continue;
    }
    const bullet = line.match(/^\s*(?:[-*•]|\d+[.)])\s+(.+)$/);
    if (bullet) { if (paragraphs.length) flush(); items.push(bullet[1]); }
    else if (!line.trim()) flush();
    else { if (items.length) flush(); paragraphs.push(line); }
  }
  flush();
  return <div className="cui-chat-answer">{blocks}</div>;
}
