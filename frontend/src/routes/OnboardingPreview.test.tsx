import { MantineProvider } from '@mantine/core';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { OnboardingPreview } from './OnboardingPreview';

function render(ui: React.ReactElement): string {
  return renderToStaticMarkup(<MantineProvider>{ui}</MantineProvider>);
}

describe('OnboardingPreview', () => {
  it('renders the page title', () => {
    const markup = render(<OnboardingPreview />);
    expect(markup).toContain('Source onboarding preview');
  });

  it('shows the no-storage redaction warning', () => {
    const markup = render(<OnboardingPreview />);
    expect(markup).toContain('not stored or applied');
    expect(markup).toContain('redacted');
  });

  it('renders the sample event textarea', () => {
    const markup = render(<OnboardingPreview />);
    expect(markup).toContain('Sample event');
  });

  it('renders the source hint input', () => {
    const markup = render(<OnboardingPreview />);
    expect(markup).toContain('Source hint');
  });

  it('renders the transport selector', () => {
    const markup = render(<OnboardingPreview />);
    expect(markup).toContain('Transport');
  });

  it('renders the preview button', () => {
    const markup = render(<OnboardingPreview />);
    expect(markup).toContain('Preview parser and pack match');
  });

  it('does not show result panels in initial empty state', () => {
    const markup = render(<OnboardingPreview />);
    expect(markup).not.toContain('Candidate parser and pack matches');
    expect(markup).not.toContain('Expected Splunk metadata');
    expect(markup).not.toContain('Preview results');
  });

  it('does not claim validation in the initial render', () => {
    const markup = render(<OnboardingPreview />);
    expect(markup).not.toContain('validated match');
    expect(markup).not.toContain('validation evidence');
  });

  it('describes the limitation that results are heuristic estimates', () => {
    const markup = render(<OnboardingPreview />);
    expect(markup).toContain('heuristic estimates');
  });

  it('instructs operator to validate before use', () => {
    const markup = render(<OnboardingPreview />);
    expect(markup).toContain('operator validation before use');
  });
});
