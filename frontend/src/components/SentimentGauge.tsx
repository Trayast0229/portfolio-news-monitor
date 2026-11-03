import { useEffect, useState } from "react";
import { ZONES, arcPath, needleRotation, zoneFor } from "../lib/gauge";

const CX = 160;
const CY = 160;
const R = 128;
const NEEDLE = 102;
const HUB = 40;
const GAP = 0.7; // score units left blank between zones

interface Props {
  /** null shows the resting gauge before anything has been analyzed */
  score: number | null;
  caption?: string;
}

export function SentimentGauge({ score, caption }: Props) {
  // Start upright and let the CSS transition sweep the needle to the score.
  const [rotation, setRotation] = useState(needleRotation(50));
  useEffect(() => {
    const id = requestAnimationFrame(() => setRotation(needleRotation(score ?? 50)));
    return () => cancelAnimationFrame(id);
  }, [score]);

  const zone = score === null ? null : zoneFor(score);
  const label = score === null ? "No score yet" : `Sentiment score ${score} of 100, ${zone!.label}`;

  return (
    <figure className="gauge" data-idle={score === null}>
      <svg viewBox="0 0 320 214" role="img" aria-label={label}>
        {ZONES.map((z) => (
          <path
            key={z.label}
            className={`gauge-zone tone-${z.tone}`}
            data-active={zone?.label === z.label}
            d={arcPath(z.from + (z.from === 0 ? 0 : GAP / 2), z.to - (z.to === 100 ? 0 : GAP / 2), CX, CY, R)}
          />
        ))}
        <text className="gauge-end" x={CX - R} y={CY + 30} textAnchor="middle">0</text>
        <text className="gauge-end" x={CX + R} y={CY + 30} textAnchor="middle">100</text>
        {/* Pivot at 0 0, then move to the hub. Safari reads a px transform-origin as
            screen pixels, so "160px" missed the hub whenever the gauge was scaled. */}
        <g transform={`translate(${CX} ${CY})`}>
          <g className="gauge-needle" style={{ transform: `rotate(${rotation}deg)`, transformOrigin: "0 0" }}>
            <line x1={0} y1={0} x2={-NEEDLE} y2={0} />
          </g>
        </g>
        <circle className={`gauge-hub ${zone ? `tone-${zone.tone}` : ""}`} cx={CX} cy={CY} r={HUB} />
        <text className="gauge-score" x={CX} y={CY} textAnchor="middle" dominantBaseline="central">
          {score ?? "–"}
        </text>
      </svg>
      <figcaption className={`gauge-label ${zone ? `tone-${zone.tone}` : ""}`}>
        {zone?.label ?? caption ?? "Waiting for a story"}
      </figcaption>
    </figure>
  );
}
