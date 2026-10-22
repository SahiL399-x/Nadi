import { useState } from 'react';
import { View, type LayoutChangeEvent } from 'react-native';
import Svg, { Circle, Defs, LinearGradient, Path, Rect, Stop, Text as SvgText } from 'react-native-svg';
import { colors } from '@/theme/tokens';

// Lightweight interactive SVG charts (react-native-svg is already linked).
// Tap a point/bar to reveal its value; weekday labels sit on the x-axis.

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

function useWidth(): [number, (e: LayoutChangeEvent) => void] {
  const [w, setW] = useState(320);
  return [w, (e) => setW(Math.max(1, Math.round(e.nativeEvent.layout.width)))];
}

export function TrendChart({ data, color, height = 150, labels = DAYS }:
  { data: number[]; color: string; height?: number; labels?: string[] }) {
  const [w, onLayout] = useWidth();
  const [sel, setSel] = useState<number | null>(null);
  const padX = 16, top = 26, bot = 24;
  const n = data.length || 1;
  const max = Math.max(...data, 1), min = Math.min(...data, 0), range = max - min || 1;
  const stepX = n > 1 ? (w - padX * 2) / (n - 1) : 0;
  const x = (i: number) => padX + i * stepX;
  const y = (v: number) => top + (1 - (v - min) / range) * (height - top - bot);
  const pts = data.map((v, i) => [x(i), y(v)] as [number, number]);
  const line = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const base = height - bot;
  const first = pts[0], last = pts[pts.length - 1];
  const area = first && last ? `${line} L${last[0].toFixed(1)},${base} L${first[0].toFixed(1)},${base} Z` : '';
  const colW = (w - padX * 2) / Math.max(n - 1, 1);
  const selPt = sel !== null ? pts[sel] : undefined;
  return (
    <View onLayout={onLayout}>
      <Svg width={w} height={height}>
        <Defs>
          <LinearGradient id="trend-grad" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor={color} stopOpacity={0.3} />
            <Stop offset="1" stopColor={color} stopOpacity={0.02} />
          </LinearGradient>
        </Defs>
        {area ? <Path d={area} fill="url(#trend-grad)" /> : null}
        <Path d={line} stroke={color} strokeWidth={2.5} fill="none" strokeLinejoin="round" strokeLinecap="round" />
        {pts.map((p, i) => (
          <Circle key={`p${i}`} cx={p[0]} cy={p[1]} r={sel === i ? 6 : 3.5} fill={color} stroke={colors.white} strokeWidth={2} />
        ))}
        {pts.map((p, i) => (
          <Rect key={`h${i}`} x={p[0] - colW / 2} y={0} width={colW} height={height} fill="transparent" onPress={() => setSel(i)} />
        ))}
        {selPt ? (
          <SvgText x={selPt[0]} y={Math.max(selPt[1] - 10, 12)} fontSize={13} fontWeight="bold" fill={colors.text} textAnchor="middle">
            {data[sel as number]}
          </SvgText>
        ) : null}
        {labels.slice(0, n).map((l, i) => (
          <SvgText key={`l${i}`} x={x(i)} y={height - 6} fontSize={10} fill={colors.textMuted} textAnchor="middle">{l.slice(0, 3)}</SvgText>
        ))}
      </Svg>
    </View>
  );
}

export function BarChart({ data, color, height = 150, labels = DAYS }:
  { data: number[]; color: string; height?: number; labels?: string[] }) {
  const [w, onLayout] = useWidth();
  const [sel, setSel] = useState<number | null>(null);
  const padX = 16, top = 26, bot = 24;
  const n = data.length || 1;
  const max = Math.max(...data, 1);
  const slot = (w - padX * 2) / n;
  const bw = slot * 0.5;
  const cx = (i: number) => padX + i * slot + slot / 2;
  const barH = (v: number) => (v / max) * (height - top - bot);
  return (
    <View onLayout={onLayout}>
      <Svg width={w} height={height}>
        {data.map((v, i) => (
          <Rect key={`b${i}`} x={cx(i) - bw / 2} y={height - bot - barH(v)} width={bw} height={Math.max(barH(v), 2)}
            rx={4} fill={color} opacity={sel === i ? 1 : 0.85} onPress={() => setSel(i)} />
        ))}
        {sel !== null && data[sel] !== undefined ? (
          <SvgText x={cx(sel)} y={height - bot - barH(data[sel]) - 6} fontSize={13} fontWeight="bold" fill={colors.text} textAnchor="middle">
            {data[sel]}
          </SvgText>
        ) : null}
        {labels.slice(0, n).map((l, i) => (
          <SvgText key={`l${i}`} x={cx(i)} y={height - 6} fontSize={10} fill={colors.textMuted} textAnchor="middle">{l.slice(0, 3)}</SvgText>
        ))}
      </Svg>
    </View>
  );
}

// Deterministic weekly trend ending at `value` (demo visualisation).
export function weeklyTrend(value: number): number[] {
  const shape = [0.52, 0.64, 0.58, 0.8, 0.73, 0.9, 1];
  return shape.map((f) => Math.max(0, Math.round(value * f)));
}
