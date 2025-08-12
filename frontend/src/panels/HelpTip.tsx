import React from 'react'

type Props = { text: string }

export default function HelpTip({ text }: Props) {
  const [open, setOpen] = React.useState(false)
  const containerRef = React.useRef<HTMLSpanElement | null>(null)
  const tipRef = React.useRef<HTMLSpanElement | null>(null)
  const [left, setLeft] = React.useState<number>(0)

  function positionTooltip() {
    const cont = containerRef.current
    const tip = tipRef.current
    if (!cont || !tip) return

    // Measure after it's visible
    const contRect = cont.getBoundingClientRect()
    const tipRect = tip.getBoundingClientRect()
    const viewport = window.innerWidth

    const desiredLeftPx = contRect.left + contRect.width / 2 - tipRect.width / 2
    const clampedLeftPx = Math.max(8, Math.min(desiredLeftPx, viewport - tipRect.width - 8))

    // Convert to container-relative
    setLeft(clampedLeftPx - contRect.left)
  }

  React.useEffect(() => {
    if (open) {
      // Defer until tooltip is in DOM flow
      const id = window.requestAnimationFrame(positionTooltip)
      return () => window.cancelAnimationFrame(id)
    }
  }, [open, text])

  return (
    <span
      className="help-tip"
      aria-label="help"
      ref={containerRef}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <span className="help-icon">?</span>
      <span
        role="tooltip"
        ref={tipRef}
        className="tooltip"
        style={{ left, opacity: open ? 1 : 0 }}
      >
        {text}
      </span>
    </span>
  )
}


