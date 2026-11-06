// Two-tone heading: dark lead words, muted tail.
export function Heading({
  lead,
  tail,
  as: Tag = "h2",
  className = "",
}: {
  lead: string;
  tail?: string;
  as?: "h1" | "h2";
  className?: string;
}) {
  return (
    <Tag className={`font-medium leading-[1.05] tracking-[-0.03em] ${className}`}>
      {lead} {tail && <span className="text-mocha">{tail}</span>}
    </Tag>
  );
}

export function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-line bg-paper px-3 py-1 text-xs font-medium text-brown">
      <span className="size-1.5 rounded-full bg-teal shadow-[0_0_0_3px_rgba(15,118,110,0.15)]" />
      {children}
    </span>
  );
}
