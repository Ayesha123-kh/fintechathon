import {
  BadgePercent, Bell, CircleCheck, CreditCard, Fingerprint, Lock, Mail, MessageCircleMore, Mic, ShieldCheck, Sparkles,
  Target, TrendingUp,
} from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { AuthActions } from "@/components/landing/AuthActions";
import { ChatMock, DealsMock, HeroMock } from "@/components/landing/Mocks";
import { Logo } from "@/components/ui";

export const metadata: Metadata = {
  title: "Saving · your savings assistant for Pakistan",
  description:
    "Saving reads your bank alerts, plans every salary around your goals and finds discounts for the cards you already have. Just chat with it, in English or Roman Urdu.",
};

const STATS = [
  { value: "23", label: "banks and wallets supported" },
  { value: "163", label: "card products matched to deals" },
  { value: "4 ways", label: "to split savings between goals" },
  { value: "30 s", label: "voice notes in English or Urdu" },
];

const FEATURES = [
  { icon: MessageCircleMore, title: "Set up by chatting",
    body: "No forms. Tell your assistant your banks, cards, salary and goals, and change anything later the same way: “I got a raise”, “add my HBL card”." },
  { icon: Mail, title: "Spending that tracks itself",
    body: "Connect Gmail (read-only) and your bank alerts become categorised transactions: food, groceries, fuel, bills, shopping and more." },
  { icon: Target, title: "Goals with a real plan",
    body: "A car, Umrah, an emergency fund: see progress, the monthly amount needed and your finish date. Split savings equally, by priority, by your own percentages or by deadline." },
  { icon: BadgePercent, title: "Deals for your exact cards",
    body: "Discounts matched to the cards you hold, at the places you actually go. Use one and the saving is spotted from your bank alert and moved to your goals." },
  { icon: Bell, title: "Nudges, not nagging",
    body: "A weekly savings win, a heads-up when a day's spending runs hot, a Sunday check-in and optional sadqah reminders, as push notifications." },
  { icon: Mic, title: "Talk in your language",
    body: "Send a voice note of up to 30 seconds and edit the text before it goes. Replies come in English, Roman Urdu or Urdu script." },
  { icon: TrendingUp, title: "Optional investment board",
    body: "Gold and silver, PSX, global stocks, crypto and real estate desks turn research into plain guidance. Educational only, with a clear disclaimer." },
  { icon: ShieldCheck, title: "Private by design",
    body: "Your own AI team that only ever sees your data, a lock after 5 idle minutes, fingerprint or face unlock, and no card numbers or passwords stored." },
];

const STEPS = [
  { title: "Create your account", body: "Sign up with your email and confirm it with a 6-digit code." },
  { title: "Connect Gmail", body: "Read-only. Only alert emails from your banks are read, and you can disconnect anytime." },
  { title: "Chat for three minutes", body: "Your assistant asks about your banks, cards, salary, goals and how you'd like to save." },
  { title: "Watch your savings grow", body: "Your dashboard, deals and nudges keep every goal on track." },
];

const PRIVACY = [
  { icon: Lock, title: "Only you see your data", body: "Every record is tied to your account, and the database itself refuses anyone else's reads." },
  { icon: Fingerprint, title: "Locks like a bank app", body: "After 5 idle minutes the app locks; open it with your password, fingerprint or face." },
  { icon: Mail, title: "Read-only email", body: "Gmail access can't send or change anything, and only your banks' alerts are read." },
  { icon: CreditCard, title: "No card numbers, ever", body: "Only the card type is kept: never the digits, CVV, PIN or OTP." },
];

const BANKS = [
  "Meezan Bank", "HBL", "UBL", "MCB", "Allied Bank", "Bank Alfalah", "Faysal Bank", "Standard Chartered", "Askari Bank",
  "Bank Al Habib", "JS Bank", "HabibMetro", "Soneri Bank", "Bank of Punjab", "National Bank", "Dubai Islamic Bank",
  "BankIslami", "Al Baraka", "Silkbank", "Easypaisa", "JazzCash", "SadaPay", "NayaPay",
];

function Eyebrow({ children, tone = "light" }: { children: React.ReactNode; tone?: "light" | "dark" }) {
  return (
    <p className={tone === "light"
      ? "inline-flex items-center gap-2 rounded-full bg-surface px-4 py-1.5 text-sm font-semibold text-forest shadow-sm dark:text-primary"
      : "inline-flex items-center gap-2 rounded-full bg-forest-2 px-4 py-1.5 text-sm font-semibold text-primary"}>
      {children}
    </p>
  );
}

function Check({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-3 text-[15px] text-ink-2 sm:text-base">
      <CircleCheck className="mt-0.5 size-5 shrink-0 text-forest dark:text-primary" aria-hidden />
      <span>{children}</span>
    </li>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-dvh overflow-x-clip">
      <header className="sticky top-0 z-40 border-b border-line/60 bg-bg/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 sm:h-[4.5rem] sm:px-6">
          <Link href="/" aria-label="Saving home" className="shrink-0"><Logo size={36} nameClassName="text-xl text-ink sm:text-2xl" /></Link>
          <nav aria-label="Page sections" className="ml-6 hidden items-center gap-1 md:flex">
            {[["#features", "Features"], ["#how-it-works", "How it works"], ["#privacy", "Privacy"]].map(([href, label]) => (
              <a key={href} href={href} className="rounded-full px-4 py-2 text-[15px] font-medium text-ink-2 transition hover:bg-hover hover:text-ink">
                {label}
              </a>
            ))}
          </nav>
          <div className="ml-auto"><AuthActions place="header" /></div>
        </div>
      </header>

      <main>
        {/* ---------------------------------------------------------------- hero */}
        <section aria-labelledby="hero-title" className="relative">
          <div aria-hidden className="pointer-events-none absolute -top-40 right-[-12rem] size-[34rem] rounded-full bg-primary/30 blur-3xl" />
          <div aria-hidden className="pointer-events-none absolute top-[28rem] -left-48 size-[26rem] rounded-full bg-forest-muted/30 blur-3xl" />
          <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-4 pt-12 pb-16 sm:px-6 sm:pt-16 lg:grid-cols-[1.05fr_1fr] lg:gap-10 lg:pt-20 lg:pb-24">
            <div>
              <Eyebrow><Sparkles className="size-4" aria-hidden /> Your savings assistant for Pakistan</Eyebrow>
              <h1 id="hero-title" className="mt-6 text-[2.6rem] leading-[1.05] font-bold tracking-tight text-ink sm:text-6xl">
                Save for what matters, one chat at a time.
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-relaxed text-ink-2 sm:text-xl">
                Saving reads your bank alerts, plans every salary around your goals and finds discounts for the cards
                already in your wallet. Then every rupee you save moves toward what you&apos;re saving for. Just talk to
                it, in English or Roman Urdu.
              </p>
              <div className="mt-8"><AuthActions place="hero" /></div>
              <ul className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted">
                {["Read-only Gmail", "No card numbers, ever", "Fingerprint or face unlock"].map((t) => (
                  <li key={t} className="flex items-center gap-1.5"><CircleCheck className="size-4 text-forest dark:text-primary" aria-hidden />{t}</li>
                ))}
              </ul>
            </div>
            <div>
              <HeroMock />
              <p className="mt-2 text-center text-xs text-muted">Illustrative example</p>
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------------------- numbers */}
        <section aria-label="Saving in numbers" className="mx-auto max-w-6xl px-4 sm:px-6">
          <dl className="grid grid-cols-2 gap-3 rounded-[2rem] bg-side p-3 sm:gap-4 sm:p-4 lg:grid-cols-4">
            {STATS.map((s) => (
              <div key={s.label} className="rounded-[1.5rem] bg-side-2 px-5 py-5 sm:px-6 sm:py-6">
                <dt className="sr-only">{s.label}</dt>
                <dd>
                  <span className="tabular block text-3xl font-bold tracking-tight text-primary sm:text-4xl">{s.value}</span>
                  <span className="mt-1 block text-sm text-side-ink sm:text-base">{s.label}</span>
                </dd>
              </div>
            ))}
          </dl>
        </section>

        {/* ---------------------------------------------------------------- features */}
        <section id="features" aria-labelledby="features-title" className="mx-auto max-w-6xl scroll-mt-24 px-4 py-20 sm:px-6 sm:py-28">
          <div className="max-w-2xl">
            <Eyebrow>Features</Eyebrow>
            <h2 id="features-title" className="mt-5 text-3xl leading-tight font-bold tracking-tight text-ink sm:text-[2.75rem]">
              Everything your money needs, in one place
            </h2>
            <p className="mt-4 text-lg text-ink-2">
              A private team of AI advisors that knows your banks, cards, goals and habits, and never anyone else&apos;s.
            </p>
          </div>
          <ul className="mt-12 grid gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-4">
            {FEATURES.map(({ icon: Icon, title, body }, i) => {
              const dark = i === 0 || i === 3;
              return (
                // Phones: icon beside the text, to keep the list short; wider screens: icon on top.
                <li key={title} className={dark
                  ? "flex gap-4 rounded-[2rem] bg-forest p-5 text-forest-ink sm:block sm:p-7"
                  : "flex gap-4 rounded-[2rem] bg-surface p-5 sm:block sm:p-7"}>
                  <span className={dark
                    ? "grid size-11 shrink-0 place-items-center rounded-2xl bg-primary text-primary-ink sm:size-12"
                    : "grid size-11 shrink-0 place-items-center rounded-2xl bg-badge text-forest dark:text-primary sm:size-12"}>
                    <Icon className="size-6" aria-hidden />
                  </span>
                  <div className="min-w-0">
                    <h3 className={dark ? "text-lg font-bold sm:mt-5 sm:text-xl" : "text-lg font-bold text-ink sm:mt-5 sm:text-xl"}>{title}</h3>
                    <p className={dark ? "mt-1.5 leading-relaxed text-forest-muted sm:mt-2" : "mt-1.5 leading-relaxed text-ink-2 sm:mt-2"}>{body}</p>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>

        {/* ---------------------------------------------------------------- chat highlight */}
        <section aria-labelledby="chat-title" className="mx-auto grid max-w-6xl items-center gap-12 px-4 pb-20 sm:px-6 sm:pb-28 lg:grid-cols-2 lg:gap-16">
          <div className="lg:order-2">
            <Eyebrow><MessageCircleMore className="size-4" aria-hidden /> Chat-first</Eyebrow>
            <h2 id="chat-title" className="mt-5 text-3xl leading-tight font-bold tracking-tight text-ink sm:text-[2.75rem]">
              Your money team, one message away
            </h2>
            <p className="mt-4 text-lg leading-relaxed text-ink-2">
              A Finance Assistant leads, with a Savings Coach and a Deals Advisor beside it, and an Investment Advisor if
              you want one. They remember what you tell them, like a raise or a new goal, and adjust every plan.
            </p>
            <ul className="mt-6 space-y-3">
              <Check>Plans each salary around your goals, the way you chose to split it</Check>
              <Check>Spots where spending creeps up and suggests easy wins, without judging</Check>
              <Check>Shows what it&apos;s working on while it thinks, so you&apos;re never left guessing</Check>
            </ul>
          </div>
          <div className="lg:order-1"><ChatMock /></div>
        </section>

        {/* ---------------------------------------------------------------- deals highlight */}
        <section aria-labelledby="deals-title" className="mx-auto grid max-w-6xl items-center gap-12 px-4 pb-20 sm:px-6 sm:pb-28 lg:grid-cols-2 lg:gap-16">
          <div>
            <Eyebrow><BadgePercent className="size-4" aria-hidden /> Deals</Eyebrow>
            <h2 id="deals-title" className="mt-5 text-3xl leading-tight font-bold tracking-tight text-ink sm:text-[2.75rem]">
              Discounts that pay into your goals
            </h2>
            <p className="mt-4 text-lg leading-relaxed text-ink-2">
              Bank and brand offers from across Pakistan, matched to 163 card products from 23 banks and wallets. Pay
              with the right card and the saving is counted for you.
            </p>
            <ul className="mt-6 space-y-3">
              <Check>Only deals your cards qualify for, in your city, on the right day</Check>
              <Check>The places you already visit come first</Check>
              <Check>What you save lands in your goals automatically</Check>
            </ul>
          </div>
          <DealsMock />
        </section>

        {/* ---------------------------------------------------------------- how it works */}
        <section id="how-it-works" aria-labelledby="how-title" className="scroll-mt-24 bg-surface py-20 sm:py-28">
          <div className="mx-auto max-w-6xl px-4 sm:px-6">
            <div className="max-w-2xl">
              <Eyebrow>How it works</Eyebrow>
              <h2 id="how-title" className="mt-5 text-3xl leading-tight font-bold tracking-tight text-ink sm:text-[2.75rem]">
                Up and running in minutes
              </h2>
            </div>
            <ol className="mt-12 grid gap-4 sm:grid-cols-2 sm:gap-5 lg:grid-cols-4">
              {STEPS.map((s, i) => (
                <li key={s.title} className="flex gap-4 rounded-[2rem] bg-bg p-5 sm:block sm:p-7">
                  <span className="tabular grid size-11 shrink-0 place-items-center rounded-full bg-forest text-lg font-bold text-forest-ink sm:size-12">
                    {i + 1}
                  </span>
                  <div className="min-w-0">
                    <h3 className="text-lg font-bold text-ink sm:mt-5 sm:text-xl">{s.title}</h3>
                    <p className="mt-1.5 leading-relaxed text-ink-2 sm:mt-2">{s.body}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* ---------------------------------------------------------------- privacy */}
        <section id="privacy" aria-labelledby="privacy-title" className="scroll-mt-24 px-4 py-20 sm:px-6 sm:py-28">
          <div className="mx-auto max-w-6xl rounded-[2.5rem] bg-forest px-6 py-12 text-forest-ink sm:px-12 sm:py-16">
            <div className="max-w-2xl">
              <Eyebrow tone="dark"><ShieldCheck className="size-4" aria-hidden /> Privacy</Eyebrow>
              <h2 id="privacy-title" className="mt-5 text-3xl leading-tight font-bold tracking-tight sm:text-[2.75rem]">
                Built to keep your money private
              </h2>
              <p className="mt-4 text-lg text-forest-muted">
                Your finances are yours alone: your assistant&apos;s team serves only you, and nothing is shared between
                people.
              </p>
            </div>
            <ul className="mt-10 grid gap-4 sm:grid-cols-2 sm:gap-5">
              {PRIVACY.map(({ icon: Icon, title, body }) => (
                <li key={title} className="flex gap-4 rounded-[1.75rem] bg-forest-2 p-5 sm:p-6">
                  <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-primary text-primary-ink"><Icon className="size-5" aria-hidden /></span>
                  <span>
                    <span className="block text-lg font-bold">{title}</span>
                    <span className="mt-1 block leading-relaxed text-forest-muted">{body}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* ---------------------------------------------------------------- banks */}
        <section aria-labelledby="banks-title" className="mx-auto max-w-6xl px-4 pb-20 text-center sm:px-6 sm:pb-28">
          <h2 id="banks-title" className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">Works with 23 banks and wallets</h2>
          <ul className="mx-auto mt-8 flex max-w-4xl flex-wrap justify-center gap-2.5">
            {BANKS.map((b) => (
              <li key={b} className="rounded-full bg-surface px-4 py-2 text-[15px] font-medium text-ink-2 shadow-sm">{b}</li>
            ))}
          </ul>
        </section>

        {/* ---------------------------------------------------------------- closing call to action */}
        <section aria-labelledby="cta-title" className="px-4 pb-20 sm:px-6 sm:pb-24">
          <div className="relative mx-auto max-w-6xl overflow-hidden rounded-[2.5rem] bg-side px-6 py-14 text-center sm:px-12 sm:py-20">
            <div aria-hidden className="pointer-events-none absolute -top-24 -right-24 size-80 rounded-full bg-primary/25 blur-3xl" />
            <div aria-hidden className="pointer-events-none absolute -bottom-28 -left-20 size-80 rounded-full bg-forest/60 blur-3xl" />
            <div className="relative">
              <span className="mx-auto grid size-16 place-items-center rounded-[30%] bg-primary text-forest">
                <Target className="size-8" aria-hidden />
              </span>
              <h2 id="cta-title" className="mt-6 text-3xl leading-tight font-bold tracking-tight text-forest-ink sm:text-5xl">
                Start saving smarter today
              </h2>
              <p className="mx-auto mt-4 max-w-xl text-lg text-side-ink">
                Set up in a three-minute chat. Your goals will thank you.
              </p>
              <div className="mt-8 flex justify-center"><AuthActions place="band" /></div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6 md:flex-row md:items-start md:justify-between">
          <div className="max-w-md">
            <Logo size={32} nameClassName="text-lg text-ink" />
            <p className="mt-4 text-sm leading-relaxed text-muted">
              Saving is a budgeting and savings assistant, not a bank. Investment insights are educational, generated by
              AI from public data, and not licensed financial advice.
            </p>
          </div>
          <nav aria-label="Footer" className="flex flex-wrap gap-x-6 gap-y-2 text-sm font-medium text-ink-2">
            <a href="#features" className="hover:text-ink">Features</a>
            <a href="#how-it-works" className="hover:text-ink">How it works</a>
            <a href="#privacy" className="hover:text-ink">Privacy</a>
            <Link href="/signin" className="hover:text-ink">Sign in</Link>
            <Link href="/signup" className="hover:text-ink">Sign up</Link>
          </nav>
        </div>
        <p className="pb-8 text-center text-xs text-muted">© {new Date().getFullYear()} Saving</p>
      </footer>
    </div>
  );
}
