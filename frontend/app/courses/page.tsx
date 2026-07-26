"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import * as api from "@/lib/api";
import type { CourseResult } from "@/lib/api";

const DEBOUNCE_MS = 300;

export default function CoursesPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CourseResult[]>([]);
  const [degraded, setDegraded] = useState(false);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // The query the current results belong to — distinguishes "not searched yet"
  // from "searched and found nothing".
  const [settledQuery, setSettledQuery] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const trimmed = query.trim();

    // Empty query: show nothing, never hit the backend.
    if (trimmed === "") {
      abortRef.current?.abort();
      setResults([]);
      setDegraded(false);
      setSearching(false);
      setError(null);
      setSettledQuery("");
      return;
    }

    const timer = setTimeout(() => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setSearching(true);
      setError(null);

      api
        .searchCourses(trimmed, controller.signal)
        .then((data) => {
          setResults(data.results);
          setDegraded(data.degraded);
          setSettledQuery(trimmed);
          setSearching(false);
        })
        .catch((err: unknown) => {
          if (err instanceof DOMException && err.name === "AbortError") return;
          setError("Search is unavailable right now. Please try again.");
          setSearching(false);
        });
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [query]);

  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">Find a course</h1>

      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search courses…"
        aria-label="Search courses"
        className="w-full rounded border border-black/20 bg-transparent px-4 py-2.5 outline-none focus:border-black/50 dark:border-white/25 dark:focus:border-white/60"
      />

      {degraded && settledQuery !== "" && (
        <p className="mt-3 text-xs text-black/50 dark:text-white/50">
          Showing basic search results — full search is temporarily unavailable.
        </p>
      )}

      {error && (
        <p role="alert" className="mt-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300">
          {error}
        </p>
      )}

      <div className="mt-6 flex flex-col gap-3">
        {results.map((course) => (
          <div
            key={course.id}
            className="rounded-lg border border-black/10 p-4 dark:border-white/15"
          >
            <h2 className="font-medium">{course.title}</h2>
            <p className="mt-1 text-sm text-black/60 dark:text-white/60">{course.description}</p>
            <Link
              href={`/courses/${course.id}/tutor`}
              className="mt-3 inline-block text-sm underline underline-offset-4 hover:no-underline"
            >
              Ask the tutor →
            </Link>
          </div>
        ))}
      </div>

      {!searching && !error && settledQuery !== "" && results.length === 0 && (
        <p className="mt-6 text-sm text-black/60 dark:text-white/60">
          No courses found for “{settledQuery}”.
        </p>
      )}

      {searching && (
        <p className="mt-6 text-sm text-black/40 dark:text-white/40">Searching…</p>
      )}
    </div>
  );
}
