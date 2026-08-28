/**
 * LanguageSwitcher.tsx – Sprachumschalter EN/DE für i18next.
 * Created: 2026-08-28
 * Last updated: 2026-08-28
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Languages } from 'lucide-react';

const LanguageSwitcher: React.FC = () => {
  const { i18n } = useTranslation();
  const current = i18n.language.startsWith('de') ? 'de' : 'en';

  const toggleLanguage = () => {
    const next = current === 'de' ? 'en' : 'de';
    void i18n.changeLanguage(next);
  };

  return (
    <button
      type="button"
      onClick={toggleLanguage}
      className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-gray-400 hover:bg-gray-800 hover:text-white transition-colors text-xs font-medium uppercase"
      title={current === 'de' ? 'Switch to English' : 'Auf Deutsch wechseln'}
      aria-label={current === 'de' ? 'Switch to English' : 'Auf Deutsch wechseln'}
    >
      <Languages className="w-4 h-4" />
      <span>{current}</span>
    </button>
  );
};

export default LanguageSwitcher;
