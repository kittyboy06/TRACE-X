// High-definition Cyber Threat Intelligence SVG node icons for Cytoscape.js

const svgToDataUri = (svgString: string): string => {
  return `data:image/svg+xml;utf8,${encodeURIComponent(svgString.trim())}`;
};

// 1. Persona (Threat Actor / Cyber Persona)
export const PERSONA_SVG = svgToDataUri(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="80" height="80">
  <defs>
    <radialGradient id="pBg" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#083344" />
      <stop offset="100%" stop-color="#020617" />
    </radialGradient>
    <linearGradient id="pBorder" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#22d3ee" />
      <stop offset="50%" stop-color="#06b6d4" />
      <stop offset="100%" stop-color="#0284c7" />
    </linearGradient>
    <filter id="pGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#06b6d4" flood-opacity="0.8" />
    </filter>
  </defs>
  <!-- Outer tech ring -->
  <circle cx="40" cy="40" r="37" fill="none" stroke="#22d3ee" stroke-width="1.5" stroke-dasharray="4 3" opacity="0.7" />
  <!-- Main circle -->
  <circle cx="40" cy="40" r="33" fill="url(#pBg)" stroke="url(#pBorder)" stroke-width="3" filter="url(#pGlow)" />
  <!-- Hacker / Threat persona avatar -->
  <g fill="#38bdf8">
    <circle cx="40" cy="30" r="10" />
    <path d="M22 57c0-9 8-15 18-15s18 6 18 15v3H22v-3z" />
    <!-- Visor / Cyber glasses accent -->
    <rect x="33" y="27" width="14" height="4" rx="2" fill="#a5f3fc" />
  </g>
</svg>
`);

// 2. PGP Key (Cryptographic Evidence)
export const PGP_KEY_SVG = svgToDataUri(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="80" height="80">
  <defs>
    <radialGradient id="kBg" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#0c2340" />
      <stop offset="100%" stop-color="#020617" />
    </radialGradient>
    <linearGradient id="kBorder" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8" />
      <stop offset="100%" stop-color="#2563eb" />
    </linearGradient>
    <filter id="kGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="0" stdDeviation="3.5" flood-color="#38bdf8" flood-opacity="0.7" />
    </filter>
  </defs>
  <!-- Diamond / Shield container -->
  <rect x="12" y="12" width="56" height="56" rx="16" fill="url(#kBg)" stroke="url(#kBorder)" stroke-width="2.5" filter="url(#kGlow)" transform="rotate(45 40 40)" />
  <!-- Key icon -->
  <g fill="#38bdf8" transform="translate(18, 18) scale(0.68)">
    <path d="M38 22a10 10 0 00-9.2 14L16 48v8h8v-4h4v-4h4l3.8-3.8A10 10 0 1038 22zm0 8a3 3 0 110 6 3 3 0 010-6z"/>
  </g>
</svg>
`);

// 3. Crypto Wallet (UTXO / Bitcoin Cluster)
export const WALLET_SVG = svgToDataUri(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="80" height="80">
  <defs>
    <radialGradient id="wBg" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#062e22" />
      <stop offset="100%" stop-color="#020617" />
    </radialGradient>
    <linearGradient id="wBorder" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#34d399" />
      <stop offset="100%" stop-color="#059669" />
    </linearGradient>
    <filter id="wGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="0" stdDeviation="3.5" flood-color="#10b981" flood-opacity="0.7" />
    </filter>
  </defs>
  <!-- Hexagon container -->
  <polygon points="40,6 70,23 70,57 40,74 10,57 10,23" fill="url(#wBg)" stroke="url(#wBorder)" stroke-width="2.5" filter="url(#wGlow)" />
  <!-- Bitcoin 'B' emblem -->
  <g fill="#34d399">
    <path d="M44 24v3h-3v-3h-3v3h-8v3h3v22h-3v3h8v3h3v-3h3v3h3v-3c4.5 0 7.5-2.2 7.5-6.5 0-3-1.5-5-4.5-5.8 2.2-.8 3.8-2.8 3.8-5.2 0-4-3-6.5-7.8-6.5zm-6 7h4.5c2.2 0 3.8 1.2 3.8 3s-1.6 3-3.8 3H38v-6zm0 9h5c2.5 0 4.2 1.3 4.2 3.5s-1.7 3.5-4.2 3.5H38V40z" />
  </g>
</svg>
`);

// 4. VASP (Virtual Asset Service Provider / Exchange)
export const VASP_SVG = svgToDataUri(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="80" height="80">
  <defs>
    <radialGradient id="vBg" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#331c04" />
      <stop offset="100%" stop-color="#020617" />
    </radialGradient>
    <linearGradient id="vBorder" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fbbf24" />
      <stop offset="100%" stop-color="#d97706" />
    </linearGradient>
    <filter id="vGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="0" stdDeviation="3.5" flood-color="#f59e0b" flood-opacity="0.7" />
    </filter>
  </defs>
  <!-- Rounded Rect container -->
  <rect x="8" y="12" width="64" height="56" rx="14" fill="url(#vBg)" stroke="url(#vBorder)" stroke-width="2.5" filter="url(#vGlow)" />
  <!-- Financial Exchange / Bank pillars -->
  <g fill="#fbbf24">
    <path d="M40 22l-18 9v4h36v-4l-18-9zM25 38v14h4V38h-4zm13 0v14h4V38h-4zm13 0v14h4V38h-4zM21 54v4h38v-4H21z"/>
  </g>
</svg>
`);

// 5. Forum (Darknet Hub / Market)
export const FORUM_SVG = svgToDataUri(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="80" height="80">
  <defs>
    <radialGradient id="fBg" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#2a0f4c" />
      <stop offset="100%" stop-color="#020617" />
    </radialGradient>
    <linearGradient id="fBorder" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#c084fc" />
      <stop offset="100%" stop-color="#7e22ce" />
    </linearGradient>
    <filter id="fGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="0" stdDeviation="3.5" flood-color="#a855f7" flood-opacity="0.7" />
    </filter>
  </defs>
  <!-- Square tech node -->
  <rect x="10" y="10" width="60" height="60" rx="14" fill="url(#fBg)" stroke="url(#fBorder)" stroke-width="2.5" filter="url(#fGlow)" />
  <!-- Network Globe -->
  <g stroke="#c084fc" stroke-width="2" fill="none">
    <circle cx="40" cy="40" r="18" />
    <ellipse cx="40" cy="40" rx="8" ry="18" />
    <line x1="22" y1="40" x2="58" y2="40" />
    <line x1="26" y1="30" x2="54" y2="30" />
    <line x1="26" y1="50" x2="54" y2="50" />
  </g>
</svg>
`);

// 6. Forum Post (Authored Message)
export const FORUM_POST_SVG = svgToDataUri(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="80" height="80">
  <defs>
    <radialGradient id="postBg" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#1e293b" />
      <stop offset="100%" stop-color="#090d16" />
    </radialGradient>
    <linearGradient id="postBorder" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#94a3b8" />
      <stop offset="100%" stop-color="#475569" />
    </linearGradient>
  </defs>
  <circle cx="40" cy="40" r="28" fill="url(#postBg)" stroke="url(#postBorder)" stroke-width="2" />
  <!-- Chat message bubble -->
  <g fill="#94a3b8">
    <path d="M26 28h28c2.2 0 4 1.8 4 4v16c0 2.2-1.8 4-4 4H34l-8 6v-6h-0c-2.2 0-4-1.8-4-4V32c0-2.2 1.8-4 4-4z" />
    <line x1="32" y1="36" x2="48" y2="36" stroke="#090d16" stroke-width="2" stroke-linecap="round" />
    <line x1="32" y1="42" x2="42" y2="42" stroke="#090d16" stroke-width="2" stroke-linecap="round" />
  </g>
</svg>
`);

// 7. Infrastructure (Server Stack / TLS / Relay)
export const INFRASTRUCTURE_SVG = svgToDataUri(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 80 80" width="80" height="80">
  <defs>
    <radialGradient id="iBg" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#331405" />
      <stop offset="100%" stop-color="#020617" />
    </radialGradient>
    <linearGradient id="iBorder" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fb923c" />
      <stop offset="100%" stop-color="#ea580c" />
    </linearGradient>
    <filter id="iGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="0" stdDeviation="3.5" flood-color="#f97316" flood-opacity="0.7" />
    </filter>
  </defs>
  <rect x="10" y="10" width="60" height="60" rx="12" fill="url(#iBg)" stroke="url(#iBorder)" stroke-width="2.5" filter="url(#iGlow)" />
  <!-- Server blades -->
  <g fill="#240c03" stroke="#fb923c" stroke-width="1.8">
    <rect x="18" y="18" width="44" height="11" rx="3" />
    <rect x="18" y="34" width="44" height="11" rx="3" />
    <rect x="18" y="50" width="44" height="11" rx="3" />
  </g>
  <!-- LED indicators -->
  <circle cx="25" cy="23.5" r="2" fill="#4ade80" />
  <circle cx="31" cy="23.5" r="2" fill="#4ade80" />
  <circle cx="25" cy="39.5" r="2" fill="#4ade80" />
  <circle cx="31" cy="39.5" r="2" fill="#4ade80" />
  <circle cx="25" cy="55.5" r="2" fill="#4ade80" />
  <circle cx="31" cy="55.5" r="2" fill="#4ade80" />
</svg>
`);
