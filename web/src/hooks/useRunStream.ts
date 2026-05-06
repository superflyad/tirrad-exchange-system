"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { streamRunUrl } from "@/lib/api/client";
import type { JsonObject, StreamMessage } from "@/types/api";

export type StreamConnectionState = "connecting" | "open" | "closed" | "retrying" | "error";

export interface RunStreamState {
  messages: StreamMessage[];
  connectionState: StreamConnectionState;
  currentStep: number | null;
  tradeCount: number;
  latestPrices: Record<string, number>;
  error: string | null;
}

const TERMINAL_CATEGORIES = new Set(["completed", "error"]);
const MAX_MESSAGES = 250;

export function useRunStream(runId: string, replayLimit = 100): RunStreamState {
  const [messages, setMessages] = useState<StreamMessage[]>([]);
  const [connectionState, setConnectionState] = useState<StreamConnectionState>("connecting");
  const [error, setError] = useState<string | null>(null);
  const terminalSeen = useRef(false);

  useEffect(() => {
    let source: EventSource | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let retryDelay = 1000;
    let stopped = false;

    const connect = () => {
      if (stopped || terminalSeen.current) return;
      setConnectionState((state) => (state === "retrying" ? "retrying" : "connecting"));
      source = new EventSource(streamRunUrl(runId, replayLimit));
      source.onopen = () => {
        retryDelay = 1000;
        setConnectionState("open");
        setError(null);
      };
      source.onmessage = (event) => handleMessage(event.data);
      for (const eventType of ["status", "progress", "event", "snapshot", "account", "log", "error", "completed"]) {
        source.addEventListener(eventType, (event) => handleMessage((event as MessageEvent).data));
      }
      source.onerror = () => {
        source?.close();
        if (stopped || terminalSeen.current) {
          setConnectionState("closed");
          return;
        }
        setConnectionState("retrying");
        setError("Stream dropped; reconnecting.");
        retryTimer = setTimeout(connect, retryDelay);
        retryDelay = Math.min(retryDelay * 2, 10_000);
      };
    };

    const handleMessage = (data: string) => {
      try {
        const message = JSON.parse(data) as StreamMessage;
        if (TERMINAL_CATEGORIES.has(message.category)) {
          terminalSeen.current = true;
          setConnectionState(message.category === "error" ? "error" : "closed");
          source?.close();
        }
        setMessages((current) => [...current, message].slice(-MAX_MESSAGES));
      } catch {
        setError("Received malformed stream message.");
      }
    };

    connect();
    return () => {
      stopped = true;
      if (retryTimer) clearTimeout(retryTimer);
      source?.close();
    };
  }, [runId, replayLimit]);

  return useMemo(() => deriveStreamState(messages, connectionState, error), [messages, connectionState, error]);
}

export function deriveStreamState(
  messages: StreamMessage[],
  connectionState: StreamConnectionState,
  error: string | null,
): RunStreamState {
  let currentStep: number | null = null;
  let tradeCount = 0;
  const latestPrices: Record<string, number> = {};
  for (const message of messages) {
    if (typeof message.step === "number") currentStep = message.step;
    const payload = message.payload;
    if (message.type === "TradeExecuted" || payload.type === "TradeExecuted") tradeCount += 1;
    const symbol = readString(payload, "symbol") ?? readNestedString(payload, "data", "symbol");
    const price = readNumber(payload, "price") ?? readNestedNumber(payload, "data", "price") ?? readNumber(payload, "mid") ?? readNumber(payload, "mid_price");
    if (symbol && typeof price === "number") latestPrices[symbol] = price;
  }
  return { messages, connectionState, currentStep, tradeCount, latestPrices, error };
}

function readString(payload: JsonObject, key: string): string | null {
  const value = payload[key];
  return typeof value === "string" ? value : null;
}

function readNumber(payload: JsonObject, key: string): number | null {
  const value = payload[key];
  return typeof value === "number" ? value : null;
}

function readNestedString(payload: JsonObject, parent: string, key: string): string | null {
  const value = payload[parent];
  return value && typeof value === "object" && !Array.isArray(value) ? readString(value as JsonObject, key) : null;
}

function readNestedNumber(payload: JsonObject, parent: string, key: string): number | null {
  const value = payload[parent];
  return value && typeof value === "object" && !Array.isArray(value) ? readNumber(value as JsonObject, key) : null;
}
