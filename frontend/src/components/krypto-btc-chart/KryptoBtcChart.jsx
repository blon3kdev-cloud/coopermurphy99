import { useId } from 'react'
import { Liveline } from 'liveline'
import { useBtcLivelineChart } from '../../hooks/useBtcLivelineChart'
import './KryptoBtcChart.css'

const btcFmt = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

function fmtUsd(v) {
  return `$${btcFmt.format(v)}`
}

export function KryptoBtcChart() {
  const chartKey = useId()
  const { data, value, windowSec, loading } = useBtcLivelineChart()

  return (
    <div
      className="bety-krypto__chart"
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
      role="presentation"
    >
      <div className="bety-krypto__chart-body">
        <Liveline
          key={chartKey}
          data={data}
          value={value}
          theme="dark"
          color="#f7931a"
          window={windowSec}
          loading={loading}
          exaggerate
          formatValue={fmtUsd}
          scrub={false}
          className="bety-krypto__chart-canvas"
        />
      </div>
    </div>
  )
}
