/**
 * Metrics provider factory and exports
 */

import { MetricsProvider, MetricsConfig, MetricsProviderType } from './interface';
import { OTelMetricsProvider } from './otel';
import { CloudWatchMetricsProvider } from './cloudwatch';
import { NoopMetricsProvider } from './noop';

export * from './interface';
export { OTelMetricsProvider } from './otel';
export { CloudWatchMetricsProvider } from './cloudwatch';
export { NoopMetricsProvider } from './noop';

/**
 * Create a metrics provider instance based on configuration
 */
export function createMetricsProvider(config: MetricsConfig): MetricsProvider {
  switch (config.provider) {
    case 'otel':
      return new OTelMetricsProvider(config);
    case 'cloudwatch':
      return new CloudWatchMetricsProvider(config);
    case 'noop':
      return new NoopMetricsProvider();
    default:
      throw new Error(`Unsupported metrics provider: ${config.provider}`);
  }
}

/**
 * Create metrics provider from environment variables
 */
export function createMetricsProviderFromEnv(): MetricsProvider {
  const provider = (process.env.METRICS_PROVIDER as MetricsProviderType) || 'otel';
  
  const config: MetricsConfig = {
    provider,
    serviceName: process.env.SERVICE_NAME || 'backyard-builder',
    serviceVersion: process.env.SERVICE_VERSION || '1.0.0'
  };

  if (provider === 'otel') {
    config.otelEndpoint = process.env.OTEL_EXPORTER_OTLP_METRICS_ENDPOINT;
    
    // Parse headers from environment variable
    if (process.env.OTEL_EXPORTER_OTLP_HEADERS) {
      const headers: Record<string, string> = {};
      const headerPairs = process.env.OTEL_EXPORTER_OTLP_HEADERS.split(',');
      
      for (const pair of headerPairs) {
        const [key, value] = pair.split('=');
        if (key && value) {
          headers[key.trim()] = value.trim();
        }
      }
      
      config.otelHeaders = headers;
    }
  } else if (provider === 'cloudwatch') {
    config.region = process.env.AWS_REGION || 'us-west-2';
    config.namespace = process.env.CLOUDWATCH_NAMESPACE || 'BackyardBuilder';
    config.accessKeyId = process.env.AWS_ACCESS_KEY_ID;
    config.secretAccessKey = process.env.AWS_SECRET_ACCESS_KEY;
  }

  return createMetricsProvider(config);
}