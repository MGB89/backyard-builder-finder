/**
 * Queue provider interface for job processing
 * Supports both pg-boss (Postgres) and AWS SQS backends
 */

export interface JobPayload {
  [key: string]: any;
}

export interface JobOptions {
  delay?: number; // Delay in seconds before job becomes available
  priority?: number; // Job priority (higher = more priority)
  retryLimit?: number; // Maximum retry attempts
  retryDelay?: number; // Delay between retries in seconds
  expireIn?: string; // Expiration time (e.g., '1 hour', '30 minutes')
  singletonKey?: string; // Ensure only one job with this key exists
}

export interface Job<T = JobPayload> {
  id: string;
  name: string;
  data: T;
  priority: number;
  retryCount: number;
  createdAt: Date;
  startedAt?: Date;
  completedAt?: Date;
  failedAt?: Date;
  error?: string;
}

export interface JobResult {
  success: boolean;
  error?: string;
  data?: any;
}

export interface QueueStats {
  waiting: number;
  active: number;
  completed: number;
  failed: number;
  delayed: number;
}

export interface QueueProvider {
  /**
   * Add a job to the queue
   */
  enqueue<T = JobPayload>(
    queueName: string,
    payload: T,
    options?: JobOptions
  ): Promise<string>; // Returns job ID

  /**
   * Process jobs from a queue
   */
  process<T = JobPayload>(
    queueName: string,
    handler: (job: Job<T>) => Promise<JobResult>
  ): Promise<void>;

  /**
   * Get job by ID
   */
  getJob(jobId: string): Promise<Job | null>;

  /**
   * Cancel a job
   */
  cancel(jobId: string): Promise<boolean>;

  /**
   * Get queue statistics
   */
  getStats(queueName: string): Promise<QueueStats>;

  /**
   * Schedule a recurring job (cron-like)
   */
  schedule(
    name: string,
    cron: string,
    payload: JobPayload,
    options?: JobOptions
  ): Promise<void>;

  /**
   * Stop processing jobs
   */
  stop(): Promise<void>;

  /**
   * Health check
   */
  healthCheck(): Promise<boolean>;
}

export type QueueProviderType = 'pgboss' | 'sqs';

export interface QueueConfig {
  provider: QueueProviderType;
  
  // PostgreSQL (pg-boss) specific
  connectionString?: string;
  
  // AWS SQS specific
  region?: string;
  accessKeyId?: string;
  secretAccessKey?: string;
  queueUrlPrefix?: string; // Base URL for SQS queues
}