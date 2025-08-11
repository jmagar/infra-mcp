import * as React from "react"
import { cn } from "@/lib/modern-design-system"

interface SparklineProps {
  data: number[]
  width?: number
  height?: number
  className?: string
  color?: string
  strokeWidth?: number
  animated?: boolean
}

export function Sparkline({ 
  data, 
  width = 100, 
  height = 24, 
  className,
  color = "rgba(59, 130, 246, 0.8)", // blue-500
  strokeWidth = 2,
  animated = true 
}: SparklineProps) {
  const pathRef = React.useRef<SVGPathElement>(null)
  
  React.useEffect(() => {
    if (animated && pathRef.current) {
      const path = pathRef.current
      const pathLength = path.getTotalLength()
      path.style.strokeDasharray = `${pathLength} ${pathLength}`
      path.style.strokeDashoffset = `${pathLength}`
      path.style.animation = 'sparkline-draw 1.5s ease-out forwards'
    }
  }, [animated, data])

  if (!data || data.length === 0) return null

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1

  // Generate SVG path
  const pathData = data.map((value, index) => {
    const x = (index / (data.length - 1)) * width
    const y = height - ((value - min) / range) * height
    return index === 0 ? `M ${x} ${y}` : `L ${x} ${y}`
  }).join(' ')

  return (
    <div className={cn("relative", className)}>
      <svg width={width} height={height} className="overflow-visible">
        <defs>
          <linearGradient id="sparklineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={color} stopOpacity="0.3" />
            <stop offset="100%" stopColor={color} stopOpacity="0.8" />
          </linearGradient>
        </defs>
        
        {/* Area fill */}
        <path
          d={`${pathData} L ${width} ${height} L 0 ${height} Z`}
          fill="url(#sparklineGradient)"
          className="opacity-20"
        />
        
        {/* Line */}
        <path
          ref={pathRef}
          d={pathData}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="drop-shadow-sm"
        />
        
        {/* Current value dot */}
        <circle
          cx={width}
          cy={height - ((data[data.length - 1] - min) / range) * height}
          r="2"
          fill={color}
          className={cn(
            "drop-shadow-sm",
            animated && "animate-pulse"
          )}
        />
      </svg>
      
      <style jsx>{`
        @keyframes sparkline-draw {
          from {
            stroke-dashoffset: ${pathRef.current?.getTotalLength() || 0};
          }
          to {
            stroke-dashoffset: 0;
          }
        }
      `}</style>
    </div>
  )
}

// Generate sample data for demonstration
export function generateSparklineData(points: number = 20, trend: 'up' | 'down' | 'volatile' = 'volatile'): number[] {
  const data: number[] = []
  let baseValue = 50
  
  for (let i = 0; i < points; i++) {
    let variation = 0
    
    switch (trend) {
      case 'up':
        variation = Math.random() * 5 + i * 0.5
        break
      case 'down':
        variation = Math.random() * 5 - i * 0.5
        break
      case 'volatile':
        variation = (Math.random() - 0.5) * 10
        break
    }
    
    baseValue += variation
    data.push(Math.max(0, Math.min(100, baseValue)))
  }
  
  return data
}