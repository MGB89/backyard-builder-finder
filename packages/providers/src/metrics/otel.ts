/**
 * OpenTelemetry metrics provider implementation
 */

import { metrics } from '@opentelemetry/api';
import { PeriodicExportingMetricReader } from '@opentelemetry/sdk-metrics';
import { OTLPMetricExporter } from '@opentelemetry/exporter-metrics-otlp-http';
import { MeterProvider } from '@opentelemetry/sdk-metrics';
import { Resource } from '@opentelemetry/resources';
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions';

import { MetricsProvider, MetricLabels, TimingOptions, EventMetadata, MetricsConfig } from './interface';

export class OTelMetricsProvider implements MetricsProvider {
  private meterProvider: MeterProvider;
  private meter: any;
  private counters: Map<string, any> = new Map();
  private gauges: Map<string, any> = new Map();
  private histograms: Map<string, any> = new Map();

  constructor(config: MetricsConfig) {
    // Create resource with service information
    const resource = new Resource({
      [SemanticResourceAttributes.SERVICE_NAME]: config.serviceName || 'backyard-builder',
      [SemanticResourceAttributes.SERVICE_VERSION]: config.serviceVersion || '1.0.0',
    });

    // Create OTLP exporter
    const exporter = new OTLPMetricExporter({
      url: config.otelEndpoint || 'http://localhost:4318/v1/metrics',
      headers: config.otelHeaders || {}
    });

    // Create metric reader
    const reader = new PeriodicExportingMetricReader({
      exporter,
      exportIntervalMillis: 10000, // Export every 10 seconds
    });

    // Create meter provider
    this.meterProvider = new MeterProvider({
      resource,
      readers: [reader]
    });

    // Set global meter provider
    metrics.setGlobalMeterProvider(this.meterProvider);

    // Get meter instance
    this.meter = metrics.getMeter('backyard-builder-metrics', '1.0.0');
  }

  counter(name: string, value: number = 1, labels?: MetricLabels): void {
    try {
      let counter = this.counters.get(name);
      if (!counter) {
        counter = this.meter.createCounter(name, {
          description: `Counter metric: ${name}`
        });
        this.counters.set(name, counter);
      }

      counter.add(value, labels || {});
    } catch (error) {
      console.error('Failed to record counter metric:', error);
    }
  }

  gauge(name: string, value: number, labels?: MetricLabels): void {
    try {
      let gauge = this.gauges.get(name);
      if (!gauge) {
        gauge = this.meter.createUpDownCounter(name, {
          description: `Gauge metric: ${name}`
        });
        this.gauges.set(name, gauge);
      }

      // For gauge behavior, we need to track the last value
      // This is a simplified implementation
      gauge.add(value, labels || {});
    } catch (error) {
      console.error('Failed to record gauge metric:', error);
    }
  }

  timing(name: string, value: number, options?: TimingOptions): void {
    try {
      let histogram = this.histograms.get(name);
      if (!histogram) {
        histogram = this.meter.createHistogram(name, {
          description: `Timing metric: ${name}`,
          unit: options?.unit || 'ms'
        });
        this.histograms.set(name, histogram);
      }

      histogram.record(value, options?.labels || {});
    } catch (error) {
      console.error('Failed to record timing metric:', error);
    }
  }

  event(name: string, metadata?: EventMetadata): void {
    // Events can be recorded as counter metrics with metadata as labels
    const labels: MetricLabels = {};
    
    if (metadata) {
      // Convert metadata to string labels (OTEL requirement)
      for (const [key, value] of Object.entries(metadata)) {
        if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
          labels[key] = value;
        } else {
          labels[key] = String(value);
        }
      }
    }

    this.counter(`events.${name}`, 1, labels);
  }

  timer(name: string, labels?: MetricLabels): () => void {
    const startTime = Date.now();
    
    return () => {
      const duration = Date.now() - startTime;
      this.timing(name, duration, { labels });
    };
  }

  async flush(): Promise<void> {
    try {
      await this.meterProvider.forceFlush();
    } catch (error) {
      console.error('Failed to flush metrics:', error);
    }
  }

  async healthCheck(): Promise<boolean> {
    try {
      // Test by recording a simple metric
      this.counter('health_check', 1, { status: 'ok' });
      return true;
    } catch (error) {
      console.error('OTel metrics provider health check failed:', error);
      return false;
    }
  }

  async shutdown(): Promise<void> {
    try {
      await this.meterProvider.shutdown();
    } catch (error) {
      console.error('Failed to shutdown metrics provider:', error);
    }
  }
}