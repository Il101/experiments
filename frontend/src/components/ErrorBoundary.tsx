/**
 * Error Boundary component to catch and handle React errors gracefully
 * Prevents entire app from crashing when a component throws an error
 */

import React, { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { Alert, Button, Container } from 'react-bootstrap';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Log error to console
    console.error('ErrorBoundary caught an error:', error);
    console.error('Error info:', errorInfo);

    // Update state with error details
    this.setState({
      error,
      errorInfo,
    });

    // Call optional error handler
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // In production, you might want to send this to an error reporting service
    // Example: Sentry.captureException(error, { contexts: { react: { componentStack: errorInfo.componentStack } } });
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  handleReload = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI
      return (
        <Container className="mt-5">
          <Alert variant="danger">
            <Alert.Heading>
              <i className="bi bi-exclamation-triangle-fill me-2"></i>
              Something went wrong
            </Alert.Heading>
            <p className="mb-0">
              The application encountered an unexpected error. Please try reloading the page.
            </p>
            
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <div className="mt-3">
                <hr />
                <h6>Error Details (Development Only):</h6>
                <pre className="text-danger" style={{ fontSize: '0.85rem' }}>
                  {this.state.error.toString()}
                </pre>
                
                {this.state.errorInfo && (
                  <>
                    <h6 className="mt-3">Component Stack:</h6>
                    <pre className="text-muted" style={{ fontSize: '0.75rem', maxHeight: '200px', overflow: 'auto' }}>
                      {this.state.errorInfo.componentStack}
                    </pre>
                  </>
                )}
              </div>
            )}
            
            <hr />
            <div className="d-flex gap-2">
              <Button variant="primary" onClick={this.handleReset}>
                Try Again
              </Button>
              <Button variant="outline-secondary" onClick={this.handleReload}>
                Reload Page
              </Button>
            </div>
          </Alert>
        </Container>
      );
    }

    return this.props.children;
  }
}

/**
 * Hook-based error boundary for functional components
 * Note: This is a workaround since React hooks don't support error boundaries directly
 */
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  fallback?: ReactNode,
  onError?: (error: Error, errorInfo: ErrorInfo) => void
): React.FC<P> {
  return (props: P) => (
    <ErrorBoundary fallback={fallback} onError={onError}>
      <Component {...props} />
    </ErrorBoundary>
  );
}
