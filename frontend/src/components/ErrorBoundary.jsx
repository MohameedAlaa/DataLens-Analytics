import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Graceful error logging without exposing secrets
    console.error('ErrorBoundary caught an error:', error?.message || error, errorInfo?.componentStack);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="p-6 rounded-2xl border border-red-500/20 bg-red-500/5 my-4 text-center space-y-3">
          <div className="flex items-center justify-center gap-2 text-red-400">
            <AlertCircle className="w-5 h-5" />
            <h3 className="heading-xs font-bold text-red-400">
              {this.props.title || 'Component Rendering Error'}
            </h3>
          </div>
          <p className="body-xs text-content-secondary max-w-md mx-auto">
            {this.state.error?.message || 'An unexpected rendering error occurred in this section.'}
          </p>
          <button
            onClick={this.handleReset}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl border border-surface-border bg-surface-elevated text-content-primary body-xs font-semibold hover:bg-surface-card transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5 text-brand-400" />
            <span>Try Again</span>
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
