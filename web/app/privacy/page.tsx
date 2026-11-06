import Link from "next/link";
import { Download, Eye, Lock, Trash2, UserCheck, Users } from "lucide-react";
import { Eyebrow, Heading } from "@/components/Heading";

export const metadata = { title: "Privacy · KinCare" };

const HOLD: [string, string, string][] = [
  ["Prescriptions you scan or type", "To remind you of doses and check each batch against regulator alerts", "Until you delete them"],
  ["Doses you tick", "To show you (and a caregiver you chose) what was taken", "Until you delete them"],
  ["Vitals you enter or say", "To tell you whether a reading needs a doctor", "Until you delete them; raw live samples 7 days"],
  ["Dadi mode and Telegram chats", "So the conversation continues where you left off", "180 days"],
  ["Batches you watch or report", "To re-check them every night; reports are pooled by batch, without your name", "Until you delete them"],
  ["Phone number (only if you sign in)", "To send your login code and keep your data across phones", "Until you delete your account"],
  ["Caregiver access log", "So you can see every time a caregiver looked or was alerted", "365 days"],
];

const RIGHTS = [
  { icon: Eye, title: "See everything", text: "Account → Download my data gives you every record we hold about you, as one file." },
  { icon: Trash2, title: "Erase everything", text: "Account → Delete all my data removes your prescriptions, doses, vitals, chats, caregiver links and login, at once." },
  { icon: Users, title: "Choose who sees what", text: "A caregiver sees only what you ticked (doses, vitals, emergencies), for one family member. Stop it anytime in Family." },
  { icon: UserCheck, title: "Know who looked", text: "Every look, reminder and alert by a caregiver appears in your access log." },
];

export default function PrivacyPage() {
  return (
    <main className="blush mx-auto max-w-4xl px-4 pb-24 pt-12 sm:px-6 sm:pt-16">
      <Eyebrow>Privacy</Eyebrow>
      <Heading as="h1" lead="Your health data" tail="belongs to you." className="mt-4 text-4xl sm:text-6xl" />
      <p className="mt-4 max-w-2xl text-lg text-muted">
        KinCare is built around India&apos;s Digital Personal Data Protection Act, 2023: we collect only what a feature needs, use it only for that,
        keep it only as long as needed, and you can see or erase all of it yourself.
      </p>

      <div className="mt-10 grid gap-4 sm:grid-cols-2">
        {RIGHTS.map((r) => (
          <div key={r.title} className="rounded-[1.75rem] border border-line bg-paper p-5">
            <r.icon className="size-5 text-teal" />
            <p className="mt-3 font-semibold">{r.title}</p>
            <p className="mt-1 text-sm text-muted">{r.text}</p>
          </div>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Link href="/account" className="inline-flex items-center gap-2 rounded-full bg-espresso px-5 py-2.5 text-sm font-medium text-paper hover:bg-brown"><Download className="size-4" /> Download or delete my data</Link>
        <Link href="/family" className="inline-flex items-center gap-2 rounded-full border border-line bg-paper px-5 py-2.5 text-sm font-medium"><Users className="size-4" /> Manage caregivers</Link>
      </div>

      <h2 className="mt-14 text-2xl font-semibold">What we keep, why, and for how long</h2>
      <div className="mt-4 overflow-x-auto rounded-[1.5rem] border border-line bg-paper">
        <table className="w-full min-w-[560px] text-left text-sm">
          <thead className="bg-cream text-brown">
            <tr><th className="px-4 py-3 font-medium">Data</th><th className="px-4 py-3 font-medium">Why</th><th className="px-4 py-3 font-medium">Kept</th></tr>
          </thead>
          <tbody>
            {HOLD.map(([d, why, kept]) => (
              <tr key={d} className="border-t border-line align-top"><td className="px-4 py-3 font-medium">{d}</td><td className="px-4 py-3 text-muted">{why}</td><td className="px-4 py-3 text-muted">{kept}</td></tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 className="mt-14 flex items-center gap-2 text-2xl font-semibold"><Lock className="size-5 text-teal" /> How it is protected</h2>
      <ul className="mt-4 space-y-2 text-muted">
        <li>• No name or email is needed. Your browser holds a random 256-bit session key in a cookie that page scripts cannot read; the server stores only its fingerprint (hash), so even a copy of our database can&apos;t be used to log in as you.</li>
        <li>• Sessions expire (30 days signed in, 90 as a guest), and you can sign out any device from Account.</li>
        <li>• Chats, doctor messages and diagnoses are encrypted in our database (AES-256-GCM).</li>
        <li>• Sharing with a caregiver or doctor needs a verified phone number, so you always know who you are sharing with.</li>
        <li>• Login codes are stored hashed, expire in 10 minutes, allow 5 tries and are rate-limited.</li>
        <li>• Caregivers can see and remind. They can never add, change or delete a medicine, dose or reading.</li>
        <li>• Strip and prescription photos are read on our own server (no third-party OCR) and are not stored.</li>
        <li>• We never sell data, show ads, or tell anyone to start, stop or change a medicine.</li>
        <li>• Symptom reports used for early safety signals are pooled by batch, without names.</li>
      </ul>

      <p className="mt-14 rounded-2xl bg-cream p-5 text-sm text-muted">
        KinCare is a Flip the Switch 2026 project, not yet a certified medical device. Questions or a complaint about your data: write to the team
        (Team Avengers).
      </p>
    </main>
  );
}
