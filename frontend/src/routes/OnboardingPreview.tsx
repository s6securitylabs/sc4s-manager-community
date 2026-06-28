import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Group,
  Select,
  Stack,
  Text,
  Textarea,
  Title,
} from '@mantine/core';
import { useState } from 'react';

import type { CandidateMatch, ExpectedMetadata, PreviewResponse } from '../api/samples';
import { previewSample } from '../api/samples';

const TRANSPORT_OPTIONS = [
  { value: 'unknown', label: 'Unknown / not specified' },
  { value: 'udp', label: 'UDP' },
  { value: 'tcp', label: 'TCP' },
  { value: 'tls', label: 'TLS' },
];

const CONFIDENCE_COLORS: Record<string, string> = {
  high: 'green',
  medium: 'yellow',
  low: 'orange',
};

function ConfidenceBadge({ confidence }: { confidence: string }) {
  return (
    <Badge color={CONFIDENCE_COLORS[confidence] ?? 'gray'} variant="light" size="sm">
      {confidence} confidence
    </Badge>
  );
}

function CandidateCard({ match }: { match: CandidateMatch }) {
  return (
    <Card withBorder p="sm" radius="md">
      <Stack gap="xs">
        <Group justify="space-between" wrap="nowrap">
          <Text fw={600}>{match.vendor_product}</Text>
          <ConfidenceBadge confidence={match.confidence} />
        </Group>
        <Text size="sm" c="dimmed">
          {match.reason}
        </Text>
        <Alert color="yellow" variant="light" p="xs" radius="sm">
          Preview only — confirm in Splunk before adding a source.
        </Alert>
      </Stack>
    </Card>
  );
}

function SplunkFieldsPanel({ metadata }: { metadata: ExpectedMetadata }) {
  const rows: [string, string | null][] = [
    ['Index', metadata.index],
    ['Sourcetype', metadata.sourcetype],
    ['Source', metadata.source],
    ['Host', metadata.host],
    ['Timestamp policy', metadata.timestamp_policy],
  ];
  return (
    <Card withBorder p="sm" radius="md">
      <Stack gap="xs">
        <Text fw={600} size="sm">
          Expected Splunk fields (preview only)
        </Text>
        {rows.map(([label, value]) => (
          <Group key={label} gap="sm" wrap="nowrap">
            <Text size="sm" c="dimmed" fw={500} miw={120}>
              {label}
            </Text>
            <Text size="sm" ff="monospace">
              {value ?? '—'}
            </Text>
          </Group>
        ))}
        <Text size="xs" c="dimmed">
          These values are heuristic estimates. Search Splunk for incoming events to confirm, rather than treating
          as authoritative.
        </Text>
      </Stack>
    </Card>
  );
}

function FallbackPanel({ nextActions }: { nextActions: string[] }) {
  return (
    <Card withBorder p="sm" radius="md">
      <Stack gap="xs">
        <Text fw={600} size="sm">
          No matched parser or pack
        </Text>
        <Text size="sm" c="dimmed">
          The sample did not match known SC4S source signatures. Next actions:
        </Text>
        <Box component="ul" pl="md" m={0}>
          {nextActions.map((action) => (
            <Text key={action} component="li" size="sm">
              {action}
            </Text>
          ))}
        </Box>
      </Stack>
    </Card>
  );
}

export function OnboardingPreview() {
  const [sample, setSample] = useState('');
  const [sourceHint, setSourceHint] = useState('');
  const [transport, setTransport] = useState<string>('unknown');
  const [result, setResult] = useState<PreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handlePreview() {
    const trimmed = sample.trim();
    if (!trimmed) {
      setError('Paste a sample event before previewing.');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await previewSample({
        sample: trimmed,
        source_hint: sourceHint.trim() || undefined,
        transport: (transport as 'udp' | 'tcp' | 'tls' | 'unknown') || 'unknown',
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview request failed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Stack gap="lg">
      <Box>
        <Title order={1}>Parser preview</Title>
        <Text c="dimmed" size="sm" mt="xs">
          Paste a sample log event to identify the likely parser and expected Splunk fields. Nothing is stored or applied.
        </Text>
      </Box>

      <Alert color="yellow" variant="light" radius="md">
        Results are estimates only and require review before use. Secret-looking strings are redacted from the output.
      </Alert>

      <Card withBorder p="md" radius="md">
        <Stack gap="md">
          <Textarea
            label="Sample event"
            description="Paste one representative raw syslog or structured log event. Do not paste live credentials or secret values."
            placeholder="<134>1 2026-01-01T00:00:00Z firewall cisco_asa - - %ASA-6-302013: Built outbound TCP..."
            minRows={4}
            autosize
            value={sample}
            onChange={(e) => setSample(e.currentTarget.value)}
            aria-label="Sample event"
          />

          <Group grow align="flex-start">
            <Textarea
              label="Source hint (optional)"
              description="Device type hint, e.g. cisco_asa"
              placeholder="cisco_asa"
              minRows={1}
              value={sourceHint}
              onChange={(e) => setSourceHint(e.currentTarget.value)}
              aria-label="Source hint"
            />
            <Select
              label="Transport"
              description="How the source sends events to SC4S"
              data={TRANSPORT_OPTIONS}
              value={transport}
              onChange={(v) => setTransport(v ?? 'unknown')}
              aria-label="Transport"
            />
          </Group>

          {error && (
            <Alert color="red" variant="light" radius="sm">
              {error}
            </Alert>
          )}

          <Button onClick={() => void handlePreview()} loading={loading} disabled={!sample.trim()}>
            Find matching parser
          </Button>
        </Stack>
      </Card>

      {result && (
        <Stack gap="md">
          <Text fw={700} size="lg">
            Preview results
          </Text>

          <Card withBorder p="sm" radius="md">
            <Stack gap="xs">
              <Text fw={600} size="sm">
                Detected format hints
              </Text>
              <Group gap="xs">
                {result.classification.format_hints.length > 0 ? (
                  result.classification.format_hints.map((f) => (
                    <Badge key={f} variant="outline" color="cyan" size="sm">
                      {f}
                    </Badge>
                  ))
                ) : (
                  <Text size="sm" c="dimmed">
                    None detected
                  </Text>
                )}
              </Group>
              {result.classification.timestamp_hint && (
                <Text size="sm">
                  Timestamp hint:{' '}
                  <Text component="span" ff="monospace">
                    {result.classification.timestamp_hint}
                  </Text>
                </Text>
              )}
              {result.classification.host_hint && (
                <Text size="sm">
                  Host hint:{' '}
                  <Text component="span" ff="monospace">
                    {result.classification.host_hint}
                  </Text>
                </Text>
              )}
              <Text size="xs" c="dimmed">
                Redacted preview:{' '}
                <Text component="span" ff="monospace">
                  {result.classification.redacted_sample_preview.slice(0, 300)}
                </Text>
              </Text>
            </Stack>
          </Card>

          {result.candidate_matches.length > 0 ? (
            <Stack gap="sm">
              <Text fw={600}>Matching parsers</Text>
              {result.candidate_matches.map((match) => (
                <CandidateCard key={match.pack_id} match={match} />
              ))}
              <SplunkFieldsPanel metadata={result.expected_metadata} />
            </Stack>
          ) : (
            <FallbackPanel nextActions={result.next_actions} />
          )}

          <Card withBorder p="xs" radius="md">
            <Text size="xs" c="dimmed">
              Limitations: {result.classification.limitations.join(' ')} This preview is not validated
              and not applied.
            </Text>
          </Card>
        </Stack>
      )}
    </Stack>
  );
}
