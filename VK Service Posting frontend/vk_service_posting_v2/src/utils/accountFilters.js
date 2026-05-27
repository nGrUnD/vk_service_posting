export const PARSE_STATUS_FILTER_OPTIONS = [
  { value: 'all', label: 'Все статусы' },
  { value: 'success', label: 'Success' },
  { value: 'failure', label: 'Failed' },
  { value: 'pending', label: 'Pending' },
];

export function matchesParseStatusFilter(filterValue, parseStatus) {
  if (!filterValue || filterValue === 'all') return true;
  const status = (parseStatus || '').toLowerCase();
  if (filterValue === 'pending') {
    return status === 'pending' || status === 'in_progress';
  }
  return status === filterValue;
}

export function getAccountCurl(account) {
  const curl = account?.curl;
  return typeof curl === 'string' && curl.trim() ? curl.trim() : null;
}
