import { ShieldAlert } from "lucide-react";
import { formatMonth, type MakerRecord } from "@/lib/api";

/** A maker's record in the CDSCO alert database. */
export function MakerBadge({ r }: { r: MakerRecord }) {
  if (!r.alerts) return <span className="ml-1 rounded-full bg-safe/15 px-2 py-0.5 text-[10px] font-semibold text-safe">No alerts on record</span>;
  return (
    <span className={`ml-1 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${r.spurious ? "bg-danger text-paper" : "bg-warn-soft text-warn"}`}>
      <ShieldAlert className="size-3" /> {r.alerts} CDSCO alert{r.alerts > 1 ? "s" : ""}{r.spurious ? `, ${r.spurious} spurious` : ""}{r.last ? `, last ${formatMonth(r.last)}` : ""}
    </span>
  );
}
