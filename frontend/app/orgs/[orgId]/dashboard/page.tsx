"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import * as api from "@/lib/api";
import { ApiError } from "@/lib/api";
import type { OrgDashboard } from "@/lib/api";

type PageState =
  | { status: "loading" }
  | { status: "forbidden" }
  | { status: "not-found" }
  | { status: "error"; message: string }
  | { status: "ready"; data: OrgDashboard };

export default function OrgDashboardPage() {
  const params = useParams<{ orgId: string }>();
  const orgId = params.orgId;
  const router = useRouter();
  const [state, setState] = useState<PageState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    api
      .getOrgDashboard(orgId)
      .then((data) => {
        if (!cancelled) setState({ status: "ready", data });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError) {
          if (err.status === 401) {
            router.replace("/login");
            return;
          }
          if (err.status === 403) {
            setState({ status: "forbidden" });
            return;
          }
          if (err.status === 404) {
            setState({ status: "not-found" });
            return;
          }
          setState({ status: "error", message: err.message });
          return;
        }
        setState({ status: "error", message: "Could not reach the server." });
      });
    return () => {
      cancelled = true;
    };
  }, [orgId, router]);

  if (state.status === "loading") {
    return <p className="text-sm text-black/40 dark:text-white/40">Loading dashboard…</p>;
  }

  if (state.status === "forbidden") {
    return (
      <div className="mt-12 text-center">
        <h1 className="text-xl font-semibold">No access to this organization</h1>
        <p className="mt-2 text-sm text-black/60 dark:text-white/60">
          You&apos;re logged in, but you&apos;re not an admin of this organization.
        </p>
      </div>
    );
  }

  if (state.status === "not-found") {
    return (
      <div className="mt-12 text-center">
        <h1 className="text-xl font-semibold">Organization not found</h1>
        <p className="mt-2 text-sm text-black/60 dark:text-white/60">
          There is no organization with this ID.
        </p>
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <p role="alert" className="mt-8 rounded bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950/50 dark:text-red-300">
        {state.message}
      </p>
    );
  }

  const { data } = state;
  const { total_seats, seats_used } = data.seat_usage;
  const seatPercent = total_seats > 0 ? Math.round((seats_used / total_seats) * 100) : 0;

  return (
    <div>
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{data.organization}</h1>
          <p className="mt-1 text-sm text-black/60 dark:text-white/60">Organization dashboard</p>
        </div>
        <a
          href={api.complianceReportUrl(orgId)}
          className="rounded bg-black px-4 py-2 text-sm font-medium text-white hover:bg-black/85 dark:bg-white dark:text-black dark:hover:bg-white/90"
        >
          Download compliance report
        </a>
      </div>

      <section className="mb-8 rounded-lg border border-black/10 p-4 dark:border-white/15">
        <div className="flex items-baseline justify-between">
          <h2 className="text-sm font-medium">Seat usage</h2>
          <span className="text-sm text-black/60 dark:text-white/60">
            {seats_used} / {total_seats} seats used
          </span>
        </div>
        <div
          role="progressbar"
          aria-valuenow={seats_used}
          aria-valuemin={0}
          aria-valuemax={total_seats}
          className="mt-3 h-2 overflow-hidden rounded-full bg-black/10 dark:bg-white/15"
        >
          <div className="h-full rounded-full bg-black dark:bg-white" style={{ width: `${seatPercent}%` }} />
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-medium">Employee progress</h2>
        {data.employees.length === 0 ? (
          <p className="rounded-lg border border-black/10 p-6 text-center text-sm text-black/50 dark:border-white/15 dark:text-white/50">
            No employees enrolled yet.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-black/10 dark:border-white/15">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-black/10 text-left dark:border-white/15">
                  <th className="px-4 py-2.5 font-medium">Name</th>
                  <th className="px-4 py-2.5 font-medium">Email</th>
                  <th className="px-4 py-2.5 font-medium">Course</th>
                  <th className="px-4 py-2.5 font-medium">Lessons completed</th>
                  <th className="px-4 py-2.5 font-medium">Certificate</th>
                </tr>
              </thead>
              <tbody>
                {data.employees.map((emp, i) => (
                  <tr key={`${emp.email}-${emp.course}-${i}`} className="border-b border-black/5 last:border-0 dark:border-white/10">
                    <td className="px-4 py-2.5">{emp.full_name}</td>
                    <td className="px-4 py-2.5 text-black/60 dark:text-white/60">{emp.email}</td>
                    <td className="px-4 py-2.5">{emp.course}</td>
                    <td className="px-4 py-2.5">{emp.lessons_completed}</td>
                    <td className="px-4 py-2.5">
                      {emp.certificate_earned ? (
                        <span className="rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800 dark:bg-green-900/50 dark:text-green-300">
                          Earned
                        </span>
                      ) : (
                        <span className="rounded-full bg-black/5 px-2.5 py-0.5 text-xs text-black/60 dark:bg-white/10 dark:text-white/60">
                          Not yet
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
