"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import * as api from "@/lib/api";
import { ApiError } from "@/lib/api";

type Message =
  | { kind: "user"; text: string }
  | { kind: "assistant"; text: string }
  | { kind: "error"; status: number | null; text: string };

function errorMessage(err: unknown): Message {
  if (err instanceof ApiError) {
    // Each documented failure gets its own human-readable rendering; the
    // server's message is the source of truth where it exists.
    switch (err.status) {
      case 401:
        return { kind: "error", status: 401, text: "You need to be logged in to ask the tutor." };
      case 403:
        return { kind: "error", status: 403, text: err.message };
      case 400:
        return { kind: "error", status: 400, text: err.message };
      case 429:
        return { kind: "error", status: 429, text: err.message };
      default:
        return { kind: "error", status: err.status, text: err.message };
    }
  }
  return { kind: "error", status: null, text: "Could not reach the tutor. Check your connection and try again." };
}

export default function TutorPage() {
  const params = useParams<{ courseId: string }>();
  const courseId = params.courseId;

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, thinking]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (question === "" || thinking) return;

    setMessages((prev) => [...prev, { kind: "user", text: question }]);
    setInput("");
    setThinking(true);
    try {
      const { answer } = await api.askTutor(courseId, question);
      setMessages((prev) => [...prev, { kind: "assistant", text: answer }]);
    } catch (err) {
      setMessages((prev) => [...prev, errorMessage(err)]);
    } finally {
      setThinking(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-8.5rem)] flex-col">
      <div className="mb-4 flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Course tutor</h1>
        <Link href="/courses" className="text-sm underline underline-offset-4 hover:no-underline">
          ← Back to courses
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto rounded-lg border border-black/10 p-4 dark:border-white/15">
        {messages.length === 0 && !thinking && (
          <p className="mt-8 text-center text-sm text-black/40 dark:text-white/40">
            Ask a question about this course&apos;s content.
          </p>
        )}

        <div className="flex flex-col gap-3">
          {messages.map((msg, i) => {
            if (msg.kind === "user") {
              return (
                <div key={i} className="self-end max-w-[85%] rounded-lg bg-black px-4 py-2 text-sm text-white dark:bg-white dark:text-black">
                  {msg.text}
                </div>
              );
            }
            if (msg.kind === "assistant") {
              return (
                <div key={i} className="self-start max-w-[85%] whitespace-pre-wrap rounded-lg bg-black/5 px-4 py-2 text-sm dark:bg-white/10">
                  {msg.text}
                </div>
              );
            }
            return (
              <div
                key={i}
                role="alert"
                className="self-start max-w-[85%] rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200"
              >
                {msg.text}
                {msg.status === 401 && (
                  <>
                    {" "}
                    <Link href="/login" className="font-medium underline underline-offset-2">
                      Log in
                    </Link>
                  </>
                )}
              </div>
            );
          })}

          {thinking && (
            <div className="self-start max-w-[85%] rounded-lg bg-black/5 px-4 py-2 text-sm text-black/50 dark:bg-white/10 dark:text-white/50">
              <span className="animate-pulse">Tutor is thinking…</span>
            </div>
          )}
        </div>
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask the tutor a question…"
          aria-label="Your question"
          disabled={thinking}
          className="flex-1 rounded border border-black/20 bg-transparent px-4 py-2.5 outline-none focus:border-black/50 disabled:opacity-50 dark:border-white/25 dark:focus:border-white/60"
        />
        <button
          type="submit"
          disabled={thinking || input.trim() === ""}
          className="rounded bg-black px-5 py-2 text-sm font-medium text-white hover:bg-black/85 disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-white/90"
        >
          Send
        </button>
      </form>
    </div>
  );
}
