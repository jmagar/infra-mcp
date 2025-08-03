import { DashboardOverview } from "@/components/dashboard-overview"
import { Sidebar } from "@/components/sidebar"

export default function HomePage() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="container mx-auto p-6">
          <div className="mb-8">
            <h1 className="text-3xl font-bold tracking-tight">Infrastructure Dashboard</h1>
            <p className="text-muted-foreground">Monitor and manage your self-hosted infrastructure</p>
          </div>
          <DashboardOverview />
        </div>
      </main>
    </div>
  )
}
