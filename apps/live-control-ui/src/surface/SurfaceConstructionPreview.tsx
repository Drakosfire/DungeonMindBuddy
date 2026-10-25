import {useEffect,useMemo,useRef,type ReactNode} from 'react';
import type {Content} from 'mdast';
import {parseMarkdownAst} from '../tiptap/markdown/parseMarkdownAst';
import './SurfacePageProposal.css';

/** Preview provider text without navigation, asset loads or authoring controls. */
function block(node:Content,key:number):ReactNode {
  const children=()=> 'children' in node ? node.children.map((child,index)=>block(child,index)) : null;
  switch(node.type){
    case 'text': return node.value;
    case 'paragraph': return <p key={key}>{children()}</p>;
    case 'heading': {
      const Tag=node.depth===1?'h1':node.depth===2?'h2':node.depth===3?'h3':node.depth===4?'h4':node.depth===5?'h5':'h6';
      return <Tag key={key}>{children()}</Tag>;
    }
    case 'strong': return <strong key={key}>{children()}</strong>;
    case 'emphasis': return <em key={key}>{children()}</em>;
    case 'delete': return <del key={key}>{children()}</del>;
    case 'inlineCode': return <code key={key}>{node.value}</code>;
    case 'code': return <pre key={key}><code>{node.value}</code></pre>;
    case 'break': return <br key={key}/>;
    case 'thematicBreak': return <hr key={key}/>;
    case 'blockquote': return <blockquote key={key}>{children()}</blockquote>;
    case 'list': return node.ordered ? <ol key={key} start={node.start??undefined}>{children()}</ol> : <ul key={key}>{children()}</ul>;
    case 'listItem': return <li key={key}>{typeof node.checked==='boolean' ? <span aria-label={node.checked?'Checked in preview':'Unchecked in preview'}>{node.checked?'☑':'☐'} </span> : null}{children()}</li>;
    case 'table': return <table key={key}>
      <thead><tr>{node.children[0]?.children.map((cell,index)=><th key={index}>{cell.children.map((child,i)=>block(child,i))}</th>)}</tr></thead>
      <tbody>{node.children.slice(1).map((row,index)=><tr key={index}>{row.children.map((cell,i)=><td key={i}>{cell.children.map((child,c)=>block(child,c))}</td>)}</tr>)}</tbody>
    </table>;
    // Links show their label but cannot navigate. Media and raw HTML stay inert.
    case 'link': case 'linkReference': return <span key={key}>{children()}</span>;
    case 'image': case 'imageReference': return <span key={key}>{node.alt}</span>;
    case 'html': return <span key={key}>{node.value}</span>;
    case 'definition': return null;
    default: return <span key={key}>{children()}</span>;
  }
}

/** Canonical AST grammar, observation only; never an editable or savable document. */
export function SurfaceConstructionPreview({markdown,status='building',onVisible}:{markdown:string;status?:'building'|'ready'|'incomplete';onVisible?:()=>void}){
  const blocks=useMemo(()=>parseMarkdownAst(markdown).children.filter(node=>node.type!=='definition'),[markdown]);
  const seen=useRef(false);
  useEffect(()=>{if(blocks.length&&!seen.current){seen.current=true;onVisible?.();}},[blocks.length,onVisible]);
  if(!blocks.length)return null;
  return <section className="surface-construction-preview" aria-label="Object construction" aria-busy={status==='building'}>
    <small role="status">{status==='incomplete'?'Incomplete · check the conversation':status==='ready'?'Ready':'Writing…'}</small>
    {blocks.map((node,index)=>block(node,index))}
  </section>;
}
