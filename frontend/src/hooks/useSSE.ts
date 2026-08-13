import { useState, useRef, useCallback } from 'react';

export interface AgentEventData {
  type: string;
  data?: any;
  message?: string;
}

export function useSSE() {
  const [events, setEvents] = useState<AgentEventData[]>([]);
  const [status, setStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle');
  const abortRef = useRef<AbortController | null>(null);

  const start = useCallback(async (url: string, body: object) => {
    abortRef.current = new AbortController();
    setStatus('running');
    setEvents([]);

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: abortRef.current.signal,
      });

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6));
              setEvents(prev => [...prev, event]);
            } catch {}
          }
        }
      }
      setStatus('done');
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setStatus('error');
      }
    } finally {
      abortRef.current = null;
    }
  }, []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setStatus('idle');
  }, []);

  const reset = useCallback(() => {
    setEvents([]);
    setStatus('idle');
  }, []);

  return { events, status, start, stop, reset };
}