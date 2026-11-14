"use client";

import { useId } from "react";

/** Trig results differ in the last digits between Node and the browser; round so server and client markup match. */
const r2d = (v: number) => Math.round(v * 100) / 100;

/**
 * An illustration, not a model output: in microgravity a droplet flame has no buoyant plume, so it burns as a
 * blue sphere around the fuel. Here the glow, the white-hot core and the orange soot shell scale with the O₂
 * partial pressure of the chosen atmosphere, so switching scenarios is felt before it is read.
 */
export function FlameOrb({ o2Fraction, pressureKpa, hazard = false, size = 300 }: {
  o2Fraction: number;
  pressureKpa: number;
  /** Outside the flown envelope (e.g. Apollo 1): the soot shell turns to warning red. */
  hazard?: boolean;
  size?: number;
}) {
  const id = useId().replace(/:/g, "");
  const pO2 = o2Fraction * pressureKpa;
  // ISS air is ~21 kPa of O2; Apollo 1's pure-O2 ground test was ~115 kPa.
  const t = Math.min(1, Math.max(0, (pO2 - 10) / 100));
  const coreR = 34 + t * 16;
  const flameR = 70 + t * 18;
  const sootOpacity = 0.12 + t * 0.75;
  const shell = hazard ? "#F0527A" : "#FF8A4C";
  const breathe = `${(4.6 - t * 2.4).toFixed(2)}s`;
  const ticks = Array.from({ length: 60 }, (_, i) => i);
  const o2Angle = -90 + o2Fraction * 360;

  return (
    <svg viewBox="0 0 300 300" width="100%" style={{ maxWidth: size }} role="img"
         aria-label={`Illustration of a spherical droplet flame at ${Math.round(o2Fraction * 100)}% oxygen and ${pressureKpa.toFixed(1)} kPa`}>
      <defs>
        <radialGradient id={`${id}-halo`} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#4F8CFF" stopOpacity={0.55 + t * 0.3} />
          <stop offset="55%" stopColor="#4F8CFF" stopOpacity={0.12 + t * 0.12} />
          <stop offset="100%" stopColor="#4F8CFF" stopOpacity="0" />
        </radialGradient>
        <radialGradient id={`${id}-flame`} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#ffffff" stopOpacity="0" />
          <stop offset="58%" stopColor="#7CB4FF" stopOpacity="0.05" />
          <stop offset="78%" stopColor="#4F8CFF" stopOpacity="0.85" />
          <stop offset="88%" stopColor={shell} stopOpacity={sootOpacity} />
          <stop offset="100%" stopColor={shell} stopOpacity="0" />
        </radialGradient>
        <radialGradient id={`${id}-core`} cx="45%" cy="42%" r="60%">
          <stop offset="0%" stopColor="#ffffff" stopOpacity={0.55 + t * 0.45} />
          <stop offset="45%" stopColor={t > 0.5 ? "#FFE7B8" : "#BFD9FF"} stopOpacity={0.35 + t * 0.4} />
          <stop offset="100%" stopColor="#4F8CFF" stopOpacity="0" />
        </radialGradient>
        <radialGradient id={`${id}-drop`} cx="38%" cy="35%" r="70%">
          <stop offset="0%" stopColor="#5B6B8F" />
          <stop offset="100%" stopColor="#0B0F1A" />
        </radialGradient>
        <linearGradient id={`${id}-ring`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#22D3EE" />
          <stop offset="100%" stopColor="#A78BFA" />
        </linearGradient>
        <filter id={`${id}-blur`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="6" />
        </filter>
      </defs>

      {/* Instrument dial: 60 ticks, the O2 fraction swept as an arc */}
      <g opacity="0.75">
        {ticks.map((i) => {
          const a = (i / 60) * Math.PI * 2;
          const long = i % 5 === 0;
          const r1 = long ? 132 : 136, r2 = 141;
          return (
            <line key={i} x1={r2d(150 + Math.cos(a) * r1)} y1={r2d(150 + Math.sin(a) * r1)} x2={r2d(150 + Math.cos(a) * r2)} y2={r2d(150 + Math.sin(a) * r2)}
                  stroke={long ? "rgba(124,180,255,0.55)" : "rgba(124,180,255,0.22)"} strokeWidth={long ? 1.4 : 1} />
          );
        })}
      </g>
      <circle cx="150" cy="150" r="146" fill="none" stroke={`url(#${id}-ring)`} strokeWidth="2.5" strokeLinecap="round"
              pathLength={100} strokeDasharray={`${(o2Fraction * 100).toFixed(1)} 100`} transform="rotate(-90 150 150)"
              style={{ filter: "drop-shadow(0 0 6px rgba(34,211,238,0.8))", transition: "stroke-dasharray 900ms var(--ease-out-expo)" }} />
      <circle cx={r2d(150 + Math.cos((o2Angle * Math.PI) / 180) * 146)} cy={r2d(150 + Math.sin((o2Angle * Math.PI) / 180) * 146)} r="4.5"
              fill="#fff" style={{ filter: "drop-shadow(0 0 6px #22D3EE)" }} />

      {/* Orbits */}
      <g className="orbit-spin">
        <ellipse cx="150" cy="150" rx="118" ry="40" fill="none" stroke="rgba(124,180,255,0.22)" strokeWidth="1" transform="rotate(-24 150 150)" />
        <circle cx="258" cy="102" r="3" fill="#22D3EE" style={{ filter: "drop-shadow(0 0 4px #22D3EE)" }} />
      </g>
      <g className="orbit-spin-rev">
        <ellipse cx="150" cy="150" rx="108" ry="30" fill="none" stroke="rgba(167,139,250,0.2)" strokeWidth="1" strokeDasharray="3 5" transform="rotate(32 150 150)" />
        <circle cx="62" cy="96" r="2.4" fill="#A78BFA" />
      </g>

      {/* The flame */}
      <g className="flame-breathe" style={{ animationDuration: breathe }}>
        <circle cx="150" cy="150" r={flameR + 40} fill={`url(#${id}-halo)`} style={{ transition: "r 900ms var(--ease-out-expo)" }} />
        <circle cx="150" cy="150" r={flameR} fill={`url(#${id}-flame)`} filter={`url(#${id}-blur)`} style={{ transition: "r 900ms var(--ease-out-expo)" }} />
        <circle cx="150" cy="150" r={flameR - 6} fill="none" stroke="#9CC6FF" strokeOpacity={0.35 + t * 0.3} strokeWidth="1.2" />
        <circle cx="150" cy="150" r={coreR} fill={`url(#${id}-core)`} />
      </g>
      {/* Fuel droplet at the centre */}
      <circle cx="150" cy="150" r="9" fill={`url(#${id}-drop)`} stroke="rgba(255,255,255,0.25)" strokeWidth="0.8" />
    </svg>
  );
}
