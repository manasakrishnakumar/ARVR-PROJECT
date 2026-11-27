import { Component, type ReactNode } from "react";

/** Keeps one broken page from blanking the whole app: the header and navigation stay usable. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (!this.state.failed) return this.props.children;
    return <p className="notice error-banner" role="alert">This page could not be shown. Choose another page from the menu, or reload.</p>;
  }
}
