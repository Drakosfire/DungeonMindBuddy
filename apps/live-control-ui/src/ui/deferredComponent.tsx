import { Component, Suspense, createElement, lazy, useMemo, useState, type ComponentProps, type ComponentType, type ReactNode } from "react";

class DeferredFailure extends Component<{ label: string; retry: () => void; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <section role="alert">
      <p>Could not load {this.props.label}.</p>
      <button type="button" onClick={this.props.retry}>Retry {this.props.label}</button>
    </section>;
    return this.props.children;
  }
}

/** Declare at module scope. Only an explicit failed-load retry replaces the child type. */
export function deferredComponent<T extends ComponentType<any>>(
  load: () => Promise<{ default: T }>, label: string,
): ComponentType<ComponentProps<T>> {
  return function DeferredComponent(props: ComponentProps<T>) {
    const [attempt, setAttempt] = useState(0);
    const Child = useMemo(() => lazy(load), [attempt]);
    return <DeferredFailure key={attempt} label={label} retry={() => setAttempt(value => value + 1)}>
      <Suspense fallback={<p role="status">Loading {label}…</p>}>
        {createElement(Child as ComponentType<ComponentProps<T>>, props)}
      </Suspense>
    </DeferredFailure>;
  };
}
