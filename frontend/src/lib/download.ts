export function sanitizeDownloadFilename(filename: string, fallback = 'download.bin'): string {
  const cleaned = filename
    .replace(/[\\/:*?"<>|\u0000-\u001f\u007f]+/g, '-')
    .replace(/^\.+/, '')
    .replace(/-+(?=\.)/g, '')
    .replace(/^-+|-+$/g, '')
    .replace(/\s+/g, ' ')
    .trim();
  return cleaned || fallback;
}

export function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = sanitizeDownloadFilename(filename);
  link.rel = 'noopener';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
