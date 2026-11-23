export function BeanGlyph({ size = 24, className }: { size?: number; className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <path d="M8 4c-3 1.5-5 4.5-5 8 0 4.5 3.5 8 8 8 4 0 7-2.5 8-6 .5-1.8 0-3.5-1.5-4.5-1.8-1.2-3.5-.3-5 .8-1.8 1.3-3.5 1.5-5 .3-1.3-1-1.5-2.8-.5-4.3C7.5 5.5 7.8 4.6 8 4Z" />
    </svg>
  );
}

export function BeanHappy({ size = 72, className }: { size?: number; className?: string }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <path d="M8 4c-3 1.5-5 4.5-5 8 0 4.5 3.5 8 8 8 4 0 7-2.5 8-6 .5-1.8 0-3.5-1.5-4.5-1.8-1.2-3.5-.3-5 .8-1.8 1.3-3.5 1.5-5 .3-1.3-1-1.5-2.8-.5-4.3C7.5 5.5 7.8 4.6 8 4Z" />
      <circle cx="9.5" cy="12" r="0.5" fill="currentColor" />
      <circle cx="14.5" cy="11.5" r="0.5" fill="currentColor" />
      <path d="M9.5 14.5c1 1 3.5 1 4.5-.3" />
    </svg>
  );
}
