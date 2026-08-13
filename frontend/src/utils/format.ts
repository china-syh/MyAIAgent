export function formatDate(dateStr: string): string {
  if (!dateStr) return '-';
  try {
    return new Date(dateStr).toLocaleString('zh-CN');
  } catch {
    return dateStr;
  }
}

export function truncate(str: string, len: number = 50): string {
  if (!str) return '';
  return str.length > len ? str.slice(0, len) + '...' : str;
}