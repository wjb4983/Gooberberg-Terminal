import { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  errorMessage: string | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = { errorMessage: null };

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { errorMessage: error.message };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('Operator console render failure', error, errorInfo);
  }

  public render(): ReactNode {
    if (this.state.errorMessage) {
      return (
        <section className="card">
          <h2>Something went wrong</h2>
          <p className="error">{this.state.errorMessage}</p>
          <p className="muted">The panel crashed, but the rest of the console is still available.</p>
        </section>
      );
    }

    return this.props.children;
  }
}
