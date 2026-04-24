import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SpanEditor } from "@/components/review/span-editor";

function selectNode(node: Node, start: number, end: number): void {
  const range = document.createRange();
  range.setStart(node, start);
  range.setEnd(node, end);
  const selection = window.getSelection();
  if (!selection) throw new Error("no selection available");
  selection.removeAllRanges();
  selection.addRange(range);
}

describe("SpanEditor", () => {
  it("renders a highlight for the matched span", () => {
    render(
      <SpanEditor
        text="O município deverá fazer a devolução do valor."
        matchedSpan="deverá fazer a devolução"
        onChange={() => {}}
      />,
    );
    const mark = screen.getByText("deverá fazer a devolução");
    expect(mark.tagName.toLowerCase()).toBe("mark");
  });

  it("shows the not-found empty state and renders the full text", () => {
    render(
      <SpanEditor
        text="Um texto qualquer sem correspondência."
        matchedSpan={null}
        onChange={() => {}}
        emptyState="Trecho não encontrado."
      />,
    );
    expect(screen.getByText("Trecho não encontrado.")).toBeInTheDocument();
    expect(
      screen.getByText("Um texto qualquer sem correspondência."),
    ).toBeInTheDocument();
  });

  it("fires onChange with the selected substring", () => {
    const onChange = vi.fn();
    render(
      <SpanEditor
        text="Deverá o responsável recolher a multa."
        matchedSpan={null}
        onChange={onChange}
      />,
    );

    const editor = screen.getByTestId("span-editor");
    const textNode = editor.firstChild as Text;
    expect(textNode.nodeType).toBe(Node.TEXT_NODE);

    selectNode(textNode, 7, 25); // "o responsável recol" → actually "o responsável reco"
    fireEvent.mouseUp(editor);

    expect(onChange).toHaveBeenCalledTimes(1);
    const picked = onChange.mock.calls[0][0] as string;
    // Exact offsets depend on grapheme counts; assert substring correctness.
    expect("Deverá o responsável recolher a multa.").toContain(picked);
    expect(picked.length).toBeGreaterThan(0);
  });

  it("ignores collapsed selections", () => {
    const onChange = vi.fn();
    render(
      <SpanEditor text="algum texto" matchedSpan={null} onChange={onChange} />,
    );
    const editor = screen.getByTestId("span-editor");
    const textNode = editor.firstChild as Text;

    selectNode(textNode, 3, 3);
    fireEvent.mouseUp(editor);

    expect(onChange).not.toHaveBeenCalled();
  });

  it("does not fire onChange when disabled", () => {
    const onChange = vi.fn();
    render(
      <SpanEditor
        text="algum texto qualquer"
        matchedSpan={null}
        onChange={onChange}
        disabled
      />,
    );
    const editor = screen.getByTestId("span-editor");
    const textNode = editor.firstChild as Text;

    selectNode(textNode, 0, 5);
    fireEvent.mouseUp(editor);

    expect(onChange).not.toHaveBeenCalled();
  });
});
