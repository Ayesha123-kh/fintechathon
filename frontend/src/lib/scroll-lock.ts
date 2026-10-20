/**
 * Stop the page scrolling under a modal or popup; returns the function that undoes it.
 *
 * The lock goes on <html>, never <body>: with html's overflow-x: clip, a body with overflow: hidden becomes a scroll
 * container of its own, and the sticky sidebar and top bar re-anchor to it and jump to the top of the page. Where the
 * page has a classic scrollbar its space is kept, so nothing shifts sideways when the scrollbar goes.
 */
export function lockPageScroll(): () => void {
  const root = document.documentElement;
  const style = root.style;
  const prev = { overflow: style.overflow, overscroll: style.overscrollBehavior, gutter: style.scrollbarGutter };
  const hasScrollbar = window.innerWidth > root.clientWidth;
  Object.assign(style, { overflow: "hidden", overscrollBehavior: "none", scrollbarGutter: hasScrollbar ? "stable" : prev.gutter });
  return () => {
    Object.assign(style, { overflow: prev.overflow, overscrollBehavior: prev.overscroll, scrollbarGutter: prev.gutter });
  };
}
