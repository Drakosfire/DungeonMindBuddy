export function SceneEncounterLauncher({onOpen,disabled=false}:{onOpen:()=>void;disabled?:boolean}){
 return <button className="surface-context-action" type="button" disabled={disabled} onClick={onOpen}>Scene encounter</button>;
}
