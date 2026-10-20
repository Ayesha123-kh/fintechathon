import clsx from "clsx";
import { Mic } from "lucide-react";
import { GroupAvatar, MEMBERS, MemberAvatar, type MemberKey } from "@/components/ChatMembers";
import { ProgressRing } from "@/components/charts";

/*
  Pieces of the app drawn for the landing page, with made-up figures. Each is one image to screen readers
  (role="img" + a description); the parts inside are hidden from them.
*/

function Mine({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex justify-end pl-10">
      <p className="rounded-2xl rounded-br-md bg-forest px-4 py-2.5 text-[15px] leading-relaxed text-forest-ink shadow-sm">{children}</p>
    </div>
  );
}

/** An advisor's message, with their avatar and name colour as in the real chat. */
function Theirs({ who, children }: { who: MemberKey; children: React.ReactNode }) {
  return (
    <div className="flex items-end gap-2 pr-8">
      <MemberAvatar who={who} />
      <div className="min-w-0">
        <p className={clsx("mb-1 px-1 text-xs font-semibold", MEMBERS[who].nameColor)}>{MEMBERS[who].name}</p>
        <div className="rounded-2xl rounded-bl-md bg-surface px-4 py-2.5 text-[15px] leading-relaxed text-ink shadow-sm">{children}</div>
      </div>
    </div>
  );
}

/** Hero: the balance card with a deal win and the month's savings around it. */
export function HeroMock() {
  return (
    <div role="img" className="relative mx-auto w-full max-w-[30rem] pb-28 sm:pb-24"
      aria-label="Example dashboard: a total balance of Rs. 424,951 with 79% saved, Rs. 39,200 saved this month, the Umrah goal at 64%, and the assistant announcing Rs. 520 saved with a KFC deal.">
      <div aria-hidden>
        {/* In the flow above the card, overlapping only its top padding, so the balance and ring stay readable. */}
        <div className="land-rise relative z-10 -mb-5 ml-auto w-[88%] sm:w-[72%]" style={{ animationDelay: "250ms" }}>
          <div className="rounded-3xl bg-surface p-3 shadow-[0_18px_40px_rgb(33_25_19/0.14)]">
            <Theirs who="deals">
              Shabash! 🎉 <b>Rs. 520</b> saved at KFC with your Meezan Visa. It&apos;s in your Umrah goal now.
            </Theirs>
          </div>
        </div>

        <div className="land-rise rounded-[2rem] bg-forest p-6 text-forest-ink shadow-[0_30px_60px_rgb(22_66_60/0.28)] sm:p-7">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[15px] text-forest-muted">Total balance</p>
              <p className="tabular mt-1 text-[2.4rem] leading-none font-bold tracking-tight sm:text-5xl">Rs. 424,951</p>
            </div>
            <ProgressRing value={0.79} size={76} thickness={10} label="79% saved"
              trackClassName="stroke-forest-track" barClassName="stroke-primary">
              <span className="tabular text-lg font-bold">79%</span>
            </ProgressRing>
          </div>
          <div className="mt-6 grid grid-cols-2 gap-3">
            <div className="rounded-2xl bg-forest-2 px-4 py-3">
              <p className="flex items-center gap-2 text-sm text-forest-muted"><span className="size-2.5 rounded-full bg-primary" />Savings</p>
              <p className="tabular mt-1 text-lg font-bold">Rs. 334,215</p>
            </div>
            <div className="rounded-2xl bg-forest-2 px-4 py-3">
              <p className="flex items-center gap-2 text-sm text-forest-muted"><span className="size-2.5 rounded-full border-[1.5px] border-forest-muted" />Spendable</p>
              <p className="tabular mt-1 text-lg font-bold">Rs. 90,736</p>
            </div>
          </div>
        </div>

        <div className="land-rise absolute bottom-0 left-0 z-10 w-[56%] sm:w-[50%]" style={{ animationDelay: "450ms" }}>
          <div className="rounded-[1.75rem] bg-primary p-5 text-primary-ink shadow-[0_18px_40px_rgb(58_18_0/0.18)]">
            <p className="text-sm font-semibold">Saved this month</p>
            <p className="tabular mt-1 text-[1.75rem] leading-tight font-bold tracking-tight">Rs. 39,200</p>
            <p className="mt-0.5 text-sm">Great going!</p>
          </div>
        </div>

        <div className="land-rise absolute right-0 bottom-6 z-10 w-[40%] sm:right-2" style={{ animationDelay: "650ms" }}>
          <div className="flex items-center gap-3 rounded-[1.5rem] bg-surface p-3 shadow-[0_18px_40px_rgb(33_25_19/0.14)]">
            <ProgressRing value={0.64} size={46} thickness={6} label="Umrah goal 64%">
              <span className="tabular text-[11px] font-bold text-ink">64%</span>
            </ProgressRing>
            <span className="min-w-0">
              <span className="block truncate text-sm font-bold text-ink">Umrah</span>
              <span className="block text-xs text-muted">by Feb 2027</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

/** The assistant planning a salary into goals, and a voice note turned into text. */
export function ChatMock() {
  return (
    <div role="img" className="mx-auto w-full max-w-[30rem] overflow-hidden rounded-[2rem] bg-surface shadow-[0_24px_50px_rgb(33_25_19/0.12)]"
      aria-label="Example chat: the person says their salary of Rs. 150,000 arrived and asks how much to save for a car; the assistant splits Rs. 37,500 of savings across the car, Umrah and emergency fund goals.">
      <div aria-hidden>
        <div className="flex items-center gap-3 border-b border-line px-5 py-4">
          <span className="relative">
            <GroupAvatar members={["assistant", "savings", "deals"]} />
            <span className="absolute -right-0.5 -bottom-0.5 size-3.5 rounded-full bg-[#3fb37f] ring-2 ring-surface" />
          </span>
          <div className="min-w-0">
            <p className="text-lg leading-tight font-bold text-ink">Your money team</p>
            <p className="truncate text-sm text-muted">Finance Assistant, Savings Coach, Deals Advisor, You</p>
          </div>
        </div>
        <div className="space-y-3 bg-bg px-4 py-5">
          <Mine>Salary aa gayi, 150k. Car ke liye kitna bachaun?</Mine>
          <Theirs who="assistant">
            <p>Mubarak ho! 🎉 I&apos;ve set aside <b>Rs. 37,500</b> (25%) and split it by deadline:</p>
            <ul className="mt-1.5 list-disc pl-5">
              <li>Car (Honda City): Rs. 18,500</li>
              <li>Umrah with parents: Rs. 12,000</li>
              <li>Emergency fund: Rs. 7,000</li>
            </ul>
          </Theirs>
          <div className="flex justify-end pl-10">
            <p className="flex items-center gap-2 rounded-2xl rounded-br-md bg-forest px-4 py-2.5 text-sm text-forest-ink shadow-sm">
              <Mic className="size-4" /> Voice note <span className="tabular text-forest-muted">0:12 / 0:30</span>
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 border-t border-line px-4 py-3">
          <span className="flex h-11 flex-1 items-center rounded-full border border-line bg-bg px-4 text-[15px] text-muted">Type a message</span>
          <span className="grid size-11 place-items-center rounded-full bg-forest text-forest-ink"><Mic className="size-5" /></span>
        </div>
      </div>
    </div>
  );
}

const DEALS = [
  { badge: "20%", merchant: "KFC", terms: "20% off dine-in on Fridays · with your Meezan Visa Platinum" },
  { badge: "Rs. 400", merchant: "Foodpanda", terms: "Rs. 400 off orders above Rs. 1,500 · any card" },
  { badge: "5%", merchant: "Carrefour", terms: "5% off groceries · with your HBL credit card" },
];

/** Deals matched to the person's cards, and the saving being counted on its own. */
export function DealsMock() {
  return (
    <div role="img" className="relative mx-auto w-full max-w-[30rem] pb-10"
      aria-label="Example deals for your cards: 20% off at KFC with a Meezan Visa Platinum, Rs. 400 off Foodpanda, 5% off at Carrefour with an HBL credit card; then a message that Rs. 520 was saved and moved to the Umrah goal.">
      <div aria-hidden>
        <div className="rounded-[2rem] bg-deal-bg p-5 shadow-[0_24px_50px_rgb(33_25_19/0.10)] sm:p-6">
          <p className="mb-4 text-xl font-bold tracking-tight text-ink">Deals for your cards</p>
          <ul className="space-y-3">
            {DEALS.map((d) => (
              <li key={d.merchant} className="flex items-center gap-3.5 rounded-2xl bg-surface p-3">
                <span className="tabular grid h-12 min-w-[4.75rem] place-items-center rounded-xl bg-deal px-2 text-[15px] font-bold text-white">{d.badge}</span>
                <span className="min-w-0">
                  <span className="block font-semibold text-ink">{d.merchant}</span>
                  <span className="block text-sm leading-snug text-muted">{d.terms}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
        <div className="land-rise absolute -bottom-1 left-4 right-4 sm:left-auto sm:w-[22rem]" style={{ animationDelay: "300ms" }}>
          <p className="rounded-2xl bg-forest px-4 py-3 text-[15px] text-forest-ink shadow-[0_18px_40px_rgb(22_66_60/0.3)]">
            <b>Great, you just saved Rs. 520!</b> 🎉 <span className="text-forest-muted">Moved to your Umrah goal.</span>
          </p>
        </div>
      </div>
    </div>
  );
}
