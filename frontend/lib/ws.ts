"use client";

import { tokenStore } from "./api";

type Handler = (msg: any) => void;

export class RealtimeClient {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers = new Set<Handler>();
  private reconnectDelay = 1000;
  private shouldReconnect = true;

  constructor(siteId?: string) {
    const base =
      (typeof window !== "undefined" && window.location.protocol === "https:")
        ? "wss://"
        : "ws://";
    const host =
      typeof window !== "undefined" ? window.location.host : "localhost:3000";
    const path = siteId ? `/ws/sites/${siteId}` : "/ws";
    this.url = `${base}${host}${path}`;
  }

  connect(): void {
    const token = tokenStore.access;
    if (!token) return;
    this.ws = new WebSocket(`${this.url}?token=${encodeURIComponent(token)}`);
    this.ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        this.handlers.forEach((h) => h(msg));
      } catch { /* noop */ }
    };
    this.ws.onclose = () => {
      if (!this.shouldReconnect) return;
      setTimeout(() => this.connect(), this.reconnectDelay);
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
    };
    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
    };
  }

  on(handler: Handler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  close(): void {
    this.shouldReconnect = false;
    this.ws?.close();
  }
}
