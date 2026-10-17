import { useEffect, useRef, useState } from 'react';
import { authenticatedApiFetch } from '../api/liveApi';
import './MediaImageWizard.css';

type Model = { id: string; label: string; formats: string[]; controls: string[] };
export type GeneratedMediaImage = { data_url: string; media_type: string; asset_id: string; state: string; delivery_url?: string | null };
export type MediaRecord = { asset_id: string; state: string; mime_type: string; data_url?: string; delivery_url?: string | null; created_at: string; provenance: { prompt?: string; model?: string; settings?: Record<string, unknown> } };
export type ImageGenerationResult = { images: GeneratedMediaImage[]; model: string; prompt: string; observation?: { latency_ms?: number; cost_usd?: number | null } };
export type ImageGenerationInput = { prompt: string; model: string; width: number; height: number; options: Record<string, string | number> };
export type ImageGenerationPort = {
  capabilities: () => Promise<{ configured: boolean; library_ready: boolean; storage_configured: boolean; models: Model[] }>;
  list: (cursor?: string) => Promise<{ items: MediaRecord[] }>;
  get: (assetId: string) => Promise<MediaRecord>;
  save: (assetId: string) => Promise<MediaRecord>;
  generate: (input: ImageGenerationInput) => Promise<ImageGenerationResult>;
};
async function request(path: string, input?: ImageGenerationInput | Record<string, never>) {
  const { response } = await authenticatedApiFetch(`/api/live/media/images/${path}`, input ? { method: 'POST', body: JSON.stringify(input) } : undefined);
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : body.detail?.message ?? 'Image generation is unavailable.');
  return body;
}
const livePort: ImageGenerationPort = {
  capabilities: () => request('capabilities'), generate: input => request('generate', input),
  list: (cursor = '') => request('library' + cursor), get: id => request(id), save: id => request(id + '/save', {}),
};

/** Surface-independent generator. The host owns placement and any eventual document write. */
export function MediaImageWizard({ onClose, onChoose, port = livePort }: {
  onClose: () => void; onChoose?: (image: GeneratedMediaImage, result: ImageGenerationResult) => void; port?: ImageGenerationPort;
}) {
  const [models, setModels] = useState<Model[]>([]);
  const [configured, setConfigured] = useState(false);
  const [storageConfigured, setStorageConfigured] = useState(false);
  const [libraryReady, setLibraryReady] = useState(false);
  const [library, setLibrary] = useState<MediaRecord[]>([]);
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [libraryBusy, setLibraryBusy] = useState(false);
  const [saving, setSaving] = useState<string | null>(null);
  const saveBusy = useRef(false);
  const [step, setStep] = useState(0);
  const [prompt, setPrompt] = useState('');
  const [modelId, setModelId] = useState('flux-2-pro');
  const [shape, setShape] = useState('1024x1024');
  const [format, setFormat] = useState('png');
  const [quality, setQuality] = useState('high');
  const [background, setBackground] = useState('opaque');
  const [seed, setSeed] = useState('');
  const [pending, setPending] = useState(false);
  const inFlight = useRef(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<ImageGenerationResult | null>(null);
  const model = models.find(item => item.id === modelId);
  useEffect(() => {
    let active = true;
    port.capabilities().then(data => { if (active) { setModels(data.models); setConfigured(data.configured); setStorageConfigured(data.storage_configured); setLibraryReady(data.library_ready); } }).catch(error => { if (active) setError(error.message); });
    return () => { active = false; };
  }, [port]);
  const submit = async () => {
    if (inFlight.current || !model || !configured || !libraryReady || !prompt.trim()) return;
    if (seed && model.controls.includes('seed') && (!/^\d+$/.test(seed) || Number(seed) > 4294967295)) { setError('Seed must be a whole number from 0 to 4294967295.'); return; }
    inFlight.current = true; setPending(true); setError('');
    const [width, height] = shape.split('x').map(Number);
    const options: Record<string, string | number> = { output_format: format };
    if (model.controls.includes('quality')) options.quality = quality;
    if (model.controls.includes('background')) options.background = background;
    if (model.controls.includes('seed') && seed !== '') options.seed = Number(seed);
    try { setResult(await port.generate({ prompt, model: modelId, width, height, options })); setStep(2); }
    catch (error) { setError(error instanceof Error ? error.message : 'Image generation did not complete.'); }
    finally { inFlight.current = false; setPending(false); }
  };
  const openLibrary = async (more = false) => {
    if (libraryBusy) return;
    setLibraryBusy(true); setError(''); setLibraryOpen(true);
    try {
      const last = more ? library[library.length - 1] : null;
      const cursor = last ? `?before_time=${encodeURIComponent(last.created_at)}&before_id=${encodeURIComponent(last.asset_id)}` : '';
      const page = await port.list(cursor);
      setLibrary(old => more ? [...old, ...page.items] : page.items);
    } catch (error) { setError(error instanceof Error ? error.message : 'The image library could not be opened.'); }
    finally { setLibraryBusy(false); }
  };
  const reopen = async (id: string) => {
    setLibraryBusy(true); setError('');
    try {
      const record = await port.get(id);
      const prompt = record.provenance.prompt ?? 'Saved image';
      setPrompt(prompt);
      const savedModel = record.provenance.model ?? 'flux-2-pro';
      if (models.some(model => model.id === savedModel)) setModelId(savedModel);
      const settings = record.provenance.settings;
      if (settings && typeof settings.width === 'number' && typeof settings.height === 'number') setShape(`${settings.width}x${settings.height}`);
      const options = settings?.options as Record<string, unknown> | undefined;
      setFormat(typeof options?.output_format === 'string' ? options.output_format : 'png');
      setQuality(typeof options?.quality === 'string' ? options.quality : 'high');
      setBackground(typeof options?.background === 'string' ? options.background : 'opaque');
      setSeed(typeof options?.seed === 'number' ? String(options.seed) : '');
      setResult({ prompt, model: savedModel, images: [{ asset_id: record.asset_id, media_type: record.mime_type, data_url: record.data_url ?? '', state: record.state, delivery_url: record.delivery_url }] });
      setStep(2); setLibraryOpen(false);
    } catch (error) { setError(error instanceof Error ? error.message : 'This image could not be opened.'); }
    finally { setLibraryBusy(false); }
  };
  const saveImage = async (id: string) => {
    if (saveBusy.current) return;
    saveBusy.current = true; setSaving(id); setError('');
    try {
      const record = await port.save(id);
      setResult(old => old && ({ ...old, images: old.images.map(image => image.asset_id === id ? { ...image, state: record.state, delivery_url: record.delivery_url } : image) }));
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Save could not be confirmed. The original image is retained.');
      try {
        const record = await port.get(id);
        setResult(old => old && ({ ...old, images: old.images.map(image => image.asset_id === id ? { ...image, state: record.state, delivery_url: record.delivery_url } : image) }));
      } catch { /* Leave existing preview intact; don't retry generation or upload. */ }
    } finally { saveBusy.current = false; setSaving(null); }
  };
  return <section className="media-image-wizard" aria-label="Create an image" aria-busy={pending}>
    <header><div><p className="media-image-wizard__eyebrow">IMAGE STUDIO</p><h2>Give your world a picture.</h2></div><button type="button" onClick={onClose} disabled={pending || saving !== null} aria-label="Close image studio">×</button></header>
    <nav aria-label="Image creation steps">{['Describe', 'Model & settings', 'Preview'].map((label, index) => <button type="button" key={label} aria-current={step === index ? 'step' : undefined} disabled={pending || (index === 2 && !result)} onClick={() => { setStep(index); setLibraryOpen(false); }}>{index + 1}. {label}</button>)}</nav>
    <button type="button" disabled={pending || saving !== null || libraryBusy || !libraryReady} onClick={() => openLibrary()}>Image library</button>
    {libraryOpen && <section className="media-image-wizard__library" aria-label="Image library"><h3>Your images</h3>{library.length === 0 && !libraryBusy && <p>No images yet. Generate your first image to begin.</p>}{library.map(record => <button type="button" key={record.asset_id} disabled={libraryBusy} onClick={() => reopen(record.asset_id)}>{record.provenance.prompt?.slice(0, 80) ?? 'Image'} · {record.state === 'ready' ? 'Saved' : 'Not yet on CDN'}</button>)}{library.length > 0 && <button type="button" disabled={libraryBusy} onClick={() => openLibrary(true)}>More images</button>}<button type="button" onClick={() => setLibraryOpen(false)}>Back to studio</button></section>}
    {!libraryReady && models.length > 0 && <p role="status">The media library needs database setup before generation.</p>}
    {error && <p role="alert">{error}</p>}
    {models.length > 0 && !configured && <p role="status">Connect the server’s fal credential to generate images.</p>}
    {!libraryOpen && step === 0 && <><label>What would you like to see?<textarea autoFocus value={prompt} maxLength={16000} rows={7} onChange={e => setPrompt(e.target.value)} placeholder="A weathered fort town at the edge of a vast swamp, warm lanterns reflected in the water…" /></label><p>A map, a portrait, a place—describe what matters to you.</p><button type="button" disabled={!prompt.trim()} onClick={() => setStep(1)}>Choose model & settings →</button></>}
    {!libraryOpen && step === 1 && <div className="media-image-wizard__settings">
      <label>Model<select value={modelId} onChange={e => { setModelId(e.target.value); setFormat('png'); }}>{models.map(item => <option value={item.id} key={item.id}>{item.label}</option>)}</select></label>
      <label>Shape<select value={shape} onChange={e => setShape(e.target.value)}><option value="1024x1024">Square · 1024 × 1024</option><option value="1536x1024">Landscape · 1536 × 1024</option><option value="1024x1536">Portrait · 1024 × 1536</option></select></label>
      <label>Format<select value={format} onChange={e => setFormat(e.target.value)}>{model?.formats.map(value => <option key={value}>{value}</option>)}</select></label>
      {model?.controls.includes('quality') && <label>Quality<select value={quality} onChange={e => setQuality(e.target.value)}>{['low', 'medium', 'high'].map(value => <option key={value}>{value}</option>)}</select></label>}
      {model?.controls.includes('background') && <label>Background<select value={background} onChange={e => setBackground(e.target.value)}>{['opaque', 'transparent', 'auto'].map(value => <option key={value}>{value}</option>)}</select></label>}
      {model?.controls.includes('seed') && <label>Seed (optional)<input inputMode="numeric" value={seed} onChange={e => setSeed(e.target.value)} placeholder="Random" /></label>}
    </div>}
    {!libraryOpen && (step === 1 || step === 2) && <footer><p>Generation uses your fal account. New images are retained privately in your library. Save uploads the artwork to a public CDN; prompts and settings stay private.</p><button type="button" disabled={pending || saving !== null || !configured || !libraryReady || !model || !prompt.trim()} onClick={submit}>{pending ? 'Generating your image…' : result ? 'Generate another image' : 'Generate image'}</button></footer>}
    {pending && <p role="status">Creating your image. You can keep working on your page while this runs.</p>}
    {result && <figure className="media-image-wizard__result" hidden={step !== 2 || libraryOpen}><figcaption>{result.prompt}</figcaption>{result.images.map((image, index) => <div key={index}><img src={image.delivery_url ?? image.data_url} alt={result.prompt} /><div className="media-image-wizard__actions"><a download={`world-image-${index + 1}.${image.media_type.split('/')[1]}`} href={image.data_url}>Download image</a>{image.state === 'ready' ? <span role="status">Saved to CDN</span> : <button type="button" disabled={saving !== null || !storageConfigured} onClick={() => saveImage(image.asset_id)}>{saving === image.asset_id ? 'Saving…' : image.state === 'staged' ? 'Save image' : 'Check Save status'}</button>}{!storageConfigured && image.state !== 'ready' && <span>CDN storage needs configuration; your image is retained.</span>}{onChoose && image.state === 'ready' && <button type="button" onClick={() => onChoose(image, result)}>Use image</button>}</div></div>)}</figure>}
  </section>;
}
