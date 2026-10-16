import clsx from "clsx";

/**
 * Curved cone joining a drop-down panel to the icon it came from (phones). It sits on the panel's top border:
 * the fill hides that stretch of border, and the stroke continues it up both curved sides to the tip.
 * `fill` must match the panel's top area and `stroke` the panel's border colour.
 */
export function DropTail({ className, fill, stroke }: { className?: string; fill: string; stroke: string }) {
  return (
    <svg viewBox="0 0 28 17" width="28" height="17" aria-hidden
      className={clsx("pointer-events-none absolute -top-[15px] z-[1] overflow-visible md:hidden", className)}>
      <path d="M0 17V15C8 15 11 9 13 3Q14 0 15 3C17 9 20 15 28 15V17Z" className={fill} />
      <path d="M-3 16C8 16 11 9 13 3Q14 0 15 3C17 9 20 16 31 16" fill="none" strokeWidth="2" strokeLinecap="round"
        className={stroke} />
    </svg>
  );
}
