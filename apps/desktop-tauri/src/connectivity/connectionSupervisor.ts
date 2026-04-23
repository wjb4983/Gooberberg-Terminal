export type CircuitState = 'closed' | 'open' | 'half-open';

export interface ConnectionSupervisorSnapshot {
  circuitState: CircuitState;
  consecutiveFailures: number;
  coolDownUntil: number | null;
  lastFailureReason?: string;
}

export interface ConnectionSupervisorOptions {
  failureThreshold?: number;
  coolDownMs?: number;
}

type Subscriber = (snapshot: ConnectionSupervisorSnapshot) => void;

export class ConnectionSupervisor {
  private readonly failureThreshold: number;
  private readonly coolDownMs: number;
  private readonly subscribers = new Set<Subscriber>();

  private snapshot: ConnectionSupervisorSnapshot = {
    circuitState: 'closed',
    consecutiveFailures: 0,
    coolDownUntil: null,
  };

  constructor(options: ConnectionSupervisorOptions = {}) {
    this.failureThreshold = options.failureThreshold ?? 3;
    this.coolDownMs = options.coolDownMs ?? 5_000;
  }

  subscribe(subscriber: Subscriber): () => void {
    this.subscribers.add(subscriber);
    subscriber(this.snapshot);
    return () => this.subscribers.delete(subscriber);
  }

  recordSuccess(): void {
    this.update({
      circuitState: 'closed',
      consecutiveFailures: 0,
      coolDownUntil: null,
      lastFailureReason: undefined,
    });
  }

  recordFailure(reason: string): void {
    const nextFailures = this.snapshot.consecutiveFailures + 1;
    if (nextFailures >= this.failureThreshold) {
      this.update({
        circuitState: 'open',
        consecutiveFailures: nextFailures,
        coolDownUntil: Date.now() + this.coolDownMs,
        lastFailureReason: reason,
      });
      return;
    }

    this.update({
      ...this.snapshot,
      consecutiveFailures: nextFailures,
      lastFailureReason: reason,
    });
  }

  markRetrying(): void {
    if (this.snapshot.circuitState !== 'open') {
      return;
    }

    if (this.snapshot.coolDownUntil && Date.now() >= this.snapshot.coolDownUntil) {
      this.update({
        ...this.snapshot,
        circuitState: 'half-open',
      });
    }
  }

  getSnapshot(): ConnectionSupervisorSnapshot {
    return this.snapshot;
  }

  private update(next: ConnectionSupervisorSnapshot): void {
    this.snapshot = next;
    for (const subscriber of this.subscribers) {
      subscriber(next);
    }
  }
}
