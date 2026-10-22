import { useState } from 'react';
import { View, type LayoutChangeEvent } from 'react-native';
import Svg, { Defs, LinearGradient, Path, Rect, Stop } from 'react-native-svg';

// Lightweight SVG charts (no native module beyond react-native-svg, which is
// already linked) — a filled area trend and a bar chart, bklit-style.

function useWidth(): [number, (e: LayoutChangeEvent) => void] {
  const [w, setW] = useState(320);
  return [w, (e) => setW(Math.max(1, Math.round(e.nativeEvent.layout.width)))];
}

export function TrendChart({ data, color, height = 120 }: { data: number[]; color: string; height?: number }) {
  const [w, onLayout] = useWidth();
  const pad = 10;
  const pts = toPoints(data, w, height, pad);
  const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const base = height - pad;
  const first = pts[0];
  const last = pts[pts.length - 1];
  const area = first && last
    ? `${line} L${last[0].toFixed(1)},${base} L${first[0].toFixed(1)},${base} Z`
    : '';
  return (
    <View onLayout={onLayout}>
      <Svg width={w} height={height}>
        <Defs>
          <LinearGradient id="area-grad" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor={color} stopOpacity={0.30} />
            <Stop offset="1" stopColor={color} stopOpacity={0.02} />
          </LinearGradient>
        </Defs>
        {area ? <Path d={area} fill="url(#area-grad)" /> : null}
        <Path d={line} stroke={color} strokeWidth={2.5} fill="none" strokeLinejoin="round" strokeLinecap="round" />
      </Svg>
    </View>
  );
}

export function BarChart({ data, color, height = 120 }: { data: number[]; color: string; height?: number }) {
  const [w, onLayout] = useWidth();
  const pad = 10;
  const max = Math.max(...data, 1);
  const n = Math.max(data.length, 1);
  const slot = (w - pad * 2) / n;
  const bw = slot * 0.56;
  return (
    <View onLayout={onLayout}>
      <Svg width={w} height={height}>
        {data.map((v, i) => {
          const bh = (v / max) * (height - pad * 2);
          const x = pad + i * slot + (slot - bw) / 2;
          return <Rect key={i} x={x} y={height - pad - bh} width={bw} height={Math.max(bh, 2)} rx={4} fill={color} opacity={0.9} />;
        })}
      </Svg>
    </View>
  );
}

function toPoints(data: number[], w: number, h: number, pad: number): [number, number][] {
  if (data.length === 0) return [];
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const stepX = data.length > 1 ? (w - pad * 2) / (data.length - 1) : 0;
  return data.map((v, i) => [pad + i * stepX, h - pad - ((v - min) / range) * (h - pad * 2)]);
}

// Deterministic, nice-looking weekly trend ending at `value` (demo visualisation).
export function weeklyTrend(value: number): number[] {
  const shape = [0.52, 0.64, 0.58, 0.8, 0.73, 0.9, 1];
  return shape.map((f) => Math.max(0, Math.round(value * f)));
}
