// Original vector art for the storefront: the Campus Customs crest and a
// Harkness Tower / Old Campus skyline at dusk. Drawn here (no external images).

export function Crest({ size = 40, className }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size * 1.15}
      viewBox="0 0 80 92"
      className={className}
      role="img"
      aria-label="Campus Customs crest"
    >
      <path d="M40 2 L76 12 V44 C76 68 60 82 40 90 C20 82 4 68 4 44 V12 Z" fill="#00356b" />
      <path
        d="M40 8 L70 16 V44 C70 64 57 76 40 83 C23 76 10 64 10 44 V16 Z"
        fill="none"
        stroke="#f4efe3"
        strokeWidth="1.6"
      />
      <text
        x="40"
        y="54"
        textAnchor="middle"
        fontFamily="'Playfair Display Variable', Georgia, serif"
        fontWeight="700"
        fontSize="28"
        fill="#f4efe3"
        letterSpacing="-1"
      >
        CC
      </text>
      <path d="M22 64 H58" stroke="#c9a227" strokeWidth="1.6" />
    </svg>
  )
}

function Pinnacle({ x, y, h = 26, w = 6 }: { x: number; y: number; h?: number; w?: number }) {
  return <path d={`M${x - w / 2} ${y} L${x} ${y - h} L${x + w / 2} ${y} Z`} />
}

function GothicWindow({ x, y, w = 10, h = 26 }: { x: number; y: number; w?: number; h?: number }) {
  return (
    <path
      d={`M${x} ${y + h} V${y + w / 2} Q${x} ${y} ${x + w / 2} ${y - w / 3} Q${x + w} ${y} ${x + w} ${y + w / 2} V${y + h} Z`}
    />
  )
}

export function HarknessSkyline({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 480 560"
      className={className}
      role="img"
      aria-label="Illustration of Harkness Tower rising over Yale's Old Campus at dusk"
      preserveAspectRatio="xMidYMax slice"
    >
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#0b2a52" />
          <stop offset="0.55" stopColor="#1f5ca8" />
          <stop offset="1" stopColor="#e9d9b8" />
        </linearGradient>
        <linearGradient id="towerShade" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#0d2240" />
          <stop offset="1" stopColor="#14325c" />
        </linearGradient>
      </defs>

      <rect width="480" height="560" fill="url(#sky)" />
      {/* moon + stars */}
      <circle cx="388" cy="92" r="26" fill="#f4efe3" opacity="0.92" />
      <circle cx="398" cy="86" r="24" fill="#16427a" opacity="0.55" />
      {[
        [60, 60], [120, 110], [210, 50], [300, 140], [440, 180], [30, 170], [160, 30], [455, 40],
      ].map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={i % 3 === 0 ? 1.8 : 1.2} fill="#f4efe3" opacity="0.8" />
      ))}

      {/* far skyline: Gothic roofs */}
      <g fill="#2a5a94" opacity="0.75">
        <path d="M0 430 L0 380 L30 380 L45 352 L60 380 L95 380 L95 360 L120 330 L145 360 L145 430 Z" />
        <path d="M330 430 L330 372 L352 372 L372 340 L392 372 L420 372 L420 350 L440 326 L460 350 L480 350 L480 430 Z" />
      </g>

      {/* Harkness Tower */}
      <g fill="url(#towerShade)">
        {/* base */}
        <rect x="186" y="300" width="108" height="200" />
        {/* tier 2 */}
        <rect x="196" y="214" width="88" height="90" />
        {/* tier 3 (belfry) */}
        <rect x="206" y="146" width="68" height="72" />
        {/* crown */}
        <rect x="216" y="104" width="48" height="46" />
        {/* spire */}
        <path d="M222 106 L240 40 L258 106 Z" />
        {/* corner buttresses */}
        <rect x="180" y="300" width="10" height="200" />
        <rect x="290" y="300" width="10" height="200" />
        <rect x="190" y="214" width="8" height="90" />
        <rect x="282" y="214" width="8" height="90" />
        <rect x="200" y="146" width="7" height="72" />
        <rect x="273" y="146" width="7" height="72" />
        {/* pinnacles */}
        <Pinnacle x={185} y={300} h={30} w={10} />
        <Pinnacle x={295} y={300} h={30} w={10} />
        <Pinnacle x={194} y={214} h={26} w={8} />
        <Pinnacle x={286} y={214} h={26} w={8} />
        <Pinnacle x={203} y={146} h={24} w={7} />
        <Pinnacle x={277} y={146} h={24} w={7} />
        <Pinnacle x={218} y={104} h={20} w={6} />
        <Pinnacle x={262} y={104} h={20} w={6} />
      </g>
      {/* tower windows, warm light */}
      <g fill="#e9c46a" opacity="0.85">
        <GothicWindow x={214} y={330} w={14} h={44} />
        <GothicWindow x={252} y={330} w={14} h={44} />
        <GothicWindow x={222} y={238} w={12} h={40} />
        <GothicWindow x={246} y={238} w={12} h={40} />
        <GothicWindow x={226} y={164} w={10} h={36} />
        <GothicWindow x={244} y={164} w={10} h={36} />
        <GothicWindow x={234} y={116} w={12} h={22} />
      </g>

      {/* near skyline: Old Campus halls */}
      <g fill="#0a1d36">
        <path d="M0 560 L0 450 L40 450 L40 420 L58 396 L76 420 L76 450 L150 450 L150 430 L170 404 L190 430 L190 560 Z" />
        <path d="M290 560 L290 436 L312 410 L334 436 L334 452 L404 452 L404 424 L422 398 L440 424 L440 452 L480 452 L480 560 Z" />
        <rect x="150" y="470" width="180" height="90" />
      </g>
      <g fill="#e9c46a" opacity="0.7">
        {[18, 52, 100, 124, 316, 352, 378, 452].map((x, i) => (
          <GothicWindow key={i} x={x} y={470} w={9} h={20} />
        ))}
        {[176, 204, 232, 260, 288].map((x, i) => (
          <GothicWindow key={`g${i}`} x={x} y={492} w={10} h={22} />
        ))}
      </g>
      {/* elms */}
      <g fill="#071629">
        <ellipse cx="128" cy="520" rx="46" ry="34" />
        <ellipse cx="96" cy="532" rx="36" ry="26" />
        <ellipse cx="360" cy="524" rx="48" ry="32" />
        <ellipse cx="398" cy="536" rx="34" ry="24" />
      </g>
    </svg>
  )
}
