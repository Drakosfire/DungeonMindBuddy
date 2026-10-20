import './BuddyContextTrace.css'
import { useId, useState, type ReactNode } from 'react'

export function ResponseEvidenceTabs({ evidence, prompt }: { evidence: ReactNode; prompt: ReactNode }) {
  const [tab, setTab] = useState<'evidence' | 'prompt'>('evidence')
  const id = useId()
  return <section className="buddy-context-trace" aria-label="Response evidence">
    <div role="tablist" aria-label="Response inspection" className="buddy-context-trace__tabs">
      {([['evidence', 'Evidence Trail'], ['prompt', 'The Prompt']] as const).map(([key, label]) =>
        <button key={key} type="button" role="tab" id={`${id}-${key}`} aria-controls={`${id}-panel`}
          aria-selected={tab === key} onClick={() => setTab(key)}>{label}</button>)}
    </div>
    <div role="tabpanel" id={`${id}-panel`} aria-labelledby={`${id}-${tab}`}>
      {tab === 'evidence' ? evidence : prompt}
    </div>
  </section>
}

