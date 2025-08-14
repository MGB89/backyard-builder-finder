/**
 * AWS SQS queue provider implementation (stub for future migration)
 */

import { SQS } from 'aws-sdk';
import { QueueProvider, Job, JobOptions, JobPayload, JobResult, QueueStats, QueueConfig } from './interface';

export class SQSQueueProvider implements QueueProvider {
  private sqs: SQS;
  private queueUrlPrefix: string;
  private processors: Map<string, boolean> = new Map();

  constructor(config: QueueConfig) {
    if (!config.region) {
      throw new Error('AWS region is required for SQS provider');
    }

    this.sqs = new SQS({
      region: config.region,
      accessKeyId: config.accessKeyId,
      secretAccessKey: config.secretAccessKey
    });

    this.queueUrlPrefix = config.queueUrlPrefix || '';
  }

  private getQueueUrl(queueName: string): string {
    return `${this.queueUrlPrefix}/${queueName}`;
  }

  async enqueue<T = JobPayload>(
    queueName: string,
    payload: T,
    options?: JobOptions
  ): Promise<string> {
    const queueUrl = this.getQueueUrl(queueName);
    
    const params: SQS.SendMessageRequest = {
      QueueUrl: queueUrl,
      MessageBody: JSON.stringify({
        id: this.generateJobId(),
        name: queueName,
        data: payload,
        priority: options?.priority || 0,
        retryCount: 0,
        createdAt: new Date().toISOString()
      })
    };

    if (options?.delay) {
      params.DelaySeconds = Math.min(options.delay, 900); // SQS max delay is 15 minutes
    }

    if (options?.singletonKey) {
      params.MessageDeduplicationId = options.singletonKey;
      params.MessageGroupId = queueName; // Required for FIFO queues
    }

    const result = await this.sqs.sendMessage(params).promise();
    return result.MessageId || '';
  }

  async process<T = JobPayload>(
    queueName: string,
    handler: (job: Job<T>) => Promise<JobResult>
  ): Promise<void> {
    const queueUrl = this.getQueueUrl(queueName);
    this.processors.set(queueName, true);

    // Poll for messages continuously
    while (this.processors.get(queueName)) {
      try {
        const result = await this.sqs.receiveMessage({
          QueueUrl: queueUrl,
          MaxNumberOfMessages: 1,
          WaitTimeSeconds: 20, // Long polling
          VisibilityTimeoutSeconds: 300 // 5 minutes to process
        }).promise();

        if (result.Messages && result.Messages.length > 0) {
          const message = result.Messages[0];
          const jobData = JSON.parse(message.Body || '{}');

          const job: Job<T> = {
            id: message.MessageId || jobData.id,
            name: jobData.name || queueName,
            data: jobData.data,
            priority: jobData.priority || 0,
            retryCount: jobData.retryCount || 0,
            createdAt: new Date(jobData.createdAt),
            startedAt: new Date()
          };

          try {
            const jobResult = await handler(job);
            
            if (jobResult.success) {
              // Delete message from queue on success
              await this.sqs.deleteMessage({
                QueueUrl: queueUrl,
                ReceiptHandle: message.ReceiptHandle!
              }).promise();
            } else {
              // Let message become visible again for retry
              // SQS will handle retries based on queue configuration
              console.error(`Job ${job.id} failed:`, jobResult.error);
            }
          } catch (error: any) {
            console.error(`Job ${job.id} threw error:`, error.message);
            // Let message become visible again for retry
          }
        }
      } catch (error) {
        console.error('Error polling SQS queue:', error);
        // Wait a bit before retrying
        await new Promise(resolve => setTimeout(resolve, 5000));
      }
    }
  }

  async getJob(jobId: string): Promise<Job | null> {
    // SQS doesn't provide a direct way to get a specific message by ID
    // This would require a separate tracking system (like DynamoDB)
    console.warn('getJob is not efficiently supported by SQS - consider using a job tracking database');
    return null;
  }

  async cancel(jobId: string): Promise<boolean> {
    // SQS doesn't provide a direct way to cancel a specific message by ID
    // This would require a separate tracking system
    console.warn('cancel is not efficiently supported by SQS - consider using a job tracking database');
    return false;
  }

  async getStats(queueName: string): Promise<QueueStats> {
    try {
      const queueUrl = this.getQueueUrl(queueName);
      
      const result = await this.sqs.getQueueAttributes({
        QueueUrl: queueUrl,
        AttributeNames: [
          'ApproximateNumberOfMessages',
          'ApproximateNumberOfMessagesNotVisible',
          'ApproximateNumberOfMessagesDelayed'
        ]
      }).promise();

      const attributes = result.Attributes || {};

      return {
        waiting: parseInt(attributes.ApproximateNumberOfMessages || '0'),
        active: parseInt(attributes.ApproximateNumberOfMessagesNotVisible || '0'),
        completed: 0, // SQS doesn't track completed messages
        failed: 0, // Would need dead letter queue stats
        delayed: parseInt(attributes.ApproximateNumberOfMessagesDelayed || '0')
      };
    } catch (error) {
      console.error('Failed to get SQS queue stats:', error);
      return { waiting: 0, active: 0, completed: 0, failed: 0, delayed: 0 };
    }
  }

  async schedule(
    name: string,
    cron: string,
    payload: JobPayload,
    options?: JobOptions
  ): Promise<void> {
    // SQS doesn't support cron scheduling directly
    // This would require EventBridge or CloudWatch Events
    console.warn('schedule is not supported by SQS directly - use EventBridge for scheduled jobs');
    throw new Error('Scheduled jobs not supported by SQS provider - use EventBridge');
  }

  async stop(): Promise<void> {
    // Stop all processors
    for (const queueName of this.processors.keys()) {
      this.processors.set(queueName, false);
    }
  }

  async healthCheck(): Promise<boolean> {
    try {
      // Try to list queues to verify SQS access
      await this.sqs.listQueues({ MaxResults: 1 }).promise();
      return true;
    } catch (error) {
      console.error('SQS health check failed:', error);
      return false;
    }
  }

  private generateJobId(): string {
    return `job_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}