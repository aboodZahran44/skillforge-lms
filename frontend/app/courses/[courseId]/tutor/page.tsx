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
    // Errors from either service (Django token issuance or FastAPI chat)
    // carry the failing response's own message.
    if (err.status === 401 && err.message === "Authentication required.") {
      return { kind: "error", status: 401, text: "You need to be logged in to ask the tutor." };
    }
    return { kind: "error", status: err.status, text: err.message };
  }
  return {
    kind: "error",
    status: null,
    text: "Could not reach the tutor. Check your connection and try again.",
  };
}

export default function TutorPage() {
  const params = useParams<{ courseId: string }>();
  const courseId = params.courseId;

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false); // whole ask cycle: token + stream
  const [waiting, setWaiting] = useState(false); // no first chunk yet
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, waiting]);

  function appendChunk(chunk: string, isFirst: boolean) {
    if (isFirst) {
      setWaiting(false);
      setMessages((prev) => [...prev, { kind: "assistant", text: chunk }]);
      return;
    }
    setMessages((prev) => {
      const next = prev.slice();
      const last = next[next.length - 1];
      if (last?.kind === "assistant") {
        next[next.length - 1] = { kind: "assistant", text: last.text + chunk };
      }
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const question = input.trim();
    if (question === "" || busy) return;

    setMessages((prev) => [...prev, { kind: "user", text: question }]);
    setInput("");
    setBusy(true);
    setWaiting(true);
    try {
      // Fresh short-lived token per question — never cached across questions.
      const { token } = await api.getTutorToken(courseId);
      let started = false;
      await api.streamTutorChat(courseId, token, question, (chunk) => {
        appendChunk(chunk, !started);
        started = true;
      });
      if (!started) {
        setMessages((prev) => [...prev, { kind: "assistant", text: "(The tutor sent no answer.)" }]);
      }
    } catch (err) {
      setMessages((prev) => [...prev, errorMessage(err)]);
    } finally {
      setWaiting(false);
      setBusy(false);
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
        {messages.length === 0 && !waiting && (
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
              const isStreaming = busy && !waiting && i === messages.length - 1;
              return (
                <div key={i} className="self-start max-w-[85%] whitespace-pre-wrap rounded-lg bg-black/5 px-4 py-2 text-sm dark:bg-white/10">
                  {msg.text}
                  {isStreaming && <span className="ml-0.5 inline-block w-2 animate-pulse">▍</span>}
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

          {waiting && (
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
          disabled={busy}
          className="flex-1 rounded border border-black/20 bg-transparent px-4 py-2.5 outline-none focus:border-black/50 disabled:opacity-50 dark:border-white/25 dark:focus:border-white/60"
        />
        <button
          type="submit"
          disabled={busy || input.trim() === ""}
          className="rounded bg-black px-5 py-2 text-sm font-medium text-white hover:bg-black/85 disabled:opacity-50 dark:bg-white dark:text-black dark:hover:bg-white/90"
        >
          Send
        </button>
      </form>
    </div>
  );
}
