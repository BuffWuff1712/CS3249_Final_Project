"use client";
import { useEffect, useRef, useState, type ReactNode } from "react";

const KEY = "beany-pane-split";
const DEFAULT = 57;
const HANDLE = 24;

export function ResizablePanes({ children }: { children: ReactNode }) {
  const container = useRef<HTMLDivElement>(null);
  const [split, setSplit] = useState(DEFAULT);
  const [width, setWidth] = useState(0);
  const [dragging, setDragging] = useState(false);
  const current = useRef(DEFAULT);
  const available = Math.max(1, width - HANDLE);
  const minimum = width ? Math.min(50, 320 / available * 100) : 0;
  const shown = Math.max(minimum, Math.min(100 - minimum, split));
  useEffect(() => {
    try {
      const saved = localStorage.getItem(KEY);
      const value = saved === null ? DEFAULT : Number(saved);
      if (Number.isFinite(value) && value > 0 && value < 100) { current.current = value; setSplit(value); }
    } catch { /* Storage is optional. */ }
    const observer = new ResizeObserver(entries => setWidth(entries[0].contentRect.width));
    if (container.current) observer.observe(container.current);
    return () => observer.disconnect();
  }, []);
  function update(value: number) {
    current.current = Math.max(minimum, Math.min(100 - minimum, value));
    setSplit(current.current);
  }
  function save() { try { localStorage.setItem(KEY, String(current.current)); } catch { /* Storage is optional. */ } }
  function finish() { setDragging(false); save(); }
  return <div ref={container} className={`cui-columns cui-resizable${width > 0 && width < 664 ? " cui-panes-stacked" : ""}${dragging ? " cui-panes-dragging" : ""}`}
    style={{ "--pane-left": `${shown}fr`, "--pane-right": `${100 - shown}fr` } as React.CSSProperties}>
    {children}
    <div className="cui-pane-controls">
      <div className="cui-pane-divider" role="separator" tabIndex={0} aria-label="Resize conversation and product panes" aria-orientation="vertical"
        aria-controls="shopping-conversation shopping-decision" aria-valuemin={Math.ceil(minimum)} aria-valuemax={Math.floor(100 - minimum)} aria-valuenow={Math.round(shown)} aria-valuetext={`Conversation ${Math.round(shown)}%, products ${Math.round(100 - shown)}%`}
        onPointerDown={event => { if (event.button !== 0) return; event.preventDefault(); event.currentTarget.setPointerCapture(event.pointerId); setDragging(true); }}
        onPointerMove={event => { if (!event.currentTarget.hasPointerCapture(event.pointerId)) return; const bounds = container.current!.getBoundingClientRect(); update((event.clientX - bounds.left - HANDLE / 2) / available * 100); }}
        onPointerUp={event => { if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId); finish(); }}
        onPointerCancel={finish} onLostPointerCapture={() => setDragging(false)}
        onKeyDown={event => { const value = event.key === "ArrowLeft" ? shown - 2 : event.key === "ArrowRight" ? shown + 2 : event.key === "Home" ? minimum : event.key === "End" ? 100 - minimum : null; if (value !== null) { event.preventDefault(); update(value); save(); } }} />
    </div>
  </div>;
}
