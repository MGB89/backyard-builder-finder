/**
 * pg-boss (PostgreSQL) queue provider implementation
 */

import PgBoss from 'pg-boss';
import { QueueProvider, Job, JobOptions, JobPayload, JobResult, QueueStats, QueueConfig } from './interface';

export class PgBossQueueProvider implements QueueProvider {
  private boss: PgBoss;
  private isStarted = false;

  constructor(config: QueueConfig) {
    if (!config.connectionString) {
      throw new Error('PostgreSQL connection string is required for pg-boss provider');
    }

    this.boss = new PgBoss({
      connectionString: config.connectionString,
      retryLimit: 3,
      retryDelay: 30,
      expireInHours: 24,
      deleteAfterHours: 48,
      schema: 'pgboss' // Use separate schema for job tables
    });
  }

  private async ensureStarted(): Promise<void> {
    if (!this.isStarted) {
      await this.boss.start();
      this.isStarted = true;
    }
  }

  async enqueue<T = JobPayload>(
    queueName: string,
    payload: T,
    options?: JobOptions
  ): Promise<string> {
    await this.ensureStarted();

    const jobOptions: any = {};
    
    if (options?.delay) {
      jobOptions.startAfter = new Date(Date.now() + options.delay * 1000);
    }
    
    if (options?.priority) {
      jobOptions.priority = options.priority;
    }
    
    if (options?.retryLimit) {
      jobOptions.retryLimit = options.retryLimit;
    }
    
    if (options?.retryDelay) {
      jobOptions.retryDelay = options.retryDelay;
    }
    
    if (options?.expireIn) {
      jobOptions.expireIn = options.expireIn;
    }
    
    if (options?.singletonKey) {
      jobOptions.singletonKey = options.singletonKey;
    }

    const jobId = await this.boss.send(queueName, payload, jobOptions);
    return jobId || '';
  }

  async process<T = JobPayload>(
    queueName: string,
    handler: (job: Job<T>) => Promise<JobResult>
  ): Promise<void> {
    await this.ensureStarted();

    await this.boss.work(queueName, async (pgBossJob) => {
      const job: Job<T> = {
        id: pgBossJob.id,
        name: pgBossJob.name,
        data: pgBossJob.data,
        priority: pgBossJob.priority || 0,
        retryCount: pgBossJob.retrycount || 0,
        createdAt: pgBossJob.createdon,
        startedAt: pgBossJob.startedon || undefined,
        completedAt: pgBossJob.completedon || undefined,
        failedAt: pgBossJob.failedon || undefined
      };

      try {
        const result = await handler(job);
        
        if (!result.success) {
          throw new Error(result.error || 'Job handler returned failure');
        }
        
        return result.data;
      } catch (error: any) {
        // pg-boss will handle retries automatically based on retryLimit
        throw error;
      }
    });
  }

  async getJob(jobId: string): Promise<Job | null> {
    await this.ensureStarted();

    const pgBossJob = await this.boss.getJobById(jobId);
    if (!pgBossJob) {
      return null;
    }

    return {
      id: pgBossJob.id,
      name: pgBossJob.name,
      data: pgBossJob.data,
      priority: pgBossJob.priority || 0,
      retryCount: pgBossJob.retrycount || 0,
      createdAt: pgBossJob.createdon,
      startedAt: pgBossJob.startedon || undefined,
      completedAt: pgBossJob.completedon || undefined,
      failedAt: pgBossJob.failedon || undefined,
      error: pgBossJob.output?.message
    };
  }

  async cancel(jobId: string): Promise<boolean> {
    await this.ensureStarted();

    try {
      await this.boss.cancel(jobId);
      return true;
    } catch (error) {
      console.error('Failed to cancel job:', error);
      return false;
    }
  }

  async getStats(queueName: string): Promise<QueueStats> {
    await this.ensureStarted();

    // pg-boss doesn't have built-in queue stats, so we'll query directly
    // This is a simplified implementation
    try {
      const [waiting, active, completed, failed] = await Promise.all([
        this.boss.getQueueSize(queueName, { state: 'created' }),
        this.boss.getQueueSize(queueName, { state: 'active' }),
        this.boss.getQueueSize(queueName, { state: 'completed' }),
        this.boss.getQueueSize(queueName, { state: 'failed' })
      ]);

      return {
        waiting: waiting || 0,
        active: active || 0,
        completed: completed || 0,
        failed: failed || 0,
        delayed: 0 // Would need custom query to get delayed jobs
      };
    } catch (error) {
      console.error('Failed to get queue stats:', error);
      return { waiting: 0, active: 0, completed: 0, failed: 0, delayed: 0 };
    }
  }

  async schedule(
    name: string,
    cron: string,
    payload: JobPayload,
    options?: JobOptions
  ): Promise<void> {
    await this.ensureStarted();

    const scheduleOptions: any = {
      tz: 'UTC' // Use UTC for consistency
    };

    if (options?.singletonKey) {
      scheduleOptions.singletonKey = options.singletonKey;
    }

    await this.boss.schedule(name, cron, payload, scheduleOptions);
  }

  async stop(): Promise<void> {
    if (this.isStarted) {
      await this.boss.stop();
      this.isStarted = false;
    }
  }

  async healthCheck(): Promise<boolean> {
    try {
      await this.ensureStarted();
      // Try to send a simple health check job
      const jobId = await this.boss.send('health-check', { timestamp: Date.now() });
      
      // Clean up the health check job immediately
      if (jobId) {
        await this.boss.cancel(jobId);
      }
      
      return true;
    } catch (error) {
      console.error('pg-boss health check failed:', error);
      return false;
    }
  }
}