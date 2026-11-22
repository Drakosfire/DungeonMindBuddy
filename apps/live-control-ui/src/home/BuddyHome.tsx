import { useState } from "react";
import { dungeonMindLoginHref, useHostedAuthStatus } from "../auth/HostedAuthGate";
import { interceptPrimaryNavigationClick } from "../chrome/appNavigation";
import { useSelectedWorld, useRetrySelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { WorldSelector } from "../selectedWorld/WorldSelector";
import { worldScopedSurfaceHref } from "../selectedWorld/worldSelectionNavigation";
import millImage from "./mill-at-dusk.webp";
import fontCreditsUrl from "../statblocks/render/statblock-theme/FONT-LICENSE.txt?url&no-inline";
import "./buddyHome.css";

const samples = [
  { name: "Old Mill", kind: "Location", text: "At the edge of the alderwood, a waterwheel turns long after the miller has gone. Narrow stone steps lead down from the riverbank." },
  { name: "Mara Venn", kind: "Character", text: "The miller's apprentice carries a brass key on a red thread. She heard three knocks beneath the floor, but has told no one why she answered." },
  { name: "The sealed door", kind: "Unresolved lead", text: "Fresh scratches mark a door sealed for twenty years. Mara's key fits its lock. Beyond it, the party heard running water — and a voice." },
  { name: "Session recap", kind: "Source", text: "At dusk, the party reached the Old Mill and met Mara Venn. She showed them the sealed door beneath the wheelhouse. They decided to return before dawn." },
] as const;

function Compass() {
  return <svg viewBox="0 0 40 40" width="38" height="38" aria-hidden="true"><circle cx="20" cy="20" r="13" fill="none" stroke="currentColor" strokeWidth="1.3" /><path d="M20 1v8m0 22v8M1 20h8m22 0h8" stroke="currentColor" /><path d="m25 10-3 12-12 8 8-12Z" fill="currentColor" /><circle cx="20" cy="20" r="2" fill="currentColor" /></svg>;
}

export function BuddyHome() {
  const auth = useHostedAuthStatus();
  const world = useSelectedWorld();
  const retryWorld = useRetrySelectedWorld();
  const [sample, setSample] = useState<number | null>(null);
  const signedOut = auth.status === "signed_out";
  return <div className="buddy-home">
    <a className="buddy-home__skip" href="#buddy-home-main">Skip to content</a>
    <header className="buddy-home__masthead">
      <a className="buddy-home__brand" href={worldScopedSurfaceHref("/", world.kind === "managed" ? world.worldId : null)} onClick={interceptPrimaryNavigationClick}><Compass /><span>DungeonMind <span className="buddy-home__brand-buddy">Buddy</span></span></a>
      <nav aria-label="Buddy introduction"><a href="#buddy-about">What is Buddy?</a><a className="buddy-home__back" href="https://www.dungeonmind.net/">← DungeonMind.net</a></nav>
    </header>
    <main id="buddy-home-main" tabIndex={-1}>
      <section className="buddy-home__hero" aria-labelledby="buddy-home-title">
        <div className="buddy-home__invitation">
          <p className="buddy-home__eyebrow">Your campaign companion</p>
          <h1 id="buddy-home-title">Your world,<br />ready for the table.</h1>
          <p className="buddy-home__intro">Keep your campaign sources, session prep, and stories connected.</p>
          <div className="buddy-home__entry">
            {signedOut ? <><a className="buddy-home__primary" href={dungeonMindLoginHref(`${window.location.pathname}${window.location.search}${window.location.hash}`)}>Sign in with DungeonMind <span aria-hidden="true">→</span></a><p>Use your existing DungeonMind account.</p></>
              : world.kind === "managed" ? world.graphStatus === "provisioning"
                ? <><a className="buddy-home__primary" href={worldScopedSurfaceHref("/build", world.worldId)} onClick={interceptPrimaryNavigationClick}>Open in Build <span aria-hidden="true">→</span></a><p>Start with a source in {world.name}. Your graph isn’t ready yet.</p></>
                : <><a className="buddy-home__primary" href={worldScopedSurfaceHref("/graph", world.worldId)} onClick={interceptPrimaryNavigationClick}>Open your World <span aria-hidden="true">→</span></a><p>Continue in {world.name}.</p></>
              : world.kind === "loading" ? <p role="status">Finding your World…</p>
              : world.kind === "error" ? <div role="alert"><p>{world.message}</p><button type="button" onClick={retryWorld}>Retry World selection</button></div>
              : <><p className="buddy-home__choose">Your next story starts with a World.</p><WorldSelector creationPath="/" /><p>Choose or create a World to get started.</p></>}
          </div>
          <a className="buddy-home__explore" href="#buddy-about">Explore the idea <span aria-hidden="true">↓</span></a>
        </div>
        <article className="buddy-home__preview" aria-labelledby="buddy-preview-title">
          <div className="buddy-home__preview-label"><span>Campaign preview</span></div>
          <h2 id="buddy-preview-title">The mill at dusk</h2>
          <img src={millImage} width="1440" height="480" alt="A lamplit watermill beside an autumn river at dusk" fetchPriority="high" />
          <p className="buddy-home__story">A sealed door waits beneath the mill. Someone has been here before.</p>
          <div className="buddy-home__references" aria-label="Explore sample campaign notes">{samples.slice(0, 3).map((item, index) => <button key={item.name} type="button" aria-expanded={sample === index} aria-controls="buddy-sample-note" onClick={() => setSample(sample === index ? null : index)}>{item.name}</button>)}</div>
          <button className="buddy-home__source" type="button" aria-expanded={sample === 3} aria-controls="buddy-sample-note" onClick={() => setSample(sample === 3 ? null : 3)}><span aria-hidden="true">▤</span> From: Session recap</button>
          {sample !== null && <section id="buddy-sample-note" className="buddy-home__sample" aria-label="Sample note" aria-live="polite"><p className="buddy-home__sample-kind">{samples[sample].kind} · Fictional example</p><h3>{samples[sample].name}</h3><p>{samples[sample].text}</p><button type="button" onClick={() => { const previous = sample; setSample(null); const triggers = document.querySelectorAll<HTMLButtonElement>(".buddy-home__references button, .buddy-home__source"); triggers[previous]?.focus(); }}>Close note</button></section>}
          <p className="buddy-home__sample-caption">An original sample, separate from your Worlds.</p>
        </article>
      </section>
      <section id="buddy-about" className="buddy-home__about" aria-labelledby="buddy-about-title">
        <h2 id="buddy-about-title">From your notes to your next session</h2>
        <div className="buddy-home__journey">
          <section><span className="buddy-home__chapter" aria-hidden="true">I</span><div><h3>Build</h3><p>Bring your campaign sources together.</p></div></section>
          <section><span className="buddy-home__chapter" aria-hidden="true">II</span><div><h3>Plan</h3><p>Shape the next session with context.</p></div></section>
          <section><span className="buddy-home__chapter" aria-hidden="true">III</span><div><h3>Play</h3><p>Keep prepared material close at the table.</p></div></section>
        </div>
        <p className="buddy-home__availability">The Buddy journey · Features vary by release and deployment.</p>
        <details className="buddy-home__more"><summary>A little more about Buddy</summary><p>Buddy helps tabletop game masters connect campaign material with session preparation and play. Follow a character back to their source, revisit an unresolved lead, and keep the story's context close. The preview above is fictional; your account's Worlds stay separate.</p><p>Use the compass navigation above to find the surfaces on this deployment. Sign in to choose an existing World; availability depends on the hosted release.</p></details>
      </section>
    </main>
    <footer className="buddy-home__footer"><span>Part of DungeonMind</span><nav aria-label="DungeonMind links"><a href="https://www.dungeonmind.net/">DungeonMind.net <span aria-hidden="true">↗</span></a><a href="#buddy-about">About Buddy</a><a href={fontCreditsUrl}>Font credits</a></nav></footer>
  </div>;
}
