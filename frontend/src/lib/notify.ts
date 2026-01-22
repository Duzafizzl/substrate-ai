/**
 * Browser notification functionality for Substrate AI
 */

// Time delay before showing the initial notification (in milliseconds)
const NOTIFICATION_DELAY = 10000; // 10 seconds

/**
 * Request notification permission and setup initial notification
 */
export function setupNotifications(): void {
  // Check if browser supports notifications
  if (!('Notification' in window)) {
    console.log('This browser does not support notifications');
    return;
  }
  
  // Request permission and schedule initial notification
  if (Notification.permission !== 'denied') {
    Notification.requestPermission().then(permission => {
      if (permission === 'granted') {
        // Schedule the "sign of life" notification
        scheduleInitialNotification();
      }
    });
  }
}

/**
 * Schedule the initial "sign of life" notification
 */
function scheduleInitialNotification(): void {
  // Check if this is the first visit
  const hasVisitedBefore = localStorage.getItem('substrate_has_visited');
  
  if (!hasVisitedBefore) {
    // Set flag to indicate the user has visited before
    localStorage.setItem('substrate_has_visited', 'true');
    
    // Schedule the notification
    setTimeout(() => {
      showNotification(
        'Welcome! 👋',
        'Your AI assistant is ready. Start a conversation anytime!'
      );
    }, NOTIFICATION_DELAY);
  }
}

/**
 * Display a notification with the given title and body
 */
export function showNotification(title: string, body: string): void {
  if (Notification.permission === 'granted') {
    const notification = new Notification(title, {
      body: body,
      icon: '/favicon.svg',
      silent: false
    });
    
    // Handle notification click
    notification.onclick = () => {
      window.focus();
      notification.close();
    };
  } else {
    console.log('Notification permission not granted');
  }
}

// Lightweight dev helper: quick checks for presence rules
export async function runPresenceSmokeTests(ask: (msgs: { role: 'user'|'assistant'; content: string }[]) => Promise<string>) {
  const tests = [
    { q: 'Who are you?', expect: /I am|I'm|assistant/i },
    { q: 'Hello!', expect: /hello|hi|hey/i },
    { q: 'Can you help me?', expect: /yes|sure|of course|help/i },
  ];
  const results: Array<{ q: string; ok: boolean; got: string }> = [];
  for (const t of tests) {
    const got = await ask([{ role: 'user', content: t.q }]);
    results.push({ q: t.q, ok: t.expect.test(got), got });
  }
  return results;
}