/**
 * No-op metrics provider for development or when metrics are disabled
 */

import { MetricsProvider, MetricLabels, TimingOptions, EventMetadata } from './interface';

export class NoopMetricsProvider implements MetricsProvider {
  counter(name: string, value?: number, labels?: MetricLabels): void {
    // No-op
  }

  gauge(name: string, value: number, labels?: MetricLabels): void {
    // No-op
  }

  timing(name: string, value: number, options?: TimingOptions): void {
    // No-op
  }

  event(name: string, metadata?: EventMetadata): void {
    // No-op
  }

  timer(name: string, labels?: MetricLabels): () => void {
    return () => {
      // No-op
    };
  }

  async flush(): Promise<void> {
    // No-op
  }

  async healthCheck(): Promise<boolean> {
    return true;
  }
}