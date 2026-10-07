import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createPoller } from './poller';

describe('createPoller', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('consulta a cada intervalo e para quando o tick devolve true', async () => {
    const tick = vi.fn<() => Promise<boolean>>().mockResolvedValueOnce(false).mockResolvedValueOnce(false).mockResolvedValueOnce(true);
    const poller = createPoller({ tick, intervalMs: 4000, isHidden: () => false });
    poller.start();
    expect(tick).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(4000);
    expect(tick).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(4000);
    expect(tick).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(4000);
    expect(tick).toHaveBeenCalledTimes(3);
    expect(poller.running).toBe(false);
    await vi.advanceTimersByTimeAsync(20000);
    expect(tick).toHaveBeenCalledTimes(3);
  });

  it('para apos maxDuration e avisa onTimeout', async () => {
    const tick = vi.fn(async () => false);
    const onTimeout = vi.fn();
    const poller = createPoller({ tick, intervalMs: 4000, maxDurationMs: 15 * 60 * 1000, onTimeout, isHidden: () => false });
    poller.start();
    await vi.advanceTimersByTimeAsync(15 * 60 * 1000 + 5000);
    expect(onTimeout).toHaveBeenCalledTimes(1);
    expect(poller.running).toBe(false);
    const calls = tick.mock.calls.length;
    await vi.advanceTimersByTimeAsync(60_000);
    expect(tick.mock.calls.length).toBe(calls);
    expect(calls).toBeGreaterThan(200); // ~225 consultas em 15 min
  });

  it('pausa com a aba oculta e retoma ao ficar visivel', async () => {
    let hidden = true;
    const tick = vi.fn(async () => false);
    const poller = createPoller({ tick, intervalMs: 4000, isHidden: () => hidden });
    poller.start();
    await vi.advanceTimersByTimeAsync(20000);
    expect(tick).not.toHaveBeenCalled();
    hidden = false;
    document.dispatchEvent(new Event('visibilitychange'));
    await vi.advanceTimersByTimeAsync(0);
    expect(tick).toHaveBeenCalledTimes(1);
    poller.stop();
  });

  it('erros do tick nao derrubam o polling', async () => {
    const tick = vi.fn<() => Promise<boolean>>().mockRejectedValueOnce(new Error('x')).mockResolvedValueOnce(true);
    const poller = createPoller({ tick, intervalMs: 1000, isHidden: () => false });
    poller.start();
    await vi.advanceTimersByTimeAsync(2100);
    expect(tick).toHaveBeenCalledTimes(2);
    expect(poller.running).toBe(false);
  });

  it('nunca roda dois ticks ao mesmo tempo', async () => {
    let resolve: (v: boolean) => void = () => undefined;
    const tick = vi.fn(() => new Promise<boolean>((r) => (resolve = r)));
    const poller = createPoller({ tick, intervalMs: 1000, isHidden: () => false });
    poller.start();
    await vi.advanceTimersByTimeAsync(1000);
    await poller.pollNow();
    expect(tick).toHaveBeenCalledTimes(1);
    resolve(true);
    await vi.advanceTimersByTimeAsync(0);
    expect(poller.running).toBe(false);
  });

  it('stop cancela tudo', async () => {
    const tick = vi.fn(async () => false);
    const poller = createPoller({ tick, intervalMs: 1000, isHidden: () => false });
    poller.start();
    poller.stop();
    await vi.advanceTimersByTimeAsync(10_000);
    expect(tick).not.toHaveBeenCalled();
  });
});
