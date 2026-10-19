"use client";

import { AdminSidebar, AdminTabs } from "@/components/AdminNav";
import { AppShell } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import { useSession } from "@/lib/session";

/** Every /admin page: the app header, the left sidebar on laptops, the tab strip on phones. */
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { user } = useSession();
  return (
    <AppShell sidebar={<AdminSidebar />}>
      {user?.role !== "admin" ? <Spinner /> : (
        <>
          <AdminTabs />
          {children}
        </>
      )}
    </AppShell>
  );
}
