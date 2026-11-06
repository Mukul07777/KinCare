import {
  Activity, BadgeIndianRupee, BarChart3, Building2, Cpu, FileSearch, HeartPulse, IndianRupee, Landmark, LayoutDashboard, ListChecks, MessageCircle,
  Mic, Play, Radar, ScanLine, ShieldAlert, ShieldCheck, Siren, Store, UserRound, Users, Waves, type LucideIcon,
} from "lucide-react";

// Every page in one place: the nav, the footer and the ⌘K palette all read from here, so nothing gets orphaned.
export type Route = { href: string; label: string; hint: string; icon: LucideIcon; keywords?: string };
export type Group = { id: "families" | "pharmacies" | "regulators" | "more"; label: string; blurb: string; routes: Route[] };

export const GROUPS: Group[] = [
  {
    id: "families", label: "Families", blurb: "Check, take and afford the right medicine",
    routes: [
      { href: "/scan", label: "Scan a strip", hint: "Photo, QR or bill, checked against every alert", icon: ScanLine, keywords: "batch check ocr camera qr bill" },
      { href: "/whatsapp", label: "WhatsApp", hint: "Send a strip photo, get the verdict. No app", icon: MessageCircle, keywords: "chat photo bot" },
      { href: "/dadi", label: "Dadi mode", hint: "Talk or type in Hindi. Big, simple, spoken back", icon: Mic, keywords: "voice hindi elder speak chat talk telegram" },
      { href: "/family", label: "Family", hint: "Look after a parent's doses and vitals, with consent", icon: Users, keywords: "caregiver son daughter parent elder monitor adherence consent" },
      { href: "/care", label: "Care", hint: "Doses, vitals, reminders, your doctor", icon: HeartPulse, keywords: "prescription reminders vitals doctor family" },
      { href: "/save", label: "Save money", hint: "Same salt, lower price, clean maker", icon: IndianRupee, keywords: "price cheaper generic jan aushadhi" },
      { href: "/watchlist", label: "Watchlist", hint: "Batches we keep checking for you", icon: ListChecks },
      { href: "/sos", label: "SOS", hint: "Location, vitals and medicines to family", icon: Siren, keywords: "emergency 108" },
    ],
  },
  {
    id: "pharmacies", label: "Pharmacies", blurb: "Stock, sales and recalls in one desk",
    routes: [
      { href: "/pharmacy", label: "Recall desk", hint: "Check stock, alert every buyer", icon: Store, keywords: "inventory sales csv" },
      { href: "/pricing", label: "Plans", hint: "₹499 a month, customers get KinCare free", icon: BadgeIndianRupee, keywords: "pricing subscription business" },
      { href: "/live", label: "60-second recall", hint: "A new list, matched and alerted live", icon: Waves, keywords: "live recall agents" },
    ],
  },
  {
    id: "regulators", label: "Regulators", blurb: "Every failed batch, followed to the home",
    routes: [
      { href: "/blast", label: "Blast radius", hint: "Who holds a failed batch, next dose first", icon: Activity, keywords: "recall holders alert" },
      { href: "/controller", label: "Controller dashboard", hint: "State view and a ranked action queue", icon: Landmark, keywords: "drug controller state cdsco" },
      { href: "/radar", label: "Fake-pack radar", hint: "Copied QR codes caught across cities", icon: Radar, keywords: "counterfeit fake spurious qr" },
      { href: "/signals", label: "Early signals", hint: "Patients report problems before any list", icon: ShieldAlert, keywords: "symptoms pvpi pharmacovigilance" },
      { href: "/insights", label: "National insights", hint: "What fails, where, and in which drugs", icon: BarChart3, keywords: "data analytics" },
      { href: "/alerts", label: "All alerts", hint: "Search 6,865 CDSCO and state alerts", icon: FileSearch, keywords: "nsq spurious list search" },
      { href: "/maker", label: "Manufacturers", hint: "A maker's alert record", icon: Building2, keywords: "company manufacturer" },
    ],
  },
  {
    id: "more", label: "More", blurb: "",
    routes: [
      { href: "/demo", label: "Live demo", hint: "One patient, prescription to first dose", icon: Play, keywords: "tour walkthrough" },
      { href: "/status", label: "Under the hood", hint: "Live accuracy, latency and data freshness", icon: Cpu, keywords: "status health architecture tech engineering" },
      { href: "/ask", label: "Ask the regulator", hint: "Questions answered from the alert data", icon: LayoutDashboard, keywords: "chat question" },
      { href: "/how", label: "How it works", hint: "Sources, matching and our limits", icon: FileSearch },
      { href: "/account", label: "Account", hint: "Plan, phone and sign out", icon: UserRound, keywords: "login profile" },
      { href: "/privacy", label: "Privacy", hint: "Your data: see it, delete it, who can see it", icon: ShieldCheck, keywords: "dpdp data delete export consent" },
    ],
  },
];

export const ALL_ROUTES: Route[] = GROUPS.flatMap((g) => g.routes);

// The one story the top bar tells: check the strip, take it on time, talk in Hindi, family keeps watch.
// Every other page sits under More (and the footer, and ⌘K).
export const PRIMARY = ["/scan", "/care", "/dadi", "/family"];
export const PRIMARY_ROUTES: Route[] = PRIMARY.map((h) => ALL_ROUTES.find((r) => r.href === h)!);
export const MORE_GROUPS: Group[] = GROUPS.map((g) => ({ ...g, routes: g.routes.filter((r) => !PRIMARY.includes(r.href)) })).filter((g) => g.routes.length);
