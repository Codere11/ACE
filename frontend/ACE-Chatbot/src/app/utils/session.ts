export function getOrCreateSid(): string {
  const KEY = 'ace_sid';
  let sid = localStorage.getItem(KEY);
  if (!sid) {
    sid = crypto.randomUUID();
    localStorage.setItem(KEY, sid);
    // meta not sent yet for this sid
    localStorage.removeItem('ace_meta_sent');
  }
  return sid;
}

export function readUtmAndContext() {
  const params = new URLSearchParams(window.location.search);
  const utm = {
    source: params.get('utm_source') || '',
    medium: params.get('utm_medium') || '',
    campaign: params.get('utm_campaign') || '',
    term: params.get('utm_term') || '',
    content: params.get('utm_content') || '',
  };
  const vertical = params.get('vertical') || '';
  const page_path = window.location.pathname + window.location.search;
  return { utm, vertical, page_path };
}

export function shouldIncludeMetaOnce(): boolean {
  // send meta only once per sid
  const FLAG = 'ace_meta_sent';
  if (localStorage.getItem(FLAG)) return false;
  localStorage.setItem(FLAG, '1');
  return true;
}