import { createHash } from 'node:crypto';

// Pure comparison policy; callers supply complete versioned API pages.
export function registryContentDigest(documents) {
  // registry_revision is global: discovery can advance it without editing
  // these records. Keep record_version and every other field so edits,
  // including changes restored before the second read, are still detected.
  const contents = documents.map(rows => rows.map(row => Object.fromEntries(
    Object.entries(row).filter(([key]) => key !== 'registry_revision'),
  )));
  return createHash('sha256').update(JSON.stringify(contents)).digest('hex');
}
