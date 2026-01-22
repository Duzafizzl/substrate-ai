/**
 * Text-to-speech functionality using Web Speech API
 */

const DEFAULT_VOICE_LANG = 'en-US';
let speaking = false;

/**
 * Speak text using Web Speech API
 * @param text Text to be spoken
 * @param lang Voice language (defaults to 'en-US')
 */
export function speak(text: string, lang: string = DEFAULT_VOICE_LANG): void {
  // Check if speech synthesis is available
  if (!('speechSynthesis' in window)) {
    console.error('Text-to-speech not supported in this browser');
    return;
  }
  
  // Cancel current speech if one is in progress
  if (speaking) {
    window.speechSynthesis.cancel();
  }
  
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = lang;
  
  // Try to find a voice that matches the language
  const voices = window.speechSynthesis.getVoices();
  const voice = voices.find(v => v.lang.includes(lang.slice(0, 2)) && v.name.includes('Female'));
  
  if (voice) {
    utterance.voice = voice;
  }
  
  // Adjust speech parameters for better quality
  utterance.pitch = 1.1;     // Slightly higher pitch (1 is default)
  utterance.rate = 1.0;      // Normal rate
  utterance.volume = 1.0;    // Full volume
  
  // Speech events
  utterance.onstart = () => {
    speaking = true;
    console.log('Started speaking');
  };
  
  utterance.onend = () => {
    speaking = false;
    console.log('Finished speaking');
  };
  
  utterance.onerror = (event) => {
    speaking = false;
    console.error('Speech error:', event.error);
  };
  
  // Start speaking
  window.speechSynthesis.speak(utterance);
}

/**
 * Stop current speech
 */
export function stopSpeaking(): void {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    speaking = false;
  }
}

/**
 * Check if speech is in progress
 */
export function isSpeaking(): boolean {
  return speaking;
}