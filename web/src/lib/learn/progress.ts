"use client";

const STORAGE_KEY = "ekg_academy_progress";

interface ProgressStore {
  completed: string[]; // "beginner/01-intro", "intermediate/03-pacs", etc.
}

function read(): ProgressStore {
  if (typeof window === "undefined") return { completed: [] };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { completed: [] };
    return JSON.parse(raw) as ProgressStore;
  } catch {
    return { completed: [] };
  }
}

function write(store: ProgressStore): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

function key(level: string, slug: string): string {
  return `${level}/${slug}`;
}

export function getProgress(): string[] {
  return read().completed;
}

export function isLessonComplete(level: string, slug: string): boolean {
  return read().completed.includes(key(level, slug));
}

export function markLessonComplete(level: string, slug: string): void {
  const store = read();
  const k = key(level, slug);
  if (!store.completed.includes(k)) {
    store.completed.push(k);
    write(store);
  }
}

export function resetProgress(): void {
  write({ completed: [] });
}
