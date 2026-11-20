import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WorldPlanAgentAnswer } from "./WorldPlanAgentAnswer";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("WorldPlanAgentAnswer", () => {
  it("activates only admitted session citations and keeps other local or unsafe links inert", () => {
    const url="/play?world=one&run=11111111-1111-4111-8111-111111111111&evidence_revision=54";
    const answer=`[Saved reflections](${url}) [Other page](/build?world=other) [Unsafe](javascript:alert)`;
    const view=render(<WorldPlanAgentAnswer answer={answer}/>);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    view.rerender(<WorldPlanAgentAnswer answer={answer} allowedInternalLinks={[url,"javascript:alert"]}/>);
    expect(screen.getByRole("link",{name:"Saved reflections"})).toHaveAttribute("href",url);
    expect(screen.getAllByRole("link")).toHaveLength(1);
  });

  it("renders paragraphs, bold emphasis, lists, and embedded reference labels", () => {
    const answer = [
      "**Saved Plan:** The party reaches the warehouse.",
      "",
      "**Evidence:** Exact support remains visible beside the answer.",
      "",
      "- Lysandra watches the loading bay.",
      "- Check the upper windows.",
      "",
      "The party can ask [Lysandra Ironveil](dmb-node:lysandra-ironveil) for help.",
    ].join("\n");
    const { container } = render(<WorldPlanAgentAnswer answer={answer} />);

    expect(container.querySelectorAll(".world-plan-agent-answer > p")).toHaveLength(3);
    expect(container.querySelectorAll(".world-plan-agent-answer > ul > li")).toHaveLength(2);
    expect(container.querySelectorAll("strong")).toHaveLength(2);
    const reference = container.querySelector('[data-plan-card-reference="graph"]');
    expect(reference?.textContent).toBe("Lysandra Ironveil");
    expect(container.textContent).toContain("Saved Plan:");
    expect(container.textContent).toContain("Evidence:");
    expect(container.textContent).toContain("Exact support remains visible beside the answer.");
  });

  it("shows unsupported HTML, unsafe links, and media as escaped source without executing or fetching", () => {
    const request = vi.fn();
    vi.stubGlobal("fetch", request);
    const answer = [
      "<script>window.compromised = true</script>",
      "",
      "[Open this](javascript:alert(1))",
      "",
      "![remote portrait](https://media.example.invalid/portrait.png)",
      "",
      "<iframe src=\"https://media.example.invalid/embed\"></iframe>",
    ].join("\n");
    const { container } = render(<WorldPlanAgentAnswer answer={answer} />);

    expect(container.textContent).toContain("<script>window.compromised = true</script>");
    expect(container.textContent).toContain("[Open this](javascript:alert(1))");
    expect(container.textContent).toContain("![remote portrait](https://media.example.invalid/portrait.png)");
    expect(container.querySelector("script, iframe, img, video, audio")).toBeNull();
    expect(container.querySelector("a[href^='javascript:']")).toBeNull();
    expect(request).not.toHaveBeenCalled();
    expect((window as Window & { compromised?: boolean }).compromised).toBeUndefined();
  });

  it("renders hard breaks without flattening the rest of the Markdown", () => {
    const answer = "First paragraph.\n\nSecond paragraph with a hard break\\\nnext line.";
    const { container } = render(<WorldPlanAgentAnswer answer={answer} />);

    expect(container.textContent).toContain("Second paragraph with a hard break");
    expect(container.querySelectorAll("br")).toHaveLength(1);
    expect(container.querySelector("img, iframe, script")).toBeNull();
  });

  it("keeps the complete answer stable when evidence segments change", () => {
    const answer = "**Saved Plan:** First claim.\n**Evidence:** Second claim.";
    const { container, rerender } = render(<WorldPlanAgentAnswer answer={answer} />);

    rerender(<WorldPlanAgentAnswer answer={answer} displaySegments={["**Saved Plan:** First claim.", "**Evidence:** Second claim."]} />);
    expect(container.querySelectorAll("strong")).toHaveLength(2);

    rerender(<WorldPlanAgentAnswer answer={answer} displaySegments={["unmatched segment"]} />);
    expect(container.textContent).toContain("Saved Plan:");
    expect(container.textContent).toContain("Evidence:");
    expect(container.querySelectorAll(".world-plan-agent-answer > .world-plan-agent-answer")).toHaveLength(0);
  });

  it("renders aligned tables and fenced code across evidence segment boundaries", () => {
    const segments = ["## People\n\n| Name | Job |", "| :--- | ---: |\n| **Nella** | Baker |\n\n```md", "# Literal heading\n```"];
    const { container } = render(<WorldPlanAgentAnswer answer={segments.join("\n")} displaySegments={segments} />);
    expect(screen.getByRole("heading", { name: "People" })).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Job" })).toHaveStyle({ textAlign: "right" });
    expect(screen.getByRole("cell", { name: "Nella" }).querySelector("strong")).not.toBeNull();
    expect(container.querySelector("pre code")?.textContent).toBe("# Literal heading");
  });

  it("supports nested lists, task lists, quotes and safe links alongside inert content", () => {
    const answer = "*Emphasis* and ~~old~~ and `code`\n\n> A quote\n\n3. Third\n   - Child\n\n- [x] Ready\n\n[Source](https://example.com) [Local](/api/action)\n\n<script>bad()</script>\n\n**Still formatted**";
    const { container } = render(<WorldPlanAgentAnswer answer={answer} />);
    expect(container.querySelector("ol")).toHaveAttribute("start", "3");
    expect(container.querySelector("ol ul li")?.textContent).toContain("Child");
    expect(container.querySelector("blockquote")?.textContent).toContain("A quote");
    expect(screen.getByRole("checkbox")).toBeChecked();
    expect(screen.getByRole("checkbox")).toBeDisabled();
    expect(screen.getByRole("link", { name: "Source" })).toHaveAttribute("href", "https://example.com");
    expect(screen.queryByRole("link", { name: "Local" })).not.toBeInTheDocument();
    expect(container.querySelector("script, img")).toBeNull();
    expect(screen.getByText("Still formatted").tagName).toBe("STRONG");
  });

  it("marks only short numeric columns for compact content-based sizing", () => {
    render(<WorldPlanAgentAnswer answer={'| d20 | Name | Detail |\n|---:|---|---|\n| 1 | Mara | Watches the gate |\n| 20 | Pell | Keeps the peace |'} />);
    expect(screen.getByRole('columnheader', { name: 'd20' })).toHaveAttribute('data-compact-column', 'true');
    expect(screen.getByRole('cell', { name: '20' })).toHaveAttribute('data-compact-column', 'true');
    expect(screen.getByRole('columnheader', { name: 'Name' })).not.toHaveAttribute('data-compact-column');
  });
});

describe("stable Buddy answer rendering", () => {
  it("retains plain answer nodes on unrelated refreshes and updates changed text", () => {
    const view = render(<WorldPlanAgentAnswer answer="A verified answer." />);
    const reply = screen.getByText("A verified answer.");
    view.rerender(<WorldPlanAgentAnswer answer="A verified answer." />);
    expect(screen.getByText("A verified answer.")).toBe(reply);
    view.rerender(<WorldPlanAgentAnswer answer="A newer verified answer." />);
    expect(screen.queryByText("A verified answer.")).not.toBeInTheDocument();
    expect(screen.getByText("A newer verified answer.")).toBeInTheDocument();
  });
  it("retains structured segments when history delivers equivalent new arrays", () => {
    const segments = ["First paragraph.\n", "Second paragraph."];
    const view = render(<WorldPlanAgentAnswer answer={segments.join("\n")} displaySegments={segments} />);
    const first = screen.getByText("First paragraph.");
    const second = screen.getByText("Second paragraph.");
    view.rerender(<WorldPlanAgentAnswer answer={segments.join("\n")} displaySegments={[...segments]} />);
    expect(screen.getByText("First paragraph.")).toBe(first);
    expect(screen.getByText("Second paragraph.")).toBe(second);
    const updated = ["First paragraph.\n", "Updated second paragraph."];
    view.rerender(<WorldPlanAgentAnswer answer={updated.join("\n")} displaySegments={updated} />);
    expect(screen.getByText("First paragraph.")).toBe(first);
    expect(screen.queryByText("Second paragraph.")).not.toBeInTheDocument();
    expect(screen.getByText("Updated second paragraph.")).toBeInTheDocument();
  });
});

it('places verified citations beside repeated claims without splitting Markdown blocks', () => {
  const first = vi.fn(), second = vi.fn();
  const segments = ['**Same fact.**', 'Same fact.', '', '- Final fact.'];
  const { container } = render(<WorldPlanAgentAnswer answer={segments.join('\n')} displaySegments={segments}
    inlineCitations={[{segmentIndex:0,label:'1',title:'Source one · revision one',onOpen:first},
      {segmentIndex:1,label:'2',title:'Source two · revision two',onOpen:second},
      {segmentIndex:3,label:'3',title:'Source three',onOpen:vi.fn()}]} />);
  expect(container.querySelectorAll('strong')).toHaveLength(1);
  expect(container.querySelectorAll('ul > li')).toHaveLength(1);
  screen.getByRole('button',{name:'Open source 2'}).click();
  expect(second).toHaveBeenCalledOnce(); expect(first).not.toHaveBeenCalled();
  expect(screen.getByRole('button',{name:'Open source 1'}).closest('p')).not.toBeNull();
  expect(screen.getByRole('button',{name:'Open source 3'}).closest('li')).not.toBeNull();
});

it('does not infer citation placement from mismatched or absent complete segments', () => {
  const props = {answer:'A fact. Another fact.',inlineCitations:[{segmentIndex:0,label:'1',title:'Exact source',onOpen:vi.fn()}]};
  const view = render(<WorldPlanAgentAnswer {...props} displaySegments={['A fact.']} />);
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
  view.rerender(<WorldPlanAgentAnswer {...props} />);
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
  expect(screen.getByText(props.answer)).toBeInTheDocument();
});

it('keeps citation controls outside links and code while preserving the original answer', () => {
  const segments = ['[Verified source](https://example.org)', '', '`literal`'];
  const {container} = render(<WorldPlanAgentAnswer answer={segments.join('\n')} displaySegments={segments}
    inlineCitations={[{segmentIndex:0,label:'1',title:'Exact source',onOpen:vi.fn()},
      {segmentIndex:2,label:'2',title:'Other source',onOpen:vi.fn()}]} />);
  expect(container.querySelector('a button, code button')).toBeNull();
  expect(screen.getByRole('link',{name:'Verified source'})).toHaveAttribute('href','https://example.org');
  expect(screen.getAllByRole('button')).toHaveLength(2);
});

it('places first and final repeated table-row citations inside their exact last cells', () => {
  const first = vi.fn(), final = vi.fn();
  const segments = ['| Place | Fact |', '| --- | --- |', '| Edge | Road crosses swamp |', '| Edge | Road crosses swamp |'];
  const {container} = render(<WorldPlanAgentAnswer answer={segments.join('\n')} displaySegments={segments}
    inlineCitations={[{segmentIndex:2,label:'1',title:'First passage',onOpen:first},
      {segmentIndex:3,label:'2',title:'Later passage',onOpen:final}]} />);
  const rows = container.querySelectorAll('tbody > tr');
  expect(rows).toHaveLength(2);
  expect(screen.getByRole('button',{name:'Open source 1'}).closest('tr')).toBe(rows[0]);
  expect(screen.getByRole('button',{name:'Open source 2'}).closest('tr')).toBe(rows[1]);
  expect(container.querySelector('tr > button, table > button')).toBeNull();
  screen.getByRole('button',{name:'Open source 2'}).click();
  expect(final).toHaveBeenCalledOnce(); expect(first).not.toHaveBeenCalled();
});
