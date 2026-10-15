import { useMemo, useState } from 'react'

import type { OhlcvDaily, QuoteSnapshot } from '../generated/client/types.gen'

type Series = 'both' | 'close' | 'snapshot'
type Point = { date: string; close: number | null; snapshot: number | null }

const WIDTH = 1200
const HEIGHT = 280
const LEFT = 82
const RIGHT = 20
const TOP = 20
const BOTTOM = 30

function asNumber(value: string | null | undefined): number | null {
  if (value == null || value === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

function buildPoints(ohlcvRows: OhlcvDaily[], priceRows: QuoteSnapshot[]): Point[] {
  const byDate = new Map<string, Point>()
  for (const row of ohlcvRows) {
    const point = byDate.get(row.date) ?? { date: row.date, close: null, snapshot: null }
    point.close = asNumber(row.close)
    byDate.set(row.date, point)
  }
  for (const row of priceRows) {
    const point = byDate.get(row.date) ?? { date: row.date, close: null, snapshot: null }
    point.snapshot = asNumber(row.price)
    byDate.set(row.date, point)
  }
  return [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date))
}

function dateBefore(date: string, days: number): string {
  const value = new Date(`${date}T00:00:00Z`)
  value.setUTCDate(value.getUTCDate() - days + 1)
  return value.toISOString().slice(0, 10)
}

function axisPrice(value: number, currency: string): string {
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency,
    notation: 'compact',
    maximumFractionDigits: 2,
  }).format(value)
}

export function PriceLineChart({
  ohlcvRows,
  priceRows,
  currency,
}: {
  ohlcvRows: OhlcvDaily[]
  priceRows: QuoteSnapshot[]
  currency: string
}) {
  const [range, setRange] = useState(30)
  const [series, setSeries] = useState<Series>('both')
  const allPoints = useMemo(() => buildPoints(ohlcvRows, priceRows), [ohlcvRows, priceRows])
  const latestDate = allPoints.at(-1)?.date
  const points = latestDate
    ? allPoints.filter((point) => point.date >= dateBefore(latestDate, range))
    : []
  const showClose = series !== 'snapshot'
  const showSnapshot = series !== 'close'
  const snapshotCount = points.filter((point) => point.snapshot !== null).length
  const values = points.flatMap((point) => [
    ...(showClose && point.close !== null ? [point.close] : []),
    ...(showSnapshot && point.snapshot !== null ? [point.snapshot] : []),
  ])
  const hasData = values.length > 0
  const rawMin = hasData ? Math.min(...values) : 0
  const rawMax = hasData ? Math.max(...values) : 1
  const padding = Math.max((rawMax - rawMin) * 0.08, Math.abs(rawMax) * 0.01, 0.01)
  const min = rawMin - padding
  const max = rawMax + padding
  const plotWidth = WIDTH - LEFT - RIGHT
  const plotHeight = HEIGHT - TOP - BOTTOM
  const x = (index: number) => LEFT + (points.length === 1 ? plotWidth / 2 : (index / (points.length - 1)) * plotWidth)
  const y = (value: number) => TOP + ((max - value) / (max - min)) * plotHeight
  const line = (key: 'close' | 'snapshot') => {
    let started = false
    return points.flatMap((point, index) => {
      if (point[key] === null) return []
      const command = `${started ? 'L' : 'M'} ${x(index)} ${y(point[key])}`
      started = true
      return [command]
    }).join(' ')
  }

  return (
    <div className="price-chart">
      <div className="chart-toolbar">
        <div className="chart-filter" aria-label="Chart date range">
          {[7, 30, 90].map((days) => (
            <button key={days} type="button" aria-pressed={range === days} onClick={() => setRange(days)}>
              {days}D
            </button>
          ))}
        </div>
        <div className="chart-filter" aria-label="Chart data series">
          {([['both', 'Both'], ['close', 'Close'], ['snapshot', 'Snapshot']] as const).map(([value, label]) => (
            <button key={value} type="button" aria-pressed={series === value} onClick={() => setSeries(value)}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {hasData ? (
        <>
          <div className="chart-canvas">
            <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={`${series === 'both' ? 'Daily closing and quote snapshot prices' : series === 'close' ? 'Daily closing prices' : 'Daily quote snapshot prices'} from ${points[0].date} to ${points.at(-1)?.date}`}>
              {[0, 0.5, 1].map((fraction) => {
                const tickY = TOP + fraction * plotHeight
                return (
                  <g key={fraction}>
                    <line className="chart-gridline" x1={LEFT} x2={WIDTH - RIGHT} y1={tickY} y2={tickY} />
                    <text className="chart-axis-label" x={LEFT - 8} y={tickY + 4} textAnchor="end">
                      {axisPrice(max - fraction * (max - min), currency)}
                    </text>
                  </g>
                )
              })}
              {showClose && <path className="chart-line close-line" d={line('close')} />}
              {showSnapshot && <path className="chart-line snapshot-line" d={line('snapshot')} />}
              {points.map((point, index) => (
                <g key={point.date}>
                  {showClose && point.close !== null && (
                    <circle className="chart-point close-point" cx={x(index)} cy={y(point.close)} r={points.length < 15 || index === points.length - 1 ? 3.5 : 2}>
                      <title>{`${point.date} · Close ${axisPrice(point.close, currency)}`}</title>
                    </circle>
                  )}
                  {showSnapshot && point.snapshot !== null && (
                    <circle className="chart-point snapshot-point" cx={x(index)} cy={y(point.snapshot)} r={points.length < 15 || index === points.length - 1 ? 4 : 2.5}>
                      <title>{`${point.date} · Snapshot ${axisPrice(point.snapshot, currency)}`}</title>
                    </circle>
                  )}
                </g>
              ))}
            </svg>
          </div>
          <div className="chart-footer">
            <span>{points[0].date}</span>
            <div className="chart-legend">
              {showClose && <span className="legend-close">OHLCV Close</span>}
              {showSnapshot && <span className="legend-snapshot">Snapshot price</span>}
            </div>
            <span>{points.at(-1)?.date}</span>
          </div>
          {showSnapshot && snapshotCount === 1 && (
            <p className="chart-note">One quote snapshot in this range; the series appears as a point.</p>
          )}
        </>
      ) : (
        <p className="chart-empty">No prices in this range.</p>
      )}
    </div>
  )
}
