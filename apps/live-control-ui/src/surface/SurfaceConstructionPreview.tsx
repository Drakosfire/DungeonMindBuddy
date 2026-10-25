import {useEffect,useMemo,useRef} from 'react';
import type {PhrasingContent} from 'mdast';
import {parseMarkdownAst} from '../tiptap/markdown/parseMarkdownAst';
import './SurfacePageProposal.css';

function text(node:PhrasingContent):string{
  if('children' in node)return node.children.map(child=>text(child as PhrasingContent)).join('');
  return 'value' in node&&typeof node.value==='string'?node.value:'';
}
/** Canonical AST grammar, inert text only; never an editable or savable document. */
export function SurfaceConstructionPreview({markdown,status='building',onVisible}:{markdown:string;status?:'building'|'ready'|'incomplete';onVisible?:()=>void}){
  const tables=useMemo(()=>parseMarkdownAst(markdown).children.filter(node=>node.type==='table'),[markdown]);
  const seen=useRef(false);
  useEffect(()=>{if(tables.length&&!seen.current){seen.current=true;onVisible?.();}},[tables.length,onVisible]);
  if(!tables.length)return null;
  return <section className="surface-construction-preview" aria-label="Table construction" aria-busy={status==='building'}>
    <small role="status">{status==='incomplete'?'Incomplete · check the conversation':status==='ready'?'Ready':'Writing…'}</small>
    {tables.map((table,index)=><table key={index}><thead><tr>{table.children[0]?.children.map((cell,i)=><th key={i}>{cell.children.map(text).join('')}</th>)}</tr></thead>
      <tbody>{table.children.slice(1).map((row,r)=><tr key={r}>{row.children.map((cell,c)=><td key={c}>{cell.children.map(text).join('')}</td>)}</tr>)}</tbody></table>)}
  </section>;
}
