import { describe, expect, it } from 'vitest';
import { productReleaseSchema } from './library';

const release = {
  kind: 'splunk_ta_product_release',
  product_id: 'pan-panos',
  display_name: 'Palo Alto PAN-OS',
  app_id: 'Splunk_TA_pan_panos',
  version: '1.2.4',
  filename: 'Splunk_TA_pan_panos-1.2.4.tgz',
  url: 'https://sechub.s6ops.com/downloads/Splunk_TA_pan_panos-1.2.4.tgz',
  sha256: 'a'.repeat(64),
  source_components: ['pan_panos'],
  install_scope: 'product_deployment',
  manager_importable: false,
} as const;

describe('product release boundary', () => {
  it('accepts only explicit non-importable product deployment records', () => {
    expect(productReleaseSchema.safeParse(release).success).toBe(true);
    expect(productReleaseSchema.safeParse({ ...release, manager_importable: true }).success).toBe(false);
    expect(productReleaseSchema.safeParse({ ...release, install_scope: 'manager_library' }).success).toBe(false);
    expect(productReleaseSchema.safeParse({ ...release, kind: 'sc4s_library_pack' }).success).toBe(false);
  });
});
