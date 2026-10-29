import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import * as WebBrowser from 'expo-web-browser';
import { Card } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { ReportCard } from '@/components/doctor/ReportCard';
import { ScanViewer } from '@/components/doctor/ScanViewer';
import { useReportFile } from '@/features/doctor/useReportFile';
import { abnormalFirst, isAbnormal } from '@/features/doctor/reportAggregate';
import type { ExtractionField, ReportView } from '@/api/doctorPortal';
import { colors, spacing, type as t } from '@/theme/tokens';

const COMPACT_LIMIT = 4;
const flagLabel = (flag?: string) => (flag === 'L' ? '↓ Low' : flag === 'H' ? '↑ High' : '');
const fieldLine = (f: ExtractionField) =>
  `${f.testNameNormalized || f.testNameRaw || 'Result'} ${f.valueRaw ?? ''}${f.unit ? ` ${f.unit}` : ''} ${flagLabel(f.flag)}`.trim();

export function ReportsSection({ patientId }: { patientId: string }) {
  const { data, isLoading } = useReportFile(patientId);
  const [expanded, setExpanded] = useState(false);
  const [viewerUri, setViewerUri] = useState<string | null>(null);

  if (isLoading) return <Skeleton height={100} />;
  const reports = data ?? [];
  if (reports.length === 0) {
    return (
      <Card>
        <Text style={{ fontSize: t.sm, color: colors.textMuted, marginBottom: spacing.xs }}>Reports</Text>
        <Text style={{ fontSize: t.sm, color: colors.text }}>No reports uploaded yet.</Text>
      </Card>
    );
  }

  const ordered = abnormalFirst(reports);
  const visible = expanded ? ordered : ordered.slice(0, COMPACT_LIMIT);
  const open = (r: ReportView) => {
    if (r.kind === 'pdf') void WebBrowser.openBrowserAsync(r.imageUrl);
    else setViewerUri(r.imageUrl);
  };

  return (
    <Card>
      <Text style={{ fontSize: t.sm, color: colors.textMuted, marginBottom: spacing.xs }}>Reports & extraction</Text>
      {visible.map((f, i) => (
        <Text key={i} style={{ fontSize: t.sm, fontWeight: isAbnormal(f) ? '700' : '400',
          color: isAbnormal(f) ? colors.emergency : colors.text }}>
          {fieldLine(f)}
        </Text>
      ))}
      {ordered.length > COMPACT_LIMIT ? (
        <Pressable onPress={() => setExpanded((e) => !e)}>
          <Text style={{ fontSize: t.sm, color: colors.navy, fontWeight: '700', marginTop: spacing.xs }}>
            {expanded ? '▴ Show less' : `▾ +${ordered.length - COMPACT_LIMIT} more results`}
          </Text>
        </Pressable>
      ) : null}
      <View style={{ height: spacing.md }} />
      {reports.map((r, i) => (
        <View key={r.reportId} style={{ marginBottom: spacing.sm }}>
          <ReportCard report={r} label={`Lab report ${i + 1}`} onOpen={() => open(r)} />
        </View>
      ))}
      <ScanViewer uri={viewerUri ?? ''} visible={viewerUri !== null} onClose={() => setViewerUri(null)} />
    </Card>
  );
}
