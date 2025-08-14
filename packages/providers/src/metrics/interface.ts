/**
 * Metrics provider interface for observability
 * Supports both OpenTelemetry and AWS CloudWatch backends
 */

export interface MetricLabels {
  [key: string]: string | number | boolean;
}

export interface TimingOptions {
  labels?: MetricLabels;
  unit?: 'ms' | 'seconds' | 'minutes';
}

export interface EventMetadata {
  [key: string]: any;
}

export interface MetricsProvider {
  /**
   * Increment a counter metric
   */
  counter(name: string, value?: number, labels?: MetricLabels): void;

  /**
   * Set a gauge metric value
   */
  gauge(name: string, value: number, labels?: MetricLabels): void;

  /**
   * Record a timing/histogram metric
   */
  timing(name: string, value: number, options?: TimingOptions): void;

  /**
   * Record a custom event with metadata
   */
  event(name: string, metadata?: EventMetadata): void;

  /**
   * Start a timer and return a function to end it
   */
  timer(name: string, labels?: MetricLabels): () => void;

  /**
   * Flush any pending metrics (if applicable)
   */
  flush?(): Promise<void>;

  /**
   * Health check
   */
  healthCheck(): Promise<boolean>;
}

export type MetricsProviderType = 'otel' | 'cloudwatch' | 'noop';

export interface MetricsConfig {
  provider: MetricsProviderType;
  
  // Common config
  serviceName?: string;
  serviceVersion?: string;
  
  // OpenTelemetry config
  otelEndpoint?: string;
  otelHeaders?: Record<string, string>;
  
  // CloudWatch config
  region?: string;
  namespace?: string;
  accessKeyId?: string;
  secretAccessKey?: string;
}