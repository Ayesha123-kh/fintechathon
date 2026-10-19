"use client";

import clsx from "clsx";
import { Search, Trash2 } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";
import { Button, Card, Input, Spinner } from "@/components/ui";
import { api, errorText, fetcher } from "@/lib/api";
import { PageHeader } from "@/components/admin";

type AdminUser = { id: string; email: string; full_name: string; is_active: boolean; onboarding_completed: boolean;
  created_at: string; last_login_at: string | null; assistant: string };

function UsersTab() {
  const [q, setQ] = useState("");
  const { data, mutate } = useSWR<{ total: number; users: AdminUser[] }>(`/admin/users?q=${encodeURIComponent(q)}`, fetcher);
  const [error, setError] = useState("");
  const patch = async (id: string, body: object) => {
    setError("");
    try {
      await api(`/admin/users/${id}`, { method: "PATCH", json: body });
      mutate();
    } catch (e) {
      setError(errorText(e));
    }
  };
  const remove = async (u: AdminUser) => {
    if (!window.confirm(`Permanently delete ${u.email}? All their data and their assistant team will be removed. This cannot be undone.`)) return;
    setError("");
    try {
      await api(`/admin/users/${u.id}`, { method: "DELETE" });
      mutate();
    } catch (e) {
      setError(errorText(e));
    }
  };
  return (
    <Card className="space-y-4">
      <div className="relative">
        <Search className="pointer-events-none absolute top-1/2 left-4 z-10 size-4 -translate-y-1/2 text-muted" aria-hidden />
        <Input placeholder="Search by name or email" value={q} onChange={(e) => setQ(e.target.value)} className="pl-10" aria-label="Search users" />
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      {!data ? <Spinner /> : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead className="text-xs text-muted"><tr>
              <th className="py-2 font-medium">User</th><th className="font-medium">Onboarded</th>
              <th className="font-medium">Assistant</th><th className="font-medium">Last login</th><th className="font-medium" />
            </tr></thead>
            <tbody className="divide-y divide-line">
              {data.users.map((u) => (
                <tr key={u.id} className={clsx(!u.is_active && "opacity-50")}>
                  <td className="py-2.5"><p className="font-semibold">{u.full_name || "—"}</p><p className="text-xs text-muted">{u.email}</p></td>
                  <td>{u.onboarding_completed ? "Yes" : "No"}</td>
                  <td className={clsx(u.assistant === "error" && "text-danger")}>{u.assistant}</td>
                  <td className="text-xs text-muted">{u.last_login_at ? new Date(u.last_login_at).toLocaleDateString() : "—"}</td>
                  <td className="space-x-1 text-right whitespace-nowrap">
                    <Button size="sm" variant={u.is_active ? "ghost" : "outline"} onClick={() => patch(u.id, { is_active: !u.is_active })}>
                      {u.is_active ? "Disable" : "Enable"}
                    </Button>
                    <button aria-label={`Delete ${u.email}`} onClick={() => remove(u)}
                      className="inline-grid size-9 place-items-center rounded-full align-middle text-danger hover:bg-hover">
                      <Trash2 className="size-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-xs text-muted">{data.total} users</p>
        </div>
      )}
    </Card>
  );
}

export default function Page() {
  return (
    <div className="space-y-5">
      <PageHeader title="Users" subtitle="Regular accounts only; admin accounts are not users." />
      <UsersTab />
    </div>
  );
}
