/**
 * Inline SVG sparkline component.
 * Inspired by WorldMonitor's miniSparkline utility.
 */

interface MiniSparklineProps {
  data: number[];
  change?: number;
  width?: number;
  height?: number;
  className?: string;
}

export function MiniSparkline({
  data,
  change = 0,
  width = 50,
  height = 16,
  className = '',
}: MiniSparklineProps) {
  if (!data || data.length < 2) return null;

  const color = change >= 0 ? 'var(--profit)' : 'var(--loss)';
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;

  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((v - min) / range) * (height - 2) - 1;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      style={{ display: 'inline-block', verticalAlign: 'middle' }}
    >
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
