import { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';

export interface SparklineDataPoint {
  value: number;
  timestamp: number;
}

interface SparklineProps {
  data: SparklineDataPoint[];
  width?: number;
  height?: number;
  color?: string;
  fillColor?: string;
  strokeWidth?: number;
  showDots?: boolean;
  showArea?: boolean;
  animate?: boolean;
  className?: string;
  min?: number;
  max?: number;
}

export function Sparkline({
  data,
  width = 80,
  height = 24,
  color = 'currentColor',
  fillColor,
  strokeWidth = 1.5,
  showDots = false,
  showArea = true,
  animate = true,
  className,
  min,
  max
}: SparklineProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [animationProgress, setAnimationProgress] = useState(animate ? 0 : 1);
  
  // Calculate min/max values if not provided
  const values = data.map(d => d.value);
  const minValue = min !== undefined ? min : Math.min(...values);
  const maxValue = max !== undefined ? max : Math.max(...values);
  const range = maxValue - minValue || 1;
  
  // Animation effect
  useEffect(() => {
    if (!animate) return;
    
    let animationFrame: number;
    let startTime: number;
    const duration = 1000; // 1 second animation
    
    const animateProgress = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const elapsed = timestamp - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      // Easing function (ease-out)
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimationProgress(eased);
      
      if (progress < 1) {
        animationFrame = requestAnimationFrame(animateProgress);
      }
    };
    
    animationFrame = requestAnimationFrame(animateProgress);
    
    return () => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
      }
    };
  }, [animate, data]);
  
  // Generate SVG path
  const generatePath = (points: SparklineDataPoint[], isArea = false) => {
    if (points.length === 0) return '';
    
    const stepX = width / Math.max(1, points.length - 1);
    
    let path = '';
    
    points.forEach((point, index) => {
      const x = index * stepX;
      const y = height - ((point.value - minValue) / range) * height;
      
      if (index === 0) {
        path += `M ${x} ${y}`;
        if (isArea) {
          // Start from bottom for area
          path = `M ${x} ${height} L ${x} ${y}`;
        }
      } else {
        path += ` L ${x} ${y}`;
      }
    });
    
    if (isArea) {
      // Close the area path
      const lastX = (points.length - 1) * stepX;
      path += ` L ${lastX} ${height} Z`;
    }
    
    return path;
  };
  
  // Animate the data based on progress
  const animatedDataLength = Math.max(1, Math.floor(data.length * animationProgress));
  const animatedData = data.slice(0, animatedDataLength);
  
  const linePath = generatePath(animatedData);
  const areaPath = showArea ? generatePath(animatedData, true) : '';
  
  const actualFillColor = fillColor || `${color}20`; // 20% opacity if no fill color specified
  
  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={cn('sparkline overflow-visible', className)}
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id={`gradient-${Math.random()}`} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0.1" />
        </linearGradient>
      </defs>
      
      {/* Area fill */}
      {showArea && areaPath && (
        <path
          d={areaPath}
          fill={`url(#gradient-${Math.random()})`}
          className="sparkline-area"
        />
      )}
      
      {/* Main line */}
      {linePath && (
        <path
          d={linePath}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="sparkline-line"
          style={{
            filter: 'drop-shadow(0 0 2px currentColor)',
          }}
        />
      )}
      
      {/* Data points */}
      {showDots && animatedData.map((point, index) => {
        const x = index * (width / Math.max(1, data.length - 1));
        const y = height - ((point.value - minValue) / range) * height;
        
        return (
          <circle
            key={`${point.timestamp}-${index}`}
            cx={x}
            cy={y}
            r={1.5}
            fill={color}
            className="sparkline-dot animate-scale-in"
            style={{
              animationDelay: `${index * 50}ms`,
            }}
          />
        );
      })}
    </svg>
  );
}

// Utility component for metric cards with sparklines
interface MetricSparklineProps {
  label: string;
  value: string | number;
  unit?: string;
  data: SparklineDataPoint[];
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  color?: string;
  className?: string;
}

export function MetricSparkline({
  label,
  value,
  unit,
  data,
  trend = 'neutral',
  trendValue,
  color,
  className
}: MetricSparklineProps) {
  const getTrendColor = () => {
    switch (trend) {
      case 'up':
        return 'text-green-600 dark:text-green-400';
      case 'down':
        return 'text-red-600 dark:text-red-400';
      default:
        return 'text-muted-foreground';
    }
  };
  
  const sparklineColor = color || (
    trend === 'up' ? '#10b981' : 
    trend === 'down' ? '#ef4444' : 
    'currentColor'
  );
  
  return (
    <div className={cn('flex items-center justify-between space-x-3', className)}>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-foreground truncate">
          {value}
          {unit && <span className="text-muted-foreground ml-1">{unit}</span>}
        </div>
        <div className="text-xs text-muted-foreground truncate">
          {label}
        </div>
        {trendValue && (
          <div className={cn('text-xs font-medium', getTrendColor())}>
            {trend === 'up' && '↗ '}
            {trend === 'down' && '↘ '}
            {trendValue}
          </div>
        )}
      </div>
      
      <div className="flex-shrink-0">
        <Sparkline
          data={data}
          width={60}
          height={20}
          color={sparklineColor}
          strokeWidth={2}
          animate
          className="opacity-75"
        />
      </div>
    </div>
  );
}

// Generate sample data for testing
export function generateSampleSparklineData(
  points = 20,
  baseValue = 50,
  variance = 20,
  trend = 0
): SparklineDataPoint[] {
  const data: SparklineDataPoint[] = [];
  const now = Date.now();
  
  for (let i = 0; i < points; i++) {
    const timestamp = now - (points - i - 1) * 60000; // Every minute
    const trendValue = trend * (i / points) * baseValue;
    const randomValue = (Math.random() - 0.5) * variance;
    const value = Math.max(0, baseValue + trendValue + randomValue);
    
    data.push({ value, timestamp });
  }
  
  return data;
}