import { useEffect, useState } from "react";

const products = [
  ["Cogent", "Collaborative agents working together.", "https://cogent.tools/"],
  ["All2WIKI", "Turn your sources into agent-ready knowledge.", "https://all2wiki.com/"],
  ["Clone Detector", "Discover phishing sites and website clones.", "https://clonedetector.com/"],
  ["Marvin", "A personal AI assistant with memory you can control.", "https://marvinpda.com/"],
  ["KLAIRE", "AI agents for business negotiations.", "https://klaire.pro/"],
  ["Megaprompting", "Turn simple requests into enhanced prompts.", "https://megaprompting.com/"],
  ["Jev MCP", "Screen spec drift, CI failures and code-rule violations.", "https://github.com/eaisdevelopment/jevmcp"],
  ["Agent Skills", "Reusable skills for AI agents and coding workflows.", "https://github.com/eaisdevelopment/skills"],
  ["MCP Multi-Edit", "Make multiple file edits in one step.", "https://github.com/eaisdevelopment/mcp-multi-edit"],
] as const;

export function ProductPromotion() {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(() => window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  useEffect(() => {
    if (paused) return;
    const timer = window.setInterval(() => { if (!document.hidden) setIndex(i => (i + 1) % products.length); }, 9000);
    return () => window.clearInterval(timer);
  }, [paused]);
  const [name, description, url] = products[index]!;
  return <section className="product-promotion" aria-label="Discover the Essential AI product family">
    <div><p className="panel-code">WORK BETTER WITH</p><h2>{name}</h2><p>{description}</p>
      <a href={url} target="_blank" rel="noopener noreferrer">Explore {name} <span aria-hidden="true">↗</span></a></div>
    <div className="product-promotion-controls"><span>{index + 1} / {products.length}</span>
      <button type="button" aria-label="Previous product" onClick={() => setIndex((index + products.length - 1) % products.length)}>←</button>
      <button type="button" aria-label="Next product" onClick={() => setIndex((index + 1) % products.length)}>→</button>
      <button type="button" onClick={() => setPaused(!paused)}>{paused ? "Play" : "Pause"}</button></div>
  </section>;
}
