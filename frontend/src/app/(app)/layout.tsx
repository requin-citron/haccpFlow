import { AppShell } from "@/components/app-shell";
import { requireCurrentUser } from "@/lib/current-user";
import { getEnabledModules } from "@/lib/module-settings";
import { getLocale } from "@/lib/locale";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const user = await requireCurrentUser();
  const enabledModules = getEnabledModules();
  const locale = await getLocale();

  return (
    <AppShell user={user} enabledModules={enabledModules} locale={locale}>
      {children}
    </AppShell>
  );
}
