import { AppShell } from "@/components/app-shell";
import { requireCurrentUser } from "@/lib/current-user";
import { getEnabledModules } from "@/lib/module-settings";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const user = await requireCurrentUser();
  const enabledModules = getEnabledModules();

  return (
    <AppShell user={user} enabledModules={enabledModules}>
      {children}
    </AppShell>
  );
}
