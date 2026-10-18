import type { LayerSpan, Source } from "./api";

const ORDER: Source[] = ["A1", "A2", "A3"];

/** The document text cut at every span boundary; each piece carries the annotators covering it. */
export function LayeredText({
  text,
  layers,
  focus,
}: {
  text: string;
  layers: Record<Source, LayerSpan[]>;
  focus: LayerSpan[];
}) {
  const cuts = new Set<number>([0, text.length]);
  for (const source of ORDER) for (const s of layers[source]) cuts.add(s.char_start).add(s.char_end);
  for (const s of focus) cuts.add(s.char_start).add(s.char_end);
  const bounds = [...cuts].sort((a, b) => a - b);

  const pieces = [];
  for (let i = 0; i + 1 < bounds.length; i++) {
    const [a, b] = [bounds[i], bounds[i + 1]];
    const covering = ORDER.filter((source) => layers[source].some((s) => s.char_start <= a && b <= s.char_end));
    const focused = focus.some((s) => s.char_start <= a && b <= s.char_end);
    if (!covering.length && !focused) {
      pieces.push(text.slice(a, b));
      continue;
    }
    const title = ORDER.map((source) => {
      const span = layers[source].find((s) => s.char_start <= a && b <= s.char_end);
      return span ? `${source}: ${span.label}` : null;
    })
      .filter(Boolean)
      .join(" · ");
    const cls = ["seg", ...covering.map((s) => s.toLowerCase()), focused ? "focus" : ""].join(" ").trim();
    pieces.push(
      <span key={a} className={cls} title={title}>
        {text.slice(a, b)}
      </span>,
    );
  }
  return <div className="text layered">{pieces}</div>;
}
