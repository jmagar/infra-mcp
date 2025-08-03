"use client"

import { useEffect, useState } from "react"

// Mock data for the chart
const generateMockData = () => {
  const now = Date.now()
  const data = []

  for (let i = 23; i >= 0; i--) {
    data.push({
      time: new Date(now - i * 60 * 60 * 1000).toLocaleTimeString("en-US", {
        hour: "2-digit",
        minute: "2-digit",
      }),
      cpu: Math.floor(Math.random() * 40) + 20,
      memory: Math.floor(Math.random() * 30) + 40,
      network: Math.floor(Math.random() * 20) + 10,
    })
  }

  return data
}

export function SystemMetricsChart() {
  const [data, setData] = useState(generateMockData())

  useEffect(() => {
    const interval = setInterval(() => {
      setData(generateMockData())
    }, 30000) // Update every 30 seconds

    return () => clearInterval(interval)
  }, [])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">System Metrics (24h)</h3>
        <div className="flex items-center space-x-4 text-xs">
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
            <span>CPU</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            <span>Memory</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 bg-purple-500 rounded-full"></div>
            <span>Network</span>
          </div>
        </div>
      </div>

      <div className="h-64 w-full">
        <svg viewBox="0 0 800 200" className="w-full h-full">
          {/* Grid lines */}
          {[0, 25, 50, 75, 100].map((y) => (
            <line
              key={y}
              x1="0"
              y1={200 - y * 2}
              x2="800"
              y2={200 - y * 2}
              stroke="currentColor"
              strokeOpacity="0.1"
              strokeWidth="1"
            />
          ))}

          {/* CPU Line */}
          <polyline
            fill="none"
            stroke="#3b82f6"
            strokeWidth="2"
            points={data.map((d, i) => `${(i * 800) / (data.length - 1)},${200 - d.cpu * 2}`).join(" ")}
          />

          {/* Memory Line */}
          <polyline
            fill="none"
            stroke="#10b981"
            strokeWidth="2"
            points={data.map((d, i) => `${(i * 800) / (data.length - 1)},${200 - d.memory * 2}`).join(" ")}
          />

          {/* Network Line */}
          <polyline
            fill="none"
            stroke="#8b5cf6"
            strokeWidth="2"
            points={data.map((d, i) => `${(i * 800) / (data.length - 1)},${200 - d.network * 2}`).join(" ")}
          />
        </svg>
      </div>

      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{data[0]?.time}</span>
        <span>Now</span>
      </div>
    </div>
  )
}
