/**
 * Poller generico (sem React) usado para consultar o status do PIX.
 *  - roda `tick` a cada `intervalMs`;
 *  - para sozinho apos `maxDurationMs`;
 *  - pausa enquanto a aba esta oculta e retoma (com uma consulta imediata) ao voltar;
 *  - nunca executa dois `tick` ao mesmo tempo.
 */
export interface PollerOptions {
  /** Retorna true para encerrar o polling (ex.: pagamento confirmado). */
  tick: () => Promise<boolean>;
  intervalMs?: number;
  maxDurationMs?: number;
  onTimeout?: () => void;
  isHidden?: () => boolean;
  now?: () => number;
}

export interface Poller {
  start(): void;
  stop(): void;
  /** Forca uma consulta imediata (ex.: botao "ja paguei"). */
  pollNow(): Promise<void>;
  readonly running: boolean;
}

export function createPoller(options: PollerOptions): Poller {
  const {
    tick,
    intervalMs = 4000,
    maxDurationMs = 15 * 60 * 1000,
    onTimeout,
    isHidden = () => typeof document !== 'undefined' && document.hidden,
    now = () => Date.now(),
  } = options;

  let timer: ReturnType<typeof setTimeout> | null = null;
  let running = false;
  let inFlight = false;
  let startedAt = 0;
  let listening = false;

  const clear = () => {
    if (timer) clearTimeout(timer);
    timer = null;
  };

  const onVisibility = () => {
    if (!running) return;
    if (!isHidden()) {
      clear();
      void run();
    }
  };

  const expired = () => now() - startedAt >= maxDurationMs;

  const schedule = () => {
    clear();
    if (!running) return;
    timer = setTimeout(() => void run(), intervalMs);
  };

  async function run(): Promise<void> {
    if (!running || inFlight) return;
    if (expired()) {
      stop();
      onTimeout?.();
      return;
    }
    if (isHidden()) {
      // pausado: o evento visibilitychange retoma
      schedule();
      return;
    }
    inFlight = true;
    let done = false;
    try {
      done = await tick();
    } catch {
      done = false;
    } finally {
      inFlight = false;
    }
    if (!running) return;
    if (done) {
      stop();
      return;
    }
    schedule();
  }

  function start() {
    if (running) return;
    running = true;
    startedAt = now();
    if (!listening && typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', onVisibility);
      listening = true;
    }
    schedule();
  }

  function stop() {
    running = false;
    clear();
    if (listening && typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', onVisibility);
      listening = false;
    }
  }

  return {
    start,
    stop,
    async pollNow() {
      if (inFlight) return;
      inFlight = true;
      let done = false;
      try {
        done = await tick();
      } catch {
        done = false;
      } finally {
        inFlight = false;
      }
      if (done) stop();
    },
    get running() {
      return running;
    },
  };
}
