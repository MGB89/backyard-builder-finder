/**
 * AWS CloudWatch metrics provider implementation (stub for future migration)
 */

import { CloudWatch } from 'aws-sdk';
import { MetricsProvider, MetricLabels, TimingOptions, EventMetadata, MetricsConfig } from './interface';

interface PendingMetric {
  MetricName: string;
  Value: number;
  Unit: string;
  Dimensions?: CloudWatch.Dimension[];
  Timestamp: Date;
}

export class CloudWatchMetricsProvider implements MetricsProvider {
  private cloudwatch: CloudWatch;
  private namespace: string;
  private pendingMetrics: PendingMetric[] = [];
  private flushInterval: NodeJS.Timeout;

  constructor(config: MetricsConfig) {
    this.cloudwatch = new CloudWatch({
      region: config.region || 'us-west-2',
      accessKeyId: config.accessKeyId,
      secretAccessKey: config.secretAccessKey
    });

    this.namespace = config.namespace || 'BackyardBuilder';

    // Auto-flush metrics every 60 seconds
    this.flushInterval = setInterval(() => {
      this.flush().catch(console.error);
    }, 60000);
  }

  counter(name: string, value: number = 1, labels?: MetricLabels): void {
    this.addMetric(name, value, 'Count', labels);
  }

  gauge(name: string, value: number, labels?: MetricLabels): void {
    this.addMetric(name, value, 'None', labels);
  }

  timing(name: string, value: number, options?: TimingOptions): void {
    let unit = 'Milliseconds';
    let convertedValue = value;

    if (options?.unit === 'seconds') {
      unit = 'Seconds';
    } else if (options?.unit === 'minutes') {
      unit = 'Seconds';
      convertedValue = value * 60;
    }

    this.addMetric(name, convertedValue, unit, options?.labels);
  }

  event(name: string, metadata?: EventMetadata): void {
    // Convert metadata to dimensions
    const labels: MetricLabels = {};
    
    if (metadata) {
      for (const [key, value] of Object.entries(metadata)) {
        labels[key] = String(value);
      }
    }

    this.addMetric(`events.${name}`, 1, 'Count', labels);
  }

  timer(name: string, labels?: MetricLabels): () => void {
    const startTime = Date.now();
    
    return () => {
      const duration = Date.now() - startTime;
      this.timing(name, duration, { labels });
    };
  }

  private addMetric(name: string, value: number, unit: string, labels?: MetricLabels): void {
    const dimensions: CloudWatch.Dimension[] = [];
    
    if (labels) {
      for (const [key, val] of Object.entries(labels)) {
        dimensions.push({
          Name: key,
          Value: String(val)
        });
      }
    }

    const metric: PendingMetric = {
      MetricName: name,
      Value: value,
      Unit: unit,
      Dimensions: dimensions.length > 0 ? dimensions : undefined,
      Timestamp: new Date()
    };

    this.pendingMetrics.push(metric);

    // Auto-flush if we have too many pending metrics
    if (this.pendingMetrics.length >= 20) {
      this.flush().catch(console.error);
    }
  }

  async flush(): Promise<void> {
    if (this.pendingMetrics.length === 0) {
      return;
    }

    const metricsToFlush = this.pendingMetrics.splice(0); // Take all pending metrics
    
    try {
      // CloudWatch accepts up to 20 metrics per call
      const chunks = this.chunkArray(metricsToFlush, 20);
      
      for (const chunk of chunks) {
        const params: CloudWatch.PutMetricDataRequest = {
          Namespace: this.namespace,
          MetricData: chunk.map(metric => ({
            MetricName: metric.MetricName,
            Value: metric.Value,
            Unit: metric.Unit,
            Dimensions: metric.Dimensions,
            Timestamp: metric.Timestamp
          }))
        };

        await this.cloudwatch.putMetricData(params).promise();
      }
    } catch (error) {
      console.error('Failed to flush metrics to CloudWatch:', error);
      // Put the metrics back for retry
      this.pendingMetrics.unshift(...metricsToFlush);
    }
  }

  async healthCheck(): Promise<boolean> {
    try {
      // Test by putting a simple metric
      const testMetric: CloudWatch.PutMetricDataRequest = {
        Namespace: this.namespace,
        MetricData: [{
          MetricName: 'health_check',
          Value: 1,
          Unit: 'Count',
          Timestamp: new Date()
        }]
      };

      await this.cloudwatch.putMetricData(testMetric).promise();
      return true;
    } catch (error) {
      console.error('CloudWatch metrics provider health check failed:', error);
      return false;
    }
  }

  private chunkArray<T>(array: T[], chunkSize: number): T[][] {
    const chunks: T[][] = [];
    for (let i = 0; i < array.length; i += chunkSize) {
      chunks.push(array.slice(i, i + chunkSize));
    }
    return chunks;
  }

  destroy(): void {
    if (this.flushInterval) {
      clearInterval(this.flushInterval);
    }
    
    // Flush any remaining metrics
    this.flush().catch(console.error);
  }
}