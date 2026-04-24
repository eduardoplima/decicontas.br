"use client";

import { useMemo, useRef } from "react";

import { cn } from "@/lib/utils";

type SpanEditorProps = {
  text: string;
  matchedSpan: string | null;
  onChange: (span: string) => void;
  disabled?: boolean;
  emptyState?: React.ReactNode;
};

/**
 * Minimal single-span editor:
 *   - renders the full text in a scrollable block,
 *   - highlights `matchedSpan` (first occurrence),
 *   - calls `onChange` with the substring the reviewer highlights.
 *
 * Only strings cross the boundary — we never emit offsets. See
 * frontend/CLAUDE.md "Span editor behavior".
 */
export function SpanEditor({
  text,
  matchedSpan,
  onChange,
  disabled,
  emptyState,
}: SpanEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  const parts = useMemo(() => {
    if (!matchedSpan) return null;
    const idx = text.indexOf(matchedSpan);
    if (idx === -1) return null;
    return {
      before: text.slice(0, idx),
      hit: text.slice(idx, idx + matchedSpan.length),
      after: text.slice(idx + matchedSpan.length),
    };
  }, [text, matchedSpan]);

  function handleMouseUp() {
    if (disabled) return;
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return;
    const container = containerRef.current;
    if (!container) return;
    // Only treat selections that originate inside this container.
    const anchor = selection.anchorNode;
    const focus = selection.focusNode;
    if (!anchor || !focus) return;
    if (!container.contains(anchor) || !container.contains(focus)) return;
    const picked = selection.toString().trim();
    if (picked.length === 0) return;
    onChange(picked);
  }

  return (
    <div
      ref={containerRef}
      onMouseUp={handleMouseUp}
      data-testid="span-editor"
      className={cn(
        "max-h-[70vh] overflow-y-auto whitespace-pre-wrap rounded-lg border bg-card p-4 text-sm leading-relaxed",
        disabled && "opacity-60",
      )}
    >
      {parts ? (
        <>
          {parts.before}
          <mark className="rounded bg-yellow-200 px-0.5">{parts.hit}</mark>
          {parts.after}
        </>
      ) : (
        <>
          {emptyState ? (
            <div className="mb-3 rounded border border-dashed bg-muted p-2 text-xs text-muted-foreground">
              {emptyState}
            </div>
          ) : null}
          {text}
        </>
      )}
    </div>
  );
}
